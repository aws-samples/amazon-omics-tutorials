# Original Copyright 2021 DeepMind Technologies Limited
# Modifications Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Full AlphaFold protein structure prediction script."""
import json
import os

import pickle
import random

import sys
import time
from typing import Dict

from absl import app
from absl import flags
from absl import logging

from alphafold.common import protein
from alphafold.common import residue_constants
from alphafold.model import config
from alphafold.model import data
from alphafold.model import model
from alphafold.relax import relax
import numpy as np

from time import strftime, gmtime
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.pyplot as plt
from resource import getrusage, RUSAGE_SELF


logging.set_verbosity(logging.INFO)

flags.DEFINE_string("target_id", None, "Target id.")
flags.DEFINE_string("features_path", None, "Path to features pkl file.")
flags.DEFINE_string("model_dir", None, "Path to unzipped model dir.")
flags.DEFINE_string(
    "output_dir", None, "Path to a directory that will " "store the results."
)
flags.DEFINE_enum(
    "model_preset",
    "monomer",
    ["monomer", "monomer_casp14", "monomer_ptm", "multimer"],
    "Choose preset model configuration - the monomer model, "
    "the monomer model with extra ensembling, monomer model with "
    "pTM head, or multimer model",
)
flags.DEFINE_integer(
    "random_seed",
    None,
    "The random seed for the data "
    "pipeline. By default, this is randomly generated. Note "
    "that even if this is set, Alphafold may still not be "
    "deterministic, because processes like GPU inference are "
    "nondeterministic.",
)
flags.DEFINE_integer(
    "num_multimer_predictions_per_model",
    5,
    "How many "
    "predictions (each with a different random seed) will be "
    "generated per model. E.g. if this is 2 and there are 5 "
    "models then there will be 10 predictions per input. "
    "Note: this FLAG only applies if model_preset=multimer",
)
flags.DEFINE_boolean(
    "run_relax",
    True,
    "Whether to run the final relaxation "
    "step on the predicted models. Turning relax off might "
    "result in predictions with distracting stereochemical "
    "violations but might help in case you are having issues "
    "with the relaxation stage.",
)
flags.DEFINE_boolean(
    "use_gpu_relax",
    True,
    "Whether to relax on GPU. "
    "Relax on GPU can be much faster than CPU, so it is "
    "recommended to enable if possible. GPUs must be available"
    " if this setting is enabled.",
)
flags.DEFINE_integer("model_max", None, "Maximum number of models to run.")

FLAGS = flags.FLAGS
RELAX_MAX_ITERATIONS = 0
RELAX_ENERGY_TOLERANCE = 2.39
RELAX_STIFFNESS = 10.0
RELAX_EXCLUDE_RESIDUES = []
RELAX_MAX_OUTER_ITERATIONS = 3


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


def predict_structure(
    target_id: str,
    output_dir: str,
    features_path: str,
    model_runners: Dict[str, model.RunModel],
    amber_relaxer: relax.AmberRelaxation,
    random_seed: int,
):
    """Predicts structure using AlphaFold for the given sequence."""
    logging.info("Predicting %s", target_id)
    metrics = {
        "model_name": "AlphaFold",
        "model_version": "2.3.1",
        "start_time": strftime("%d %b %Y %H:%M:%S +0000", gmtime()),
        "target_id": target_id,
    }
    timings = {}
    metrics["timings"] = {}
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    msa_output_dir = os.path.join(output_dir, "msas")
    if not os.path.exists(msa_output_dir):
        os.makedirs(msa_output_dir)

    # Load features from features.pkl
    t_start = t_0 = time.time()
    with open(features_path, "rb") as f:
        feature_dict = pickle.load(f)
    timings["features"] = time.time() - t_0
    metrics["timings"].update({"load_features": round(timings["features"], 3)})
    seq = feature_dict["sequence"][0].decode("utf-8")
    metrics.update({"sequence_length": len(seq), "sequence": seq})

    unrelaxed_pdbs = {}
    relaxed_pdbs = {}
    relax_metrics = {}
    ranking_confidences = {}

    # Run the models.
    t_1 = time.time()
    num_models = len(model_runners)
    metrics["model_results"] = {}
    for model_index, (model_name, model_runner) in enumerate(model_runners.items()):
        logging.info("Running model %s on %s", model_name, target_id)
        t_0 = time.time()
        model_random_seed = model_index + random_seed * num_models
        processed_feature_dict = model_runner.process_features(
            feature_dict, random_seed=model_random_seed
        )
        timings[f"process_features_{model_name}"] = time.time() - t_0

        t_0 = time.time()
        prediction_result = model_runner.predict(
            processed_feature_dict, random_seed=model_random_seed
        )
        t_diff = time.time() - t_0
        timings[f"predict_and_compile_{model_name}"] = t_diff
        logging.info(
            "Total JAX model %s on %s predict time (includes compilation time): %.1fs",
            model_name,
            target_id,
            t_diff,
        )

        plddt = prediction_result["plddt"]
        mean_plddt = round(plddt.mean(), 3)
        predicted_aligned_error = prediction_result["predicted_aligned_error"]
        max_predicted_aligned_error = round(
            prediction_result["max_predicted_aligned_error"].item(), 3
        )
        ptm = round(prediction_result["ptm"].item(), 3)
        ranking_confidences[model_name] = prediction_result["ranking_confidence"]

        metrics["model_results"].update(
            {
                model_name: {
                    "plddt": mean_plddt,
                    "ptm": ptm,
                    "max_predicted_aligned_error": max_predicted_aligned_error,
                    "ranking_confidence": round(
                        prediction_result["ranking_confidence"], 3
                    ),
                }
            }
        )
        plot_pae(predicted_aligned_error, os.path.join(output_dir, model_name + "_pae.png"))
        # Save the model outputs.
        result_output_path = os.path.join(output_dir, f"result_{model_name}.pkl")
        with open(result_output_path, "wb") as f:
            pickle.dump(prediction_result, f, protocol=4)

        # Add the predicted LDDT in the b-factor column.
        # Note that higher predicted LDDT value means higher model confidence.
        plddt_b_factors = np.repeat(
            plddt[:, None], residue_constants.atom_type_num, axis=-1
        )
        unrelaxed_protein = protein.from_prediction(
            features=processed_feature_dict,
            result=prediction_result,
            b_factors=plddt_b_factors,
            remove_leading_feature_dimension=not model_runner.multimer_mode,
        )

        # Save the unrelaxed PDB
        unrelaxed_pdbs[model_name] = protein.to_pdb(unrelaxed_protein)
        unrelaxed_pdb_path = os.path.join(output_dir, f"unrelaxed_{model_name}.pdb")
        with open(unrelaxed_pdb_path, "w") as f:
            f.write(unrelaxed_pdbs[model_name])

        if amber_relaxer:
            # Relax the prediction.
            t_0 = time.time()
            relaxed_pdb_str, _, violations = amber_relaxer.process(
                prot=unrelaxed_protein
            )
            relax_metrics[model_name] = {
                "remaining_violations": violations,
                "remaining_violations_count": sum(violations),
            }
            timings[f"relax_{model_name}"] = time.time() - t_0

            relaxed_pdbs[model_name] = relaxed_pdb_str

            # Save the relaxed PDB.
            relaxed_output_path = os.path.join(output_dir, f"relaxed_{model_name}.pdb")
            with open(relaxed_output_path, "w") as f:
                f.write(relaxed_pdb_str)

    metrics["timings"].update({"prediction": round(time.time() - t_1, 3)})
    t_2 = time.time()

    # Rank by model confidence and write out relaxed PDBs in rank order.
    ranked_order = []
    for idx, (model_name, _) in enumerate(
        sorted(ranking_confidences.items(), key=lambda x: x[1], reverse=True)
    ):
        ranked_order.append(model_name)
        ranked_output_path = os.path.join(output_dir, f"ranked_{idx}.pdb")
        with open(ranked_output_path, "w") as f:
            if amber_relaxer:
                f.write(relaxed_pdbs[model_name])
            else:
                f.write(unrelaxed_pdbs[model_name])

    ranking_output_path = os.path.join(output_dir, "ranking_debug.json")
    with open(ranking_output_path, "w") as f:
        label = "iptm+ptm" if "iptm" in prediction_result else "plddts"
        f.write(
            json.dumps({label: ranking_confidences, "order": ranked_order}, indent=4)
        )

    top_ranked_mode_name = ranked_order[0]
    metrics["plddt"] = metrics["model_results"][top_ranked_mode_name]["plddt"]
    metrics["ptm"] = metrics["model_results"][top_ranked_mode_name]["ptm"]
    metrics["max_predicted_aligned_error"] = metrics["model_results"][
        top_ranked_mode_name
    ]["max_predicted_aligned_error"]

    # Write out metrics
    logging.info("Final timings for %s: %s", target_id, timings)
    timings_output_path = os.path.join(output_dir, "timings.json")
    with open(timings_output_path, "w") as f:
        f.write(json.dumps(timings, indent=4))
    if amber_relaxer:
        relax_metrics_path = os.path.join(output_dir, "relax_metrics.json")
        with open(relax_metrics_path, "w") as f:
            f.write(json.dumps(relax_metrics, indent=4))
    metrics["timings"].update({"output": round(time.time() - t_2, 3)})
    metrics["timings"].update({"total": round(time.time() - t_start, 3)})
    metrics.update({"end_time": strftime("%d %b %Y %H:%M:%S +0000", gmtime())})
    # metrics.update({"peak_memory_gb": round(getrusage(RUSAGE_SELF).ru_maxrss / 1000000, 3)})

    metrics_output_path = os.path.join(output_dir, "metrics.json")
    with open(metrics_output_path, "w") as f:
        f.write(json.dumps(metrics))


def main(argv):
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")

    run_multimer_system = "multimer" in FLAGS.model_preset

    if FLAGS.model_preset == "monomer_casp14":
        num_ensemble = 8
    else:
        num_ensemble = 1

    num_predictions_per_model = (
        FLAGS.num_multimer_predictions_per_model if run_multimer_system else 1
    )

    model_runners = {}
    model_names = config.MODEL_PRESETS[FLAGS.model_preset]

    if FLAGS.model_max:
        model_names = model_names[: FLAGS.model_max]

    for model_name in model_names:
        model_config = config.model_config(model_name)
        if run_multimer_system:
            model_config.model.num_ensemble_eval = num_ensemble
        else:
            model_config.data.eval.num_ensemble = num_ensemble
        model_params = data.get_model_haiku_params(
            model_name=model_name, data_dir=FLAGS.model_dir
        )
        model_runner = model.RunModel(model_config, model_params)
        for i in range(num_predictions_per_model):
            model_runners[f"{model_name}_pred_{i}"] = model_runner

    logging.info("Have %d models: %s", len(model_runners), list(model_runners.keys()))

    if FLAGS.run_relax:
        amber_relaxer = relax.AmberRelaxation(
            max_iterations=RELAX_MAX_ITERATIONS,
            tolerance=RELAX_ENERGY_TOLERANCE,
            stiffness=RELAX_STIFFNESS,
            exclude_residues=RELAX_EXCLUDE_RESIDUES,
            max_outer_iterations=RELAX_MAX_OUTER_ITERATIONS,
            use_gpu=FLAGS.use_gpu_relax,
        )
    else:
        amber_relaxer = None

    random_seed = FLAGS.random_seed
    if random_seed is None:
        random_seed = random.randrange(sys.maxsize // len(model_runners))
    predict_structure(
        target_id=FLAGS.target_id,
        features_path=FLAGS.features_path,
        output_dir=FLAGS.output_dir,
        model_runners=model_runners,
        amber_relaxer=amber_relaxer,
        random_seed=random_seed,
    )


if __name__ == "__main__":
    flags.mark_flags_as_required(
        [
            "target_id",
            "features_path",
            "output_dir",
            "model_dir",
        ]
    )

    app.run(main)
