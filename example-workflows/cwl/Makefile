include ../_scripts/common.mk

# gatk workflows all use the same containers which can be pulled with omx-ecr-helper
build/sfn-container-puller: build/config.json build/omx-container-puller
	$(PYTHON) $(scripts)/build.py -c $(config) sfn -t container-puller containers/container_image_manifest.json

run-%: build/config.json build/sfn-container-puller build/workflow-% build/s3-output-uri build/iam-workflow-role
	$(PYTHON) $(scripts)/build.py -c $(config) run $*
