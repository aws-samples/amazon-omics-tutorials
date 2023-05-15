import { Arn, Stack } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import { PolicyStatement } from 'aws-cdk-lib/aws-iam';


// replicating the task construct pattern for CodeBuildStartBuild
// https://github.com/aws/aws-cdk/blob/main/packages/aws-cdk-lib/aws-stepfunctions-tasks/lib/codebuild/start-build.ts
export class EcrDescribeImage extends sfn.TaskStateBase {
    protected readonly taskMetrics?: sfn.TaskMetricsConfig | undefined;
    protected readonly taskPolicies?: PolicyStatement[] | undefined;
    
    constructor(scope: Construct, id: string, private readonly props: EcrDescribeImageProps) {
        super(scope, id, props);
        this.taskPolicies = [
            new PolicyStatement({
                actions: ["ecr:DescribeImages"],
                resources: [
                    Arn.format(
                        {service: "ecr", resource: "repository", resourceName: "*"},
                        Stack.of(this))
                ]
            })
        ];
    }

    protected _renderTask(): any {
        return {
            Resource: "arn:aws:states:::aws-sdk:ecr:describeImages",
            Parameters: sfn.FieldUtils.renderObject({
                RepositoryName: this.props.repositoryName,
                ImageIds: [ 
                    {ImageTag: this.props.imageTag}
                ]
            })
        }
    }

    public addFallback(fallback: sfn.IChainable): EcrDescribeImage {
        this.addCatch(
            new sfn.Pass(this, 'ECR Image Does Not Exist', {
                parameters: { "image.$": "$.image" }
            }).next(fallback),
            { resultPath: "$.error" }
        )
        return this;
    }
}


export interface EcrDescribeImageProps extends sfn.TaskStateBaseProps {
    readonly repositoryName: string
    readonly imageTag: string
}


export class EcrDescribeRepository extends sfn.TaskStateBase {
    protected readonly taskMetrics?: sfn.TaskMetricsConfig | undefined;
    protected readonly taskPolicies?: PolicyStatement[] | undefined;

    constructor(scope: Construct, id: string, private readonly props: EcrDescribeRepositoryProps) {
        super(scope, id, props);
        this.taskPolicies = [
            new PolicyStatement({
                actions: ["ecr:DescribeRepositories"],
                resources: [
                    Arn.format(
                        {service: "ecr", resource: "repository", resourceName: "*"},
                        Stack.of(this))
                ]
            })
        ];
    }

    protected _renderTask(): any {
        return {
            Resource: "arn:aws:states:::aws-sdk:ecr:describeRepositories",
            Parameters: sfn.FieldUtils.renderObject({
                RepositoryNames: this.props.repositoryNames
            })
        }
    }

    public addFallback(fallback: sfn.IChainable): EcrDescribeRepository {
        this.addCatch(
            new sfn.Pass(this, 'ECR Repository Does Not Exist', {
                parameters: { "image.$": "$.image" }
            }).next(fallback),
            { resultPath: "$.error" }
        )
        return this;
    }
}


export interface EcrDescribeRepositoryProps extends sfn.TaskStateBaseProps {
    readonly repositoryNames: string
}


export class EcrCreateRepository extends sfn.TaskStateBase {
    protected readonly taskMetrics?: sfn.TaskMetricsConfig | undefined;
    protected readonly taskPolicies?: PolicyStatement[] | undefined;

    constructor(scope: Construct, id: string, private readonly props: EcrCreateRepositoryProps) {
        super(scope, id, props);
        this.taskPolicies = [
            new PolicyStatement({
                actions: [
                    "ecr:CreateRepository",
                    "ecr:TagResource"
                ],
                resources:[
                    Arn.format(
                        {service: "ecr", resource: "*"},
                        Stack.of(this))
                ]
            })
        ]
    }

    protected _renderTask() {
        return {
            Resource: "arn:aws:states:::aws-sdk:ecr:createRepository",
            Parameters: sfn.FieldUtils.renderObject({
                RepositoryName: this.props.repositoryName,
                Tags: this.props.tags
            })
        }
    }
}


export interface EcrCreateRepositoryProps extends sfn.TaskStateBaseProps {
    readonly repositoryName: string
    readonly tags?: [{Key: string, Value: string}]
}

