#!/bin/env python3

"""
Generates a parameter json for AWS HealthOmics workflows
from NF-CORE nextflow schema JSON.
"""

from argparse import ArgumentParser, FileType
import json
from pprint import pprint
import logging
import sys

# Create a logger
logging.basicConfig(format="%(name)s - %(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

parser = ArgumentParser(description="A script to parse the nf-core nextflow_schema.json to \
                        generate the parameter-temmplate.json required while creating an AWS HealthOmics workflow")
parser.add_argument('nfcore_schema_file', 
                    nargs='?',
                    type=FileType('r'),
                    default=sys.stdin,
                    help="nextflow schema JSON used in NF-CORE nextflow workflows")
parser.add_argument('output_file', 
                    nargs='?',
                    type=FileType('w'),
                    default=sys.stdout,
                    help="output file name")
args = parser.parse_args()

if args.nfcore_schema_file.isatty():
    parser.print_help()
    exit(1)
    
def create_param_json(schema):
    parameter_json_object = {}
    
    if "definitions" not in schema:
        raise KeyError("Schema does not contain key: definitions")
    
    for key, value in schema["definitions"].items():
        logger.info("processing key: %s" % key)
        if "required" in value:
            required_params = value["required"]
        else:
            required_params = []

        if "properties" not in value:
            raise KeyError("Schema does not contain key: properties")
        
        for param_key, param_value in value["properties"].items():
            logger.info("processing param key: %s" % param_key)
            parameter_json_object[param_key] = {}
            
            if "description" not in param_value:
                raise KeyError("Schema does not contain key: description")
            parameter_json_object[param_key]["description"] = param_value["description"]

            if param_key in required_params:
                parameter_json_object[param_key]["optional"] = False
            else:
                parameter_json_object[param_key]["optional"] = True

    return parameter_json_object


if __name__ == "__main__":
    args = parser.parse_args()
    logger.info("opening schema file")

    schema = json.load(args.nfcore_schema_file)
    
    logger.info("creating parameter json")
    parameter_json_object = create_param_json(schema)

    logger.info("printing parameter json")
    json.dump(parameter_json_object, args.output_file, indent=4)
