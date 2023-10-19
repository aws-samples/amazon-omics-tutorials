SHELL = /bin/bash

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
	python3 ${scripts}/build.py -c $(config) config

build/omx-ecr-helper: build/config.json
	sed 's#{{staging_uri}}#$(staging_uri)#g' $(assets)/omx-ecr-helper-config.json > $(cdk_app_config)
	export CDK_APP_CONFIG=$(cdk_app_config)
	export CDK_DEPLOY_REGION=$(region)
	if [[ $(profile) -eq $(default_profile_name) ]]; then \
			cdk deploy --all --require-approval never  $(cdk_app) $(cdk_out); \
	else \
			cdk deploy --all --require-approval never --profile $(profile) $(cdk_app) $(cdk_out); \
	fi

build/workflow-%: build/config.json build/s3-staging-uri
	python3 $(scripts)/build.py -c $(config) workflow $*

build/s3-output-uri build/s3-staging-uri: build/config.json
	python3 $(scripts)/build.py -c $(config) s3

build/iam-workflow-role: build/config.json
	python3 $(scripts)/build.py -c $(config) iam

.PHONY: clean test

# this only removes local artifacts
# AWS resources (e.g. ecr repositories, s3 buckets, workflows, and runs) will need to be removed manually
clean:
	rm -rf build/

test:
	@echo "this is a test"