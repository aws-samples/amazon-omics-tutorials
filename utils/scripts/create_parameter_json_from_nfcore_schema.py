#!/bin/env python3

"""
Generates a parameter json for AWS HealthOmics workflows
from NF-CORE nextflow schema JSON.
"""

from argparse import ArgumentParser
import json
from pprint import pprint
import logging

# Create a logger
logging.basicConfig(format="%(name)s - %(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

parser = ArgumentParser()
parser.add_argument('--nfcore_schema_file', type=str, required=True,
                    help="nextflow schema JSON used in NF-CORE nextflow workflows")
parser.add_argument('--output_file', type=str, required=True,
                    help="output file name")
    
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
    with open(args.nfcore_schema_file) as f:
        schema = json.load(f)
    
    logger.info("creating parameter json")
    parameter_json_object = create_param_json(schema)

    logger.info("printing parameter json")
    with open(args.output_file, "w") as f:
        json.dump(parameter_json_object, f, indent=4)
