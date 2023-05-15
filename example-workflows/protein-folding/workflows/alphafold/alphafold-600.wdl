version 1.0

workflow AlphaFoldFlow {
    input {
        File fasta_path
        Int max_length = 600

        String ecr_registry
        String aws_region

    }

    String src_bucket = "aws-genomics-static-" + aws_region
    String src_prefix = "/omics-data/protein-folding"

    File uniref90_database_src = "s3://" + src_bucket + src_prefix + "/ref_data/uniref90.tar.gz"
    File mgnify_database_src = "s3://" + src_bucket + src_prefix + "/ref_data/mgy_clusters_2022_05.fa.gz"
    File bfd_database_src = "s3://" + src_bucket + src_prefix + "/ref_data/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt.tar.gz"
    File uniref30_database_src = "s3://" + src_bucket + src_prefix + "/ref_data/UniRef30_2021_03.tar.gz"
    File pdb70_src = "s3://" + src_bucket + src_prefix + "/ref_data/pdb70_from_mmcif_200401.tar.gz"
    File pdb_seqres_src = "s3://" + src_bucket + src_prefix + "/ref_data/pdb_seqres.txt"
    File pdb_mmcif_src = "s3://" + src_bucket + src_prefix + "/ref_data/pdb_mmcif.tar.gz"
    File alphafold_model_parameters = "s3://" + src_bucket + src_prefix + "/ref_data/alphafold_params_2022-12-06.tar"

    String alphafold_data_container_image = ecr_registry + "/alphafold-data:omics"
    String validate_inputs_container_image = ecr_registry + "/protein-utils:omics"
    String alphafold_predict_container_image = ecr_registry + "/alphafold-predict:omics"

    call ValidateInputsTask{
        input:
            fasta_path = fasta_path,
            docker_image = validate_inputs_container_image,
            max_length = max_length
    }
    call SearchUniref90{
        input:
            fasta_path = ValidateInputsTask.fasta,
            database_src = uniref90_database_src,
            docker_image = alphafold_data_container_image
    }
    call SearchMgnify{
        input:
            fasta_path = ValidateInputsTask.fasta,
            database_src = mgnify_database_src,
            docker_image = alphafold_data_container_image
    }
    call SearchBFD{
        input:
            fasta_path = ValidateInputsTask.fasta,
            bfd_database_src = bfd_database_src,
            uniref30_database_src = uniref30_database_src,
            docker_image = alphafold_data_container_image
    }
    call SearchTemplatesTask{
        input:
            msa_path = SearchUniref90.msa,
            pdb70_src = pdb70_src,
            pdb_seqres_src = pdb_seqres_src,
            docker_image = alphafold_data_container_image
    }
    call GenerateFeaturesTask{
        input:
            fasta_path = ValidateInputsTask.fasta,
            msa_path = [SearchUniref90.msa, SearchMgnify.msa, SearchBFD.msa],
            template_hits = SearchTemplatesTask.pdb_hits,
            pdb_mmcif_src = pdb_mmcif_src,
            docker_image = alphafold_data_container_image
    }
    call AlphaFoldTask{
        input:
            target_id = ValidateInputsTask.seq_info["id"],
            features = GenerateFeaturesTask.features,
            model_parameters = alphafold_model_parameters,
            docker_image = alphafold_predict_container_image
    }
    output {        
        File seq_info = write_map(ValidateInputsTask.seq_info)
        File fasta = ValidateInputsTask.fasta
        File uniref90_msa = SearchUniref90.msa
        File uniref90_metrics = SearchUniref90.metrics
        File mgnify_msa = SearchMgnify.msa
        File mgnify_metrics = SearchMgnify.metrics
        File bfd_msa = SearchBFD.msa
        File bfd_metrics = SearchBFD.metrics        
        File templates = SearchTemplatesTask.pdb_hits
        File templates_metrics = SearchTemplatesTask.metrics
        File features = GenerateFeaturesTask.features
        File features_metrics = GenerateFeaturesTask.metrics
        File prediction = AlphaFoldTask.results
        File prediction_metrics = AlphaFoldTask.metrics
    } 
}


task ValidateInputsTask {
    input {
        File fasta_path
        Int cpu = 2
        String memory = "4 GiB"        
        String docker_image = "protein-utils"
        Int max_seq = 1
        Int max_length = 2000
        String output_file = "input.fasta"
    }
    command <<<
        set -euxo pipefail
        /opt/venv/bin/python /opt/venv/lib/python3.8/site-packages/putils/validate_inputs.py ~{fasta_path} --max_seq=~{max_seq} --max_length=~{max_length} --output_file=~{output_file}
    >>>
    runtime {
        docker: docker_image,
        memory: memory,
        cpu: cpu
    }
    output {
        Map[String, String] seq_info = read_json("seq_info.json")
        File fasta = "~{output_file}"
    }
}

task SearchUniref90 {
    input {
        File fasta_path
        File database_src = "ref_data/uniref90.tar.gz"
        String database_type = "uniref90"
        String output_dir = "output"
        String tmp_dir = "/tmp"
        Int cpu = 8
        String memory = "32 GiB"
        String docker_image = "alphafold-data"
    }
    command <<<
        set -euxo pipefail
        tar -xvf ~{database_src} -C ~{tmp_dir}
        /opt/venv/bin/python /opt/create_msa_monomer.py \
          --fasta_path=~{fasta_path} \
          --database_type=~{database_type} \
          --database_path=~{tmp_dir} \
          --output_dir=~{output_dir} \
          --cpu=~{cpu}
    >>>
    runtime {
        docker: docker_image,
        memory: memory,
        cpu: cpu
    }
    output {
        File msa = "~{output_dir}/uniref90_hits.sto"
        File metrics = "~{output_dir}/metrics.json"
    }
}

task SearchMgnify {
    input {
        File fasta_path
        File database_src = "ref_data/mgy_clusters_2022_05.fa.gz"
        String database_type = "mgnify"
        String output_dir = "output"
        String tmp_dir = "/tmp"
        Int cpu = 8
        String memory = "32 GiB"
        String docker_image = "alphafold-data"
    }
    command <<<
        set -euxo pipefail
        gunzip -c ~{database_src} > ~{tmp_dir}/mgy_clusters_2022_05.fa
        /opt/venv/bin/python /opt/create_msa_monomer.py \
          --fasta_path=~{fasta_path} \
          --database_type=~{database_type} \
          --database_path=~{tmp_dir} \
          --output_dir=~{output_dir} \
          --cpu=~{cpu}
    >>>
    runtime {
        docker: docker_image,
        memory: memory,
        cpu: cpu
    }
    output {
        File msa = "~{output_dir}/mgnify_hits.sto"
        File metrics = "~{output_dir}/metrics.json"
    }
}

task SearchBFD {
    input {
        File fasta_path
        File bfd_database_src = "ref_data/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt.tar.gz"
        File uniref30_database_src = "ref_data/UniRef30_2021_03.tar.gz"
        String database_type = "bfd"
        String output_dir = "output"
        String tmp_dir = "/tmp"
        Int cpu = 4
        String memory = "64 GiB"
        String docker_image = "alphafold-data"
    }
    command <<<
        set -euxo pipefail
        mkdir -p ~{tmp_dir}/bfd 
        tar -xvf ~{bfd_database_src} -C ~{tmp_dir}/bfd
        mkdir -p ~{tmp_dir}/uniref30
        tar -xvf ~{uniref30_database_src} -C ~{tmp_dir}/uniref30
        /opt/venv/bin/python /opt/create_msa_monomer.py \
          --fasta_path=~{fasta_path} \
          --database_type=~{database_type} \
          --database_path=~{tmp_dir} \
          --output_dir=~{output_dir} \
          --cpu=~{cpu}
    >>>
    runtime {
        docker: docker_image,
        memory: memory,
        cpu: cpu
    }
    output {
        File msa = "~{output_dir}/bfd_hits.a3m"
        File metrics = "~{output_dir}/metrics.json"
    }
}

task SearchTemplatesTask {
    input {
        File msa_path
        File pdb70_src = "ref_data/pdb70_from_mmcif_200401.tar.gz"
        File pdb_seqres_src = "ref_data/pdb_seqres.txt"
        String model_preset = "monomer_ptm"
        String output_dir = "output"
        String tmp_dir = "/tmp"        
        Int cpu = 2
        String memory = "8 GiB"
        String docker_image = "alphafold-data"
    }
    command <<<
        set -euxo pipefail
        tar -xvf ~{pdb70_src} -C ~{tmp_dir}
        cp ~{pdb_seqres_src} ~{tmp_dir}
        /opt/venv/bin/python /opt/search_templates.py \
          --msa_path=~{msa_path} \
          --output_dir=~{output_dir} \
          --database_path=~{tmp_dir} \
          --model_preset=~{model_preset} \
          --cpu=~{cpu}
    >>>
    runtime {
        docker: docker_image,
        memory: memory,
        cpu: cpu
    }
    output {
        File pdb_hits = "~{output_dir}/pdb_hits.hhr"
        File metrics = "~{output_dir}/metrics.json"
    }
}

task GenerateFeaturesTask {
    input {
        File fasta_path
        Array[File]+ msa_path
        File template_hits
        File pdb_mmcif_src = "ref_data/pdb_mmcif.tar.gz"
        String output_dir = "output"
        String tmp_dir = "/tmp"        
        String max_template_date = "2023-01-01"
        String model_preset = "monomer_ptm"
        Int cpu = 2
        String memory = "8 GiB"
        String docker_image = "alphafold-data"
    }
    command <<<
        set -euxo pipefail
        cp -p ~{sep=" " msa_path} ~{tmp_dir}
        cp -p ~{template_hits} ~{tmp_dir}
        tar -xzf ~{pdb_mmcif_src} -C ~{tmp_dir}
        /opt/venv/bin/python /opt/generate_features.py \
          --fasta_paths=~{fasta_path} \
          --msa_dir=~{tmp_dir} \
          --template_mmcif_dir="~{tmp_dir}/pdb_mmcif/mmcif_files" \
          --obsolete_pdbs_path="~{tmp_dir}/pdb_mmcif/obsolete.dat" \
          --template_hits=~{template_hits} \
          --model_preset=~{model_preset} \
          --output_dir=~{output_dir} \
          --max_template_date=~{max_template_date}          
    >>>
    runtime {
        docker: docker_image,
        memory: memory,
        cpu: cpu
    }
    output {
        File features = "~{output_dir}/features.pkl"
        File metrics = "~{output_dir}/metrics.json"
    }
}

task AlphaFoldTask {
    input {
        String target_id
        File features
        File model_parameters = "ref_data/alphafold_params_2022-12-06.tar"
        String model_preset="monomer_ptm"
        String model_dir = "/tmp"
        String output_dir = "output"
        Int random_seed = 42
        Boolean run_relax = false
        Boolean use_gpu_relax = false
        Int model_max = 5        
        Int cpu = 8
        String memory = "32 GiB"
        String docker_image = "alphafold-predict"
    }
    command <<<
        set -euxo pipefail
        mkdir -p ~{model_dir}/params
        tar -xvf ~{model_parameters} -C ~{model_dir}/params
        /opt/conda/bin/python /opt/predict.py \
          --target_id=~{target_id} --features_path=~{features} --model_preset=~{model_preset} \
          --model_dir=~{model_dir} --random_seed=~{random_seed} --output_dir=~{output_dir} \
          --run_relax=~{run_relax} --use_gpu_relax=~{use_gpu_relax} --model_max=~{model_max}
        mv ~{output_dir}/metrics.json .
        rm -rf ~{output_dir}/msas
        tar -czvf results.tar.gz -C ~{output_dir} .
    >>>
    runtime {
        docker: docker_image,
        memory: memory,
        acceleratorCount: 1,
        acceleratorType: "nvidia-tesla-t4-a10g",
        cpu: cpu        
    }
    output {
        File results = "results.tar.gz"
        File metrics = "metrics.json"
    }
}

