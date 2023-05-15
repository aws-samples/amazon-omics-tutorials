version 1.0

workflow ESMFoldFlow {
    input {
        File fasta_path
        Int max_length = 800

        String ecr_registry
        String aws_region

    }

    String src_bucket = "aws-genomics-static-" + aws_region
    String src_prefix = "/omics-data/protein-folding"

    File esmfold_model_parameters = "s3://" + src_bucket + src_prefix + "/ref_data/esmfold_parameters_221230.tar"

    String validate_inputs_container_image = ecr_registry + "/protein-utils:omics"
    String esmfold_predict_container_image = ecr_registry + "/esmfold:omics"

    call ValidateInputsTask{
        input:
            fasta_path = fasta_path,
            docker_image = validate_inputs_container_image,
            max_length = max_length
    }
    call ESMFoldTask{
        input:
            fasta_path = ValidateInputsTask.fasta,
            model_parameters = esmfold_model_parameters,
            docker_image = esmfold_predict_container_image
    }
    output {
        File seq_info = write_map(ValidateInputsTask.seq_info)
        File fasta = ValidateInputsTask.fasta
        File pdb = ESMFoldTask.pdb
        File metrics = ESMFoldTask.metrics
        File pae = ESMFoldTask.pae
        File outputs = ESMFoldTask.outputs
    } 
}

task ValidateInputsTask {
    input {
        File fasta_path
        Int cpu = 2
        String memory = "4 GiB"        
        String docker_image = "protein-utils"
        Int max_seq = 1
        Int max_length = 800
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

task ESMFoldTask {
    input {
        File fasta_path
        File model_parameters = "ref_data/esmfold_parameters_221230.tar"
        String memory = "32 GiB"
        Int cpu = 4
        String docker_image = "esmfold"
        String chunk_size = "128"    
        String output_dir = "output"    
    }
    command <<<
        tar -xvf ~{model_parameters} -C $TMPDIR
        /opt/venv/bin/python /opt/esm/scripts/esmfold_inference.py -i ~{fasta_path} -o ~{output_dir} -m $TMPDIR --chunk-size ~{chunk_size} --cpu-only
    >>>
    runtime {
        docker: docker_image,
        memory: memory,
        acceleratorCount: 1,
        acceleratorType: "nvidia-tesla-t4-a10g",
        cpu: cpu        
    }
    output {
        File pdb = "~{output_dir}/prediction.pdb"
        File metrics = "~{output_dir}/metrics.json"
        File pae = "~{output_dir}/pae.png"
        File outputs = "~{output_dir}/outputs.pt"
    }
}

