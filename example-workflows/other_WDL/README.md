# AWS HealthOmics WDL Workflows

This folder contains example WDL based workflows.

These are provided AS-IS and are intended to demonstrate conventions, patterns, and best practices for writing workflows for scale. They are intended as starting points that you can customize to fit your specific requirements.

## Step 0: Assumptions and prerequisites
- All steps below assume you are working from your `$HOME` directory on a Linux or macOS system and should take ~1hr to complete.
- Source for the workflows and supporting assets in this example are in `$HOME/amazon-omics-tutorials/example-workflows/gatk-best-practices`
- The [Amazon ECR Helper for AWS HealthOmics](https://github.com/aws-samples/amazon-ecr-helper-for-aws-healthomics) CDK app has been deployed to your account
- The following required software is available on your system
    - [AWS CLI v2](https://aws.amazon.com/cli/)
    - [jq](https://stedolan.github.io/jq/)
    - Python 3.9 or higher
    - Python packages: see `requirements.txt`
    - make

To install Python package requirements use:
```bash
$HOME/amazon-omics-tutorials/example-workflows/_scripts
pip install -r requirements.txt
```

## Step 1: Build container images

Run the following:

```bash
make
make build/sfn-container-builder
```

This will do the following: 
- Initialize `make`
- Check if the Amazon ECR Helper for AWS HealthOmics CDK app has been deployed

  Workflows that run in AWS HealthOmics must have containerized tooling sourced from ECR private image repositories. These workflows use 4 unique container images. The Amazon ECR Helper for AWS HealthOmics is a CDK application that automates building container images from source.

- Copy container image source to a staging location in S3. Note this staging location is defined in `_conf/default.ini` and should match one of the `source_uris` in the [`app-config.json`](https://github.com/aws-samples/amazon-ecr-helper-for-aws-healthomics?tab=readme-ov-file#building-containers) for Amazon ECR Helper for AWS HealthOmics.
- Create a manifest of container images to build
- Execute a Step Functions state machine to process the contaimer image manifest

## Step 2: Testing

Use the steps below to verify execution of these pipelines AWS HealthOmics as needed. Data for these tests are available in the following regions:

- us-east-1
- us-west-2
- eu-west-1
- eu-west-2
- eu-central-1
- ap-southeast-1

By default, workflow runs will use the region that is configured for the `default` profile via the AWS CLI. You can override this by etting the `region` option in `amazon-omics-tutorials/example-workflows/_conf/default.ini`.


To run a specific workflow run the following from root of this example set (e.g. at the same location this README file is):

```bash
make run-{workflow_name}  # substitute "{workflow_name}" accordingly
```

If this is the first time running any workflow, `make` will perform the following build steps: 

1. Create AWS IAM roles and permissions policies required for workflow runs
2. Create an Amazon S3 bucket for staging workflow definition bundles and workflow execution outputs
3. Create a zip bundle for the workflow that is registered with AWS HealthOmics
4. Start an AWS HealthOmics Workflow run for the workflow with test parameters

Additional artifacts produced by the build process will be generated in `build/`.

You can customize the build process by modifying `conf/default.ini`.

## Cleanup
To remove local build assets run:

```bash
make clean
```

**Note**: this command does not delete any deployed AWS resources. You are expected to manage these as needed. Resources of note:

- No cost resources:
    - HealthOmics Workflows do not incur costs when not running

- Resources with costs
    - Amazon ECR Private repositories for container images have a storage cost - see [Amazon ECR pricing](https://aws.amazon.com/ecr/pricing/) for more details
    - Data generated and stored in S3 have a storage cost - see [Amazon S3 pricing](https://aws.amazon.com/s3/pricing/) for more details

## Further reading
Each workflow defintion and any supporting files are in its own folder with the following structure:

```text
workflows
├── {workflow_name}
│   ├── cli-input.yaml
│   ├── (main | named-entrypoint).wdl
│   ├── parameter-template.json
│   ├── test.parameters.json
│   └── ... additional supporting files ...
...
```

### Parameter details

The `parameter-template.json` file for each workflow should match `inputs{}` defined in the `workflow{}` stanza of the main entrypoint WDL.

The `test.parameters.json` file is a subset of the parameters used. Additional parameters:

- `ecr_registry`
- `aws_region`

are added and populated based on the AWS profile used during the build process (when you execute `make run-{workflow-name}`).