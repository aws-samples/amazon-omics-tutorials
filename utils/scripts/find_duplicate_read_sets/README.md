# AWS HealthOmics Sequence Store Duplicate Read Set Finder script

This is provided AS-IS and is intended to aid in identifying read sets that are duplicate within and across sequence stores in the same region. This is a starting point, feel free to customize as needed to fit your specific requirements.

## find_duplicate_read_sets.py

This script was written to help in the identification of duplicate read sets stored in [AWS HealthOmics sequence stores](https://docs.aws.amazon.com/omics/latest/dev/what-is-service.html). This script relies on [HealthOmics ETags](https://docs.aws.amazon.com/omics/latest/dev/etags-and-provenance.html) which is a hash of the ingested content in a sequence store. 

To run this script, simply identify the sequence store IDs you want to search across in a region, specify the input parameters, and you receive a CSV with the read set sources that share an ETag. 

### Prerequisits
1. Python 3.10 or above is installed along with the AWS SDK for Python (`boto3`)
2. AWS CLI v2 is installed and configured with a profile with read access to AWS HealthOmics sequence stores
3. All library dependencies are outlined in the attached `requirements.txt` including the following libraries: `pandas, argparse, boto3`
4. The sequence store IDs input all exist within the region identified.  If the region and sequence store IDs do not match, an error for `The specified sequence store does not exist`will be generated.

usage: find_duplicate_read_sets.py usage: find_duplicate_read_setst.py [-h] -s SEQUENCESTOREIDS [-o OUTPUT] [--region REGION] [--pofile PROFILE]

### Options
  &nbsp;&nbsp;-h, --help  

  &nbsp;&nbsp;-s SEQUENCESTOREIDS, -seq-store-ids INPUT  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;A comma separated list of 1 or more sequence store IDs to check, all in the same region. (e.g. 5068895345,1504776472")*  

  &nbsp;&nbsp;-o OUTPUT, --output OUTPUT  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(optional) The path and file name for the output csv file containing all the duplicate read sets. Include the file name and prefix (e.g. "~/path/to/out/duplicates.csv"). The default file name is duplicate_read_sets.csv and will write to the current directory.*

  &nbsp;&nbsp;--region REGION  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(optional) The region where the sequence stores are in. They must all be in the same region. If this is left unspecified, the code will use the default configured region.*    

  &nbsp;&nbsp;--profile PROFILE  
  *&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(optional) The profile name for boto3 to use if you do not want it to use the default profile configured. Profiles can be created through the AWS CLI using `aws configure` [docs](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)*    

## Usage

#### Single Sequence Store

To identify duplicate read sets within a single sequence store you can pass in a single sequence store ID. 

``` python
python find_duplicate_read_sets.py -s "0123456789" -o ~/scratch/duplicate_read_sets.csv
```
#### Multiple Sequence Store

To identify duplicate read sets across multiple sequence store you can pass in a comma separated list of sequence store ID. 

``` python
python find_duplicate_read_sets.py -s "0123456789,6543210987,2134567890" -o ~/scratch/duplicate_read_sets.csv --region "us-west-2"
```
## AWS HealthOmics Sequence Store
For detailed information on how semantic identity works with AWS HealthOmics sequence stores  please visit [ETag calculation and data provenance](https://docs.aws.amazon.com/omics/latest/dev/etags-and-provenance.html)