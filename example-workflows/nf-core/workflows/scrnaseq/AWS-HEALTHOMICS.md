# Migrating to AWS HealthOmics Workflows

The following are the **MINIMAL** steps needed to migrate and test the Nextflow [nf-core/scrnaseq v2.1.0](https://github.com/nf-core/scrnaseq/tree/2.1.0) workflow (the version of the pipeline in this repo) to run on AWS HealthOmics Workflows while retaining as much in-built Nextflow and NF-core functionality as possible. Successful execution of the workflow (with 14 underlying tasks) was verified in `us-west-2` using documented test data.

## Step 0: Assumptions and prerequisites

* All steps below assume you are working from your `$HOME` directory on a Linux or macOS system and should take ~1hr to complete.
* Source for this workflow is in `$HOME/nf-core-scrnaseq`
* Source for the `omx-ecr-helper` CDK app is in `$HOME/omx-ecr-helper`
* The following required software is available on your system
  * [AWS CDK](https://aws.amazon.com/cdk/)
  * [AWS CLI v2](https://aws.amazon.com/cli/)
  * [jq](https://stedolan.github.io/jq/)


## Step 1: Privatize container images

### Create a public registry namespace config file

A copy of the `public_registry_properties.json` [file](../../../../utils/cdk/omx-ecr-helper/lib/lambda/parse-image-uri/public_registry_properties.json) from the `omx-ecr-helper` CDK app was used.

### Run `inspect_nf.py` on the workflow project

The `inspect_nf.py` script is a utility that inspects a Nextflow workflow definition that uses NF-Core conventions and generates the following:

- A file called `container_image_manifest.json` that lists all the container image URIs used by the workflow
- A supplemental config file for Nextflow called `conf/omics.config`

The commands to do the above look like:

```bash
cd /path/to/workflow
python3 ~/amazon-omics-tutorials/utils/scripts/inspect_nf.py
    -n /path/to/public_registry_properties.json \
    --output-config-file conf/omics.config \
    .
```

### Deploy the `omx-ecr-helper` CDK app

Workflows that run in AWS HealthOmics must have containerized tooling sourced from ECR private image repositories. This workflow uses 14 unique container images. The `omx-ecr-helper` is a CDK application that automates converting container images from public repositories like Quay.io, ECR-Public, and DockerHub to ECR private image repositories.

```
cd ~/amazon-omics-tutorials/utils/cdk/omx-ecr-helper
cdk deploy --all
```

### Process the container image manifest with the omx-ecr-helper app

```bash
cd /path/to/workflow
aws stepfunctions start-execution \
    --state-machine-arn arn:aws:states:<aws-region>:<aws-account-id>:stateMachine:omx-container-puller \
    --input file://container_image_manifest.json
```

## Step 2: Modify the workflow

### Modify the main `nextflow.config` file

Add the following to the bottom of the file:

```groovy
includeConfig 'conf/omics.config'
```

### Enable schema validation for HealthOmics related parameters

In the `nextflow_schema.json` file under `definitions.generic_options.properties` add:

```json
"ecr_registry": {
    "type": "string",
    "description": "Amazon ECR registry to use for container images",
    "fa_icon": "fas fa-cog",
    "hidden": true
}
```

The above removes the warning that `ecr_registry` is an unrecognized parameter when the workflow runs

### Create a `parameter-template.json` file

```json
{
    "input": {
        "description": "S3 URI to samplesheet.csv. Rows therein point to S3 URIs for fastq data"
    },
    "genome": {
        "description": "Name of iGenomes reference. - e.g. GRCh38",
        "optional": true
    },
    "igenomes_base": {
        "description": "URI base for iGenomes references. (e.g. 's3://ngi-igenomes/igenomes')",
        "optional": true
    },
    "fasta": {
        "description": "Path to FASTA genome file. This parameter is mandatory if --genome is not specified. If you don't have the appropriate alignment index available this will be generated for you automatically.",
        "optional": true
    },
    "gtf": {
        "description": "Path to GTF annotation file. This parameter is mandatory if --genome is not specified.",
        "optional": true
    },
    "aligner": {
        "description": "Name of the tool to use for scRNA (pseudo-) alignment. (e.g. alevin)",
        "optional": true
    },
    "protocol": {
        "description": "The protocol that was used to generate the single cell data, e.g. 10XV2 (default).",
        "optional": true
    },
    
    "ecr_registry": {
        "description": "Amazon ECR registry for container images (e.g. '<account-id>.dkr.ecr.<region>.amazonaws.com')",
        "optional": false
    }
}
```

These are the minimal paramters needed to run the workflow as determined by:

- inspecting the workflow's [parameter documentation](https://nf-co.re/scrnaseq/2.1.0/parameters), specifically looking for parameters noted as "required" and "mandatory"
- inspecting the workflow's `conf/test.config` file, which provides a configuration used for development and testing

## Step 3: Testing

The steps below verify that the migrated pipeline will run on HealthOmics using a minimal test dataset. Test completion time depends on the data size used. For the set documented below, the workflow completed in ~1hr.

### Clone the nf-core/test-datasets repository and checkout the `scrnaseq` branch

```
cd
git clone https://github.com/nf-core/test-datasets.git
cd ~/test-datasets
git checkout scrnaseq
```

> NOTE: this repository has test data for several (if not all) “released” NF-Core workflows. If you are using an EC2 instance make sure you have at least 10GB of free disk space


Create a bucket to store test data in S3:

```
aws s3 mb s3://<mybucket>
```


Modify `test-datasets/samplesheet-2-0.csv`, replacing: 

```
https://raw.githubusercontent.com/nf-core/test-datasets/scrnaseq
```

with:

```
s3://<mybucket>/test-datasets/nf-core-scrnaseq
```


Sync this data to a bucket in your AWS operating region

```
cd ~
aws s3 sync ./test-datasets s3://<mybucket>/test-datasets/nf-core-scrnaseq --exclude .git/*
```



### Create a `test.parameters.json` file 

```
{
    "input": "s3://<mybucket>/test-datasets/nf-core-scrnaseq/samplesheet-2.0.csv",
    "fasta": "s3://<mybucket>/test-datasets/nf-core-scrnaseq/reference/GRCm38.p6.genome.chr19.fa",
    "gtf": "s3://<mybucket>/test-datasets/nf-core-scrnaseq/reference/gencode.vM19.annotation.chr19.gtf",
    "aligner": "star",
    "protocol": "10XV2"
}
```

These parameters completely circumvent the need to use iGenomes references and thereby minimize the need to make a copy of iGenomes. The trade-off is that the workflow will take longer to run as it will need to compute a reference index.


### Bundle and register the workflow with HealthOmics

The following sequence of shell commands does the following:

1. Bundles the workflow definition (excluding the `.git/` folder into a Zip file).
2. Uploads the zip file to an S3 staging location. This is required because the zip bundle exceeds the 4MiB size limit for direct upload to AWS HealthOmics via the AWS CLI.
3. Registers the workflow definition with AWS HealthOmics and waits for it to become active.

```
cd ~

workflow_name="nf-core-scrnaseq"
( cd ~/${workflow_name} && zip -9 -r "${OLDPWD}/${workflow_name}.zip" . -x "./.git/*")

definition_uri=s3://**<mybucket>**/omics-workflows/${workflow_name}.zip
aws s3 cp ${workflow_name}.zip ${definition_uri}

workflow_id=$(aws omics create-workflow \
    --engine NEXTFLOW \
    --definition-uri ${definition_uri} \
    --name "${workflow_name}-$(date +%Y%m%dT%H%M%SZ%z)" \
    --parameter-template file://${workflow_name}/parameter-template.json \
    --query 'id' \
    --output text
)

aws omics wait workflow-active --id "${workflow_id}"
aws omics get-workflow --id "${workflow_id}" > "workflow-${workflow_name}.json"
```

### Start a test run of the workflow in HealthOmics

```
workflow_name="nf-core-scrnaseq"
OMICS_WORKFLOW_ROLE_ARN="arn:aws:iam::**<account-id>**:role/**<rolename>**"
aws omics start-run \
    --role-arn "${OMICS_WORKFLOW_ROLE_ARN}" \
    --workflow-id "$(jq -r '.id' workflow-${workflow_name}.json)" \
    --name "test $(date +%Y%m%d-%H%M%S)" \
    --output-uri s3://<mybucket>/omics-output \
    --parameters file://${workflow_name}/test.parameters.json
```

You can then monitor the progress of the workflow via the [AWS HealthOmics Console](https://console.aws.amazon.com/omics/home#/runs). The workflow should complete in ~1hr.

## Congrats!

The above process should take no more than 1-2hrs to complete and at the end you will have successfully run the nf-core/scrnaseq workflow using AWS HealthOmics. From this point you can further customize the workflow as needed.


## Further reading: migration details

The source code for this workflow is largely unchanged from the [upstream version from NF-core](https://github.com/nf-core/scrnaseq/tree/2.1.0). 