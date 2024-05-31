# Utility scripts for AWS HealthOmics

These are scripts that support using AWS HealthOmics

## [inspect_nf](./inspect_nf.py)

Python script that inspects a Nextflow workflow definition and generates resources to help migrate it to run on AWS HealthOmics.

Specifically designed to handle NF-Core based workflows, but in theory could handle any Nextflow workflow definition.

Prerequisites:
- Python 3

What it does:
- look through all *.nf files
- find `container` directives
- extract container uris to:
  - build an image uri manifest
  - create a custom nextflow.config file

Usage:

```text
usage: inspect_nf.py [-h] [-s CONTAINER_SUBSTITUTIONS] [-n NAMESPACE_CONFIG] [--output-manifest-file OUTPUT_MANIFEST_FILE] [--output-config-file OUTPUT_CONFIG_FILE]
                     [--region REGION] [--profile PROFILE]
                     project

positional arguments:
  project               Top level directory of Nextflow workflow project

optional arguments:
  -h, --help            show this help message and exit
  -s CONTAINER_SUBSTITUTIONS, --container-substitutions CONTAINER_SUBSTITUTIONS
                        JSON file of container image substitutions.
  -n NAMESPACE_CONFIG, --namespace-config NAMESPACE_CONFIG
                        JSON file with public registry to ecr repository namespace mappings. This should be the same as what is used by omx-ecr-helper.
  --output-manifest-file OUTPUT_MANIFEST_FILE
                        Filename to use for generated container image manifest
  --output-config-file OUTPUT_CONFIG_FILE
                        Filename to use for generated nextflow config file
  --region REGION       AWS region name
  --profile PROFILE     AWS CLI profile to use. (See `aws configure help` for more info)
```

## [compute_pricing.py](./compute_pricing.py)

Python script that computes the cost of a workflow run breaking out details for individual tasks and run storage.

Prerequisites:
- Python 3
- Python packages
  - boto3
  - requests

What it does:
- retrieves regional AWS HealthOmics pricing using the [AWS Price List bulk API](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-ppslong.html)
- retrieves workflow run details from AWS HealthOmics
- matches reported run task `omics.*` instance types to pricing SKUs
- prints a JSON summary of the run's costs

Usage:

```text
usage: compute_pricing.py [-h] [--profile PROFILE] [--region REGION] [--offering OFFERING] run_id

positional arguments:
  run_id               HealthOmics workflow run-id to analyze

optional arguments:
  -h, --help           show this help message and exit
  --profile PROFILE    AWS profile to use
  --region REGION      AWS region to use
  --offering OFFERING  path to pricing offer JSON
```


## [timeline.py](./timeline.py)

Python script that generates a timeline plot of a workflow run

Prerequisites:
- Python 3
- Python packages
  - boto3
  - bokeh == 2.4.3
  - pandas
  - requests
- Other scripts
  - compute_pricing.py

What it does:
- retrieves workflow run details from AWS HealthOmics
- creates a csv file with task details
- creates an html document with an interactive Bokeh plot that shows task timing with instance cpu and memory allocated per task

Usage:
```text
usage: timeline.py [-h] [--profile PROFILE] [--region REGION] [-u {sec,min,hr,day}] [-o OUTPUT_DIR] [--no-show] runid

positional arguments:
  runid                 HealthOmics workflow run-id to plot

optional arguments:
  -h, --help            show this help message and exit
  --profile PROFILE     AWS profile to use (default: None)
  --region REGION       AWS region to use (default: None)
  -u {sec,min,hr,day}, --time-units {sec,min,hr,day}
                        Time units to use for plot (default: min)
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Directory to save output files (default: .)
  --no-show             Do not show plot (default: False)
```