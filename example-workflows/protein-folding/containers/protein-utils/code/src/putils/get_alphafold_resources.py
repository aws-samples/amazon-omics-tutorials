import argparse
import logging
from numpy.polynomial import Polynomial
from Bio import SeqIO
import json
import re

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

def get_sequence_metrics(seq_list):
    seq_length = 0
    seq_count = 0
    for seq_record in seq_list:
        seq_length += len(seq_record.seq)
        seq_count += 1
        id = seq_record.id
    id = re.match("[0-9a-zA-Z]*", id)
    id = id[0] if id else None
    return (id, seq_length, seq_count)

def filter_fasta(fasta_file, max_seq=1):
    seqs = [seq for seq in SeqIO.parse(fasta_file, "fasta")]
    return seqs[:max_seq]

def get_alphafold_resources(fasta_file, max_seq=1, output_file=None):
    filtered_fasta = filter_fasta(fasta_file, max_seq)
    if output_file:
        with open(output_file, "w") as output_handle:
            SeqIO.write(filtered_fasta, output_handle, "fasta")
    id, seq_length, seq_count = get_sequence_metrics(filtered_fasta)
    resources = {
        "id": str(id),
        "seq_length": str(seq_length),
        "seq_count": str(seq_count),
        "template_cpu": "2",
        "template_memory": "4 GiB",
        "feature_cpu": "2",
        "feature_memory": "4 GiB",
        "predict_cpu": "8",
        "predict_memory": "32 GiB",
    }

    if seq_length <= 750:
        resources.update({
            "uniref90_cpu": "8",
            "uniref90_memory": "16 GiB",
            "mgnify_cpu": "8",
            "mgnify_memory": "16 GiB",
            "bfd_cpu": "16",
            "bfd_memory": "32 GiB",
        })
    elif 750 < seq_length <= 2000:
        resources.update({
            "uniref90_cpu": "8",
            "uniref90_memory": "16 GiB",
            "mgnify_cpu": "8",
            "mgnify_memory": "16 GiB",
            "bfd_cpu": "16",
            "bfd_memory": "128 GiB",
        })
    else:
        resources.update({
            "uniref90_cpu": "8",
            "uniref90_memory": "32 GiB",
            "mgnify_cpu": "8",
            "mgnify_memory": "32 GiB",
            "bfd_cpu": "48",
            "bfd_memory": "192 GiB",
        })
        
    return resources
    

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "fasta_file",
        help="Path to input FASTA file",
        type=str
    )
    parser.add_argument(
        "--max_seq",
        help="Maxiumum number of sequences to return",
        default=1,
        type=str
    )
    parser.add_argument(
        "--output_file",
        help="(Optional) file name of an output file for the filtered fasta",
        default=None,
        type=str
    )

    args = parser.parse_args()
    output = get_alphafold_resources(args.fasta_file, args.max_seq, args.output_file)
    print(output)
    with open("resources.json", "w") as f:
        json.dump(output, f)

