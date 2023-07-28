import argparse
import os


from builder import Builder

SCRIPT_PATH = os.path.realpath(__file__)
ASSETS_DIR = os.path.join(os.path.dirname(SCRIPT_PATH), 'assets')

parser = argparse.ArgumentParser()
parser.add_argument(
    '-c', '--config-file', type=str, help="path to config file to use",
    default='conf/default.ini')
parser.add_argument(
    '-a', '--assets-dir', type=str, help="",
    default=ASSETS_DIR)

subparsers = parser.add_subparsers(dest='subcommand')

parser_config = subparsers.add_parser('config')

parser_s3 = subparsers.add_parser('s3')
parser_iam = subparsers.add_parser('iam')

parser_sfn = subparsers.add_parser('sfn')
parser_sfn.add_argument(
    'manifest_file', type=str, help='path to JSON manifest to process')
parser_sfn.add_argument(
    '-n', '--name', type=str, help="name to append to build asset")
parser_sfn.add_argument(
    '-t', '--machine-type', type=str, help="type of build either 'container-puller' (default) or 'container-builder'",
    default='container-puller')

parser_workflow = subparsers.add_parser('workflow')
parser_workflow.add_argument(
    'workflow_name', type=str, help="name of workflow to register")

parser_samplesheet = subparsers.add_parser('samplesheet')
parser_samplesheet.add_argument(
    'workflow_name', type=str, help="name of workflow samplesheet is used with")

parser_run = subparsers.add_parser('run')
parser_run.add_argument(
    'workflow_name', type=str, help="name of workflow to run")


def main(args):
    kwargs = vars(args)
    config_file = kwargs.pop('config_file')
    assets_dir = kwargs.pop('assets_dir')
    subcommand = kwargs.pop('subcommand')

    builder = Builder(config_file=config_file, assets_dir=assets_dir)
    getattr(builder, f'build_{subcommand}')(**kwargs)

if __name__ == "__main__":
    args = parser.parse_args()
    main(args)