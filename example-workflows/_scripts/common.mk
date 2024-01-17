SHELL = /bin/bash
PYTHON = /usr/bin/env python

scripts = ../_scripts
assets = ../_scripts/assets
config = ../_conf/default.ini

omx_ecr_helper = $(shell jq -r '.omx_ecr_helper' build/config.json)
profile = $(shell jq -r '.profile' build/config.json)
region = $(shell jq -r '.region' build/config.json)
staging_uri = $(shell jq -r '.staging_uri' build/config.json)
cdk_app = --app 'npx ts-node --prefer-ts-exts $(omx_ecr_helper)/bin/omx-ecr-helper.ts'
cdk_out = -o build/omx-ecr-helper/cdk.out
cdk_app_config = build/omx-ecr-helper-config.json
default_profile_name = default

# keep all build assets
.NOTINTERMEDIATE:
.SECONDARY:

build/:
	mkdir -p build

build/config.json: build/
	$(PYTHON) ${scripts}/build.py -c $(config) config

build/omx-container-%: build/config.json
	@if [[ $(profile) == $(default_profile_name) ]]; then \
		export PROFILE="--profile $(profile)"; \
	fi
	@if [[ "null" == $$(aws $$PROFILE --region $(region) stepfunctions list-state-machines --query 'stateMachines[?name==`omx-container-$*`] | [0]') ]]; then \
		( \
			echo "ECR Helper for HealthOmics not found. Refer to: https://github.com/aws-samples/amazon-ecr-helper-for-aws-healthomics"; \
			exit 1 \
		); \
	fi

build/workflow-%: build/config.json build/s3-staging-uri
	$(PYTHON) $(scripts)/build.py -c $(config) workflow $*

build/s3-output-uri build/s3-staging-uri: build/config.json
	$(PYTHON) $(scripts)/build.py -c $(config) s3

build/iam-workflow-role: build/config.json
	$(PYTHON) $(scripts)/build.py -c $(config) iam

.PHONY: clean test

# this only removes local artifacts
# AWS resources (e.g. ecr repositories, s3 buckets, workflows, and runs) will need to be removed manually
clean:
	rm -rf build/

test:
	@echo "this is a test"