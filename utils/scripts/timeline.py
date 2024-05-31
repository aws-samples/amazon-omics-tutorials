import argparse
import os
import os.path as path
from textwrap import dedent

from bokeh.models import ColumnDataSource, Range1d, Div
from bokeh.layouts import gridplot, column
from bokeh.plotting import figure, output_file, show
from bokeh.resources import CDN
import boto3
import pandas as pd

from compute_pricing import get_pricing


parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("runid", help="HealthOmics workflow run-id to plot")
parser.add_argument("--profile", default=None, help="AWS profile to use")
parser.add_argument("--region", default=None, help="AWS region to use")
parser.add_argument("-u", "--time-units", default="min", choices=['sec', 'min', 'hr', 'day'], help="Time units to use for plot")
parser.add_argument("-o", "--output-dir", default='.', help="Directory to save output files")
parser.add_argument("--no-show", action="store_true", help="Do not show plot")


TIME_SCALE_FACTORS = {
    "sec": 1, "min": 1/60, "hr": 1/3600, "day": 1/86400
}

TASK_COLORS={'COMPLETED': 'cornflowerblue', 'FAILED': 'crimson', 'CANCELLED': 'orange'}

def get_tasks(runid, client=None):
    if not client:
        client = boto3.client('omics')
    
    request = {"id": runid }
    tasks = []
    while True:
        response = client.list_run_tasks(**request)
        next_token = response.get("nextToken")
        tasks += response.get('items')
        if not next_token:
            break
        else:
            request["startingToken"] = next_token
    
    return tasks


def get_task_timings_data(tasks, time_units='min', pricing=None):
    time_scale_factor = TIME_SCALE_FACTORS[time_units]
    tare = min([task['creationTime'] for task in tasks])

    for i, task in enumerate(tasks):
        task['y'] = i
        task['color'] = TASK_COLORS[task['status']]
        
        task['running_left'] = (task['startTime'] - tare).total_seconds() * time_scale_factor
        task['running_right'] = (task['stopTime'] - tare).total_seconds() * time_scale_factor
        task['running_duration'] = task['running_right'] - task['running_left']

        if pricing:
            duration_hr = task['running_duration'] / time_scale_factor / 3600
            usd_per_hour = float(pricing[task['instanceType']]['priceDimensions']['pricePerUnit']['USD'])
            task['cost_usd'] = duration_hr * usd_per_hour

        task['queued_left'] = (task['creationTime'] - tare).total_seconds() * time_scale_factor
        task['queued_right'] = task['running_left']
        task['queued_duration'] = task['queued_right'] - task['queued_left']

        task['memory_to_cpus'] = task['memory'] / task['cpus']
        
        task['label'] = f"({task['taskId']}) {task['name']}"
        task['text_x'] = ((task['stopTime'] - tare).total_seconds() + 30) * time_scale_factor

        tasks[i] = task
    
    return pd.DataFrame.from_records(tasks).sort_values('creationTime')


def plot_timeline(tasks, title="", time_units='min', max_duration_hrs=5, show_plot=True, pricing=None):
    time_scale_factor = TIME_SCALE_FACTORS[time_units]
    if isinstance(tasks, list):
        data = get_task_timings_data(tasks, time_units=time_units, pricing=pricing)
    elif isinstance(tasks, pd.DataFrame):
        data = tasks
    else:
        raise ValueError("tasks must be a list or DataFrame")
    
    source = ColumnDataSource(data)

    tooltips = [
        ("taskId", "@taskId"),
        ("name", "@name"),
        ("cpus", "@cpus"),
        ("memory", "@memory GiB"),
        ("memory/vcpus", "@memory_to_cpus"),
        ("queued", f"@queued_duration {time_units}"),
        ("duration", f"@running_duration {time_units}"),
        ("status", "@status"),
    ]

    if pricing and 'cost_usd' in data.columns:
        tooltips.append(("cost", "@cost_usd USD"))

    p_run = figure(width=960, height=800, sizing_mode="stretch_both", tooltips=tooltips)
    p_run.hbar(y='y', left='queued_left', right='queued_right', height=0.8, color='lightgrey', source=source, legend_label="queued")
    p_run.hbar(y='y', left='running_left', right='running_right', height=0.8, color='color', source=source, legend_label="running")
    #p_run.text(x='text_x', y='y', text='label', alpha=0.4, text_baseline='middle', text_font_size='1.5ex', source=source)
    x_max = max_duration_hrs*3600 * time_scale_factor # max expected workflow duration in hours
    x_min = -(x_max * 0.05)
    p_run.x_range = Range1d(x_min, x_max)
    p_run.y_range.flipped = False
    p_run.xaxis.axis_label = f"task execution time ({time_units})"
    p_run.yaxis.visible = False
    p_run.legend.location = "top_right"
    p_run.title.text = (
        f"tasks: {len(tasks)}, "
        f"wall time: {(data['stopTime'].max() - data['creationTime'].min()).total_seconds() * time_scale_factor:.2f} {time_units}"
    )

    p_cpu = figure(width=160, y_range=p_run.y_range, sizing_mode="stretch_height", tooltips=tooltips)
    p_cpu.hbar(y='y', right='cpus', height=0.8, color="darkgrey", source=source)
    p_cpu.x_range = Range1d(-1, data['cpus'].max())
    p_cpu.xaxis.axis_label = "vcpus"
    p_cpu.yaxis.visible = False
    p_cpu.title.text = f"max cpus: {max(source.data['cpus'])}"
    
    p_mem = figure(width=160, y_range=p_run.y_range, sizing_mode="stretch_height", tooltips=tooltips)
    p_mem.hbar(y='y', right='memory', height=0.8, color="darkgrey", source=source)
    p_mem.x_range = Range1d(-1, data['memory'].max())
    p_mem.xaxis.axis_label = "memory (GiB)"
    p_mem.yaxis.visible = False
    p_mem.title.text = f"max mem: {max(source.data['memory']):.2f} GiB"

    p_mcr = figure(width=160, y_range=p_run.y_range, sizing_mode="stretch_height", tooltips=tooltips)
    p_mcr.hbar(y='y', right='memory_to_cpus', height=0.8, color="darkslateblue", source=source)
    p_mcr.ray(x=[2, 4, 8], y=-1, length=0, angle=90, angle_units="deg", color="darkred")
    p_mcr.x_range = Range1d(-0.01, data['memory_to_cpus'].max())
    p_mcr.xaxis.axis_label = "memory/vcpus"
    p_mcr.yaxis.visible = False
    p_mcr.title.text = f"max mem/vcpus: {max(source.data['memory_to_cpus']):.2f}"

    plots = [p_cpu, p_mem, p_mcr, p_run]

    if pricing and 'cost_usd' in data.columns:
        p_usd = figure(width=160, y_range=p_run.y_range, sizing_mode="stretch_height", tooltips=tooltips)
        p_usd.hbar(y='y', right='cost_usd', height=0.8, color="limegreen", source=source)
        p_usd.x_range = Range1d(-0.01, data['cost_usd'].max())
        p_usd.xaxis.axis_label = "cost ($)"
        p_usd.yaxis.visible = False
        p_usd.title.text = f"tot. task cost: ${sum(source.data['cost_usd']):.2f}"

        plots = [p_usd] + plots

    g = gridplot(plots, ncols=len(plots), toolbar_location="right")
    layout = column(Div(text=f"<strong>{title}</strong>"), g)

    if show_plot:
        show(layout)
    
    return layout


def main(args):
    runid = args.runid

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    omics = session.client('omics')
    pricing = get_pricing(client=omics)
    run = omics.get_run(id=runid)
    tasks = get_tasks(runid, client=omics)

    run_duration_hrs = (run['stopTime'] - run['startTime']).total_seconds() / 3600
    
    output_file_basename = f"{runid}_timeline"
    if not args.output_dir == '.':
        os.makedirs(args.output_dir, exist_ok=True)

    data = get_task_timings_data(tasks)
    data.to_csv(path.join(args.output_dir, f"{output_file_basename}.csv"), index=False)

    output_file(filename=path.join(args.output_dir, f"{output_file_basename}.html"), title=runid, mode="cdn")
    title = f"arn: {run['arn']}, name: {run.get('name')}"
    g = plot_timeline(tasks, title=title, time_units=args.time_units, max_duration_hrs=run_duration_hrs, show_plot=(not args.no_show), pricing=pricing)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args)