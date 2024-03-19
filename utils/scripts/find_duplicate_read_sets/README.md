# AWS HealthOmics Sequence Store Duplicate Read Set Finder script

This is provided AS-IS and is intended to aid in identifying read sets that are duplicate within and across sequence stores in the same region. This is a starting point, feel free to customize as needed to fit your specific requirements.

## find_duplicate_read_sets.py

This script was written to help in the identification of duplicate read sets stored in [AWS HealthOmics sequence stores](https://docs.aws.amazon.com/omics/latest/dev/what-is-service.html). This script relies on [HealthOmics ETags](https://docs.aws.amazon.com/omics/latest/dev/etags-and-provenance.html) which is a hash of the ingested content in a sequence store. 

To run this script, simply identify the sequence store IDs you want to search across in a region, specify the input parameters, and you receive a CSV with the read set sources that share an ETag. 

This script makes a few assumptions:
1. The boto3 configured by default in your python account or the passed in profile has access to list read sets in the HealthOmics sequence stores identified. 
2. The sequence store IDs input all exist within the region identified.  If the region and sequence store IDs do not match, an error for `The specified sequence store does not exist`will be generated.
3. The command has permission to write out a file to the output path specified. 

usage: find_duplicate_read_sets.py usage: find_duplicate_read_setst.py [-h] -s SEQUENCESTOREIDS -r REGION [-o OUTPUT] [-p PROFILENAME]

### options:  
  &nbsp;&nbsp;-h, --help  

  &nbsp;&nbsp;-s SEQUENCESTOREIDS, --seq_store_ids INPUT  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;A comma separated list of 1 or more sequence store IDs to check, all in the same region. (e.g. ""5068895345,1504776472")*  

  &nbsp;&nbsp;-r REGION, --region REGION  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;The region where the sequence stores are in. They must all be in the same region.*  

  &nbsp;&nbsp;-o OUTPUT, --output OUTPUT  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(optional) The path and file name for the output csv file containing all the duplicate read sets. Include the file name and prefix (e.g. "~/path/to/out/duplicates.csv"). The default file name is duplicate_read_sets.csv and will write to the current directory.*  

  &nbsp;&nbsp;-p PROFILENAME, --profile_name PROFILENAME  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(optional) The profile name for boto3 to use if you do not want it to use the default profile configured.*  

## Usage

#### Single Sequence Store:

To identify duplicate read sets within a single sequence store you can pass in a single sequence store ID. 

``` python
python find_duplicate_read_sets.py -s "0123456789" -r "us-west-2" -o ~/scratch/duplicate_read_sets.csv
```
#### Multiple Sequence Store:

To identify duplicate read sets across multiple sequence store you can pass in a comma separated list of sequence store ID. 

``` python
python find_duplicate_read_sets.py -s "0123456789,6543210987,2134567890" -r "us-west-2" -o ~/scratch/duplicate_read_sets.csv
```
## AWS HealthOmics Sequence Store
For detailed information on how semantic identity works with AWS HealthOmics sequence stores  please visit [ETag calculation and data provenance](https://docs.aws.amazon.com/omics/latest/dev/etags-and-provenance.html)