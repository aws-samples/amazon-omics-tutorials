# Utility scripts for Amazon Omics

These are scripts that support using Amazon Omics

## [inspect_nf](./inspect_nf.py)

Python script that inspects a Nextflow workflow definition and generates resources to help migrate it to run on Amazon Omics.

Specifically designed to handle NF-Core based workflows, but in theory could handle any Nextflow workflow definition.

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

**Note:** Cost calculation for workflows that leverage GPUs will be a lower estimate. The instance matching cannot distinguish between tasks that use NVIDIA Tesla T4 vs NVIDIA A10G accelerators and will default to the lowest cost option.

What it does:
- retrieves regional Amazon Omics pricing using the [AWS Price List bulk API](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-ppslong.html)
- retrieves workflow details from Amazon Omics
- matches run task resources (e.g. CPU and Memory) to `omics.*` instances via pricing SKUs

Usage:

```text
usage: compute_pricing.py [-h] [--profile PROFILE] [--region REGION] [--offering OFFERING] run_id

positional arguments:
  run_id               Omics workflow run-id to analyze

optional arguments:
  -h, --help           show this help message and exit
  --profile PROFILE    AWS profile to use
  --region REGION      AWS region to use
  --offering OFFERING  path to pricing offer JSON
```
