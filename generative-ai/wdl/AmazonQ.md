# Creating and Running AWS HealthOmics Workflows

This guide walks through the process of creating, deploying, and running genomics workflows using AWS HealthOmics. It covers the key steps from workflow definition to retrieving results, with examples based on a simple greeting workflow.

## Table of Contents

1. [Understanding AWS HealthOmics](#understanding-aws-healthomics)
2. [Prerequisites](#prerequisites)
3. [Workflow Definition](#workflow-definition)
4. [Parameter Configuration](#parameter-configuration)
5. [Packaging the Workflow](#packaging-the-workflow)
6. [Creating the Workflow in AWS HealthOmics](#creating-the-workflow-in-aws-healthomics)
7. [Workflow Versioning](#workflow-versioning)
8. [Running the Workflow](#running-the-workflow)
9. [Monitoring Workflow Status](#monitoring-workflow-status)
10. [Retrieving Workflow Outputs](#retrieving-workflow-outputs)
11. [Troubleshooting](#troubleshooting)
12. [Best Practices](#best-practices)

## Understanding AWS HealthOmics

AWS HealthOmics is a purpose-built service for storing, processing, and analyzing genomic, transcriptomic, and other omics data. It provides a managed environment for running bioinformatics workflows at scale.

**Key Questions to Ask:**
- What type of omics analysis are you performing?
- What is the expected scale of your data processing needs?
- Do you have existing workflows you want to migrate, or are you building new ones?
- What steps will the workflow perform?

## Prerequisites

Before creating and running HealthOmics workflows, you need:

1. **AWS Account with HealthOmics Access**
2. **IAM Role for HealthOmics**
   - Needs permissions for S3 access, CloudWatch logging, and other AWS services your workflow might use. If S3 input or output locations are encrypted by
   a customer managed KMS key, the role will need access to the key.
3. **S3 Bucket for Outputs**
4. **AWS CLI Configured**

**Example IAM Role Creation:**
```bash
aws iam create-role \
  --role-name HealthOmicsWorkflowRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "omics.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# Attach necessary policies
aws iam attach-role-policy \
  --role-name HealthOmicsWorkflowRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

**CloudWatch Logging Permissions:**
The IAM role for HealthOmics workflows also needs permissions to write logs to CloudWatch. Add the following policy statements to enable run logs and task logs:

```json
{
    "Effect": "Allow",
    "Action": [
        "logs:CreateLogGroup"
    ],
    "Resource": [
        "arn:aws:logs:*:ACCOUNT_ID:log-group:/aws/omics/WorkflowLog:*"
    ]
},
{
    "Effect": "Allow",
    "Action": [
        "logs:DescribeLogStreams",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
    ],
    "Resource": [
        "arn:aws:logs:*:ACCOUNT_ID:log-group:/aws/omics/WorkflowLog:log-stream:*"
    ]
}
```

Replace `ACCOUNT_ID` with your AWS account ID. These permissions allow HealthOmics to create log groups and streams, and to write log events to CloudWatch, which is essential for troubleshooting workflow runs.

**Key Questions to Ask:**
- Do you have an existing IAM role for HealthOmics or need to create one?
- What S3 bucket(s) will you use for workflow inputs?
- What S3 bucket will you use for workflow outputs?
- What AWS region will you be using for HealthOmics? The input and output buckets will need to be in the same region.

## Workflow Definition

AWS HealthOmics supports several workflow languages, including WDL (Workflow Description Language), Nextflow, and CWL (Common Workflow Language). This guide focuses on WDL.

**Example WDL Workflow (main.wdl):**
```wdl
version 1.1

workflow GreetingWorkflow {
    input {
        Array[String] names
        String ubuntu_container = "<ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/dockerhub/library/ubuntu:20.04"
    }

    scatter (name in names) {
        call GenerateGreeting {
            input:
                name = name,
                container = ubuntu_container
        }
    }

    call ConcatenateGreetings {
        input:
            greetings = GenerateGreeting.greeting,
            container = ubuntu_container
    }

    output {
        File final_greetings = ConcatenateGreetings.combined_greetings
    }
}

task GenerateGreeting {
    input {
        String name
        String container
    }

    command <<<
        set -euxo pipefail
        echo "Hello, ~{name}!" > greeting.txt
    >>>

    runtime {
        docker: container
        cpu: 1
        memory: "2 GB"
    }

    output {
        File greeting = "greeting.txt"
    }
}

task ConcatenateGreetings {
    input {
        Array[File] greetings
        String container
    }

    command <<<
        set -euxo pipefail
        cat ~{sep(" ", greetings)} > combined_greetings.txt
    >>>

    runtime {
        container: container
        cpu: 1
        memory: "4 GB"
    }

    output {
        File combined_greetings = "combined_greetings.txt"
    }
}
```

***Notes:***
The runtime stanza of each task requires a `container` directive, a `cpu` directive and a `memory` directive. Containers must come from ECR private repositories
in the same region. If they are not already present you may have to create the repository, pull the container from the original registry, re-tag it for the new
repository and push it. The repository should have permissions allowing the omics principal to pull the container.

**Key Questions to Ask:**
- Which workflow language are you most comfortable with (WDL, Nextflow, CWL)?
- What are the computational requirements for your tasks?
- Will your workflow need to access reference data?
- Do you need to use specific container images for your tasks?

## Parameter Configuration

HealthOmics workflows require two parameter-related files:

1. **Parameter Template** - Defines the structure and requirements of workflow inputs
2. **Parameters File** - Contains the actual values for a specific workflow run

**Example Parameter Template (parameter-template.json):**
```json
{
    "names": {
        "description": "Array of names to generate greetings for",
        "optional": false
    },
    "ubuntu_container": {
        "description": "Ubuntu container image to use",
        "optional": true
    }
}
```

**Example Parameters File (parameters.json):**
```json
{
    "names": ["Alice", "Bob", "Charlie"],
    "ubuntu_container": "123456789012.dkr.ecr.us-east-1.amazonaws.com/dockerhub/library/ubuntu:20.04"
}
```

**Key Questions to Ask:**
- What inputs does your workflow require?
  - If the workflow requires file inputs, ask for S3 URIs or which S3 directory or directories should be searched for appropriate inputs.
- Which inputs should be optional vs. required?
- Do you need to use private container repositories?
- Will you need different parameter sets for different runs?

## Packaging the Workflow

Before uploading to AWS HealthOmics, you need to package your workflow definition files:

**Example Packaging Script (1-package-workflow.sh):**
```bash
#!/bin/bash

# Package the workflow into a zip file
echo "Packaging workflow..."
zip -r definition.zip main.wdl

echo "Workflow packaged as definition.zip"
```

If the workflow imports tasks for subworkflows be sure to include those as well:
```bash
zip -r definition.zip main.wdl tasks/ sub-workflows/
```

**Key Questions to Ask:**
- Do you have additional files that need to be included in the workflow package?
- Are there any dependencies between workflow files?

## Creating the Workflow in AWS HealthOmics

Once packaged, you can create the workflow in AWS HealthOmics:

**Example Workflow Creation Script (2-create-workflow.sh):**
```bash
#!/bin/bash

# Check if the workflow is already packaged
if [ ! -f definition.zip ]; then
  echo "Workflow package not found. Running packaging step first..."
  ./1-package-workflow.sh
fi

# Create the workflow in AWS HealthOmics
echo "Creating workflow in AWS HealthOmics..."
WORKFLOW_ID=$(aws omics create-workflow \
  --definition-zip fileb://definition.zip \
  --name "Greeting Workflow" \
  --description "Generate personalized greetings" \
  --parameter-template file://parameter-template.json \
  --query 'id' \
  --output text)

if [ $? -eq 0 ]; then
  echo "Workflow created successfully with ID: $WORKFLOW_ID"
  echo $WORKFLOW_ID > workflow-id.txt
  echo "Workflow ID saved to workflow-id.txt"
else
  echo "Failed to create workflow"
  exit 1
fi

# Wait for the workflow to become ACTIVE
echo "Waiting for workflow to become ACTIVE..."
STATUS=$(aws omics get-workflow --id $WORKFLOW_ID --query 'status' --output text)
while [ "$STATUS" != "ACTIVE" ]; do
  echo "Current status: $STATUS. Checking again in 5 seconds..."
  sleep 5
  STATUS=$(aws omics get-workflow --id $WORKFLOW_ID --query 'status' --output text)
  
  # Check for failure states
  if [ "$STATUS" == "FAILED" ]; then
    echo "Workflow creation failed. Please check the AWS console for details."
    exit 1
  fi
done

echo "Workflow is now ACTIVE and ready to use."
aws omics get-workflow --id $WORKFLOW_ID
```

**Key Questions to Ask:**
- What naming convention will you use for your workflows?
- Do you need to version your workflows?
- Will you need to share workflows across teams or AWS accounts?

## Workflow Versioning

AWS HealthOmics supports workflow versioning, which allows you to create multiple versions of a workflow while maintaining a logical grouping. Workflow versions are immutable (except for allowed configuration changes that don't impact execution logic) and provide several benefits:

1. **Logical Grouping**: Versions form a logical group of related workflows
2. **Concurrent Execution**: You can run multiple versions of a workflow simultaneously
3. **Simplified Management**: All versions share the same workflow ID and base ARN
4. **Data Provenance**: Each version has a unique ARN for tracking and auditing
5. **Sharing Flexibility**: Workflow owners can update workflows without disrupting subscribers

### Workflow Version Naming

When creating a workflow version, you must provide a unique name that:
- Starts with a letter or number
- Can include upper-case and lower-case letters, numbers, hyphens, periods, and underscores
- Has a maximum length of 64 characters

Examples of version naming schemes:
- Simple sequential: `1`, `2`, `3`
- Semantic versioning: `2.7.0`, `2.7.1`, `2.7.2`

### Creating a Workflow Version

**Example Workflow Version Creation Script:**
```bash
#!/bin/bash

# Check if the workflow is already packaged
if [ ! -f definition.zip ]; then
  echo "Workflow package not found. Running packaging step first..."
  ./1-package-workflow.sh
fi

# Check if workflow ID file exists
if [ ! -f workflow-id.txt ]; then
  echo "Workflow ID not found. Please run the create-workflow script first."
  exit 1
fi

# Read the workflow ID from file
WORKFLOW_ID=$(cat workflow-id.txt)

# Create a new version of the workflow
echo "Creating workflow version in AWS HealthOmics..."
VERSION_NAME="1"

aws omics create-workflow-version \
  --workflow-id $WORKFLOW_ID \
  --version-name $VERSION_NAME \
  --definition-zip fileb://definition.zip \
  --description "Initial stable version" \
  --parameter-template file://parameter-template.json \
  --storage-type STATIC \
  --storage-capacity 1200

if [ $? -eq 0 ]; then
  echo "Workflow version created successfully: $VERSION_NAME"
  echo $VERSION_NAME > workflow-version.txt
  echo "Version name saved to workflow-version.txt"
else
  echo "Failed to create workflow version"
  exit 1
fi

# Wait for the workflow version to become ACTIVE
echo "Waiting for workflow version to become ACTIVE..."
STATUS=$(aws omics get-workflow-version --workflow-id $WORKFLOW_ID --version-name $VERSION_NAME --query 'status' --output text)
while [ "$STATUS" != "ACTIVE" ]; do
  echo "Current status: $STATUS. Checking again in 5 seconds..."
  sleep 5
  STATUS=$(aws omics get-workflow-version --workflow-id $WORKFLOW_ID --version-name $VERSION_NAME --query 'status' --output text)
  
  # Check for failure states
  if [ "$STATUS" == "FAILED" ]; then
    echo "Workflow version creation failed. Please check the AWS console for details."
    exit 1
  fi
done

echo "Workflow version is now ACTIVE and ready to use."
aws omics get-workflow-version --workflow-id $WORKFLOW_ID --version-name $VERSION_NAME
```

### Default Version

After you create one or more versions of a workflow, HealthOmics treats the original workflow as the default version. When starting a run, if you don't specify a version, HealthOmics uses this default version. Important notes about the default version:

- The original workflow always remains the default version
- You can't assign any other version to be the default
- You can't delete a workflow's default version if there are other versions associated with the workflow

### Managing Workflow Versions

**Updating a Workflow Version:**
```bash
aws omics update-workflow-version \
  --workflow-id $WORKFLOW_ID \
  --version-name $VERSION_NAME \
  --storage-type DYNAMIC \
  --description "Updated description"
```

**Deleting a Workflow Version:**
```bash
aws omics delete-workflow-version \
  --workflow-id $WORKFLOW_ID \
  --version-name $VERSION_NAME
```

Note: You cannot delete the default version of a workflow if other versions exist. You must delete all user-defined versions first, then delete the workflow.

### Running a Specific Workflow Version

When starting a workflow run, you can specify which version to use:

```bash
aws omics start-run \
  --workflow-id $WORKFLOW_ID \
  --workflow-version-name $VERSION_NAME \
  --role-arn $OMICS_ROLE \
  --name "Versioned Workflow Run" \
  --output-uri s3://omics-outputs/ \
  --storage-type DYNAMIC \
  --parameters file://parameters.json
```

If you don't specify a workflow version name, HealthOmics uses the default version.

**Key Questions to Ask:**
- How will you name and track your workflow versions?
- Do you need to maintain multiple versions for different environments (dev, test, prod)?
- Will you need to roll back to previous versions if issues are found?
- How will you communicate version changes to workflow users?

## Running the Workflow

After creating the workflow, you can run it with specific parameters:

**Example Run Script (3-run-workflow.sh):**
```bash
#!/bin/bash

# Check if workflow ID file exists
if [ ! -f workflow-id.txt ]; then
  echo "Workflow ID not found. Please run the create-workflow script first."
  exit 1
fi

# Read the workflow ID from file
WORKFLOW_ID=$(cat workflow-id.txt)

# Check if version name is provided
VERSION_OPTION=""
if [ -f workflow-version.txt ]; then
  VERSION_NAME=$(cat workflow-version.txt)
  VERSION_OPTION="--workflow-version-name $VERSION_NAME"
  echo "Using workflow version: $VERSION_NAME"
fi

if [ -z "$OMICS_ROLE" ]; then
  echo "No suitable IAM role found. Please specify a role ARN manually."
  echo "Usage: OMICS_ROLE=<your-role-arn> ./3-run-workflow.sh"
  exit 1
fi

echo "Using role ARN: $OMICS_ROLE"

# Start the workflow run
echo "Starting workflow run..."
RUN_ID=$(aws omics start-run \
  --workflow-id $WORKFLOW_ID \
  $VERSION_OPTION \
  --role-arn $OMICS_ROLE \
  --name "Greeting Workflow Run" \
  --output-uri s3://omics-outputs/ \
  --storage-type DYNAMIC \
  --parameters file://parameters.json \
  --query 'id' \
  --output text)

if [ $? -eq 0 ]; then
  echo "Workflow run started successfully with ID: $RUN_ID"
  echo $RUN_ID > run-id.txt
  echo "Run ID saved to run-id.txt"
else
  echo "Failed to start workflow run"
  exit 1
fi

# Output the run status
echo "Run status..."
aws omics get-run --id $RUN_ID
```

**Key Questions to Ask:**
- What IAM role should the workflow run under?
- Where should workflow outputs be stored?
- Do you need to use STATIC or DYNAMIC storage for your workflow?
- Will you need to run the workflow multiple times with different parameters?

## Using Run Cache for Workflow Development

When developing and iterating on workflows, using a run cache can significantly speed up development cycles by reusing outputs from previously completed tasks. This is especially valuable for workflows with long-running tasks that don't change between iterations.

### How Run Cache Works

1. When you create a run cache, you specify an S3 location to store cached outputs
2. During a workflow run, completed task outputs are exported to this S3 location
3. For subsequent runs, the workflow engine checks if there's a matching cache entry for each task
4. If a match is found, the cached results are used instead of recomputing the task

### Creating a Run Cache

**Example Run Cache Creation:**
```bash
#!/bin/bash

# Create a run cache for workflow development
echo "Creating run cache..."
CACHE_ID=$(aws omics create-run-cache \
  --name "Workflow Development Cache" \
  --description "Cache for workflow development iterations" \
  --cache-s3-location "s3://your-cache-bucket/cache/" \
  --cache-behavior "CACHE_ALWAYS" \
  --query 'id' \
  --output text)

if [ $? -eq 0 ]; then
  echo "Run cache created successfully with ID: $CACHE_ID"
  echo $CACHE_ID > cache-id.txt
  echo "Cache ID saved to cache-id.txt"
else
  echo "Failed to create run cache"
  exit 1
fi
```

### Cache Behavior Options

- **CACHE_ALWAYS**: Task outputs are always written to the cache
- **CACHE_ON_FAILURE**: Outputs from successful tasks are only written to the cache if the run fails

### Updated Run Script with Cache Support

```bash
#!/bin/bash

# Check if workflow ID file exists
if [ ! -f workflow-id.txt ]; then
  echo "Workflow ID not found. Please run the create-workflow script first."
  exit 1
fi

# Read the workflow ID from file
WORKFLOW_ID=$(cat workflow-id.txt)

# Check if version name is provided
VERSION_OPTION=""
if [ -f workflow-version.txt ]; then
  VERSION_NAME=$(cat workflow-version.txt)
  VERSION_OPTION="--workflow-version-name $VERSION_NAME"
  echo "Using workflow version: $VERSION_NAME"
fi

# Check if cache ID file exists and read it
CACHE_OPTION=""
if [ -f cache-id.txt ]; then
  CACHE_ID=$(cat cache-id.txt)
  CACHE_OPTION="--cache-id $CACHE_ID --cache-behavior CACHE_ON_FAILURE"
  echo "Using run cache with ID: $CACHE_ID"
fi

if [ -z "$OMICS_ROLE" ]; then
  echo "No suitable IAM role found. Please specify a role ARN manually."
  echo "Usage: OMICS_ROLE=<your-role-arn> ./3-run-workflow.sh"
  exit 1
fi

echo "Using role ARN: $OMICS_ROLE"

# Start the workflow run
echo "Starting workflow run..."
RUN_ID=$(aws omics start-run \
  --workflow-id $WORKFLOW_ID \
  $VERSION_OPTION \
  --role-arn $OMICS_ROLE \
  --name "Greeting Workflow Run" \
  --output-uri s3://omics-outputs/ \
  --storage-type DYNAMIC \
  --parameters file://parameters.json \
  $CACHE_OPTION \
  --query 'id' \
  --output text)

if [ $? -eq 0 ]; then
  echo "Workflow run started successfully with ID: $RUN_ID"
  echo $RUN_ID > run-id.txt
  echo "Run ID saved to run-id.txt"
else
  echo "Failed to start workflow run"
  exit 1
fi

# Output the run status
echo "Run status..."
aws omics get-run --id $RUN_ID
```

### Best Practices for Run Cache

1. **Declare Intermediate Files as Outputs**: To cache intermediate task files, declare them as task outputs in your workflow definition
2. **Use Consistent Inputs**: Cache matching relies on consistent inputs; changing inputs will result in cache misses
3. **Consider Cache Size**: Monitor the size of your cache S3 location and clean up when necessary
4. **Share Caches Across Workflows**: A single run cache can be used by multiple workflows
5. **Use Cache Selectively**: For production runs, you might want to disable caching or use CACHE_ON_FAILURE

**Key Questions to Ask:**
- Do you need to speed up workflow development iterations?
- Which tasks in your workflow are time-consuming but stable?
- How much storage space will your cached outputs require?
- Should you use different caches for different workflow versions?

## Monitoring Workflow Status

You can monitor the status of your workflow run:

**Example Status Check Script (4-check-run-status.sh):**
```bash
#!/bin/bash

# Check if run ID file exists
if [ ! -f run-id.txt ]; then
  echo "Run ID not found. Please run the run-workflow script first."
  exit 1
fi

# Read the run ID from file
RUN_ID=$(cat run-id.txt)

# Get the run status
echo "Checking status of run $RUN_ID..."
STATUS=$(aws omics get-run --id $RUN_ID --query 'status' --output text)
echo "    $STATUS"

# Summarize the status count for run tasks
echo ""
echo "Summarizing task counts for run $RUN_ID..."
aws omics list-run-tasks --id $RUN_ID --query 'items[*].[status]' --output text | sort | uniq -c
```

**Key Questions to Ask:**
- How frequently do you want to check workflow status?
  - Checks that are more frequent than once per minute are not recommended.
- Do you need to set up notifications for workflow completion or failure?
- Will you need detailed task-level monitoring?

## Retrieving Workflow Outputs

Once the workflow completes, you can retrieve the outputs:

**Example Output Retrieval Script (5-get-run-output.sh):**
```bash
#!/bin/bash

# Check if run ID file exists
if [ ! -f run-id.txt ]; then
  echo "Run ID not found. Please run the run-workflow script first."
  exit 1
fi

# Read the run ID from file
RUN_ID=$(cat run-id.txt)

# Get the run status to check if it's completed
STATUS=$(aws omics get-run --id $RUN_ID --query 'status' --output text)

if [ "$STATUS" != "COMPLETED" ]; then
  echo "Run is not yet completed. Current status: $STATUS"
  echo "Please wait until the run completes before retrieving outputs."
  exit 1
fi

# Create a directory for outputs
mkdir -p outputs

# Get the output uri and concatenate RUN_ID
OUTPUT_URI=$(aws omics get-run --id $RUN_ID --query 'outputUri' --output text)
OUTPUT_URI="$OUTPUT_URI$RUN_ID"
# Get the output file from S3
echo "Retrieving output files from $OUTPUT_URI"
aws s3 cp "$OUTPUT_URI" outputs/"$RUN_ID"/ --recursive
# Link outputs/$RUN_ID as _LATEST
rm -rf outputs/_LATEST
ln -s "$RUN_ID" outputs/_LATEST

echo "Output files saved to the 'outputs' directory"

# Display the content of the greeting file
if [ -f outputs/_LATEST/out/final_greetings/combined_greetings.txt ]; then
  echo ""
  echo "Contents of final_greetings:"
  echo "---------------------------"
  cat outputs/_LATEST/out/final_greetings/combined_greetings.txt
else
  echo "Output file not found. Check the S3 path manually."
fi
```

**Key Questions to Ask:**
- Do you want to download one or more outputs or keep them in S3?
- How will you organize and store workflow outputs?
- Do you need to post-process the outputs?
- Will you need to integrate the outputs with other systems?

## Troubleshooting

Common issues when working with AWS HealthOmics workflows:

1. **Workflow Creation Failures**
   - Check WDL syntax errors
    - If the `miniwdl` python package is installed you should check syntax with `miniwdl check`
   - Verify parameter template format
   - Ensure container images are accessible to the service and in the same region
   - Ensure S3 URIs point to objects accessible to the service and in the same region

2. **Workflow Run Failures**
   - Check IAM role permissions
   - Verify S3 bucket access
   - Examine task and engine-level logs

**Example Troubleshooting Commands:**
```bash
# Get detailed workflow information
aws omics get-workflow --id $WORKFLOW_ID

# Get detailed run information
aws omics get-run --id $RUN_ID

# List and examine task logs
aws omics list-run-tasks --id $RUN_ID
aws omics get-run-task --id $RUN_ID --task-id $TASK_ID

# Check CloudWatch logs (if enabled)
aws logs get-log-events --log-group-name /aws/omics/runs --log-stream-name $RUN_ID
```

**Key Questions to Ask:**
- Have you enabled logging for your workflows?
- Do you have a process for debugging failed workflows?
- Are there specific error patterns you're encountering?

## Best Practices

1. **Workflow Design**
   - Use modular task design
   - Include appropriate error handling
   - Set reasonable resource requirements
   - During workflow development it can be useful to include `echo` or `set -x` statements in the task `command` to provide additional information to the task log

2. **Container Management**
   - Use specific container versions (tags)
   - ECR is required for container storage
   - Test containers locally before using in workflows

3. **Cost Optimization**
   - Use appropriate task `cpu` and `memory`
   - After a run (or runs), consider using the AWS HealthOmicsTools run analyzer to obtain recommendations about refining the `cpu` and `memory` requests
   - Clean up completed workflow data

4. **Security**
   - Use least-privilege IAM roles
   - Encrypt sensitive data

**Key Questions to Ask:**
- What is your workflow development lifecycle?
- How will you manage workflow versions?
- Do you have specific cost or performance requirements?
- What security requirements apply to your genomics data?

## Conclusion

AWS HealthOmics provides a powerful platform for running genomics workflows at scale. By following the steps outlined in this guide, you can create, deploy, and run workflows efficiently while adhering to best practices for performance, cost, and security.

For more information, refer to the [AWS HealthOmics documentation](https://docs.aws.amazon.com/omics/).
