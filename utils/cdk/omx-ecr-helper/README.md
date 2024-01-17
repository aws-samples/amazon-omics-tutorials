# Amazon ECR Helper for AWS HealthOmics

This is a simple serverless application that helps automate preparing containers for use with [AWS HealthOmics](https://aws.amazon.com/omics/) Workflows that performs two key functions:

1. `container-puller`: Retrieves container images from public registries like (Amazon ECR Public, Quay.io, DockerHub) and stages them in [Amazon ECR](https://aws.amazon.com/ecr/) Private image repositories in your AWS account
2. `container-builder`: Builds ECR Private container images from source bundles staged in S3

Under the hood, it this application leverages [AWS Step Functions](https://aws.amazon.com/step-functions/), [AWS CodeBuild](https://aws.amazon.com/codebuild/), and Amazon ECR for much of the heavy lifting.

More details and source code for this application can be found at:
https://github.com/aws-samples/amazon-ecr-helper-for-aws-healthomics
