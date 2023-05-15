# Original Copyright 2021 DeepMind Technologies Limited
# Modifications Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Full AlphaFold protein structure prediction script."""
import os
import pathlib
import pickle
import shutil
import time
from time import strftime, gmtime
import json
from typing import Dict, Union, MutableMapping, Optional
from absl import app
from absl import flags
from absl import logging
from alphafold.data import templates
from alphafold.data import parsers
import numpy as np
from resource import getrusage, RUSAGE_SELF

from new_pipelines import (
    GenerateMonomerFeaturesDataPipeline,
    GenerateMultimerFeaturesDataPipeline,
)

# Internal import (7716).

FeatureDict = MutableMapping[str, np.ndarray]

logging.set_verbosity(logging.INFO)

flags.DEFINE_list(
    "fasta_paths",
    None,
    "Paths to FASTA files, each containing a prediction "
    "target that will be folded one after another. If a FASTA file contains "
    "multiple sequences, then it will be folded as a multimer. Paths should be "
    "separated by commas. All FASTA paths must have a unique basename as the "
    "basename is used to name the output directories for each prediction.",
)

flags.DEFINE_string("msa_dir", None, "Path to directory of .a3m, and .sto files.")
flags.DEFINE_string("template_hits", None, "Path to a .hhr or .sto ")

flags.DEFINE_string(
    "output_dir", None, "Path to a directory that will " "store the results."
)
flags.DEFINE_string(
    "kalign_binary_path", shutil.which("kalign"), "Path to the Kalign executable."
)
flags.DEFINE_string(
    "template_mmcif_dir",
    "pdb_mmcif",
    "Path to a directory with " "template mmCIF structures, each named <pdb_id>.cif",
)
flags.DEFINE_string(
    "max_template_date",
    None,
    "Maximum template release date "
    "to consider. Important if folding historical test sets.",
)
flags.DEFINE_string(
    "obsolete_pdbs_path",
    "obsolete.dat",
    "Path to file containing a "
    "mapping from obsolete PDB IDs to the PDB IDs of their "
    "replacements.",
)
flags.DEFINE_enum(
    "model_preset",
    "monomer",
    ["monomer", "monomer_casp14", "monomer_ptm", "multimer"],
    "Choose preset model configuration - the monomer model, "
    "the monomer model with extra ensembling, monomer model with "
    "pTM head, or multimer model",
)

FLAGS = flags.FLAGS
MAX_TEMPLATE_HITS = 20


def load_msas(
    msa_out_path: str, msa_format: str, max_sto_sequences: Optional[int] = None
) -> Dict:
    logging.warning("Reading MSA from file %s", msa_out_path)
    if msa_format == "sto" and max_sto_sequences is not None:
        precomputed_msa = parsers.truncate_stockholm_msa(
            msa_out_path, max_sto_sequences
        )
        result = {"sto": precomputed_msa}
    else:
        with open(msa_out_path, "r") as f:
            result = {msa_format: f.read()}
    return result


def generate_features(
    fasta_path: str,
    msa_dir: str,
    fasta_name: str,
    output_dir: str,
    data_pipeline: Union[
        GenerateMonomerFeaturesDataPipeline, GenerateMultimerFeaturesDataPipeline
    ],
) -> None:
    """Predicts structure using AlphaFold for the given sequence."""
    metrics = {
        "process": "Feature Generation",
        "start_time": strftime("%d %b %Y %H:%M:%S +0000", gmtime()),
        "timings": {},
    }
    logging.info("Predicting %s", fasta_name)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    t_0 = time.time()

    feature_dict = data_pipeline.process(
        input_fasta_path=fasta_path, msa_output_dir=msa_dir
    )

    metrics.update(
        {
            "template_count": feature_dict["template_domain_names"].shape[0],
            "dedup_msa_size": int(feature_dict["num_alignments"][0]),
        }
    )

    # Write out features as a pickled dictionary.
    features_output_path = os.path.join(output_dir, "features.pkl")
    logging.info(f"Writing features to {features_output_path}")
    with open(features_output_path, "wb") as f:
        pickle.dump(feature_dict, f, protocol=4)
    process_time = time.time() - t_0
    metrics["timings"].update({"total": round(process_time, 3)})
    logging.info(f"Feature generation completed in {process_time} seconds.")
    metrics.update(
        {
            "model_preset": FLAGS.model_preset,
            "max_template_date": FLAGS.max_template_date,
            "max_template_hits": MAX_TEMPLATE_HITS,
            "end_time": strftime("%d %b %Y %H:%M:%S +0000", gmtime()),
        }
    )
    metrics_output_path = os.path.join(FLAGS.output_dir, "metrics.json")
    with open(metrics_output_path, "w") as f:
        f.write(json.dumps(metrics))

def main(argv):

    for tool_name in ["kalign"]:
        if not FLAGS[f"{tool_name}_binary_path"].value:
            raise ValueError(
                f'Could not find path to the "{tool_name}" binary. Make '
                "sure it is installed on your system."
            )

    run_multimer_system = "multimer" in FLAGS.model_preset

    # Check for duplicate FASTA file names.
    fasta_names = [pathlib.Path(p).stem for p in FLAGS.fasta_paths]
    if len(fasta_names) != len(set(fasta_names)):
        raise ValueError("All FASTA paths must have a unique basename.")

    if run_multimer_system:
        template_featurizer = templates.HmmsearchHitFeaturizer(
            mmcif_dir=FLAGS.template_mmcif_dir,
            max_template_date=FLAGS.max_template_date,
            max_hits=MAX_TEMPLATE_HITS,
            kalign_binary_path=FLAGS.kalign_binary_path,
            release_dates_path=None,
            obsolete_pdbs_path=FLAGS.obsolete_pdbs_path,
        )
    else:
        template_featurizer = templates.HhsearchHitFeaturizer(
            mmcif_dir=FLAGS.template_mmcif_dir,
            max_template_date=FLAGS.max_template_date,
            max_hits=MAX_TEMPLATE_HITS,
            kalign_binary_path=FLAGS.kalign_binary_path,
            release_dates_path=None,
            obsolete_pdbs_path=FLAGS.obsolete_pdbs_path,
        )

    monomer_data_pipeline = GenerateMonomerFeaturesDataPipeline(
        template_featurizer=template_featurizer
    )

    if run_multimer_system:
        data_pipeline = GenerateMultimerFeaturesDataPipeline(
            monomer_data_pipeline=monomer_data_pipeline
        )
    else:
        data_pipeline = monomer_data_pipeline

    # Generate features for each of the sequences.
    for i, fasta_path in enumerate(FLAGS.fasta_paths):
        fasta_name = fasta_names[i]
        generate_features(
            fasta_path=fasta_path,
            msa_dir=FLAGS.msa_dir,
            fasta_name=fasta_name,
            output_dir=FLAGS.output_dir,
            data_pipeline=data_pipeline,
        )


if __name__ == "__main__":
    flags.mark_flags_as_required(
        ["fasta_paths", "msa_dir", "template_hits", "output_dir", "max_template_date"]
    )

    app.run(main)
