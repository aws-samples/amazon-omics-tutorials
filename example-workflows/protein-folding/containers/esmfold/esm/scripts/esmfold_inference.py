# Original Copyright 2022 Facebook, Inc. and its affiliates.
# Modifications Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import argparse
import json
import esm
import logging
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.pyplot as plt
from pathlib import Path
import re
from resource import getrusage, RUSAGE_SELF
import sys
from time import gmtime, strftime
from timeit import default_timer as timer
import torch
import typing as T
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%y/%m/%d %H:%M:%S",
)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
PathLike = T.Union[str, Path]


def enable_cpu_offloading(model):
    from torch.distributed.fsdp import CPUOffload, FullyShardedDataParallel
    from torch.distributed.fsdp.wrap import enable_wrap, wrap

    torch.distributed.init_process_group(
        backend="nccl", init_method="tcp://localhost:9999", world_size=1, rank=0
    )
    wrapper_kwargs = dict(cpu_offload=CPUOffload(offload_params=True))
    with enable_wrap(wrapper_cls=FullyShardedDataParallel, **wrapper_kwargs):
        for layer_name, layer in model.layers.named_children():
            wrapped_layer = wrap(layer)
            setattr(model.layers, layer_name, wrapped_layer)
        model = wrap(model)
    return model


def init_model_on_gpu_with_cpu_offloading(model):
    model = model.eval()
    model_esm = enable_cpu_offloading(model.esm)
    del model.esm
    model.cuda()
    model.esm = model_esm
    return model


def create_joined_sequence_datasest(sequences: T.List[T.Tuple[str, str]]) -> T.Tuple[str, str]:
    batch_headers, batch_sequences = [], []
    for header, seq in sequences:
        clean_header = re.search("^\w+", header)
        if clean_header:
            batch_headers.append(clean_header[0])
        else:
            batch_headers.append(uuid.uuid4().hex[:4])
        batch_sequences.append(seq)

    return ":".join(batch_headers), ":".join(batch_sequences)

def plot_pae(pae, output) -> None:
    fig = plt.figure()
    ax = fig.add_subplot()
    hcls_cmap = LinearSegmentedColormap.from_list(
        "hclscmap", ["#FFFFFF", "#007FAA", "#005276"]
    )
    _ = plt.imshow(pae, vmin=0.0, vmax=pae.max(), cmap=hcls_cmap)
    ax.set_title("Predicted Aligned Error")
    ax.set_xlabel("Scored residue")
    ax.set_ylabel("Aligned residue")
    fig.savefig(output)
    return None

if __name__ == "__main__":
    start_time = timer()
    metrics = {
        "model_name": "ESMFold",
        "model_version": esm.__version__,
        "start_time": strftime("%d %b %Y %H:%M:%S +0000", gmtime())
    }
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--fasta",
        help="Path to input FASTA file",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "-o", "--pdb", help="Path to output PDB directory", type=Path, required=True
    )
    parser.add_argument(
        "-m",
        "--model-dir",
        help="Parent path to Pretrained ESM data directory. ",
        type=Path,
        default="data/weights",
    )
    parser.add_argument(
        "--num-recycles",
        type=int,
        default=None,
        help="Number of recycles to run. Defaults to number used in training (4).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        choices=[16, 32, 64, 128],
        help="Chunks axial attention computation to reduce memory usage from O(L^2) to O(L). "
        "Equivalent to running a for loop over chunks of of each dimension. Lower values will "
        "result in lower memory usage at the cost of speed. Recommended values: 128, 64, 32. "
        "Default: None.",
    )
    parser.add_argument("--cpu-only", help="CPU only", action="store_true")
    parser.add_argument("--cpu-offload", help="Enable CPU offloading", action="store_true")
    parser.add_argument(
        "-t",
        "--target-id",
        type=str,
        default=None,
        help="Target ID to use instead of the fasta file header",
    )
    args = parser.parse_args()
    if not args.fasta.exists():
        raise FileNotFoundError(args.fasta)
    args.pdb.mkdir(exist_ok=True)
    

    # Read fasta and sort sequences by length
    logger.info(f"Reading sequences from {args.fasta}")
    start_sequence_load_time = timer()
    all_sequences = sorted(
        esm.data.read_fasta(args.fasta), key=lambda header_seq: len(header_seq[1])
    )
    logger.info(f"Loaded {len(all_sequences)} sequences from {args.fasta}")
    logger.info(f"Raw input is {all_sequences}")
    metrics.update({"timings": {"sequence_load": round(timer() - start_sequence_load_time, 3)}})

    # Load models
    logger.info("Loading model")
    start_model_load_time = timer()
    torch.hub.set_dir(args.model_dir)
    model = esm.pretrained.esmfold_v1()
    model = model.eval()
    model.set_chunk_size(args.chunk_size)
    if args.cpu_only:
        model.esm.float()  # convert to fp32 as ESM-2 in fp16 is not supported on CPU
        model.cpu()
    elif args.cpu_offload:
        model = init_model_on_gpu_with_cpu_offloading(model)
    else:
        model.cuda()
    metrics["timings"].update({"model_load": round(timer() - start_model_load_time, 3)})

    # Predict structure
    logger.info("Starting Predictions")
    start_prediction_time = timer()
    header, seq = create_joined_sequence_datasest(all_sequences)
    if args.target_id:
        header = args.target_id
    logger.info(f"Header is {header}")
    logger.info(f"Sequence is {seq}")
    seq_len = len(seq.replace(":", ""))
    metrics.update({"target_id": header, "length": seq_len, "sequence": seq})
    try:
        output = model.infer(seq, num_recycles=args.num_recycles)
    except RuntimeError as err:
        if err.args[0].startswith("CUDA out of memory"):
            logger.info(f"Failed (CUDA out of memory) on sequence {header} of length {seq_len}.")
        metrics.update({"error": err.args[0]})
        metrics.update({"end_time": strftime("%d %b %Y %H:%M:%S +0000", gmtime())})
        with open(f"{args.pdb}/metrics.json", "w") as f:
            json.dump(metrics, f)
        raise
    except Exception as err:
        metrics.update({"error": err})
        metrics.update({"end_time": strftime("%d %b %Y %H:%M:%S +0000", gmtime())})
        with open(f"{args.pdb}/metrics.json", "w") as f:
            json.dump(metrics, f)
        raise
    metrics["timings"].update({"prediction": round(timer() - start_prediction_time, 3)})

    # Parse outputs
    start_output_time = timer()
    output = {key: value.cpu() for key, value in output.items()}
    pdb_string = model.output_to_pdb(output)[0]
    output_file = args.pdb / "prediction.pdb"
    output_file.write_text(pdb_string)
    mean_plddt = round(output["mean_plddt"].item(), 3)
    ptm = round(output["ptm"].item(), 3)
    max_predicted_aligned_error = round(output["max_predicted_aligned_error"].item(), 3)
    peak_mem = getrusage(RUSAGE_SELF).ru_maxrss / 1000000
    peak_gpu_mem = torch.cuda.max_memory_allocated() / 1000000000

    torch.save(output, args.pdb / "outputs.pt")

    pae = output['predicted_aligned_error']
    plot_pae(pae[0], args.pdb / "pae.png")

    metrics.update(
            {
                "pLDDT": mean_plddt,
                "pTM": ptm,
                "max_predicted_aligned_error": max_predicted_aligned_error,
                "peak_memory_gb": peak_mem,
                "peak_gpu_memory_gb": peak_gpu_mem,
            }
        )

    metrics["timings"].update({"output": round(timer() - start_output_time, 3)})
    end_time = timer()
    total_time = round(end_time - start_time, 3)
    metrics["timings"].update({"total": total_time})
    metrics.update({"end_time": strftime("%d %b %Y %H:%M:%S +0000", gmtime())})
    logger.info(
        f"Predicted structure for {header} with length {seq_len}, pLDDT {mean_plddt}, "
        f"pTM {ptm} in {total_time}s. "
        f"Peak memory usage (GB) {peak_mem}. "
        f"Peak GPU memory usage (GB) {peak_gpu_mem}."
    )  
    with open(f"{args.pdb}/metrics.json", "w") as f:
        json.dump(metrics, f)
