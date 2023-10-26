#!/bin/env python3
"""
Script to inspect a Nextflow workflow definition and generate resources
to help migrate it to run on AWS HealthOmics.

Specifically designed to handle NF-Core based workflows, but in theory could
handle any Nextflow workflow definition.

What it does:
- look through all *.nf files
- find `container` directives
- extract container uris to:
  - build an image uri manifest
  - create a custom nextflow.config file
"""

import argparse
from glob import glob
import json
from os import path
from textwrap import dedent


import boto3


from nf import *


parser = argparse.ArgumentParser()

parser.add_argument(
    'project', type=str, 
    help="Top level directory of Nextflow workflow project")
parser.add_argument(
    '-s', '--container-substitutions', type=str,
    help="JSON file of container image substitutions."
)
parser.add_argument(
    '-n', '--namespace-config', type=str,
    help="JSON file with public registry to ecr repository namespace mappings. This should be the same as what is used by omx-ecr-helper. (e.g. omx-ecr-helper/lib/lambda/parse-image-uri/public_registry_properties.json)"
)
parser.add_argument(
    '--output-manifest-file', type=str,
    default="container_image_manifest.json",
    help="Filename to use for generated container image manifest")
parser.add_argument(
    '--output-config-file', type=str,
    default="omics.config",
    help="Filename to use for generated nextflow config file"
)
parser.add_argument(
    "--region", type=str,
    help="AWS region name"
)
parser.add_argument(
    "--profile", type=str,
    help="AWS CLI profile to use. (See `aws configure help` for more info)"
)


if __name__ == "__main__":

    args = parser.parse_args()
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    workflow = NextflowWorkflow(args.project)

    substitutions = None
    if args.container_substitutions:
        with open(args.container_substitutions, 'r') as f:
            substitutions = json.load(f)
    
    namespace_config = None
    if args.namespace_config:
        with open(args.namespace_config, 'r') as f:
            namespace_config = json.load(f)
    
    print(f"Creating container image manifest: {args.output_manifest_file}")
    manifest = workflow.get_container_manifest(substitutions=substitutions)
    with open(args.output_manifest_file, 'w') as file:
        json.dump({"manifest": manifest}, file, indent=4)
    
    print(f"Creating nextflow config file: {args.output_config_file}")
    config = workflow.get_omics_config(
        session=session, substitutions=substitutions, namespace_config=namespace_config)
    with open(args.output_config_file, 'w') as file:
        file.write(config)
