version 1.0
##Copyright Broad Institute, 2018
##
## This WDL converts paired FASTQ to uBAM and adds read group information
##
## Requirements/expectations :
## - Pair-end sequencing data in FASTQ format (one file per orientation)
## - The following metada descriptors per sample:
##  - readgroup
##  - sample_name
##  - library_name
##  - platform_unit
##  - run_date
##  - platform_name
##  - sequecing_center
##
## Outputs :
## - Set of unmapped BAMs, one per read group
## - File of a list of the generated unmapped BAMs
## For program versions, see docker containers.
##
## LICENSING :
## This script is released under the WDL source code license (BSD-3) (see LICENSE in
## https://github.com/broadinstitute/wdl). Note however that the programs it calls may
## be subject to different licenses. Users are responsible for checking that they are
## authorized to run all programs before running this script. Please see the docker
## page at https://hub.docker.com/r/broadinstitute/genomes-in-the-cloud/ for detailed
## licensing information pertaining to the included programs.

# WORKFLOW DEFINITION
workflow ConvertPairedFastQsToUnmappedBamWf {
    input {
        String sample_name
        File fastq_1
        File fastq_2
        String readgroup_name
        String platform
        String ecr_registry
    }

    String gatk_docker = ecr_registry + "/ecr-public/aws-genomics/broadinstitute/gatk:4.2.6.1-corretto-11"
    String gatk_path = "/gatk/gatk"


    # Convert pair of FASTQs to uBAM
    call PairedFastQsToUnmappedBAM {
        input:
            sample_name = sample_name,
            fastq_1 = fastq_1,
            fastq_2 = fastq_2,
            readgroup_name = readgroup_name,
            platform = platform,
            gatk_path = gatk_path,
            docker = gatk_docker
    }


    # Outputs that will be retained when execution is complete
    output {
        File output_unmapped_bam = PairedFastQsToUnmappedBAM.output_unmapped_bam
    }
}

# TASK DEFINITIONS

# Convert a pair of FASTQs to uBAM
task PairedFastQsToUnmappedBAM {
    input {
        # Command parameters
        String sample_name
        File fastq_1
        File fastq_2
        String readgroup_name
        # The platform type (e.g. illumina, solid)
        String platform
        String gatk_path

        # Runtime parameters
        Int machine_mem_gb = 8
        String docker
    }
    Int command_mem_gb = machine_mem_gb - 1
    String disk_usage_cmd = "echo storage remaining: $(df -Ph . | awk 'NR==2 {print $4}')"

    command {
        set -e
        # determine scratch size used
        ~{disk_usage_cmd}

        echo "FASTQ to uBAM" >&2
        echo "fastq_1 ~{fastq_1}" >&2
        echo "fastq_2 ~{fastq_2}" >&2
        echo "sample_name ~{sample_name}" >&2
        echo "readgroup_name ~{readgroup_name}" >&2
        echo "platform ~{readgroup_name}" >&2

        ~{gatk_path} --java-options "-Dsamjdk.compression_level=2 -Xmx~{command_mem_gb}g" \
        FastqToSam \
        --FASTQ ~{fastq_1} \
        --FASTQ2 ~{fastq_2} \
        --OUTPUT ~{readgroup_name}.unmapped.bam \
        --READ_GROUP_NAME ~{readgroup_name} \
        --PLATFORM ~{platform} \
        --SAMPLE_NAME ~{sample_name}

        # determine final scratch size used
        ~{disk_usage_cmd}
    }
    runtime {
        docker: docker
        memory: machine_mem_gb + " GiB"
        cpu: 2
    }
    output {
        File output_unmapped_bam = "~{readgroup_name}.unmapped.bam"
    }
}


