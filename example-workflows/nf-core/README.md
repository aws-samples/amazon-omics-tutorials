# Example Nextflow (NF-Core) workflows for AWS HealthOmics

This folder contains example Nextflow based workflows from NF-Core modified to run on AWS HealthOmics.

These are provided AS-IS and are intended to demonstrate conventions, patterns, and best practices for writing workflows for scale. They are intended as starting points that you can customize to fit your specific requirements.

## Step 0: Assumptions and prerequisites
- All steps below assume you are working from your `$HOME` directory on a Linux or macOS system and should take ~1hr to complete.
- Source for the workflows and supporting assets in this example are in `$HOME/amazon-omics-tutorials/example-workflows/nf-core`
- Source for the `omx-ecr-helper` CDK app is in `$HOME/amazon-omics-tutorials/utils/cdk/omx-ecr-helper`
- The following required software is available on your system
    - [AWS CDK](https://aws.amazon.com/cdk/)
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

## Step 1: Testing

Use the steps below to verify execution of these pipelines AWS HealthOmics as needed. Data for these tests are currently available in the following regions:

- us-east-1
- us-west-2
- eu-west-1
- eu-west-2
- eu-central-1
- ap-southeast-1

By default, workflow runs will use the region that is configured for the `default` profile via the AWS CLI. You can override this by etting the `region` option in `amazon-omics-tutorials/example-workflows/_conf/default.ini`.

To run a specific workflow run the following from root of this example set (e.g. at the same location this README file is):

```bash
make
make run-{workflow_name}  # substitute "{workflow_name}" accordingly
```

If this is the first time running any workflow, `make` will perform the following build steps: 

1. Configure and deploy the `omx-ecr-helper` CDK app

   Workflows that run in AWS HealthOmics must have containerized tooling sourced from ECR private image repositories. Each of these workflows use several (>10) container images. The `omx-ecr-helper` is a CDK application that automates converting container images from public repositories like Quay.io, ECR-Public, and DockerHub to ECR private image repositories.

2. Run a Step functions state machine from `omx-ecr-helper` to pull container images used by these workflows into ECR Private Repositories
3. Create AWS IAM roles and permissions policies required for workflow runs
4. Create an Amazon S3 bucket for staging workflow definition bundles and workflow execution outputs
5. Create a zip bundle for the workflow that is registered with AWS HealthOmics
6. Start an AWS HealthOmics Workflow run for the workflow with test parameters

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
│   ├── (main | named-entrypoint).nf
│   ├── parameter-template.json
│   ├── test.parameters.json
│   └── ... additional supporting files ...
...
```

### Parameter details

The `parameter-template.json` file for each workflow should match required and recommended `params` defined in the main `nextflow.config` file for each workflow.

The `test.parameters.json` file is a subset of the parameters used. Additional parameters:

- `ecr_registry`
- `aws_region`

are added and populated based on the AWS profile used during the build process (when you execute `make run-{workflow-name}`).


### Migration details

Additional details on modifications applied to run each workflow on AWS HealthOmics is available in `AMAZON-OMICS.md` files.