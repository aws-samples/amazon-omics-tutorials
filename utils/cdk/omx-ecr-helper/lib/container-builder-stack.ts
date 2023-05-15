import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as ecrTasks from './sfn/ecr-tasks';
import * as buildTasks from './sfn/build-tasks';

import { URL } from 'url';

export interface ContainerBuilderStackProps extends cdk.StackProps {
    source_uris?: string[]
}

export class ContainerBuilderStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props?: ContainerBuilderStackProps) {
        super(scope, id, props);

        const build_project = new codebuild.Project(this, 'CodeBuild_ContainerBuild', {
            projectName: 'container-builder',
            description: 'builds container images and pushes into an ECR private repo',
            environment: {
                buildImage: codebuild.LinuxBuildImage.STANDARD_6_0,
                computeType: codebuild.ComputeType.LARGE,  // building containers can be compute intensive
                privileged: true,
                environmentVariables: {
                    SOURCE_URI: {value: ''},
                    SOURCE_IS_ZIP: {value: 'false'},
                    TARGET_IMAGE: {value: ''}
                }
            },
            buildSpec: codebuild.BuildSpec.fromObject({
                version: 0.2,
                env: {
                    shell: 'bash'
                },
                phases: {
                    build: {
                        commands: [
                            'REGISTRY_ID=$(aws ecr describe-registry --query registryId --output text)',
                            'REGISTRY=$REGISTRY_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com',
                            
                            // retrieve source zip
                            '[[ "$SOURCE_IS_ZIP" == "true" ]] && aws s3 cp $SOURCE_URI ./source.zip || true',
                            '[[ "$SOURCE_IS_ZIP" == "true" ]] && unzip ./source.zip -d ./source || true',
                            
                            // retrieve bare bundle
                            '[[ "$SOURCE_IS_ZIP" == "false" ]] && aws s3 cp --recursive $SOURCE_URI ./source || true',
                            
                            // what are we working with
                            'ls -l',

                            // build the container
                            'cd ./source && docker build -t $REGISTRY/$TARGET_IMAGE .'
                        ]
                    },
                    post_build: {
                        commands: [
                            'echo Logging in to Amazon ECR...',
                            'REGISTRY_ID=$(aws ecr describe-registry --query registryId --output text)',
                            'REGISTRY=$REGISTRY_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com',
                            'aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $REGISTRY',
                            'docker push $REGISTRY/$TARGET_IMAGE'
                        ]
                    }
                }
            })
        })

        const policy_build_project_ecr = new iam.Policy(this, 'Policy_BuildProject_EcrAccess', {})
        policy_build_project_ecr.addStatements(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:CompleteLayerUpload",
                    "ecr:InitiateLayerUpload",
                    "ecr:PutImage",
                    "ecr:UploadLayerPart",
                    "ecr:TagResource"
                ],
                resources: [
                    cdk.Arn.format(
                        {service: "ecr", resource: "repository", resourceName: "*"},
                        this
                        )
                    ]
                }),
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    "ecr:DescribeRegistry",
                    "ecr:GetAuthorizationToken"
                ],
                resources: ["*"]
            })
        )

        build_project.role?.attachInlinePolicy(policy_build_project_ecr)

        if ( props?.source_uris && props?.source_uris.length ) {
            const policy_build_project_s3 = new iam.Policy(this, 'Policy_BuildProject_S3Access', {})
            policy_build_project_s3.addStatements(
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: [
                        "s3:GetObject",
                        "s3:ListBucket"
                    ],
                    resources: this._generate_bucket_resourcees(props?.source_uris)
                })
            )
    
            build_project.role?.attachInlinePolicy(policy_build_project_s3)
        }
        
        const BuildContainerImage = new buildTasks.BuildContainerTask(this, 'Build Container Image',
            build_project,
            {
                SOURCE_URI: { value: sfn.JsonPath.stringAt('$.image.source.uri') },
                SOURCE_IS_ZIP: { value: sfn.JsonPath.stringAt('$.image.source.is_zip') },
                TARGET_IMAGE: { value: sfn.JsonPath.format(
                    '{}:{}', 
                    sfn.JsonPath.stringAt('$.image.name'), 
                    sfn.JsonPath.stringAt('$.image.tag')
                ) }
            }
        )

        const EcrDescribeRepository = new ecrTasks.EcrDescribeRepository(this, 'ECR Describe Repository', {
            repositoryNames: sfn.JsonPath.stringAt('States.Array($.image.name)'),
            resultPath: '$.repository.details'
        })

        EcrDescribeRepository.addFallback(
            new ecrTasks.EcrCreateRepository(this, 'ECR Create Repository', {
                repositoryName: sfn.JsonPath.stringAt('$.image.name'),
                tags: [
                    {Key: "createdBy", Value: "omx-ecr-helper"}
                ],
                resultPath: '$.repository.created'
            })
            .next(BuildContainerImage)
        )

        EcrDescribeRepository.next(BuildContainerImage)

        // state-machine to build containers
        const sfn_workflow = new sfn.StateMachine(this, 'StateMachine', {
            stateMachineName: 'omx-container-builder',
            definition: new sfn.Map(this, 'Manifest Items', {
                itemsPath: "$.manifest",
                maxConcurrency: 10
            }).iterator(
                new sfn.Pass(this, 'Parse Image Name', {
                    parameters: {
                        target_image: sfn.JsonPath.stringAt('$.target_image'),
                        image: {
                            source: {
                                uri: sfn.JsonPath.stringAt('$.source_uri')
                            },
                            "name.$": "States.ArrayGetItem(States.StringSplit($.target_image, ':'), 0)",
                            "tag.$": "States.ArrayGetItem(States.StringSplit($.target_image, ':'), 1)"
                        }
                    }
                })
                .next(
                    new sfn.Choice(this, 'Source is ZIP?')
                    .when(
                        sfn.Condition.stringMatches('$.image.source.uri', '*.zip'),
                        new sfn.Pass(this, 'Source is ZIP - Yes', {
                            parameters: {
                                uri: sfn.JsonPath.stringAt('$.image.source.uri'),
                                is_zip: 'true'
                            },
                            resultPath: '$.image.source'
                        })
                        .next(EcrDescribeRepository)
                    )
                    .otherwise(
                        new sfn.Pass(this, 'Source is ZIP - No', {
                            parameters: {
                                uri: sfn.JsonPath.stringAt('$.image.source.uri'),
                                is_zip: 'false'
                            },
                            resultPath: '$.image.source'
                        })
                        .next(EcrDescribeRepository)
                    )
                )
            )
        })
        
    }

    private _generate_bucket_resourcees(s3uris: string[]): string[] {
        // for each uri
        // create a bucket resource for s3:ListBucket
        // create a prefix resource for s3:GetObject

        return s3uris.map( s3uri => {
            let url = new URL(s3uri)
            let bucketname = url.hostname;
            let prefix = url.pathname;

            let bucket_arn = cdk.Arn.format(
                {service: "s3", region: "", account: "", resource: bucketname},
                this
            )

            let prefix_arn;
            if (prefix && prefix.length) {
                prefix = prefix.slice(1);
                if (prefix.endsWith('/')) {
                    // prefix is provided as a folder
                    prefix = prefix + "*";
                } else {
                    // prefix is provided as a key, assume it's a folder
                    prefix = prefix + "/*"
                }
                prefix_arn = cdk.Arn.format(
                    {service: "s3", region: "", account: "", resource: bucketname, resourceName: prefix},
                    this
                )
            } else {
                prefix_arn = cdk.Arn.format(
                    {service: "s3", region: "", account: "", resource: bucketname, resourceName: "*"},
                    this
                )
            }

            return [bucket_arn, prefix_arn]
        }).flat()
    }
}
