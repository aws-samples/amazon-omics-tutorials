import * as path from 'path';

import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
// import * as sqs from 'aws-cdk-lib/aws-sqs';

import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as events from 'aws-cdk-lib/aws-events';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as targets from 'aws-cdk-lib/aws-events-targets';

import * as buildTasks from './sfn/build-tasks';
import * as ecrTasks from './sfn/ecr-tasks';

export class ContainerPullerStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        // policy for lambda
        // allows the lambda to add ecr repository policies
        const policy_set_repo_policy = new iam.Policy(this, 'Policy_ECRRepoAccess', {})
        policy_set_repo_policy.addStatements(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: ["ecr:SetRepositoryPolicy"],
                resources: [
                    // "arn:aws:ecr:*:{acct-id}:repository/*",
                    cdk.Arn.format({
                        service: "ecr",
                        // stack must be deployed per region, so an IAM role per region is used
                        resource: "repository",
                        resourceName: "*"
                    }, this)
                ]
            })
        )

        // lambda function to add ECR repo policy
        const fn_add_repo_policy = new lambda.Function(this, 'Function_AddOmicsECRRepoPolicy', {
            runtime: lambda.Runtime.PYTHON_3_9,
            handler: 'lambda_function.lambda_handler',
            code: lambda.Code.fromAsset(path.join(__dirname, 'lambda', 'add-omics-ecr-repo-policy'))
        });

        fn_add_repo_policy.role?.attachInlinePolicy(policy_set_repo_policy);

        // event rule
        const rule = new events.Rule(this, 'EventRule_CreateECRRepository', {
            // this event pattern ONLY matches repo creation initiated by pull-through caching
            eventPattern: {
                source: ["aws.ecr"],
                detail: {
                    "eventSource": ["ecr.amazonaws.com"],
                    "eventName": ["CreateRepository"],
                    "eventType": ["AwsServiceEvent", "AwsApiCall"],
                    "errorCode": [{ "exists": false }]
                }
            }
        })
        rule.addTarget(new targets.LambdaFunction(fn_add_repo_policy));

        // ecr pull through caching rules
        const cfn_pull_thru_ecr_public = new ecr.CfnPullThroughCacheRule(this, 'PullThroughCacheRule_ECRPublic', {
            ecrRepositoryPrefix: 'ecr-public',
            upstreamRegistryUrl: 'public.ecr.aws'
        });

        const cfn_pull_thru_quay = new ecr.CfnPullThroughCacheRule(this, 'PullThroughCacheRule_Quay', {
            ecrRepositoryPrefix: 'quay',
            upstreamRegistryUrl: 'quay.io'
        });

        // build project to pull containers
        const build_project = new codebuild.Project(this, 'CodeBuild_ContainerPull', {
            projectName: 'omx-container-pull',
            description: 'pulls container images into ECR Private repos',
            environment: {
                buildImage: codebuild.LinuxBuildImage.STANDARD_6_0,
                privileged: true,
                environmentVariables: {
                    SOURCE_URI: { value: '' }, 
                    IMAGE_TAG: { value: '' },
                    PULL_THROUGH_SUPPORTED: { value: '' },
                    ECR_REPO_NAME: { value: '' },
                    AWS_ACCOUNT_ID: { value: props?.env?.account }
                }
            },
            buildSpec: codebuild.BuildSpec.fromObject({
                version: 0.2,
                env: {
                    shell: 'bash'
                },
                phases: {
                    pre_build: {
                        commands: [
                            'echo Logging in to Amazon ECR...',
                            'REGISTRY=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com',
                            'aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $REGISTRY'
                        ]
                    },
                    build: {
                        commands: [
                            'REGISTRY=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com',
                            
                            // pull through supported uris
                            '[[ "$PULL_THROUGH_SUPPORTED" == "true" ]] && echo "Materializing image ... $REGISTRY/$ECR_REPO_NAME:$IMAGE_TAG" || true',
                            '[[ "$PULL_THROUGH_SUPPORTED" == "true" ]] && docker pull $REGISTRY/$ECR_REPO_NAME:$IMAGE_TAG || true',

                            // other uris
                            '[[ "$PULL_THROUGH_SUPPORTED" == "false" ]] && echo "Retrieving $SOURCE_URI" || true',
                            '[[ "$PULL_THROUGH_SUPPORTED" == "false" ]] && docker pull $SOURCE_URI || true',
                            '[[ "$PULL_THROUGH_SUPPORTED" == "false" ]] && echo "Pushing as $REGISTRY/$ECR_REPO_NAME:$IMAGE_TAG" || true',
                            '[[ "$PULL_THROUGH_SUPPORTED" == "false" ]] && docker tag $SOURCE_URI $REGISTRY/$ECR_REPO_NAME:$IMAGE_TAG || true',
                            '[[ "$PULL_THROUGH_SUPPORTED" == "false" ]] && docker push $REGISTRY/$ECR_REPO_NAME:$IMAGE_TAG || true',

                        ]
                    }
                }
            })
        })

        const policy_build_project = new iam.Policy(this, 'Policy_BuildProjectECRAccess', {})
        policy_build_project.addStatements(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:CompleteLayerUpload",
                    "ecr:InitiateLayerUpload",
                    "ecr:PutImage",
                    "ecr:UploadLayerPart",
                    "ecr:TagResource"
                ],
                resources: [
                    // "arn:aws:ecr:*:{acct-id}:repository/*",
                    // stack must be deployed per region, so an IAM role per region is used and arn is regionalized
                    cdk.Arn.format(
                        {service: "ecr",resource: "repository", resourceName: "*"}, 
                        this)
                ],
            }),
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    "ecr:BatchImportUpstreamImage",
                    "ecr:CreateRepository",  // this only works with "*" resource
                    "ecr:GetAuthorizationToken"
                ],
                resources: ["*"]
            })
        )

        build_project.role?.attachInlinePolicy(policy_build_project)

        // state-machine to prime container images into ECR        
        // // lambda function to parse image names
        const fn_parse_image_uri = new lambda.Function(this, 'Function_ParseImageURI', {
            runtime: lambda.Runtime.PYTHON_3_9,
            handler: 'lambda_function.lambda_handler',
            code: lambda.Code.fromAsset(path.join(__dirname, 'lambda', 'parse-image-uri'))
        });

        const ProcessImageURI = new buildTasks.BuildContainerTask(this, 'Process Image URI', build_project, {
            SOURCE_URI: { value: sfn.JsonPath.stringAt('$.image.source_uri') },
            IMAGE_TAG: { value: sfn.JsonPath.stringAt('$.image.tag') },
            PULL_THROUGH_SUPPORTED: { value: sfn.JsonPath.stringAt('$.image.pull_through_supported') },
            ECR_REPO_NAME: { value: sfn.JsonPath.stringAt('$.image.ecr_repository') }
        })
        // const PullAndPushContainer = new states.CodeBuildPullContainer(this, 'Pull and Push Container Image', build_project_pull_and_push)
        
        const sfn_workflow = new sfn.StateMachine(this, 'StateMachine', {
            stateMachineName: 'omx-container-puller',
            definition: new sfn.Map(this, 'Manifest Items', {
                itemsPath: "$.manifest",
                // Default maxConcurrency for inline Map state is 40. 
                // This is below the default limit for concurrent CodeBuild Project builds which is 60
                // For safety set this to 10 for enough headroom
                maxConcurrency: 10
            }).iterator(
                //ParseNameAndTag
                new tasks.LambdaInvoke(this, 'Parse Image URI', {
                    lambdaFunction: fn_parse_image_uri,
                    payload: sfn.TaskInput.fromObject({"uri.$": "$"}),
                    payloadResponseOnly: true
                })
                .next(
                    new ecrTasks.EcrDescribeImage(this, 'ECR Describe Image', {
                        repositoryName: sfn.JsonPath.stringAt('$.image.ecr_repository'),
                        imageTag: sfn.JsonPath.stringAt('$.image.tag'),
                        resultPath: '$.image_details',
                        resultSelector: {
                            "registry.$": "$.ImageDetails[0].RegistryId",
                            "repositoryName.$": "$.ImageDetails[0].RepositoryName",
                            "imageTag.$": "$.ImageDetails[0].ImageTags[0]"
                        }
                    }).addFallback(
                        // check that repo name is supported by ECR pull through caching
                        new sfn.Choice(this, 'Is Pull Through Supported?')
                            .when(
                                sfn.Condition.stringEquals('$.image.pull_through_supported', 'true'),
                                ProcessImageURI
                            )
                            .otherwise(
                                // not a pull through supported repository
                                // check if repository already exists
                                new ecrTasks.EcrDescribeRepository(this, 'ECR Describe Repository', {
                                    repositoryNames: sfn.JsonPath.stringAt('States.Array($.image.ecr_repository)'),
                                    resultPath: '$.repository.details'
                                })
                                .addFallback(
                                    new ecrTasks.EcrCreateRepository(this, 'ECR Create Repository', {
                                        repositoryName: sfn.JsonPath.stringAt('$.image.ecr_repository'),
                                        tags: [
                                            {Key: "createdBy", Value: "omx-ecr-helper"}
                                        ],
                                        resultPath: '$.repository.created'
                                    })
                                    .next(ProcessImageURI)
                                )
                                .next(
                                    ProcessImageURI
                                )
                            )
                    )
                )
                .next(
                    new sfn.Pass(this, 'Image Exists', {
                        parameters: {
                            "image.$": "$.image",
                            "status": "SKIPPED",
                            "statusMessage.$": 
                                "States.Format('image {}:{} exists in registry {}', $.image.ecr_repository, $.image.tag, $.image_details.registry)"
                        }
                    })
                )
            )
        })

    }
}
