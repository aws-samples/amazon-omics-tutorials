# Agentic Generative AI Tutorial

This document explains how you can use Agentic AI tools to create workflows and interact with the [AWS HealthOmics](https://docs.aws.amazon.com/omics/latest/dev/what-is-healthomics.html) service using natural language prompts.

## What is Amazon Q Developer CLI
[Amazon Q Developer](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/what-is.html) for command line (Amazon Q Developer CLI) is a powerful agentic AI tool that can perform many actions including generating code and interacting with AWS and other command line tools on your machine to acheive complex tasks. Amazon Q for command line integrates contextual information, providing Amazon Q with an enhanced understanding of your use case, enabling it to provide relevant and context-aware responses. As you begin typing, Amazon Q populates contextually relevant subcommands, options, and arguments.

## Prerequisites
1. Access to an AWS Account.
2. A role that includes access to HealthOmics and Q Developer.
3. An [installation](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-installing.html) of Q Developer CLI.
4. You should review the [security considerations and best practices](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-chat-security.html) guidance before using Q CLI's generative and agentic AI capabilities.

## Understanding Contexts
Contexts can be used to give Q CLI access to additional information beyond what it's internal LLM model was trained on. The model has a good 'native' understanding of WDL, Nextflow and CWL. By giving Q access to contextual information about the HealthOmics service and how it operates, Q can improve it's ability to author workflows, create them in HealthOmics, run them, debug them and improve them. When you interact with Q it maintains a context of some or all of your current session. By creating a context we can ensure that Q always has access to this additional context throughout your session, including at the very start before you have issued any commands.

## Step 1: Create a context and profile
Profiles allow you to switch between contexts. We will create a profile that contains context relevant HealthOmics. We will call the profile `aho` (short for AWS HealthOmics) but you can use a different name if desired.

At any time you can quit Q CLI with `/quit`

1. Clone the repository or copy `contexts\` and `rules\` to your local machine. A good location is `~/.healthomics/` but it can be anywhere.
   ```bash
   mkdir -p ~/.healthomics
   cp -r contexts/ rules/ ~/.healthomics/
   ```
2. Start a Q chat session with `q chat`
3. In the chat session type `/profile create aho`
4. Your profile should now be created and your session set to this profile. You can use `/profile set aho` to set the profile when starting a later session.
5. Add the content of `~/.healthomics/` to your context `/context add ~/.healthomics/**/*`
6. Verify your context now contains the location you added `/context show`


## Step 2: Create and run a workflow
At this point you are ready to start exploring what Q Developer CLI can do for you. The exact set of steps you take is going to depend a lot on what you ask Q to do and how it responds. Generative AI is non-deterministic and the actions Q takes will depend on what you ask it to do and the context of your session so far. At times Q will ask you for permission to perform actions. You should review these before accepting (`y`). For your first few interactions it is better to not let it run automatically in trusted mode (`t`) so you can get a good feel for what the tool is doing.

These are some suggestions of things you can ask it to do but feel free to diverge and explore:
1. *"Create a WDL 1.1 workflow file as `main.wdl` that will run on HealthOmics. The workflow will take a reference genome as an input and pairs of fastq files. It will index the reference genome using BWA and then map each pair of fastq files to the reference. Finally to a single BAM file and output this file and it's bai index."*
2. *"Package the workflow and create it in HealthOmics"*
3. *"Update the inputs.json file to use real files from my S3 bucket `my-bucket-with-genome-data`"* (You can give it a more specific location or you can let it explore)
4. *"Find suitable containers in my ECR respositories and update inputs.json to use these"*
5. *"Find or create a suitable IAM role to use when running the workflow"*
6. *"Create a run cache for my workflow"*
7. *"Run the workflow in HealthOmics"*
8. *"Check the status of the run"*

## Step 3: Debug
If the workflow fails it might be that the generated workflow has a bug (or two) or the selected inputs might not be suitable. If something goes wrong Q can help diagnose the problem.

1. *"My run (12345678) failed, diagnose the cause of the error and suggest fixes"*
2. *"Update my workflow definition with the suggested fixes" or "Update my inputs.json with the suggested fixes"*
3. *"Package the workflow and create a new workflow version in HealthOmics"*
4. *"Run the new version of the workflow"*
5. *"Create a run cache and run the new version of the workflow with the cache"*

## Step 4: On Success
Once a run has finished you can try things like:

1. *"Download the output files to xyz"*
2. *"Analyze the metrics of the run and suggest improvements to resource allocation"*
3. *"Modify my workflow definition to incorporate the suggested improvements"*

## Step 5: Clean Up
If you wish to remove artifacts created in the session, you can ask Q to:

1. *"Delete my run outputs"*
2. *"Delete my workflow from HealthOmics"*
3. *"Delete any run caches or IAM roles you created in this session"*
4. You can type `/quit` to exit Q developer CLI at any time.

