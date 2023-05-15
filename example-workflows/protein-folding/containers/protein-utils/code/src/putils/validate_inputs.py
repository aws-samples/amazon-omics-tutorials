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

def validate_inputs(fasta_file, max_seq=1, max_length=2000, output_file=None):
    filtered_fasta = filter_fasta(fasta_file, max_seq)
    if output_file:
        with open(output_file, "w") as output_handle:
            SeqIO.write(filtered_fasta, output_handle, "fasta")
    id, seq_length, seq_count = get_sequence_metrics(filtered_fasta)

    if seq_length > max_length:
        raise Exception(f"Sequence length {seq_length} is greater than the maximum of {max_length}")

    seq_info = {
        "id": str(id),
        "seq_length": str(seq_length),
        "seq_count": str(seq_count)
    }        
    return seq_info
    

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
        type=int
    )
    parser.add_argument(
        "--max_length",
        help="Maxiumum length of (combined) sequences",
        default=2000,
        type=int
    )    
    parser.add_argument(
        "--output_file",
        help="(Optional) file name of an output file for the filtered fasta",
        default=None,
        type=str
    )

    args = parser.parse_args()
    output = validate_inputs(args.fasta_file, args.max_seq, args.max_length, args.output_file)
    print(output)
    with open("seq_info.json", "w") as f:
        json.dump(output, f)

