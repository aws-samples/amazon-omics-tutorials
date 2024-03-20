import boto3
import pandas as pd
import argparse


def find_duplicates(seq_store_ids, omics_client, output_path):
    """
    Iterates through all the read sets in all the sequence stores and returns a dataframe with
    the read sets that share an ETag. This will find duplicates for read sets across sequence 
    stores.

    """

    # intiate a blank dataframe to store the information for read sets
    df = pd.DataFrame(columns=['sequence_store_id','read_set_id','name','type','source', 'etag'])

    # setup the paginator to use list read sets
    paginator = omics_client.get_paginator('list_read_sets')

    # iterate by sequence store.  You can modify this loop if you want to limit to finding duplicates just within the sequence store 
    for seq_store in seq_store_ids:

        # iterate by page within a read set
        for page in paginator.paginate(sequenceStoreId=seq_store):

            # get just the read set information
            for rs in page['readSets']:
                read_set_id = rs['id']
                if rs.get('etag',''):

                    # there may be 2 sources if the file type is a FASTQ
                    etag_source_1 = rs['etag'].get('source1','')
                    etag_source_2 = rs['etag'].get('source2','')
                    file_type = rs.get('fileType')
                    name = rs.get('name')

                    # only log if a etag was found
                    if etag_source_1:
                        s1 = {
                            'sequence_store_id': seq_store,
                            'read_set_id': read_set_id, 
                            'name': name,
                            'type': file_type,
                            'source': 'source 1', 
                            'etag': etag_source_1
                        } 
                        df = pd.concat([df, pd.DataFrame([s1])])
                    if etag_source_2:
                        s2 = {
                            'sequence_store_id': seq_store,
                            'read_set_id': read_set_id, 
                            'name': name,
                            'type': file_type,
                            'source': 'source 2', 
                            'etag': etag_source_2
                        } 
                        df = pd.concat([df, pd.DataFrame([s2])])

    # filters to only duplicates based on the etag field
    filtered_df = df[df.duplicated(subset='etag', keep=False)]

    # sorts for easy identification
    df_sorted = filtered_df.sort_values(by=['etag','read_set_id'], ascending=True)

    return df_sorted



# Driver Code

# Decide the two file paths according to your
# computer system

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('-s', '--seq-store-ids', type=str, required=True, 
                        help='A comma separated list of 1 or more sequence store IDs to check, all in the same region.')
    parser.add_argument('-o', '--output', type=str, default='duplicate_read_sets.csv', 
                        help='(optional) The path and file name for the output csv file containing all the duplicate read sets. Include the file \
                        name and prefix (e.g. "~/path/to/out/duplicates.csv"). The default file name is duplicate_read_sets.csv and will write to \
                        the current directory.')
    parser.add_argument('--region', type=str, required=False, 
                        help='(optional) The region where the sequence stores are in. They must all be in the same region. If this is left \
                        unspecified, the code will use the default configured region.')
    parser.add_argument('--profile', type=str, 
                        help='(optional) The profile name for boto3 to use if you do not want it to use the default profile configured.')
    
    args = parser.parse_args()

    # parse the input sequence store IDs so it's clear what will get passed to the function. 
    parsed_seq_store_ids = [i.strip() for i in args.seq_store_ids.split(',')]
    if len(parsed_seq_store_ids) == 0:
        sys.exit(f'\nERROR: could not parse sequence store ids input: {args.seqStoreIds}')

    print('\nArguments used:\nSequence Store IDs:', str(parsed_seq_store_ids))
    
    print('Output:', args.output)
    # print optional inputs only if they're specified
    if args.region:
        print('Region:', args.region)
    if args.profile:
        print('Profile:', args.profile)

    # setup the boto3 client
    session = boto3.Session(region_name=args.region, profile_name=args.profile)
    omics_client = session.client('omics')
    
    # identify duplicates
    df = find_duplicates(parsed_seq_store_ids, omics_client, args.output)

    # counts the duplicates found
    print(f'Duplicates found: {len(df)}')

    # prints out the read sets. We use 1 since 1 read set can't be a duplicate. 
    if len(df) > 1:
        df.to_csv(args.output,index=False)

