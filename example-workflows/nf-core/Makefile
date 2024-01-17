include ../_scripts/common.mk

# nf-core workflows use containers that can be pulled with omx-ecr-helper
# container manifests are specific to each workflow
build/sfn-container-puller-%: build/config.json build/omx-container-puller
	$(PYTHON) $(scripts)/build.py -c $(config) sfn -t container-puller -n $* workflows/$*/container_image_manifest.json

# nf-core workflows use samplesheets as input the S3URIs therein need to be regionalized accordingly
# the samplesheet itself needs to be staged in S3
build/samplesheet-%.csv build/samplesheet-%-uri: build/config.json build/s3-staging-uri
	$(PYTHON) $(scripts)/build.py -c $(config) samplesheet $*

run-%: build/config.json build/sfn-container-puller-% build/workflow-% build/s3-output-uri build/iam-workflow-role build/samplesheet-%-uri
	$(PYTHON) $(scripts)/build.py -c $(config) run $*
