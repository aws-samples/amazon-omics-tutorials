include ../_scripts/common.mk

# nf-core workflows use containers that can be pulled with omx-ecr-helper
# container manifests are specific to each workflow
build/sfn-container-puller-%: build/config.json build/omx-container-puller
	$(PYTHON) $(scripts)/build.py -c $(config) sfn -t container-puller -n $* workflows/$*/container_image_manifest.json

run-%: build/config.json build/sfn-container-puller-% build/workflow-% build/s3-output-uri build/iam-workflow-role 
	$(PYTHON) $(scripts)/build.py -c $(config) run $*
