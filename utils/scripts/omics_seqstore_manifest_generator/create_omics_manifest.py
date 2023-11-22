import sys
import getopt
import argparse
import csv 
import json
import uuid
import time
import ast

def del_none(d):
    """
    Delete keys with the value ``None`` in a dictionary, recursively.

    This alters the input so you may wish to ``copy`` the dict first.
    """
    # For Python 3, write `list(d.items())`; `d.items()` won’t work
    for key, value in list(d.items()):
        if value is None:
            del d[key]
        elif isinstance(value, dict):
            del_none(value)
    return d  # For convenience

def del_non_console(d):
    """
    Delete keys that are ignored in the console recursively.
    """
    keys_ignored_in_console = ['referenceArn']
    
    for key in keys_ignored_in_console:
        if key in d:
            del d[key]

    return d  # For convenience


def process_tag(tag_text):
    """
    Takes in a tag string and converts it into a tag dictionary
    """
    if tag_text.strip():
        tag = ast.literal_eval(str(tag_text))
    else:
        tag = ''
    return tag

def row_to_source(csvRow, location):
    """
    Converts a CSV row into a manifest row 
    """
    #convert each csv row into python dict
    primary_fields = ['sourceFileType', 'subjectId', 'sampleId','referenceArn','name','description','generatedFrom','tags']

    d = {k: (None if str(v).strip() == '' else v) for k, v in csvRow.items() if k in primary_fields}
    d['sourceFiles'] = {k: v for k, v in csvRow.items() if k not in primary_fields and v}
    # result.append(d)

    # Some basic sanity checks for inputs            
    if d['sourceFileType'] not in ('BAM','CRAM','FASTQ','UBAM'):
        sys.exit('\nERROR: sourceFileType has a controlled vocabulary, it must be "BAM", "CRAM", "FASTQ","UBAM". Please check the entries in the CSV/TSV')
    if not d['sourceFiles']['source1'].startswith('s3://'):
        sys.exit('\nERROR: sourceFile source1 does not begin with s3. The file must be in s3 to load into the sequence store.')
    if (d['sourceFileType'] == 'BAM' and not d['sourceFiles']['source1'].endswith('.bam')):
        sys.exit('\nERROR: BAM files must end with .bam')
    if (d['sourceFileType'] == 'UBAM' and not d['sourceFiles']['source1'].endswith('.bam')):
        sys.exit('\nERROR: UBAM files must end with .bam')
    if (d['sourceFileType'] == 'CRAM' and not d['sourceFiles']['source1'].endswith('.cram')):
        sys.exit('\nERROR: CRAM files must end with .cram')
    if d['sourceFileType'] in ['BAM','CRAM'] and not d.get('referenceArn','') and location != 'console':
        sys.exit('\nERROR: A referenceArn is required if the source file type is BAM or CRAM.')   
    if (d['sourceFileType'] != 'FASTQ' and d['sourceFiles'].get('source2','').strip()):
        sys.exit('\nERROR: Source 2 can only be provided for FASTQ source file types')    
    if d['sourceFileType'] == 'FASTQ':
        if not d['sourceFiles']['source1'].endswith(('.fastq.gz','.fq.gz')):
            sys.exit('\nERROR: sourceFile source1 is a FASTQ but it does not end with fastq.gz or fq.gz.')
        if d['sourceFiles'].get('source2',''):
        # source 2 is optional so only validating source 2 only if it exists
            if not d['sourceFiles']['source2'].startswith('s3://'):
                sys.exit('\nERROR: sourceFile source2 does not begin with s3. The file must be in s3 to load into the sequence store.')
            if not d['sourceFiles']['source2'].endswith(('.fastq.gz','.fq.gz')):
                sys.exit('\nERROR: sourceFile source2 is a FASTQ but it does not end with fastq.gz or fq.gz.')

    #process tags from string into dictionary
    if d.get('tags',''):
        tags = process_tag(d.get('tags',''))
        if tags:
            d['tags'] = tags

    # delete values that are none or empty
    d=del_none(d)    
    
    # deletes keys that the console ignores
    if location == 'console':
        d=del_non_console(d)
    
    return d

def launch_import(region, roleArn, sequenceStoreId, sourceDict, jobProfileName):
    """
    Launches an import job based on the region provided and the generated json
    """
    import boto3

    if jobProfileName and jobProfileName != 'NA':
        boto3.setup_default_session(profile_name=jobProfileName)
    
    omics_client = boto3.client('omics', region_name=region)
    token = str(uuid.uuid4())
    
    print('Manifest: \n', sourceDict)
    time.sleep(1)

    try:
        import_job = omics_client.start_read_set_import_job(
            clientToken=token,
            roleArn=roleArn,
            sequenceStoreId=sequenceStoreId,
            sources=sourceDict
        )
        print('\nImport Jobs started successfully\n\n',import_job)
    except Exception as error:
        print(error)
        sys.exit('\nERROR: Import Jobs start failed\n\n')
        
    
    
def write_run_manifest(location, jsonFilePath, fileCounter, jsonArray, omicsSeqStoreID, omicsRoleArn, launchJob, jobRegion,jobProfileName):
    """
    Writes out a file for the manifest created
    """
    jsonFilePathFull=f'{jsonFilePath}_{str(fileCounter)}.json'
    
    
    # launches import job if configured
    if launchJob:
        launch_import(jobRegion, omicsRoleArn, omicsSeqStoreID, jsonArray, jobProfileName)
    
    # manifest writer
    else:
        
        # adds in api specific configurations and nests the sources array
        if location == 'api':
            jsonArray = {'sequenceStoreId':omicsSeqStoreID, 
                         'roleArn':omicsRoleArn,
                         'sources':jsonArray}

        # dumps either the rewritten jsonArray for the API or the original
        jsonString = json.dumps(jsonArray, indent=4)

        with open(jsonFilePathFull, 'w', encoding='utf-8') as jsonf: 
            jsonf.write(jsonString)
        
        
def input_to_json(inFilePath, jsonFilePath, sourceQuota, delimiter, omicsRoleArn, omicsSeqStoreID, location, launchJob, jobRegion,jobProfileName):
    jsonArray = []
    delims = {'csv':',','tsv':'\t'}

    #read csv file
    primary_fields = ['sourceFileType', 'subjectId', 'sampleId','referenceArn','name','description','generatedFrom']
    result = []
    sampleCounter=0
    fileCounter=1

    with open(inFilePath, mode='r', encoding='utf-8-sig') as input_file: 
        #load csv file data using csv library's dictionary reader
        csvReader = csv.DictReader(input_file, delimiter=delims.get(delimiter, delims['csv']))

        #convert each csv row into python dict
        for row in csvReader: 
            sampleCounter += 1
            d = row_to_source(row, location)
            jsonArray.append(d)

            if sampleCounter == sourceQuota :
                write_run_manifest(location, jsonFilePath, fileCounter, jsonArray, omicsSeqStoreID, omicsRoleArn, launchJob, jobRegion,jobProfileName)
                
                sampleCounter = 0
                jsonArray = []
                fileCounter += 1
  
    #convert python jsonArray to JSON String and write to file
    write_run_manifest(location, jsonFilePath, fileCounter, jsonArray, omicsSeqStoreID, omicsRoleArn, launchJob, jobRegion,jobProfileName)


# Driver Code

# Decide the two file paths according to your
# computer system

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input', type=str, required=True, dest='input', 
                        help='The csv/tsv file that containes the list of s3 locations for the files to load into the AWS HealthOmics Sequence Store')
    parser.add_argument('-o', '--outputPrefix', type=str, required=True, dest='outputPrefix', 
                        help='The prefix for the output JSON file containing all the sequences in the csv/tsv.')
    parser.add_argument('-d', '--delimiter', type=str, default='csv', dest='type', choices=['csv','tsv'],
                        help='The input file type csv or tsv. options: csv/tsv default: csv')
    parser.add_argument('-l', '--location', type=str, default='console', dest='location', choices=['api','console'],
                        help='Optional if you are loading the JSON through the console or api directly. This will be auto set to \
                        api if you are launching a job. options: console/api default: console')
    parser.add_argument('-r', '--role-arn', type=str, default='NA', dest='roleArn', 
                        help='Required for API manifest and job launching: The IAM Role omics will use to import the genomic readsets')
    parser.add_argument('-s', '--seq-store-id', type=str, default='NA', dest='seqID', 
                        help='Required for API manifest and job launching: The AWS HealthOmics Sequence Store ID you will be loading the import sets to.')
    parser.add_argument('-c', '--json-batch-quota', type=int, default=100, dest='seqStoreQuota', 
                        help='Optional therwise set for default in AWS HealthOmics: The number of samples in a JSON file. \
                        AWS HealthOmics has a Maximum Import Job Read Sets quota of 100 at this time.')
    parser.add_argument('-j', '--launch-job', default=False, action="store_true", dest='launchJob', 
                        help='Optional flag used to launch the sequence store import job. Add this flag to generate an import jobs \
                        instead of generating a manifest.')
    parser.add_argument('-jr', '--job-region', type=str, default='NA', dest='jobRegion', 
                        help='Required only for launching a job. This is the region where the import job will be \
                        launched and should match the region of the s3 files and sequence store.')
    parser.add_argument('-jp', '--job-profile-name', type=str, default='NA', dest='jobProfileName', 
                        help='Optional and only considered for launching a job. The profile name for boto3 to use if you \
                        do not want it to use the default profile configured.')


    args = parser.parse_args()

    # overwrites the location argument if the user is trying to launch a job
    args.location = 'api' if args.launchJob else args.location

    print('\nArguments used:\ninput:', args.input)
    print('Output:', args.outputPrefix)
    print('Delimiter:', args.type)
    print('Manifest location:', args.location)
    print('IAM role Arn:', args.roleArn)
    print('Sequence store ID:', args.seqID)
    print('Batch size:', args.seqStoreQuota)
    print('Launch job:', args.launchJob)
    print('Job region:', args.jobRegion)
    print('Profile name:', args.jobProfileName,'\n')

    if args.location == 'api' and (args.roleArn == 'NA' or args.seqID == 'NA'):
        sys.exit('\nERROR: You need both the IAM Role arn and the AWS HealthOmics Sequence Store ID to generate the api manifest or launch a job.')

    if args.launchJob and args.jobRegion == 'NA':
        sys.exit('\nERROR: A job region, IAM Role arn, and AWS HealthOmics Sequence Store ID must be provided if the load location is job.')
        
    input_to_json(args.input, 
                  args.outputPrefix, 
                  args.seqStoreQuota, 
                  args.type, 
                  args.roleArn, 
                  args.seqID, 
                  args.location,
                  args.launchJob, 
                  args.jobRegion,
                  args.jobProfileName)
