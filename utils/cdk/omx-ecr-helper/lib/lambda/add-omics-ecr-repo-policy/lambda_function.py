import json
from pprint import pprint

import boto3

def lambda_handler(event, context):
    pprint(event)
    
    ecr = boto3.client('ecr')
    policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Sid': 'omics workflow access',
                'Effect': 'Allow',
                'Principal': {'Service': 'omics.amazonaws.com'},
                'Action': [
                    'ecr:GetDownloadUrlForLayer',
                    'ecr:BatchGetImage',
                    'ecr:BatchCheckLayerAvailability'
                ]
            }
        ]
    }
    
    event_detail = event['detail']
    event_type = event_detail['eventType']
    repository_name = None
    repository_tags = None
    set_policy = False

    if event_type == 'AwsServiceEvent': 
        repository_name = event_detail['serviceEventDetails']['repositoryName']
        set_policy = True
    elif event_type == 'AwsApiCall':
        # AwsApiCall
        repository_name = event_detail['requestParameters']['repositoryName']
        repository_tags = event_detail['requestParameters']['tags']

        if repository_tags:
            valid_tags = [
                tag 
                for tag in repository_tags 
                if tag['key'] == "createdBy" and tag['value'] == 'omx-ecr-helper'
            ]
            set_policy = len(valid_tags) > 0

    else:
        # unhandled event type
        pass
    
    if set_policy:
        response = ecr.set_repository_policy(
            repositoryName=repository_name,
            policyText = json.dumps(policy)
        )
    else:
        response = {'message': 'noop: repository does not meet criteria'}

    return {
        'statusCode': 200,
        'body': response
    }
