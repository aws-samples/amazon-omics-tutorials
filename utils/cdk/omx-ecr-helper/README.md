# HealthOmics ECR Helper

This is a simple serverless application that helps automate preparing containers for use with [AWS HealthOmics](https://aws.amazon.com/omics/) Workflows that performs two key functions:

1. `container-puller`: Retrieves container images from public registries like (Amazon ECR Public, Quay.io, DockerHub) and stages them in [Amazon ECR](https://aws.amazon.com/ecr/) Private image repositories in your AWS account
2. `container-builder`: Builds ECR Private container images from source bundles staged in S3

Under the hood, it this application leverages [AWS Step Functions](https://aws.amazon.com/step-functions/), [AWS CodeBuild](https://aws.amazon.com/codebuild/), and Amazon ECR for much of the heavy lifting.

## Requirements

* The following software is required in your environment
  * [AWS CDK](https://aws.amazon.com/cdk/)
  * [AWS CLI v2](https://aws.amazon.com/cli/)

## Usage

Deploy the [AWS CloudFormation](https://aws.amazon.com/cloudformation/) stacks used by the application in each region you intend to run AWS HealthOmics Workflows using the following:

> **_NOTE:_**  
> Ensure you are in the same directory where this file is located

```bash
# install package dependencies
npm install

# in your default region (specify profile if other than 'default')
cdk deploy --all --profile <aws-profile>

```

### Retriving public containers

Create a `container_image_manifest.json` file with contents like:

```json
{
    "manifest": [
        "ubuntu:20.04",
      	"us.gcr.io/broad-gatk/gatk:4.4.0.0",
      	"ghcr.io/miniwdl-ext/miniwdl-aws:v0.9.0-1-g243f36f",
        "quay.io/biocontainers/bcftools:1.16--hfe4b78e_1",
        "public.ecr.aws/docker/library/python:3.9.16-bullseye",
        "quay/biocontainers/bwa-mem2:2.2.1--he513fc3_0",
      	"ecr-public/aws-genomics/google/deepvariant:1.4.0"
    ]
}
```

Execute the following to pull this list of container images into your ECR private registry:

```bash
aws stepfunctions start-execution \
    --state-machine-arn arn:aws:states:<aws-region>:<aws-account-id>:stateMachine:omx-container-puller \
    --input file://container_image_manifest.json
```

The state-machine will pull source image uris into your private ECR registry according to the following rules:

* Images are privatized into repositories with namespaces that correspond to their original source public registry - e.g. a full repository name is of the format `<namespace>/<image-name>` and a full private image uri will be of the form `<aws-account-id>.dkr.ecr.<aws-region>.amazonaws.com/<namespace>/<image-name>:<image-tag>`

* Images from Quay.io or ECR Public (public.ecr.aws) use ECR pull through caching
    * An image from Quay.io will be pulled into a repository with the `quay/` namespace
    * An images from public.ecr.aws will be pulled into a repository with the 'ecr-public/` namespace

* Images from other known public registries are pulled and pushed into a custom created ECR private repository using a CodeBuild project
    * An image from Google Container Registry (gcr.io) will be pulled into a repository with the `gcr/` namespace
    * An image from Google Artifact Registry (pkg.dev) will be pulled into a repository with the `gar/` namespace
    * An image from Github Container Registry (ghcr.io) will be pulled into a repository with the `ghcr/` namespace
    * An image from Microsoft Container Registry (mcr.microsoft.com) will be pulled into a repository with the `mcr/` namespace
    * An image from DockerHub will be pulled into a repository with the `dockerhub/` namespace 

* Images from other (less common) public registries are not supported at this time

### Building containers

Create a config file at the root level of this application called `app-config.json` with contents like:

```json
{
    "container_builder": {
        "source_uris": [
            "s3://my-bucket-1",
            "s3://my-bucket-2/path/to/source"
        ]
    }
}
```

The `source_uris` list specifies S3 locations where source for container images (e.g. `Dockerfiles` and accompanying assets) have been staged. You **must** create these locations beforehand.

(Re)deploy the application using:

```bash
cdk deploy --all
```

Sync container image source to the location(s) you specified above. These can either be bare source:

```bash
aws s3 sync ./path/to/container-source/image-foo s3://my-bucket-1/container-source/image-foo
```

or zip bundles:

```bash
(cd ./path/to/container-source/image-bar && zip -r ../image-bar.zip .)
aws s3 cp ./path/to/container-source/image-bar.zip s3://my-bucket/container-source/image-bar.zip
```

Create a `container_build_manifest.json` with contents like the following:

```json
{
    "manifest": [
        {
            "source_uri": "s3://my-bucket/container-source/image-foo/",
            "target_image": "foo:omics"
        },
        {
            "source_uri": "s3://my-bucket/container-source/image-bar.zip",
            "target_image": "bar:omics"
        }
    ]
}
```

Execute the following to build this list of container images and place them in your ECR private registry:

```bash
aws stepfunctions start-execution \
    --state-machine-arn arn:aws:states:<aws-region>:<aws-account-id>:stateMachine:omx-container-builder \
    --input file://container_build_manifest.json
```

The state-machine will retrieve the source bundles and build images using the available `Dockerfile` in each. Images are built and pushed to ECR private repositories that match the `target_image` values in the input manifest. Full private image uris will be of the form `<aws-account-id>.dkr.ecr.<aws-region>.amazonaws.com/<target_image>`. If you need images to have specific namespaces you can include them in the `target_image` - e.g. `mynamespace/foo:omics`.


### Configure and run workflow

After processing the manifests above, configure your workflow to use images from your ECR Private Registry:

```js
// how this is defined depends on the workflow lanugage used, but is effectively something like:
// configure list of containers
ecr_registry = "aws-account-id>.dkr.ecr.<aws-region>.amazonaws.com"
containers = {
    "task1": ecr_registry + "/dockerhub/ubuntu:20.04",
    "task2": ecr_registry + "/gcr/broad-gatk/gatk:4.4.0.0",
    "task3": ecr_registry + "/ghcr/miniwdl-ext/miniwdl-aws:v0.9.0-1-g243f36f",
    "task4": ecr_registry + "/quay/biocontainers/bcftools:1.16--hfe4b78e_1",
    "task5": ecr_registry + "/ecr-public/docker/library/python:3.9.16-bullseye",
    "task6": ecr_registry + "/quay/biocontainers/bwa-mem2:2.2.1--he513fc3_0",
    "task7": ecr_registry + "/ecr-public/aws-genomics/google/deepvariant:1.4.0",
    "task8": ecr_registry + "/foo:omics",
    "task9": ecr_registry + "/bar:omics"

}

// use containers[task_name] in task definitions
task task1 {
    runtime {
        container: containers['task1']
    }

    ...
}
```

Then create and run your workflow using AWS HealthOmics.


## How it works

### Retrieving container images

The `container-puller` stack automates "privatizing" container images - re-staging them from public registries to an ECR Private registry.

To do this, it first relies on ECR Pull-through caching which:
* allows docker clients to pull an image URI that looks like it comes from ECR Private
* creates a private image repository based on the public image that is being pulled
* pulls the public image and caches it in the private repository

Second, an EventBridge rule is used to detect when an image repository is created.

Third, the EventBridge rule triggers a Lambda function that applies the required access policy to the ECR repository that was created. This policy looks like:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "omics workflow access",
            "Effect": "Allow",
            "Principal": {"Service": "omics.amazonaws.com"},
            "Action": [
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:BatchCheckLayerAvailability"
            ]
        }
    ]
}
```

Currently, AWS HealthOmics checks for the existence of ECR image repositories and specific image URIs before launching ECS tasks. This pre-check means you need to "prime" container images into ECR Private prior to a running a workflow that depends on them the first time, even if pull-through caching is enabled.

The priming process is automated by submitting a container image manifest to a StepFunctions state machine that calls a CodeBuild Project that retrieves container image URIs.

The mechanisms above are also generalized to support other public container registries in the following ways:

* The ECR CreateRepository API is called when a corresponding repository does not exist. This is only used when retriving images from public registries that do not support pull-through caching.
* `AwsApiCall` events that create ECR repositories with the tag `Key=createdBy,Value=omx-ecr-helper` will also trigger the Lambda Function.
* The CodeBuild project is parameterized to do either pull-through only or pull and push actions

To save costs the workflow will only run the CodeBuild project if a requested image uri does not already have a corresponding private ECR image.

### Building container images

The `container-builder` stack automates building container images using AWS Step Functions and AWS CodeBuild. An ECR private repository is created as needed for the image. It also utilizes the same EventBridge rule, trigger, and Lambda above to add required ECR repository policies.

**Note**: There are no capabilities at this time to check if the image source has changed such that it would result in an updated image relative to an existing one in ECR Private. Therefore. CodeBuild project builds in this stack will always execute when processing a manifest. As a result, if images already exist in ECR Private they will be overwritten.

## Development

The `cdk.json` file tells the CDK Toolkit how to execute your app.

### Useful commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `cdk deploy`      deploy this stack to your default AWS account/region
* `cdk diff`        compare deployed stack with current state
* `cdk synth`       emits the synthesized CloudFormation template
