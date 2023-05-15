from absl import logging
from alphafold.data import parsers, pipeline, templates
import numpy as np
import os
from typing import MutableMapping, Optional, Sequence, Union
from alphafold.data import msa_pairing
from alphafold.data.pipeline_multimer import DataPipeline as MultimerDataPipeline
from alphafold.data.tools import hhsearch, hmmsearch, jackhmmer, hhblits
from alphafold.data.pipeline import run_msa_tool

logging.set_verbosity(logging.INFO)
FeatureDict = MutableMapping[str, np.ndarray]
TemplateSearcher = Union[hhsearch.HHSearch, hmmsearch.Hmmsearch]


def load_msas(
    msa_out_path: str, msa_format: str, max_sto_sequences: Optional[int] = None
):
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


class GenerateMonomerFeaturesDataPipeline:
    """Loads existing MSA results and templates and assembles the input features."""

    def __init__(
        self,
        template_featurizer: templates.TemplateHitFeaturizer,
        mgnify_max_hits: int = 501,
        uniref_max_hits: int = 10000,
    ):
        """Initializes the data pipeline."""
        self.template_featurizer = template_featurizer
        self.mgnify_max_hits = mgnify_max_hits
        self.uniref_max_hits = uniref_max_hits

    def process(self, input_fasta_path: str, msa_output_dir: str) -> FeatureDict:
        """Runs alignment tools on the input sequence and creates features."""
        with open(input_fasta_path) as f:
            input_fasta_str = f.read()
        input_seqs, input_descs = parsers.parse_fasta(input_fasta_str)
        if len(input_seqs) != 1:
            raise ValueError(
                f"More than one input sequence found in {input_fasta_path}."
            )
        input_sequence = input_seqs[0]
        input_description = input_descs[0]
        num_res = len(input_sequence)

        # Load Uniref90 MSA
        uniref90_out_path = os.path.join(msa_output_dir, "uniref90_hits.sto")
        jackhmmer_uniref90_result = load_msas(
            msa_out_path=uniref90_out_path,
            msa_format="sto",
            max_sto_sequences=self.uniref_max_hits,
        )
        uniref90_msa = parsers.parse_stockholm(jackhmmer_uniref90_result["sto"])
        logging.info("Uniref90 MSA size: %d sequences.", len(uniref90_msa))

        # Load MGnify MSA
        mgnify_out_path = os.path.join(msa_output_dir, "mgnify_hits.sto")
        jackhmmer_mgnify_result = load_msas(
            msa_out_path=mgnify_out_path,
            msa_format="sto",
            max_sto_sequences=self.mgnify_max_hits,
        )
        mgnify_msa = parsers.parse_stockholm(jackhmmer_mgnify_result["sto"])
        logging.info("MGnify MSA size: %d sequences.", len(mgnify_msa))

        # Load BFD MSA (Optional)
        bfd_msa = None
        if os.path.exists(os.path.join(msa_output_dir, "bfd_uniref_hits.a3m")):
            hhblits_bfd_uniref_result = load_msas(
                msa_out_path=os.path.join(msa_output_dir, "bfd_uniref_hits.a3m"),
                msa_format="a3m",
            )
            bfd_msa = parsers.parse_a3m(hhblits_bfd_uniref_result["a3m"])
            logging.info("BFD MSA size: %d sequences.", len(bfd_msa))
        elif os.path.exists(os.path.join(msa_output_dir, "small_bfd_hits.sto")):
            jackhmmer_small_bfd_result = load_msas(
                msa_out_path=os.path.join(msa_output_dir, "small_bfd_hits.sto"),
                msa_format="sto",
            )
            bfd_msa = parsers.parse_stockholm(jackhmmer_small_bfd_result["sto"])
            logging.info("BFD MSA size: %d sequences.", len(bfd_msa))

        if os.path.exists(os.path.join(msa_output_dir, "pdb_hits.hhr")):
            with open(os.path.join(msa_output_dir, "pdb_hits.hhr"), "r") as f:
                pdb_templates_result = f.read()
                pdb_template_hits = parsers.parse_hhr(pdb_templates_result)

        elif os.path.exists(os.path.join(msa_output_dir, "pdb_hits.sto")):
            with open(os.path.join(msa_output_dir, "pdb_hits.sto"), "r") as f:
                pdb_templates_result = f.read()
                a3m_string = parsers.convert_stockholm_to_a3m(
                    pdb_templates_result, remove_first_row_gaps=False
                )
                pdb_template_hits = parsers.parse_hmmsearch_a3m(
                    query_sequence=input_sequence,
                    a3m_string=a3m_string,
                    skip_first=False,
                )

        templates_result = self.template_featurizer.get_templates(
            query_sequence=input_sequence, hits=pdb_template_hits
        )
        logging.info(
            "Total number of templates (NB: this can include bad "
            "templates and is later filtered to top 4): %d.",
            templates_result.features["template_domain_names"].shape[0],
        )

        # Generate features from MSAs
        if bfd_msa:
            msa_features = pipeline.make_msa_features((uniref90_msa, bfd_msa, mgnify_msa))
        else:
            msa_features = pipeline.make_msa_features((uniref90_msa, mgnify_msa))
        logging.info(
            "Final (deduplicated) MSA size: %d sequences.",
            msa_features["num_alignments"][0],
        )

        # Generate features from sequence
        sequence_features = pipeline.make_sequence_features(
            sequence=input_sequence, description=input_description, num_res=num_res
        )

        return {**sequence_features, **msa_features, **templates_result.features}


class GenerateMultimerFeaturesDataPipeline(MultimerDataPipeline):

    """Runs the alignment tools and assembles the input features."""

    def __init__(
        self,
        monomer_data_pipeline: pipeline.DataPipeline,
        max_uniprot_hits: int = 50000,
    ):
        """Initializes the data pipeline.

        Args:
          monomer_data_pipeline: An instance of pipeline.DataPipeline - that runs
            the data pipeline for the monomer AlphaFold system.
          max_uniprot_hits: The maximum number of hits to return from uniprot.
        """
        self._monomer_data_pipeline = monomer_data_pipeline
        self._max_uniprot_hits = max_uniprot_hits

    def _all_seq_msa_features(self, input_fasta_path, msa_output_dir):
        """Get MSA features for unclustered uniprot, for pairing."""
        del input_fasta_path
        out_path = os.path.join(msa_output_dir, "uniprot_hits.sto")
        # Updated to read msa data from file, rather than run alignment
        result = load_msas(msa_out_path=out_path, msa_format="sto")

        msa = parsers.parse_stockholm(result["sto"])
        msa = msa.truncate(max_seqs=self._max_uniprot_hits)
        all_seq_features = pipeline.make_msa_features([msa])
        valid_feats = msa_pairing.MSA_FEATURES + ("msa_species_identifiers",)
        feats = {
            f"{k}_all_seq": v for k, v in all_seq_features.items() if k in valid_feats
        }
        return feats


class TemplateSearchPipeline:
    """Searches for templates."""

    def __init__(
        self,
        template_searcher: TemplateSearcher,
        uniref_max_hits: int = 10000,
        cpu: int = 4,
    ):
        """Initializes the data pipeline."""
        self.template_searcher = template_searcher
        self.uniref_max_hits = uniref_max_hits
        self.cpu = cpu

    def process(self, msa_path: str, output_dir: str) -> str:
        """Runs alignment tools on the input sequence and creates features."""

        msa_result = load_msas(
            msa_out_path=msa_path,
            msa_format="sto",
            max_sto_sequences=self.uniref_max_hits,
        )

        msa_for_templates = msa_result["sto"]
        msa_for_templates = parsers.deduplicate_stockholm_msa(msa_for_templates)
        msa_for_templates = parsers.remove_empty_columns_from_stockholm_msa(
            msa_for_templates
        )

        if self.template_searcher.input_format == "sto":
            pdb_templates_result = self.template_searcher.query(
                msa_for_templates, self.cpu
            )
        elif self.template_searcher.input_format == "a3m":
            uniref90_msa_as_a3m = parsers.convert_stockholm_to_a3m(msa_for_templates)
            pdb_templates_result = self.template_searcher.query(
                uniref90_msa_as_a3m, self.cpu
            )
        else:
            raise ValueError(
                "Unrecognized template input format: "
                f"{self.template_searcher.input_format}"
            )

        pdb_hits_out_path = os.path.join(
            output_dir, f"pdb_hits.{self.template_searcher.output_format}"
        )
        with open(pdb_hits_out_path, "w") as f:
            f.write(pdb_templates_result)

        logging.info(f"MSA written to {pdb_hits_out_path}")

        return pdb_hits_out_path


class MonomerMSAPipeline:
    """Creates a MSA for a monomer input"""

    def __init__(
        self,
        jackhmmer_binary_path: str,
        hhblits_binary_path: str,
        database_type: str,
        database_path: str,
        cpu: int = 8,
        max_sto_hits: int = 501,
        use_precomputed_msas: bool = True,
    ):
        """Initializes the data pipeline."""

        if database_type == "bfd":
            self.runner = hhblits.HHBlits(
                binary_path=hhblits_binary_path,
                databases=[
                    os.path.join(
                        database_path,
                        "bfd",
                        "bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt",
                    ),
                    os.path.join(database_path, "uniref30", "UniRef30_2021_03"),
                ],
                n_cpu=cpu,
            )
        elif database_type == "uniref90":
            self.runner = jackhmmer.Jackhmmer(
                binary_path=jackhmmer_binary_path,
                database_path=os.path.join(database_path, "uniref90.fasta"),
                n_cpu=cpu,
            )
        elif database_type == "mgnify":
            self.runner = jackhmmer.Jackhmmer(
                binary_path=jackhmmer_binary_path,
                database_path=os.path.join(database_path, "mgy_clusters_2022_05.fa"),
                n_cpu=cpu,
            )
        else:
            raise ValueError(
                f'{database_type} is not a valid database type. Please select either "bfd", "uniref90", or "mgnify"'
            )

        self.database_type = database_type
        self.max_sto_hits = max_sto_hits
        self.use_precomputed_msas = use_precomputed_msas
        self.msa_format = "a3m" if self.database_type == "bfd" else "sto"
        self.output_name = f"{self.database_type}_hits.{self.msa_format}"

    def process(self, input_fasta_path: str, msa_output_dir: str) -> str:
        """Runs alignment tools on the input sequence."""
        with open(input_fasta_path) as f:
            input_fasta_str = f.read()
            input_seqs, _ = parsers.parse_fasta(input_fasta_str)
        if len(input_seqs) != 1:
            raise ValueError(
                f"More than one input sequence found in {input_fasta_path}."
            )

        msa_out_path = os.path.join(msa_output_dir, self.output_name)
        run_msa_tool(
            msa_runner=self.runner,
            input_fasta_path=input_fasta_path,
            msa_out_path=msa_out_path,
            msa_format=self.msa_format,
            use_precomputed_msas=self.use_precomputed_msas,
            max_sto_sequences=self.max_sto_hits,
        )

        return msa_out_path
