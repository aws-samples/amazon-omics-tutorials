# AWS HealthOmics Sequence Store Manifest Generator script

This is provided AS-IS and is intended to aid in generation of manifests and demonstrate pattern. This is a starting point, feel free to customize as needed to fit your specific requirements.

## create_omics_manifest.py

This script was written to help in the generation of a json manifest for AWS HealthOmics sequence store import jobs. This script is ideally suited to aid in the migration of larges batches of sample data to take advantage of the benefits offered by [AWS HealthOmics storage](https://docs.aws.amazon.com/omics/latest/dev/what-is-service.html) (ex large batches of FASTQs, BAMs, uBAMs or CRAMs).

Simply create a list of your FASTQs, BAMs, uBAMs, or CRAMs in TSV/CSV format (flag -d) and this script will generate the required JSON or even start the import job. (See examples in the *test_files* directory) This script will generate multiple JSON files or jobs if needed based on the number of read sets desired per file (flag -c). In its current form this will prepare files for upload through the console or the CLI (flag -l) or it will start import jobs. 

This script makes a few assumptions:
1. The files are already sitting in S3 in the same region as the sequence store you are ingesting into.
2. The files are going to the same sequence store.
3. For API usage, the omics Role provided has permission to read the S3 bucket where the sample files are sitting and write to the sequence store the files will be ingested into.
4. For Job start, the boto3 configured by default in your python account or the passed in profile has access to start import jobs in HealthOmics on the sequence store provided. 
5. None of the column names in the TSV/CSV have been modified, they are used to build the json.

BAMs and CRAMs require a reference stored in the reference store and you will be required to provide the arn in the api call. uBAMs and FASTQs do not need a reference associated with it.

Please note: AWS HealthOmics has a Maximum Import Job Read Sets quota of **100** at this time. This has been set as the default setting but can be customized to the desired amount using the -c flag. 

usage: create_omics_manifest.py usage: create_omics_manifest.py [-h] -i INPUT -o OUTPUTPREFIX [-d {csv,tsv}] [-l {api,console}] [-r ROLEARN] [-s SEQID] [-c SEQSTOREQUOTA] [-j] [-jr JOBREGION] [-jp JOBPROFILENAME] 

### options:  
  &nbsp;&nbsp;-h, --help  
  
  &nbsp;&nbsp;-i INPUT, --input INPUT  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;The csv/tsv file that containes the list of s3 locations for the files to load into the AWS HealthOmics Sequence Store*  
  
  &nbsp;&nbsp;-o OUTPUT, --output OUTPUT  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;The output JSON file containing all the sequences in the csv/tsv.*  
  
  &nbsp;&nbsp;-d TYPE, --delimiter TYPE  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;The input file type. options: csv/tsv default: csv*  
  
  &nbsp;&nbsp;-l LOCATION, --location LOCATION  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;If you are loading the JSON through the console or api. This will be auto set to api if you are launching a job. options: console/api default: console*  
  
  &nbsp;&nbsp;-r ROLEARN, --role-arn ROLE.ARN  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Required for API manifest and job launching: The IAM Role omics will use to import the genomic read sets*  
  
  &nbsp;&nbsp;-s SEQID, --seq-store-id SEQUENCE.STORE.ID  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Required for API manifest and job launching: The AWS HealthOmics Sequence Store ID you will be loading the import sets to.*  
  
  &nbsp;&nbsp;-c SEQSTOREQUOTA, --json-batch-quota SEQSTOREQUOTA  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Optional otherwise set for default in AWS HealthOmics: The number of samples in a JSON file. AWS HealthOmics has a Maximum Import Job Read Sets quota of 100 at this time.*  
  
  &nbsp;&nbsp;-j LAUNCHJOB, --launch-job LAUNCHJOB  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Optional flag used to launch the sequence store import job. Add this flag to generate an import jobs instead of generating a manifest.*  
  
  &nbsp;&nbsp;-j JOBREGION, --job-region JOBREGION  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Required only for launching a job. This is the region where the import job will be launched and should match the region of the s3 files and sequence store.*  
  
  &nbsp;&nbsp;-jp JOBPROFILENAME, --job-profile-name JOBPROFILENAME  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Optional and only considered for launching a job. The profile name for boto3 to use if you do not want it to use the default profile configured.*  

## Usage
#### Console:
Please note: Because the console has an option to choose the reference, you will need to split your read sets by reference.

Fields for the JSON manifest when uploading through the console:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **name** - your name of the file - *Optional but highly encouraged*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **sampleId** - sample name - *Required*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **subjectId** - subject name - *Required*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **sourceFileType** - FASTQ, BAM, uBAM, or CRAM - *Required*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **source1** - s3 URI for FASTQ R1, BAM, uBAM, or CRAM - *Required*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **source2** - s3 URI for FASTQ R2 - *Optional*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **tags** - json string of any tags to be associated with the read set. - *Optional*   

*tsv:*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Delimiter:** tab  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Example file:** test_files/test_json_console.txt  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Output File:** output_files/output_console_tsv_1.json  
``` 
python3 create_omics_manifest.py -i test_files/test_json_console.txt -o output_files/output_console_tsv -d tsv
```
or
*csv:*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Delimiter:** comma  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Example file:** test_files/test_json_console.csv  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Output File:** output_files/output_console_csv_1.json  
```
python3 create_omics_manifest.py -i test_files/test_json_console.csv -o output_files/output_console_csv
```

#### AWS CLI:
To use the CLI you will need to add some information, but unlike the console you can mix references in one manifest.

Fields for the JSON manifest when uploading through the console:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **name** - your name of the file - *Optional but highly encouraged*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **referenceArn** - the ARN of the reference file (stored in the AWS HealthOmics reference store) which for the sample being uploaded. - *Required for BAM and CRAM only*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **sampleId** - sample name - *Required*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **subjectId** - subject name - *Required*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **sourceFileType** - FASTQ, BAM, uBAM, or CRAM - *Required*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **source1** - s3 URI for FASTQ R1, BAM, uBAM, or CRAM - *Required*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **source2** - s3 URI for FASTQ R2 - *Optional*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **tags** - json string of any tags to be associated with the read set. - *Optional*  

*tsv:*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Delimiter:** tab  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Example file:** test_files/test_json_api.txt  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Output File:** output_files/output_api_tsv_1.json  
``` 
python3 create_omics_manifest.py -i test_files/test_json_api.txt -o output_files/output_api_tsv -d tsv -l api -r arn:aws:iam::111111111111:role/omicsRole -s 2222222222
```
or
*csv:*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Delimiter:** comma  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Example file:** test_files/test_json_api.csv  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Output File:** output_files/output_api_csv_1.json  
```
python3 create_omics_manifest.py -i test_files/test_json_api.csv -o output_files/output_api_csv -l api -r arn:aws:iam::111111111111:role/omicsRole -s 2222222222
```

#### AWS Boto3 Import Jobs:
To use boto3 to launch import jobs, you will need to provide the same information as you would for the API manifest generation.

Fields for the JSON manifest when uploading through the console:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **name** - your name of the file - *Optional but highly encouraged*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **referenceArn** - the ARN of the reference file (stored in the AWS HealthOmics reference store) which for the sample being uploaded. - *Required for BAM and CRAM only*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **sampleId** - sample name - *Required*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **subjectId** - subject name - *Required*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **sourceFileType** - FASTQ, BAM, uBAM, or CRAM - *Required*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **source1** - s3 URI for FASTQ R1, BAM, uBAM, or CRAM - *Required*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **source2** - s3 URI for FASTQ R2 - *Optional*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **tags** - json string of any tags to be associated with the read set. - *Optional*  

*tsv:*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Delimiter:** tab  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Example file:** test_files/test_json_api.txt
``` 
python3 create_omics_manifest.py -i test_files/test_json_api.txt -o output_files/output_api_tsv -d tsv -r arn:aws:iam::111111111111:role/omicsRole -s 2222222222 -j -jr us-west-2 -jp testProfile
```
or
*csv:*  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Delimiter:** comma  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Example file:** test_files/test_json_api.csv
```
python3 create_omics_manifest.py -i test_files/test_json_api.csv -o output_files/output_api_csv -r arn:aws:iam::111111111111:role/omicsRole -s 2222222222 -j -jr us-west-2 -jp testProfile
```

## AWS HealthOmics Sequence Store
For detailed information on how to import manifests into the AWS HealthOmics sequence store, please visit [Sequence store imports](https://docs.aws.amazon.com/omics/latest/dev/import-sequence-store.html)
