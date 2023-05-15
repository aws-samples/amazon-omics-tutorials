# Original Copyright 2021 DeepMind Technologies Limited
# Modifications Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Script to identify templates for AlphaFold"""
import os
import shutil
import time
from time import strftime, gmtime
from resource import getrusage, RUSAGE_SELF
import json
from absl import app
from absl import flags
from absl import logging

from alphafold.data.tools import hhsearch
from alphafold.data.tools import hmmsearch
from new_pipelines import TemplateSearchPipeline

logging.set_verbosity(logging.INFO)

flags.DEFINE_string("msa_path", None, "Path to a .sto file containing MSA hits.")
flags.DEFINE_string(
    "output_dir", None, "Path to a directory that will store the results."
)
flags.DEFINE_string(
    "hhsearch_binary_path", shutil.which("hhsearch"), "Path to the HHsearch executable."
)
flags.DEFINE_string(
    "hmmsearch_binary_path",
    shutil.which("hmmsearch"),
    "Path to the hmmsearch executable.",
)
flags.DEFINE_string(
    "hmmbuild_binary_path", shutil.which("hmmbuild"), "Path to the hmmbuild executable."
)
flags.DEFINE_string(
    "database_path", "/database", "Path to the PDB70 and pdb_seqres databases."
)
flags.DEFINE_enum(
    "model_preset",
    "monomer",
    ["monomer", "monomer_casp14", "monomer_ptm", "multimer"],
    "Choose preset model configuration - the monomer model, "
    "the monomer model with extra ensembling, monomer model with "
    "pTM head, or multimer model",
)
flags.DEFINE_integer("cpu", 4, "Number of cpus to use for search")

FLAGS = flags.FLAGS


def search_templates(
    msa_path: str, output_dir: str, data_pipeline: TemplateSearchPipeline
) -> None:
    """Search for templates"""
    metrics = {
        "process": "Template Search",
        "start_time": strftime("%d %b %Y %H:%M:%S +0000", gmtime()),
        "timings": {},
    }
    logging.info("Searching for templates")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Search for templates
    t_0 = time.time()
    pdb_hits_out_path = data_pipeline.process(msa_path=msa_path, output_dir=output_dir)
    logging.info(f"Template hits written to {pdb_hits_out_path}")
    process_time = time.time() - t_0
    metrics["timings"].update({"total": round(process_time, 3)})

    logging.info(f"Template search completed in {process_time} seconds.")
    metrics.update(
        {
            "model_preset": FLAGS.model_preset,
            "cpu": FLAGS.cpu,
            "end_time": strftime("%d %b %Y %H:%M:%S +0000", gmtime()),
            # "peak_reserved_memory_gb": round(getrusage(RUSAGE_SELF).ru_maxrss / 1000000, 3),
        }
    )
    metrics_output_path = os.path.join(FLAGS.output_dir, "metrics.json")
    with open(metrics_output_path, "w") as f:
        f.write(json.dumps(metrics))

def main(argv):

    for tool_name in ("hhsearch", "hmmsearch", "hmmbuild"):
        if not FLAGS[f"{tool_name}_binary_path"].value:
            raise ValueError(
                f'Could not find path to the "{tool_name}" binary. Make '
                "sure it is installed on your system."
            )

    run_multimer_system = "multimer" in FLAGS.model_preset

    if run_multimer_system:
        data_pipeline = TemplateSearchPipeline(
            template_searcher=hmmsearch.Hmmsearch(
                binary_path=FLAGS.hmmsearch_binary_path,
                hmmbuild_binary_path=FLAGS.hmmbuild_binary_path,
                database_path=FLAGS.database_path + "/pdb_seqres.txt",
            ),
            cpu=FLAGS.cpu,
        )
    else:
        data_pipeline = TemplateSearchPipeline(
            template_searcher=hhsearch.HHSearch(
                binary_path=FLAGS.hhsearch_binary_path,
                databases=[FLAGS.database_path + "/pdb70"],
            ),
            cpu=FLAGS.cpu,
        )

    search_templates(
        msa_path=FLAGS.msa_path,
        output_dir=FLAGS.output_dir,
        data_pipeline=data_pipeline,
    )


if __name__ == "__main__":
    flags.mark_flags_as_required(["msa_path", "output_dir"])

    app.run(main)
