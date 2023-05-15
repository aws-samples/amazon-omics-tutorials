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

def get_sequence_length(seq_list):
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

def run(fasta_file, alg, output_file = None):
    filtered_fasta = filter_fasta(fasta_file)
    if output_file:
        with open(output_file, "w") as output_handle:
            SeqIO.write(filtered_fasta, output_handle, "fasta")
    id, seq_length, seq_count = get_sequence_length(filtered_fasta)
    if alg.lower() == 'esmfold':
        if seq_length <= 750:
            response = {
                "id": id,
                "seq_count": seq_count,
                "predict_resources": {
                    "vcpu": 4,
                    "memory": "16 GiB",
                    "gpu": "True"
                }
            }
        else:
            response = {
                "id": id,
                "seq_count": seq_count,
                "predict_resources": {
                    "vcpu": 4,
                    "memory": f"{round(Polynomial([9, 0.009, 0.000006])(seq_length)*1.1)} GiB",
                    "gpu": "False"
                }
            }
    elif alg.lower() == 'alphafold':
            response = {
                "id": id,
                "seq_count": seq_count,
            }
            if seq_length <= 750:
                response = {
                    "predict_resources": {
                        "vcpu": 8,
                        "memory": "16 GiB",
                        "gpu": "True"
                    },
                    "uniref90_msa_resources": {
                        "vcpu": 8,
                        "memory": "16 GiB",
                        "gpu": "False"
                    },
                    "mgnify_msa_resources": {
                        "vcpu": 8,
                        "memory": "16 GiB",
                        "gpu": "False"
                    },
                    "bfd_msa_resources": {
                        "vcpu": 16,
                        "memory": "32 GiB",
                        "gpu": "False"
                    },
                }
            elif 750 < seq_length <= 2000:
                response = {
                    "id": id,
                    "seq_count": seq_count,
                    "predict_resources": {
                        "vcpu": 8,
                        "memory": "16 GiB",
                        "gpu": "True"
                    },
                    "uniref90_msa_resources": {
                        "vcpu": 8,
                        "memory": "16 GiB",
                        "gpu": "False"
                    },
                    "mgnify_msa_resources": {
                        "vcpu": 8,
                        "memory": "16 GiB",
                        "gpu": "False"
                    },
                    "bfd_msa_resources": {
                        "vcpu": 16,
                        "memory": "128 GiB",
                        "gpu": "False"
                    },
                }
            else:
                response = {
                    "id": id,
                    "seq_count": seq_count,
                    "predict_resources": {
                        "vcpu": 8,
                        "memory": "16 GiB",
                        "gpu": "True"
                    },
                    "uniref90_msa_resources": {
                        "vcpu": 8,
                        "memory": "16 GiB",
                        "gpu": "False"
                    },
                    "mgnify_msa_resources": {
                        "vcpu": 8,
                        "memory": "16 GiB",
                        "gpu": "False"
                    },
                    "bfd_msa_resources": {
                        "vcpu": 48,
                        "memory": "192 GiB",
                        "gpu": "False"
                    },
                }
            
    else:
        return {"ID": id, "Memory": "16 GiB", "GPU": "False", "Sequence_Count": seq_count}
    return response
    

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "fasta_file",
        help="Path to input FASTA file",
        type=str
    )
    parser.add_argument(
        "--alg",
        help="Name of the algorithm to estimate resources for",
        default="Other",
        type=str
    )
    parser.add_argument(
        "--max_seq",
        help="Maxiumum number of sequences to return",
        default=1,
        type=str
    )

    args = parser.parse_args()
    output = run(args.fasta_file, args.alg)
    print(output)
    with open("resources.json", "w") as f:
        json.dump(output, f)

