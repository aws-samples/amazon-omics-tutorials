from glob import glob
from os import path

import pytest

from ..nf import *


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


def test_parse_workflow():
    project_path = path.join(WORKING_DIR, 'workflow')
    workflow = NextflowWorkflow(project_path)

    assert workflow.containers == sorted([
        "image:tag",
        "foo:fizz",
        "bar:buzz",
        "ubuntu:20.04"
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