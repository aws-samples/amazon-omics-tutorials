from glob import glob
from os import path
import json
import pytest

from ..nf import *

NAMESPACE="""{
    "public.ecr.aws": { "namespace": "ecr-public", "pull_through": true },
    "ecr-public": { "namespace": "ecr-public", "pull_through": true },

    "quay.io": { "namespace": "quay", "pull_through": true },
    "quay": { "namespace": "quay", "pull_through": true },
    
    "us.gcr.io": { "namespace": "gcr", "pull_through": false },
    "eu.gcr.io": { "namespace": "gcr", "pull_through": false },
    "asia.gcr.io": { "namespace": "gcr", "pull_through": false },
    "pkg.dev": { "namespace": "gar", "pull_through": false },
    "nvcr.io": { "namespace": "nvcr", "pull_through": false},
    
    "ghcr.io": { "namespace": "ghcr", "pull_through": false },
    "mcr.microsoft.com": { "namespace": "mcr", "pull_through": false },
    
    "dockerhub": { "namespace": "dockerhub", "pull_through": false },
    "": { "namespace": "dockerhub", "pull_through": false }
}"""

WORKING_DIR = path.dirname(path.realpath(__file__))

@pytest.fixture
def nf_workflow():
    project_path = path.join(WORKING_DIR, 'workflow')
    nf_files = glob(path.join(project_path, '**/*.nf'), recursive=True)
    contents = dict()
    for nf_file in nf_files:
        with open(nf_file, 'r') as f:
            contents[nf_file] = f.read()
    return contents


def test_parse_process_happy(nf_workflow):
    nf_file = path.join(WORKING_DIR, 'workflow', 'processes', 'happy.nf')
    assert nf_file in nf_workflow

    procs = parse_processes(nf_workflow[nf_file])

    assert procs
    assert procs == [NextflowProcess(from_dict={
        "name": "HAPPY",
        "container": "image:tag"
    })]


def test_parse_process_no_container(nf_workflow):
    nf_file = path.join(WORKING_DIR, 'workflow', 'processes', 'no_container.nf')
    assert nf_file in nf_workflow

    with pytest.warns(UserWarning, match="has no container directive"):
        procs = parse_processes(nf_workflow[nf_file])
    
    assert procs
    assert procs == [NextflowProcess(from_dict={
        "name": "NO_CONTAINER",
        "container": None
    })]


def test_parse_process_multiple(nf_workflow):
    nf_file = path.join(WORKING_DIR, 'workflow', 'processes', 'multiple.nf')
    assert nf_file in nf_workflow

    procs = parse_processes(nf_workflow[nf_file])

    assert procs
    assert procs == [
        NextflowProcess(from_dict={
            "name": "FOO",
            "container": "foo:fizz"
        }),
        NextflowProcess(from_dict={
            "name": "BAR",
            "container": "bar:buzz"
        }),
    ]

def test_parse_process_gunzip(nf_workflow):
    nf_file = path.join(WORKING_DIR, 'workflow', 'processes', 'gunzip', 'main.nf')
    assert nf_file in nf_workflow

    procs = parse_processes(nf_workflow[nf_file])
    assert procs

def test_parse_process_cellranger_count(nf_workflow):
    nf_file = path.join(WORKING_DIR, 'workflow', 'processes', 'cellranger', 'count', 'main.nf')
    assert nf_file in nf_workflow

    procs = parse_processes(nf_workflow[nf_file])
    assert procs

    proc = procs[0]
    assert proc.container == "nfcore/cellranger:7.1.0"


def test_find_docker_uri_simple():
    container = "image:tag"
    uri = find_docker_uri(container)
    assert uri == 'image:tag'


def test_find_docker_uri_nfcore_ternary():
    container = """${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/fastqc:0.11.9--0' :
        'quay.io/biocontainers/fastqc:0.11.9--0' }"""
    uri = find_docker_uri(container)
    assert uri == 'quay.io/biocontainers/fastqc:0.11.9--0'


def test_find_docker_uri_quoted():
    container = "'image:tag'"
    uri = find_docker_uri(container)
    assert uri == 'image:tag'

    container = '"image:tag"'
    uri = find_docker_uri(container)
    assert uri == 'image:tag'

def test_ecr_private_repo_detection():
    project_path = path.join(WORKING_DIR, 'workflow_with_config_and_private_ecr')
    workflow = NextflowWorkflow(project_path)
    
    assert "111111111111.dkr.ecr.us-east-1.amazonaws.com/rnaseq-nf:1.1.1" in workflow.containers
    assert workflow.is_ecr_private_repo("111111111111.dkr.ecr.us-east-1.amazonaws.com")
    assert not workflow.is_ecr_private_repo("1234.dcr.ecr.us-east-1.amazonaws.com")

def test_parse_workflow():
    project_path = path.join(WORKING_DIR, 'workflow')
    workflow = NextflowWorkflow(project_path)

    assert workflow.containers == sorted([
        "image:tag",
        "foo:fizz",
        "bar:buzz",
        "ubuntu:20.04",
        "nfcore/cellranger:7.1.0"
    ])

    procs = {
        "happy": NextflowProcess(
            from_dict={"name": "HAPPY", "container": "image:tag"}),
        "no_container": NextflowProcess(
            from_dict={"name": "NO_CONTAINER", "container": None}),
        "foo": NextflowProcess(
            from_dict={"name": "FOO", "container": "foo:fizz"}),
        "bar": NextflowProcess(
            from_dict={"name": "BAR", "container": "bar:buzz"}),
        "has_comments": NextflowProcess(
            from_dict={"name": "HAS_COMMENTS", "container": "foo:fizz"}),
    }

    assert procs['happy'] in workflow.processes
    assert procs['no_container'] in workflow.processes
    assert procs['foo'] in workflow.processes
    assert procs['bar'] in workflow.processes
    assert procs['has_comments'] in workflow.processes

def test_nextflow_config_not_exists():
    project_path = path.join(WORKING_DIR, 'workflow')
    workflow = NextflowWorkflow(project_path)
    with pytest.raises(FileNotFoundError):
        workflow.docker_registry()

def test_nextflow_config_exists():
    project_path = path.join(WORKING_DIR, 'workflow_with_config')
    workflow = NextflowWorkflow(project_path)
    workflow.nextflow_config = path.join(project_path, 'nextflow.config')
    assert workflow.docker_registry == 'quay.io'

    project_path = path.join(WORKING_DIR, 'workflow_with_config')
    workflow = NextflowWorkflow(project_path)

    assert workflow.containers == sorted([
        "image:tag",
        "foo:fizz",
        "bar:buzz",
        "ubuntu:20.04",
        "nfcore/cellranger:7.1.0"
    ])

    procs = {
        "happy": NextflowProcess(
            from_dict={"name": "HAPPY", "container": "image:tag"}),
        "no_container": NextflowProcess(
            from_dict={"name": "NO_CONTAINER", "container": None}),
        "foo": NextflowProcess(
            from_dict={"name": "FOO", "container": "foo:fizz"}),
        "bar": NextflowProcess(
            from_dict={"name": "BAR", "container": "bar:buzz"}),
        "has_comments": NextflowProcess(
            from_dict={"name": "HAS_COMMENTS", "container": "foo:fizz"}),
    }
    print(workflow._get_ecr_image_name(procs['happy'].container))
    assert procs['happy'] in workflow.processes
    assert procs['no_container'] in workflow.processes
    assert procs['foo'] in workflow.processes
    assert procs['bar'] in workflow.processes
    assert procs['has_comments'] in workflow.processes