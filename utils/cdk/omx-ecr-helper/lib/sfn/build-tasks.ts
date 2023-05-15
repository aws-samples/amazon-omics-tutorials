import { Construct } from 'constructs';

import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { Duration } from 'aws-cdk-lib';


export class BuildContainerTask extends tasks.CodeBuildStartBuild {
    constructor(scope: Construct, id: string, build_project: codebuild.Project, environment_variables: { [name: string]: codebuild.BuildEnvironmentVariable }, timeout_minutes = 60) {
        super(scope, id, {
            project: build_project,
            environmentVariablesOverride: environment_variables,
            integrationPattern: sfn.IntegrationPattern.RUN_JOB,
            taskTimeout: sfn.Timeout.duration(Duration.minutes(timeout_minutes)),
            resultSelector: {
                "id.$": "$.Build.Id",
                "status.$": "$.Build.BuildStatus"
            },
            resultPath: "$.build"
        })

        this.addRetry({
            errors: ['States.TaskFailed'],
            maxAttempts: 1
        })

        this.addCatch(
            new FailedBuildHandler(this, id), {
                resultPath: '$.error'
            }
        )

        this.next(
            new sfn.Pass(this, this.id + ' - Success', {
                parameters: {
                "image.$": "$.image",
                "status.$": "$.build.status"
                }
            })
        )
    }
}


export class FailedBuildHandler extends sfn.Pass {
    constructor(scope: Construct, id: string) {
        super(scope, id + ' - FailedBuildHandler', {
            parameters: {
            "image.$": "$.image",
            "error.$": "States.StringToJson($.error.Cause)"
            }
        })

        this.next(
            new sfn.Pass(scope, id + ' - CauseProcessor', {
            parameters: {
                "image.$": "$.image",
                "build": {
                    "id.$": "$.error.Build.Id",
                    "logs": {
                        "logstream.$": "$.error.Build.Logs.CloudWatchLogsArn",
                        "deeplink.$": "$.error.Build.Logs.DeepLink"
                    }
                },
                "status.$": "$.error.Build.BuildStatus",
                "statusMessage": "Container pull failed. Check build logs."
            }
            })
        )
    }
}

