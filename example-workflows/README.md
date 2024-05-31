# Example workflows for AWS HealthOmics

This folder contains example WDL and Nextflow workflows that run on AWS HealthOmics.

These are provided AS-IS and are intended to demonstrate conventions, patterns, and best practices for writing workflows for scale on AWS HealthOmics. They are intended as starting points that you can customize to fit your specific requirements.

## What's available

Example workflows are in the following groupings ( :open_file_folder: ). Additional details are in the READMEs for each grouping.

- WDL workflows
  - :open_file_folder: [GATK Best Practice workflows](./gatk-best-practices/)
    - [Analysis ready germline BAM to VCF](./gatk-best-practices/workflows/analysis-ready-germline-bam-to-vcf/)
    - [CRAM to BAM](./gatk-best-practices/workflows/cram-to-bam/)
    - [FASTQs to analysis ready BAM](./gatk-best-practices/workflows/fastqs-to-analysis-ready-bam/)
    - [Germline FASTQs to VCF](./gatk-best-practices/workflows/germline-fastqs-to-vcf/)
    - [Somatic SNPs and InDELs](./gatk-best-practices/workflows/somatic-snps-and-indels/)

  - :open_file_folder: [Protein folding workflows](./protein-folding/)
    - [AlphaFold](./protein-folding/workflows/alphafold/)
    - [ESMFold](./protein-folding/workflows/esmfold/)

  - :open_file_folder: [Other WDL workflows](./other_WDL/)
    - [HISAT-Genotype HLA Caller](./other_WDL/workflows/HISAT-genotype/)
 
- Nextflow workflows
  - :open_file_folder: [NF-Core workflows](./nf-core/)
    - [FASTQC](./nf-core/workflows/fastqc/)
    - [RNAseq](./nf-core/workflows/rnaseq/)
    - [scRNAseq-cellranger](./nf-core/workflows/scrnaseq-cellranger/)
    - [scRNAseq](./nf-core/workflows/scrnaseq/)
    - [TaxProfiler](./nf-core/workflows/taxprofiler/)

  - :open_file_folder: [Other Nextflow workflows](./other_nextflow/)
    - [VEP](./other_nextflow/workflows/vep/)

## Prerequisites
- The [Amazon ECR Helper for AWS HealthOmics](https://github.com/aws-samples/amazon-ecr-helper-for-aws-healthomics) CDK app has been deployed to your account
- Required tooling:
    - [AWS CLI v2](https://aws.amazon.com/cli/)
    - [jq](https://stedolan.github.io/jq/)
    - Python 3.9 or higher
    - Python packages: see `_scripts/requirements.txt`
    - make

```bash
cd _scripts/
pip install -r requirements.txt
```

## General usage

To run these sample workflows the overall process is:

```bash
cd {workflow_group}

# retrieve or build container images
# ... specific commands per group ...

# execute a test run
make
make run-{workflow_name}
```

See README files in each workflow group for any special cases.


## Further reading

Each workflow group will have one or more workflows in a `workflows/` folder. Each example workflow definition and supporting files have the following structure:

```text
workflows
├── {workflow_name}
│   ├── cli-input.yaml
│   ├── (main | named-entrypoint).(wdl|nf)
│   ├── parameter-template.json
│   ├── test.parameters.json
│   └── ... additional supporting files ...
...
```

Each workflow group may also have either of the following:

- A top level `containers/` folder, that holds:
    - Source for building container images shared by all workflows in the group, and a corresponding `container_build_manifest.json` file.
    - A `container_image_manifest.json` file that lists publicly available container images shared by all workflows in the group.

- `container_image_manifest.json` files per workflow that lists publicly available container images used by each workflow.
