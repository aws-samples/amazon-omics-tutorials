# Example workflows for Amazon Omics

This folder contains example WDL and Nextflow workflows that run on Amazon Omics.

These are provided AS-IS and are intended to demonstrate conventions, patterns, and best practices for writing workflows for scale on Amazon Omics. They are intended as starting points that you can customize to fit your specific requirements.

## Prerequisites
- Required tooling:
    - [AWS CDK](https://aws.amazon.com/cdk/)
    - [AWS CLI v2](https://aws.amazon.com/cli/)
    - [jq](https://stedolan.github.io/jq/)
    - Python 3.9 or higher
    - Python packages: see `_scripts/requirements.txt`
    - make

```bash
cd _scripts/
pip install -r requirements.txt
```

## What's available

Example workflows are in the following groups. Additional details for each group can be found within their respective folders.

- [GATK Best Practice workflows](./gatk-best-practices/)
- [NF-Core workflows](./nf-core/)
- [Protein folding workflows](./protein-folding/)


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
