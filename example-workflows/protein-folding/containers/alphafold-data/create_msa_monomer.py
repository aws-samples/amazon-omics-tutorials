# Original Copyright 2021 DeepMind Technologies Limited
# Modifications Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Script to create MSAs for AlphaFold"""
import json
import os
import shutil
import time
from time import strftime, gmtime
from absl import app
from absl import flags
from absl import logging
from new_pipelines import MonomerMSAPipeline
from resource import getrusage, RUSAGE_SELF


logging.set_verbosity(logging.INFO)

flags.DEFINE_string("fasta_path", None, "Path to FASTA file with a single sequence.")
flags.DEFINE_enum(
    "database_type",
    "bfd",
    ["bfd", "uniref90", "mgnify"],
    "Type of database to search against.",
)
flags.DEFINE_string("database_path", None, "Path to directory of supporting data.")
flags.DEFINE_string(
    "output_dir", "output", "Path to a directory that will store the results."
)
flags.DEFINE_string(
    "jackhmmer_binary_path",
    shutil.which("jackhmmer"),
    "Path to the JackHMMER executable.",
)
flags.DEFINE_string(
    "hhblits_binary_path", shutil.which("hhblits"), "Path to the HHblits executable."
)
flags.DEFINE_boolean(
    "use_precomputed_msas",
    True,
    "Whether to read MSAs that "
    "have been written to disk instead of running the MSA "
    "tools. The MSA files are looked up in the output "
    "directory, so it must stay the same between multiple "
    "runs that are to reuse the MSAs. WARNING: This will not "
    "check if the sequence, database or configuration have "
    "changed.",
)
flags.DEFINE_integer("cpu", 8, "Number of cpus to use for search")

FLAGS = flags.FLAGS


def create_msas(
    fasta_path: str,
    output_dir: str,
    data_pipeline: MonomerMSAPipeline,
):
    """Create MSA"""
    logging.info(f"Analyzing {fasta_path}")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Search datbase
    t_0 = time.time()
    msa_out_path = data_pipeline.process(
        input_fasta_path=fasta_path, msa_output_dir=output_dir
    )
    logging.info(f"MSA written to {msa_out_path}")
    process_time = time.time() - t_0
    logging.info(f"MSA creation completed in {process_time} seconds.")


def main(argv):

    metrics = {
        "process": "MSA Creation",
        "start_time": strftime("%d %b %Y %H:%M:%S +0000", gmtime()),
        "timings": {}
    }
    t_start = time.time()

    for tool in ["jackhmmer", "hhblits"]:
        if not FLAGS[f"{tool}_binary_path"].value:
            raise ValueError(
                f'Could not find path to the "{tool}" binary. Make '
                "sure it is installed on your system."
            )

    metrics.update(
        {
            "input_fasta": FLAGS.fasta_path,
            "database_type": FLAGS.database_type,
            "cpu": FLAGS.cpu,
        }
    )

    data_pipeline = MonomerMSAPipeline(
        jackhmmer_binary_path=FLAGS.jackhmmer_binary_path,
        hhblits_binary_path=FLAGS.hhblits_binary_path,
        database_type=FLAGS.database_type,
        database_path=FLAGS.database_path,
        use_precomputed_msas=FLAGS.use_precomputed_msas,
        cpu=FLAGS.cpu,
    )

    # Predict structure for the sequence.
    create_msas(
        fasta_path=FLAGS.fasta_path,
        output_dir=FLAGS.output_dir,
        data_pipeline=data_pipeline,
    )

    metrics["timings"].update({"total": round(time.time() - t_start, 3)})
    metrics.update({"end_time": strftime("%d %b %Y %H:%M:%S +0000", gmtime())})
    # metrics.update({"peak_reserved_memory_gb": round(getrusage(RUSAGE_SELF).ru_maxrss / 1000000, 3)})
    metrics_output_path = os.path.join(FLAGS.output_dir, "metrics.json")
    with open(metrics_output_path, "w") as f:
        f.write(json.dumps(metrics))

if __name__ == "__main__":
    flags.mark_flags_as_required(["fasta_path", "database_path"])

    app.run(main)
