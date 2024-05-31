include ../_scripts/common.mk

# protein folding workflows all use the same containers that need to be built with omx-ecr-helper
build/sfn-container-builder: build/config.json build/omx-container-builder build/s3-staging-uri
	aws --profile $(profile) --region $(region) s3 sync ./containers $(staging_uri)/containers
	sed 's#{{staging_uri}}#$(staging_uri)#g' containers/container_build_manifest.json > build/container_build_manifest.json
	$(PYTHON) $(scripts)/build.py -c $(config) sfn -t container-builder build/container_build_manifest.json


# this depends on build/sfn-container-builder
# but it is an expensive (time wise) operation 
# that only needs to be run once
#run-%: build/sfn-container-builder build/config.json build/workflow-% build/s3-output-uri build/iam-workflow-role
run-%:  build/config.json build/workflow-% build/s3-output-uri build/iam-workflow-role
#	@if [[ ! -f "build/sfn-container-builder-output" ]]; then echo "build/sfn-container-builder required" && exit 1; fi
	$(PYTHON) $(scripts)/build.py -c $(config) run $*
