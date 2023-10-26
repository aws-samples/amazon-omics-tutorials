version 1.0
## Copyright Broad Institute, 2017
## This script should convert a CRAM to SAM to BAM and output a BAM, BAM Index, and validation.

## LICENSING : This script is released under the WDL source code license (BSD-3) (see LICENSE in https://github.com/broadinstitute/wdl).
## Note however that the programs it calls may be subject to different licenses. Users are responsible for checking that they are authorized to run all programs before running this script.
## Please see the docker for detailed licensing information pertaining to the included programs.
##
#WORKFLOW DEFINITION
workflow CramToBamFlow {
    input {
        File input_cram
        String sample_name
        String ecr_registry
        String aws_region
    }
    
    String src_bucket_name = "aws-genomics-static-" + aws_region

    File ref_fasta="s3://" + src_bucket_name + "/omics-data/broad-references/hg38/v0/Homo_sapiens_assembly38.fasta"
    File ref_fasta_index="s3://" + src_bucket_name + "/omics-data/broad-references/hg38/v0/Homo_sapiens_assembly38.fasta.fai"
    File ref_dict="s3://" + src_bucket_name + "/omics-data/broad-references/hg38/v0/Homo_sapiens_assembly38.dict"

    String gitc_docker = ecr_registry + "/ecr-public/aws-genomics/broadinstitute/genomes-in-the-cloud:2.5.7-2021-06-09_16-47-48Z-corretto-11"

    #converts CRAM to SAM to BAM and makes BAI
    call CramToBamTask{
        input:
            ref_fasta = ref_fasta,
            ref_fasta_index = ref_fasta_index,
            ref_dict = ref_dict,
            input_cram = input_cram,
            sample_name = sample_name,
            docker_image = gitc_docker,
    }

    #validates Bam
    call ValidateSamFile{
        input:
            input_bam = CramToBamTask.outputBam,
            docker_image = gitc_docker,
    }

    #Outputs Bam, Bai, and validation report
    output {
        File outputBam = CramToBamTask.outputBam
        File outputBai = CramToBamTask.outputBai
        File validation_report = ValidateSamFile.report
    }

}

#Task Definitions
task CramToBamTask {
    input {
        # Command parameters
        File ref_fasta
        File ref_fasta_index
        File ref_dict
        File input_cram
        String sample_name

        # Runtime parameters
        Int machine_mem_size = 2
        String docker_image
    }

    #Calls samtools view to do the conversion
    command {
        echo "Cram to Bam" >&2
        echo "input_cram: ~{input_cram}" >&2
        echo "sample_name: ~{sample_name}" >&2
        set -eo pipefail

        samtools view -h -T ~{ref_fasta} ~{input_cram} |
        samtools view -b -o ~{sample_name}.bam -
        samtools index -b ~{sample_name}.bam
        mv ~{sample_name}.bam.bai ~{sample_name}.bai
    }

    #Run time attributes:
    #Use a docker with samtools. Set this up as a workspace attribute.
    #cpu of one because no multi-threading is required. This is also default, so don't need to specify.
    #disk_size should equal input size + output size + buffer
    runtime {
        docker: docker_image
        memory: machine_mem_size + " GiB"
        cpu: 2
    }

    #Outputs a BAM and BAI with the same sample name
    output {
        File outputBam = "~{sample_name}.bam"
        File outputBai = "~{sample_name}.bai"
    }
}

#Validates BAM output to ensure it wasn't corrupted during the file conversion
task ValidateSamFile {
    input {
        File input_bam
        Int machine_mem_size = 3
        String docker_image
    }
    String output_name = basename(input_bam, ".bam") + ".validation_report"
    Int command_mem_size = machine_mem_size - 1
    command {
        set -e
        echo "Validate" >&2
        echo "input_bam: ~{input_bam}" >&2
        echo "output_name: ~{output_name}" >&2

        java -Xmx~{command_mem_size}G -jar /usr/gitc/picard.jar \
        ValidateSamFile \
        INPUT=~{input_bam} \
        OUTPUT=~{output_name} \
        MODE=SUMMARY \
        IS_BISULFITE_SEQUENCED=false 2>/dev/null
    }
    #Run time attributes:
    #Use a docker with the picard.jar.
    runtime {
        docker: docker_image
        memory: machine_mem_size + " GiB"
        cpu: 2
    }
    #A text file is generated that will list errors or warnings that apply.
    output {
        File report = "~{output_name}"
    }
}
