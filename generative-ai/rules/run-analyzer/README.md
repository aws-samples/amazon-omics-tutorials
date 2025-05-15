# HealthOmics Run Analyzer

This tool provides a convenient wrapper for the HealthOmics run analyzer utility, allowing you to analyze one or more HealthOmics workflow runs with configurable resource headroom settings.

## Prerequisites

- Python virtual environment with the HealthOmics CLI tools installed
- The virtual environment should be in a `venv` directory in the same location as this script

## Usage

```bash
./run_analyzer.sh <run-id1> [run-id2 run-id3 ...] [--headroom <value>]
```

### Parameters

- `<run-id>`: One or more HealthOmics run IDs (at least one required)
- `--headroom <value>`: Optional positive float between 0.0 and 1.0 (default: 0.1). A value of 0.1 or 0.2 is usually reasonable unless you expect to use much larger inputs for your workflows in the future.
  - This value represents the resource headroom factor for the analysis

### Examples

Analyze a single run with default headroom (0.1):
```bash
./run_analyzer.sh 123456
```

Analyze multiple runs with default headroom:
```bash
./run_analyzer.sh 123456 223456 323456
```

Analyze a single run with custom headroom:
```bash
./run_analyzer.sh 123456 --headroom 0.2
```

Analyze multiple runs with custom headroom:
```bash
./run_analyzer.sh 123456 123457 --headroom 0.2
```

The `--headroom` parameter can be placed anywhere in the command:
```bash
./run_analyzer.sh --headroom 0.2 123456 123457
```

## How It Works

The script:
1. Validates that at least one run ID is provided
2. Validates that the headroom value (if specified) is between 0.0 and 1.0
3. Calls the underlying Python module with the appropriate parameters
4. Displays the command being executed for transparency

## Error Handling

The script will exit with an error message if:
- No run IDs are provided
- The headroom value is not a valid float between 0.0 and 1.0
- The `--headroom` flag is used without a value

## Underlying Command

The script builds and executes a command in this format:
```bash
venv/bin/python -m omics.cli.run_analyzer -b <run-id1> [run-id2 ...] --headroom <value>
```

## Understanding the output

The run analyzer analyzes one or more runs and computes aggregate statics. These statics are reported in CSV format:

- "type": The type of row (currently always task),
- "name": The base name of the task with any scatter suffix removed
- "count": The number of times the named task has been observed in the runs
- "meanRunningSeconds": The average runtime in seconds for the named tasks
- "maximumRunningSeconds": The longest runtime in seconds for the named task
- "stdDevRunningSeconds": The standard deviation of runtimes for the named task
- "maximumCpuUtilizationRatio": The highest CPU utilization ratio seen for any of the named tasks
- "meanCpuUtilizationRation": The average CPU utilization ratio for the named task
- "maximumMemoryUtilizationRatio": The highest memory utilization ratio seen for any of the named tasks
- "meanMemoryUtilizationRation": The average memory utilization ratio for the named task
- "maximumGpusReserved": The largest number of GPUs reserved for the named tasks
- "meanGpusReserved": The average number of GPUs reserved for the named task
- "recommendedCpus": The recommended number of CPUs that would accommodate all observed instances of the named task (including any headroom factor)
- "recommendedMemoryGiB": The recommended GiBs of memory that would accommodate all observed instances of the named task (including any headroom factor)
- "recommendOmicsInstanceType": The recommended omics instance type that would accomodate all observed instances of the named task
- "maximumEstimatedUSD": The largest estimated cost observed for the named task.
- "meanEstimatedUSD": The average estimated cost observed for the named task.

Using these statistics you can identify long running and resource hungry workflow tasks. You can also identify tasks that are requesting too many
resources and use the recommendedCPUs and recommendedMemoryGiB statistics to update the relevant tasks in the workflow definition.
