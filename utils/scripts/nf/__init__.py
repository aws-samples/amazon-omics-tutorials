from glob import glob
import re
from os import path
from textwrap import dedent
import warnings


__NF_DIRECTIVES : str = """
    accelerator,afterScript,
    beforeScript,
    cache,clusterOptions,conda,container,containerOptions,cpus,
    debug,disk,
    echo,errorstrategy,executor,ext,
    fair,
    label,
    machineType,maxErrors,maxRetries,memory,module,
    penv,pod,publishDir,
    queue,
    resourceLabels,
    scratch,spack,storeDir,stageInMode,stageOutMode,
    tag,
    time,
"""

__NF_PROCESS_SYNTAX : str = """
    input,output,when,script,shell,exec,stub
"""

# limit this set to keywords used in control structures
__GROOVY_KEYWORDS : str = """
    assert,def,do,for,if,switch,try,while
"""


def __nf_tokenize(tokens):
    _tokens = re.sub(r'[\s\n]+', '', tokens, re.DOTALL | re.MULTILINE)
    if _tokens.endswith(','):
        _tokens = _tokens[:-1]
    _tokens = _tokens.split(',')
    return _tokens


NF_DIRECTIVES : list = __nf_tokenize(__NF_DIRECTIVES)
NF_PROCESS_SYNTAX : list = __nf_tokenize(__NF_PROCESS_SYNTAX)
GROOVY_KEYWORDS : list = __nf_tokenize(__GROOVY_KEYWORDS)


def parse_processes(contents, nf_file=None):
    # contents is the content of a single nf_file
    # an nf_file can have multiple process definitions

    # remove all comments since they interfere with token parsing
    _contents = re.sub('/\\*.*\\*/', '', contents, flags=re.DOTALL)
    _contents = [re.sub('(.*)//.*', '\\1', line) for line in _contents.split('\n')]
    _contents = '\n'.join(_contents)
    
    _processes = []

    # capture the name of processes and their definitions
    pattern = 'process([\\w\\s]+?)\\{(.+?)\\}(?=\\s+process|\\s*\\Z)'
    matches = re.findall(pattern, _contents, flags=re.MULTILINE|re.DOTALL)

    if matches:
        _processes = [
            {"nf_file": nf_file, "name": match[0].strip(), "body": match[1].strip()}
            for match in matches
        ]
    
    # capture all directive and stanza definitions
    tokens = NF_DIRECTIVES + NF_PROCESS_SYNTAX + GROOVY_KEYWORDS
    for ix, _proc in enumerate(_processes):
        for token in tokens:
            _token = token
            _group = '(\\s+.+?)'
            _look_ahead = '\\s+?(?=' + '|'.join(tokens) + ')'

            if token in NF_PROCESS_SYNTAX:
                _token += ':'
            
            if token in ("script", "stub"):
                _look_ahead = '(?=' + '|'.join(NF_PROCESS_SYNTAX + ['\\Z']) + ')'
            
            pattern = _token + _group + _look_ahead
            matches = re.findall(pattern, _proc['body'], flags=re.MULTILINE|re.DOTALL)
            
            # some tokens can be defined multiple times
            if matches:
                _proc[token] = [match.strip() for match in matches]
        
        if not _proc.get('container'):
            warnings.warn(f"process '{_proc['name']}' in file '{_proc['nf_file']}' has no container directive", UserWarning)
        
        _processes[ix] = NextflowProcess(from_dict=_proc)
    
    return _processes


class NextflowWorkflow:
    def __init__(self, project_path:str) -> None:
        self._project_path = project_path
        self._nf_files = glob(path.join(project_path, '**/*.nf'), recursive=True)
        self.use_ecr_pull_through_cache = True
        self._container_substitutions = None
        self._nf_config = path.join(project_path, 'nextflow.config')
    
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
            _processes += parse_processes(content, nf_file=nf_file)
        return _processes
    
    @property
    def containers(self) -> list:
        """
        returns the list of container uris specified by the workflow definition
        does not make any adjustments for cacheable uris or substitutions.
        """
        uris = set()
        for process in self.processes:
            if process.container:
                uris.add(process.container)
        
        return sorted(list(uris))
    
    @property
    def docker_registry(self) -> str:
        """
        returns the docker registry specified by the workflow definition
        specified in its own line in a nextflow.config file as 
        docker.registry = 'quay.io'
        """
        _docker_registry = None
        try:
            with open(self._nf_config, 'r') as _file:
                for line in _file:
                    if line.startswith('docker.registry'):
                        _docker_registry = line.strip().split('=')[1].replace('\'', '').replace('"', '').strip()
                        break
        except FileNotFoundError as fnfe:
            print(f"nextflow.config file not found in project directory: {self._project_path}")
            raise fnfe
        return _docker_registry
        
    def is_ecr_private_repo(self, _registry_name):
        """
        Detect private registry in format <awsaccountid>.dkr.ecr.<awsregion>.amazonaws.com
        """
        return re.match('[0-9]{12}\.dkr\.ecr\.[a-zA-Z0-9-]{1,}\.amazonaws\.com', _registry_name)
           
    def get_container_manifest(self, substitutions=None) -> list:
        """
        generates a list of unique container image URIs to pull into an ECR Private registry
        """
        uris = set()        
        for uri in self.containers:
            if substitutions and uri in substitutions:
                uri = substitutions.get(uri)
            if self.docker_registry:
                uri = "/".join([self.docker_registry, uri])
            uris.add(uri)
        
        return sorted(list(uris))

    def _get_ecr_image_name(self, uri, substitutions=None, namespace_config=None):
        if substitutions and uri in substitutions:
            uri = substitutions.get(uri)

        if self.docker_registry:
            uri = "/".join([self.docker_registry, uri])

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
            else:
                if self.is_ecr_private_repo(source_registry):
                    uri = image_name
        
        return uri
            
    def get_omics_config(self, session=None, substitutions=None, namespace_config=None) -> str:
        """
        generates nextflow.config contents to use when running on AWS HealthOmics

        :param: session: boto3 session
        :param: namespace_config: dictionary that maps public registries to image repository namespaces
        """

        ecr_registry = ''
        if session:
            ecr = session.client('ecr')
            response = ecr.describe_registry()
            ecr_registry = f"{response['registryId']}.dkr.ecr.{session.region_name}.amazonaws.com"

        process_configs = []
        _tpl = "withName: '(.+:)?::process.name::' { container = '::process.container.uri::' }"
        for process in self.processes:
            if process.container:
                container_uri = self._get_ecr_image_name(
                    process.container, 
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

            docker {
                enabled = true
                registry = params.ecr_registry
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
        self.name = props.get('name')
        self.body = props.get('body')
        self.nf_file = props.get('nf_file')

        for attr in (NF_DIRECTIVES + NF_PROCESS_SYNTAX):
            if props.get(attr) and len(props.get(attr)) == 1:
                value = props.get(attr)[0]
            else:
                value = props.get(attr)
            setattr(self, attr, value)
        
        if self.container:
            self.container = find_docker_uri(self.container)
    
    def __hash__(self) -> int:
        # omit self.nf_file from hashing
        # this assumes a process with the same name same container are identical
        # even if defined in two different files
        # TODO: make hashing consider process body as a whole
        return hash((self.name, self.container))
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, container={self.container}, nf_file={self.nf_file})"
    
    def __eq__(self, __value: object) -> bool:
        # TODO: make equality compare more than name and container
        return (
            self.name == __value.name 
            and self.container == __value.container
        )


def find_docker_uri(container:str) -> dict:
    # check if provided a quoted string and strip bounding quotes
    match = re.match("^(['\"])", container)
    if match:
        container = container[1:-1]
    
    # only look for public docker container uri
    # spot check of several nf-core workflows shows container directives use a ternary definition
    # to select between singularity and docker
    match = re.search("(\\:|params.ecr_registry \\+)\\s+?'(.+?)'", container)
    uri = None
    if match:
        uri = match.groups()[1]
    else:
        # there are edge cases where a "simple" container directive is used - e.g. only a URI string
        uri = container
    
    return uri