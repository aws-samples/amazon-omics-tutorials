#!/usr/bin/env python3

import configparser
from base64 import b64decode
from datetime import datetime, timezone
import glob
import io
import json
import os
from textwrap import dedent
from time import sleep
from urllib.parse import urlparse
import warnings
from zipfile import ZipFile, ZIP_DEFLATED


import boto3
import botocore
import yaml


CONFIG_DEFAULTS = {
    'profile': None,
    'region': None,
    'allow_ecr_overwrite': True,
    'staging_uri': None,
    'output_uri': None,
    'workflow_role_name': None,
    'ecr_registry': None,
    'omx_ecr_helper': '~/amazon-omics-tutorials/utils/cdk/omx-ecr-helper'
}

class Builder:
    def __init__(self, config_file='conf/default.ini', assets_dir='assets') -> None:
        self._read_config(config_file)

        self._assets_dir = assets_dir
        
    
    def _read_config(self, config_file) -> dict:
        config = configparser.ConfigParser()
        config.read(config_file)

        cfg = CONFIG_DEFAULTS
        cfg |= { key: config['default'].get(key) for key in CONFIG_DEFAULTS if config['default'].get(key) }

        session = boto3.Session(profile_name=cfg.get('profile'), region_name=cfg.get('region'))  
        account_id = session.client('sts').get_caller_identity()['Account']
        profile_name = session.profile_name
        region_name = session.region_name
        cfg |= {'profile': profile_name, 'region': region_name}

        if not cfg['workflow_role_name']:
            cfg['workflow_role_name'] = f'omics-workflow-role-{account_id}-{region_name}'
        
        if not cfg['output_uri']:
            cfg['output_uri'] = f's3://omics-output-{account_id}-{region_name}'
        
        if not cfg['staging_uri']:
            cfg['staging_uri'] = cfg['output_uri']
        
        if not cfg['ecr_registry']:
            cfg['ecr_registry'] = f'{account_id}.dkr.ecr.{region_name}.amazonaws.com'
        
        if account_id not in cfg:
            cfg['account_id'] = account_id
        
        self.session = session
        self.account_id = account_id
        self.config = cfg
        
        return cfg

    def build_config(self) -> None:
        self._write_artifact(self.config, 'build/config.json')

    def _create_bucket_from_s3uri(self, s3uri) -> None:
        session = self.session

        s3c = session.client('s3')
        region_name = session.region_name
        try:
            request = {"Bucket": urlparse(s3uri).netloc}
            if region_name != 'us-east-1':
                # location constraint only works for regions that are not us-east-1
                request |= {'CreateBucketConfiguration': {'LocationConstraint': region_name}}

            response = s3c.create_bucket(**request)
        except (s3c.exceptions.BucketAlreadyExists, s3c.exceptions.BucketAlreadyOwnedByYou) as e:
            print(f"{e} ::: this is ok as long as you own this bucket", flush=True)
    
    def _write_artifact(self, obj, path: str) -> None:
        print(f'creating build artifact: {path}')
        with open(path, 'w') as f:
            json.dump(obj, f, indent=4, default=str)
    
    def build_s3(self) -> None:
        cfg = self.config
        self._create_bucket_from_s3uri(cfg['output_uri'])

        if cfg['staging_uri'] != cfg['output_uri']:
            self._create_bucket_from_s3uri(cfg['staging_uri'])
        
        self._write_artifact({"output_uri": cfg['output_uri']}, 'build/s3-output-uri')
        self._write_artifact({"staging_uri": cfg['staging_uri']}, 'build/s3-staging-uri')

    def build_iam(self) -> None:
        cfg = self.config
        session = self.session
        account_id = self.account_id
        region_name = cfg['region']
        assets_dir = self._assets_dir
        output_uri = cfg['output_uri']
        staging_uri = cfg['staging_uri']
        workflow_role_name = cfg['workflow_role_name']

        iam = session.client('iam')

        print(f"attmpting to create iam role: {workflow_role_name}")
        try:
            with open(os.path.join(assets_dir, 'omics-trust-relationship.json'), 'r') as f:
                trust_policy = f.read()
            
            response = iam.create_role(
                RoleName=workflow_role_name,
                AssumeRolePolicyDocument=trust_policy
            )
            waiter = iam.get_waiter('role_exists')
            waiter.wait(RoleName=workflow_role_name)

        except iam.exceptions.EntityAlreadyExistsException as e:
            print(f"{e} ::: this is ok as long as this is the role you intend to use. verify its permissions are correct", flush=True)
        
        response = iam.get_role(RoleName=workflow_role_name)
        workflow_role = response['Role']
        
        with open(os.path.join(assets_dir, 'omics-workflow-startrun-policy.json'), 'r') as f:
            contents = f.read()
            contents = contents.replace('{{region}}', region_name)
            contents = contents.replace('{{account_id}}', account_id)

            # output and staging uris need to be formatted to be compatible with an arn
            for key, value in zip(['output_uri', 'staging_uri'], [output_uri, staging_uri]):
                _value = value.replace('s3://', '')
                if value.endswith("/"):
                    contents = contents.replace('{{' + key + '}}', _value[:-1])
                else:
                    contents = contents.replace('{{' + key + '}}', _value)
            
            policy_document = contents
        
        policy_name = 'omics-workflow-startrun-policy'
        print(f"adding inline policy to iam role {workflow_role_name}")
        iam.put_role_policy(
            RoleName=workflow_role_name,
            PolicyName=policy_name,
            PolicyDocument=policy_document
        )
        
        policy = iam.get_role_policy(
            RoleName=workflow_role_name,
            PolicyName=policy_name
        )

        self._write_artifact(workflow_role, 'build/iam-workflow-role')
        self._write_artifact(policy, 'build/iam-workflow-startrun-pollicy')
    
    def build_sfn(self, manifest_file, name=None, machine_type='container-puller') -> None:
        cfg = self.config
        session = self.session
        account_id = self.account_id
        region_name = cfg['region']

        sfn = session.client('stepfunctions')

        with open(manifest_file, 'r') as f:
            manifest = f.read()
        
        state_machine_arn = f"arn:aws:states:{region_name}:{account_id}:stateMachine:omx-{machine_type}"
        execution = sfn.start_execution(
            stateMachineArn=state_machine_arn,
            input=manifest
        )

        # poll to wait for the state machine to finish
        # it most cases this shouldn't take more than a few minutes, but could take up to 4hrs
        # depending on the number of containers to pull/build and individual task duration
        # timeout here after 4hrs
        print(f"waiting for state machine execution to complete: {execution['executionArn']}")
        while True:
            print('.', end='', flush=True)
            execution = sfn.describe_execution(executionArn=execution['executionArn'])
            if execution.get('stopDate'):
                # machine finished
                print(' complete')
                break

            duration = datetime.now(timezone.utc) - execution.get('startDate')
            if duration.total_seconds() >= 4*3600:
                print(' timeout')
                raise RuntimeError(f"{machine_type} state machine took >= 4hrs to complete")
            
            sleep(10)
        
        asset_name = f'sfn-{machine_type}'
        if name:
            asset_name += f'-{name}'

        # if we get to here, the execution completed, check if it failed
        if execution['status'] == 'FAILED':
            raise RuntimeError(f"state machine exited with FAILED status")

        # the state machines are designed to catch errors, verify that all containers have either SUCCEEDED or SKIPPED statuses
        output = json.loads(execution['output'])
        if [image for image in output if image['status'] in ("FAILED")]:
            warnings.warn(f"there are FAILED images ::: check build/{asset_name}-output for details")
        
        self._write_artifact(execution, f'build/{asset_name}')
        self._write_artifact(output, f'build/{asset_name}-output')
    
    @staticmethod
    def bundle_workflow(workflow_name, workflow_root_dir, target_zip="build/bundle-{workflow_name}.zip"):
        target_zip = target_zip.format(workflow_name=workflow_name)
        print(f"creating zip bundle for workflow '{workflow_name}': {target_zip}")
        
        buffer = io.BytesIO()
        with ZipFile(buffer, mode='w', compression=ZIP_DEFLATED) as zf:
            for file in glob.iglob(os.path.join(workflow_root_dir, '**/*'), recursive=True):
                if os.path.isfile(file):
                    arcname = file.replace(os.path.join(workflow_root_dir, ''), '')
                    print(f".. adding: {file} -> {arcname}")
                    zf.write(file, arcname=arcname)
        
        # write out the zip file but preserve the buffer for later use
        with open(target_zip, 'wb') as f:
            f.write(buffer.getvalue())

        return buffer

    def build_workflow(self, workflow_name) -> None:
        cfg = self.config
        session = self.session

        omics = session.client('omics')

        # create zip file
        buffer = Builder.bundle_workflow(workflow_name, f"workflows/{workflow_name}")

        # check the size of the buffer, if more than 4MiB it needs to be staged to S3
        buffer.seek(0, 2)
        definition_uri = None
        if buffer.tell() / 1024. > 4.0:
            staging_uri = cfg['staging_uri']
            
            definition_uri = urlparse("/".join([staging_uri, f"bundle-{workflow_name}.zip"]))
            print(f"staging workflow definition to {definition_uri.geturl()}")

            s3c = session.client('s3')
            s3c.put_object(
                Body=buffer.getvalue(),
                Bucket=definition_uri.netloc,
                Key=definition_uri.path[1:]
            )
        
        # register workflow (use provided cli-input-yaml)
        with open(f'workflows/{workflow_name}/cli-input.yaml', 'r') as f:
            cli_input = yaml.safe_load(f)
        
        with open(f'workflows/{workflow_name}/parameter-template.json', 'r') as f:
            parameter_template = json.load(f)

        request_args = {
            "parameterTemplate": parameter_template
        }

        if definition_uri:
            request_args |= { "definitionUri": definition_uri.geturl() }
        else:
            request_args |= { "definitionZip": buffer.getvalue() }

        request_args |= cli_input
        response = omics.create_workflow(**request_args)
        workflow_id = response['id']

        # wait for workflow to be active
        # let the build fail if there's an error here
        try:
            waiter = omics.get_waiter('workflow_active')
            waiter.wait(id=workflow_id)

            workflow = omics.get_workflow(id=workflow_id)
            self._write_artifact(workflow, f'build/workflow-{workflow_name}')
        except botocore.exceptions.WaiterError as e:
            response = omics.get_workflow(id=workflow_id)
            cause = response['statusMessage']

            print(f"Encountered the following error: {e}\n\nCause:\n{cause}")

            raise RuntimeError
        
    def build_samplesheet(self, workflow_name) -> None:
        # this is only used for nf-core based workflows
        cfg = self.config
        session = self.session
        region_name = cfg['region']

        staging_uri = cfg['staging_uri']
        
        with open(f'workflows/{workflow_name}/samplesheet-template.csv', 'r') as f, \
            open(f'build/samplesheet-{workflow_name}.csv', 'w') as g:
            contents = f.read()
            contents = contents.replace('{{region}}', region_name)

            g.write(contents)
        
        samplesheet = contents

        object_uri = urlparse("/".join([staging_uri, f"samplesheet-{workflow_name}.csv"]))
        print(f"staging samplesheet to {object_uri.geturl()}")

        s3c = session.client('s3')
        s3c.put_object(
            Body=samplesheet.encode('utf-8'),
            Bucket=object_uri.netloc,
            Key=object_uri.path[1:]
        )

        self._write_artifact({"samplesheet_uri": object_uri.geturl()}, f'build/samplesheet-{workflow_name}-uri')

    def build_run(self, workflow_name) -> None:
        cfg = self.config
        session = self.session
        profile = session.profile_name
        region_name = cfg['region']

        omics = session.client('omics')

        # merge test parameters with build/ecr-registry asset
        # workflows have ecr_registry parameterized
        ecr_registry = {'ecr_registry': cfg['ecr_registry']}        
        staging_uri = cfg['staging_uri']
        output_uri = cfg['output_uri']
        account_id = cfg['account_id']

        with open(f'workflows/{workflow_name}/test.parameters.json', 'r') as f:
            test_parameters = f.read()

        test_parameters = test_parameters.replace('{{region}}', region_name)
        test_parameters = test_parameters.replace('{{staging_uri}}', staging_uri)
        test_parameters = test_parameters.replace('{{account_id}}', account_id)
        test_parameters = json.loads(test_parameters)

        test_parameters |= ecr_registry | {"aws_region": region_name}
        
        # get workflow-id from build asset
        with open(f'build/workflow-{workflow_name}', 'r') as f:
            workflow_id = json.load(f)['id']

        # get role arn from build asset
        with open(f'build/iam-workflow-role', 'r') as f:
            workflow_role_arn = json.load(f)['Arn']
            
        omics = session.client('omics')
        run = omics.start_run(
            workflowId=workflow_id,
            name=f"test: {workflow_name}",
            roleArn=workflow_role_arn,
            outputUri=output_uri,
            parameters=test_parameters
        )

        # write out final test parameters for tracking
        self._write_artifact(test_parameters, f'build/parameters-{workflow_name}.json')
        
        check_command=f"aws omics get-run --id {run['id']} --region {region_name}"
        if profile:
            check_command += f" --profile {profile}"
        
        print(dedent(f"""
            successfully started run '{run['id']}':
            
            {run}
            
            using parameters:
            {test_parameters}
            
            to check on the status of this run you can use the following command:
            $ {check_command}
            """
        ).strip())
