# AWS HealthOmics WDL Workflows

This folder contains example WDL based workflows.

These are provided AS-IS and are intended to demonstrate conventions, patterns, and best practices for writing workflows for scale. They are intended as starting points that you can customize to fit your specific requirements.

## Step 0: Assumptions and prerequisites
- All steps below assume you are working from your `$HOME` directory on a Linux or macOS system and should take ~1hr to complete.
- Source for the workflows and supporting assets in this example are in `$HOME/amazon-omics-tutorials/example-workflows/protein-folding`
- Source for the `omx-ecr-helper` CDK app is in `$HOME/amazon-omics-tutorials/utils/cdk/omx-ecr-helper`
- The following required software is available on your system
    - [AWS CDK](https://aws.amazon.com/cdk/)
    - [AWS CLI v2](https://aws.amazon.com/cli/)
    - [jq](https://stedolan.github.io/jq/)
    - Python 3.9 or higher
    - Python packages: see `requirements.txt`
    - make
    - CDK should be bootstrapped to your account and region. See https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html

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
- Configure and deploy the `omx-ecr-helper` CDK app

  Workflows that run in AWS HealthOmics must have containerized tooling sourced from ECR private image repositories. These workflows use 4 unique container images. The `omx-ecr-helper` is a CDK application that automates building container images from source.

- Copy container image source to a staging location in S3
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
    - The `omx-ecr-helper` CDK app is serverless and does not incur costs when idle.
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


### Manually configuring and running `omx-ecr-helper`'s `container-builder`

If you want, you can run the `container-builder` state machine in `omx-ecr-helper` manually. To do this use the following steps:

1. Create a staging bucket for container image source

```bash
aws s3 mb s3://my-staging-bucket
```

2. Sync container source

```bash
cd ~/protein-folding
aws s3 sync ./containers s3://my-staging-bucket/containers
```

3. Create a `container_build_manifest.json` with contents like the following:

```json
{
    "manifest": [
        {
            "source_uri": "{{staging_uri}}/containers/hisat-genotype",
            "target_image": "hisat-genotype:latest"
        }
    ]
}
```

4. Create an `app-config.json` for `omx-ecr-helper` with contents like the following:

```json
{
    "container_builder": {
        "source_uris": [
            "s3://my-staging-bucket/containers/"
        ]
    }
}

```

5. Execute the following to build container images

```bash
aws stepfunctions start-execution \
    --state-machine-arn arn:aws:states:<aws-region>:<aws-account-id>:stateMachine:omx-container-builder \
    --input file://container_build_manifest.json
```
