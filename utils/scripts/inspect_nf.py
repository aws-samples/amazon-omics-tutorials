#!/bin/env python3
"""
Script to inspect a Nextflow workflow definition and generate resources
to help migrate it to run on Amazon Omics.

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
import re
from os import path
from textwrap import dedent
import warnings


import boto3


class NextflowWorkflow:
    def __init__(self, project_path:str) -> None:
        self._project_path = project_path
        self._nf_files = glob(path.join(project_path, '**/*.nf'), recursive=True)
        self.use_ecr_pull_through_cache = True
        self._container_substitutions = None
    
    @property
    def _contents(self) -> dict:
        contents = dict()
        for nf_file in self._nf_files:
            with open(nf_file, 'r') as file:
                contents[nf_file] = file.read()
        return contents
    
    @property
    def processes(self) -> list:
        _processes = []
        for nf_file, content in self._contents.items():
            # this pattern will match multiple process definitions in a file if they are present
            # the objective is to only get the process name and container directive for now
            # TODO: issue a warning if a process is found without a container directive
            matches = re.findall(r'process([\w\s]+?)\{.+?container "(.+?)"', content, flags=re.MULTILINE|re.DOTALL)
            if matches:
                _processes += [
                    NextflowProcess(from_dict={
                        "name": match[0].strip(), 
                        "container": find_docker_uri(match[1]),
                        "nf_file": nf_file
                    }) for match in matches
                ]
        return _processes
    
    @property
    def containers(self) -> list:
        """
        returns the list of container uris specified by the workflow definition
        does not make any adjustments for cacheable uris or substitutions.
        """
        uris = set()
        for process in self.processes:
            uris.add(process.container['uri'])
        
        return sorted(list(uris))
        
    def get_container_manifest(self, substitutions=None) -> list:
        """
        generates a list of unique container image URIs to pull into an ECR Private registry
        """
        uris = set()        
        for uri in self.containers:
            if substitutions and uri in substitutions:
                uri = substitutions.get(uri)
            uris.add(uri)
        
        return sorted(list(uris))

    def _get_ecr_image_name(self, uri, substitutions=None, namespace_config=None):
        if substitutions and uri in substitutions:
            uri = substitutions.get(uri)

        if namespace_config:
            uri_parts = uri.split('/')
            if len(uri_parts) > 1:
                source_registry = uri_parts[0]
                image_name = "/".join(uri_parts[1:])
            else:
                source_registry = ""
                image_name = uri
            
            props = namespace_config.get(source_registry)
            if props:
                uri = "/".join([props['namespace'], image_name])
        
        return uri
            
    def get_omics_config(self, session=None, substitutions=None, namespace_config=None) -> str:
        """
        generates nextflow.config contents to use when running on Amazon Omics

        :param: session: boto3 session
        :param: namespace_config: dictionary that maps public registries to image repository namespaces
        """

        ecr_registry = ''
        if session:
            ecr = session.client('ecr')
            response = ecr.describe_registry()
            ecr_registry = f"{response['registryId']}.dkr.ecr.{session.region_name}.amazonaws.com"

        process_configs = []
        _tpl = "withName: '(.+:)?::process.name::' { container = \"${ ([params.ecr_registry, '::process.container.uri::'] - '').join('/') }\" }"
        for process in self.processes:
            container_uri = self._get_ecr_image_name(
                process.container['uri'], 
                substitutions=substitutions, 
                namespace_config=namespace_config)
                
            process_configs += [
                ( _tpl
                    .replace('::process.name::', process.name)
                    .replace('::process.container.uri::', container_uri)
                )
            ]
        
        config = dedent(
            """\
            params {
                ecr_registry = ':::ecr_registry:::'
                outdir = '/mnt/workflow/pubdir'
            }
            
            manifest {
                nextflowVersion = '!>=22.04.0'
            }

            conda {
                enabled = false
            }
            
            process {
            withName: '.*' { conda = null }
            :::process_configs:::
            }
            """
        )
        config = config.replace(":::ecr_registry:::", ecr_registry)
        config = config.replace(":::process_configs:::", "\n".join(process_configs))

        return config


class NextflowProcess:
    def __init__(self, from_dict=None) -> None:
        if from_dict:
            self._load_from_dict(from_dict)
    
    def _load_from_dict(self, props) -> None:
        self.name = props['name']
        self.container = props['container']
        self.nf_file = props['nf_file']
    
    def __hash__(self) -> int:
        # omit self.nf_file from hashing
        # this assumes a process with the same name same container are identical
        # even if defined in two different files
        return hash((self.name, self.container['uri'], self.container['use_ecr_registry_param']))
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, container={self.container}, nf_file={self.nf_file})"


def find_docker_uri(container:str) -> dict:
    # only look for public docker container uri
    # spot check of several nf-core workflows shows container directives use a ternary definition
    # to select between singularity and docker
    match = re.search("(\\:|params.ecr_registry \\+)\s+?'(.+?)'", container)
    uri = None
    use_ecr_registry_param = False
    if match:
        # check if ecr_registry has been parameterized
        use_ecr_registry_param = match.groups()[0].startswith('params.ecr_registry')
        uri = match.groups()[1]
    else:
        # there are edge cases where a "simple" container directive is used - e.g. only a URI string
        uri = container
    
    return {"uri": uri, "use_ecr_registry_param": use_ecr_registry_param}


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
    help="JSON file with public registry to ecr repository namespace mappings. This should be the same as what is used by omx-ecr-helper."
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
