![AWS HealthOmics](./assets/aws-healthomics-banner_600px.png)

# AWS HealthOmics Tutorials

Example code that demonstrates how to store, process, and query genomic and biological datasets using AWS HealthOmics

## Background

[AWS HealthOmics](https://aws.amazon.com/omics/) helps healthcare and life sciences customers store, query, analyze, and generate insights from genomic and other biological data to improve human health.

This repository contains resources (e.g. code scripts, jupyter notebooks, etc) that demonstrate the usage of AWS HealthOmics.

## Setup

The quickest setup to run example notebooks includes:
- An [AWS account](http://docs.aws.amazon.com/omics/latest/dev/setting-up.html#setting-up-aws-sign-up)
- Proper [IAM User and Role](http://docs.aws.amazon.com/omics/latest/dev/setting-up.html#setting-up-create-iam-user) setup
- An [Amazon SageMaker Notebook Instance](http://docs.aws.amazon.com/sagemaker/latest/dg/gs-setup-working-env.html)


## Tutorials
### Storage
* [Using HealthOmics Storage with genomics references and readsets](./notebooks/200-omics_storage.ipynb): Get acquainted with HealthOmics storage by creating reference and sequence stores, importing data from FASTQ and CRAM files, and downloading readsets.
### Workflows
* [Running WDL and Nextflow pipelines with HealthOmics Workflows](./notebooks/200-omics_workflows.ipynb): Learn how to create, run, and debug WDL and Nextflow based pipelines that process data from HealthOmics Storage and Amazon S3 using HealthOmics Workflows.
### Analytics
* [Querying annotations and variants with HealthOmics Analytics](./notebooks/200-omics_analytics.ipynb): Get started with HealthOmics Analytics by importing variant and annotation data from VCF, TSV, and GFF files, and performing genome scale analysis queries using Amazon Athena.

## License

This library is licensed under the [Apache 2.0 License](http://aws.amazon.com/apache2.0/). For more details, please take a look at the [LICENSE](./LICENSE) file.

## Security

See the [Security issue notifications](./CONTRIBUTING.md#security-issue-notifications) section of our [contributing guidelines](./CONTRIBUTING.md) for more information.

## Contributing
Although we're extremely excited to receive contributions from the community, we're still working on the best mechanism to take in examples from external sources. Please bear with us in the short-term if pull requests take longer than expected or are closed. Please read our [contributing guidelines](./CONTRIBUTING.md) if you'd like to open an issue or submit a pull request.