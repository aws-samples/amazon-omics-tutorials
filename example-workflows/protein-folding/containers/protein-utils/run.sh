#!/bin/bash

# Copyright 2013-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the
# License. A copy of the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "LICENSE.txt" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and
# limitations under the License.

# This script can help you download files from S3, run a command, and then
# upload the results back up to S3
#
# Usage: 
# bash run.sh \
#   && -i s3://mybucket/file.text:/home/user/file.txt \
#   && -i s3://mybucket/myfolder/:/home/user/myfolder/ \
#   && -o /home/user/output.txt:s3://mybucket/output.txt \
#   && -o /home/user/myresults/:s3://mybucket/myresults/ \
#   && mycmd \
#   [ Additional script arguments ]
set -e

# Adapted from https://github.com/awslabs/aws-batch-helpers/blob/master/fetch-and-run/fetch_and_run.sh
STARTTIME=`date +%s`
BASENAME="${0##*/}"

usage () {
  if [ "${#@}" -ne 0 ]; then
    echo "* ${*}"
    echo
  fi
  cat <<ENDUSAGE
Usage:
bash run.sh [options] <command> [parameters]

Options:
    -i (string)

    The download source and destination paths in the format "s3://<bucket>/<key>:<local path>"

    -o (string)

    The upload source and destination paths in the format "<local path>:s3://<bucket>/<key>"

ENDUSAGE

  exit 2
}

# Standard function to print an error and exit with a failing return code
error_exit () {
  echo "${BASENAME} - ${1}" >&2
  exit 1
}

# Function to cp files recursively if the last character is a "/"
recursive_cp () {
    if [ ${1:0-1} = "/" ]
    then
        aws s3 cp --recursive $2 $3;
    else
        aws s3 cp $2 $3;
    fi
}

# Check that necessary programs are available
aws --version >/dev/null 2>&1 || error_exit "Unable to find AWS CLI executable."

# Parse inputs
inputs=()
outputs=()
while getopts 'i:o:' OPTION; do
    case "$OPTION" in
        i)
            inputs+=($OPTARG);;
        o)
            outputs+=($OPTARG);;
        *)
            usage
    esac
done 

# Extract command and parameters from input
shift "$(($OPTIND -1))"
command=$@

# Download from s3
for download in ${inputs[@]}
do
    IFS=':'; splitArray=($download); unset IFS;
    if [ ${splitArray[0]} = "s3" ]
    then
        src="${splitArray[0]}:${splitArray[1]}"
        dest=${splitArray[2]}
    else
        src="s3://${splitArray[0]}"
        dest=${splitArray[1]}
    fi
    recursive_cp $src $src $dest
done

echo "Running command '$command'"
eval $command

# Upload to s3
for upload in ${outputs[@]}
do
    IFS=':'; splitArray=($upload); unset IFS;
    if [ ${splitArray[1]} = "s3" ]
    then
        src=${splitArray[0]}
        dest="${splitArray[1]}:${splitArray[2]}"
    else
        src=${splitArray[0]}
        dest="s3://${splitArray[1]}"
    fi
    recursive_cp $src $src $dest
done
ENDTIME=`date +%s`
echo "Process completed in $((ENDTIME-STARTTIME)) sec."