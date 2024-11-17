cwlVersion: v1.2
class: CommandLineTool
requirements:

- class: InlineJavascriptRequirement
- class: ShellCommandRequirement
- class: ResourceRequirement
  ramMin: $(inputs.docker_ram_in_mb)
  coresMin: $(inputs.docker_cores)
- class: DockerRequirement
  dockerPull: $(inputs.gatk_docker)
- class: InitialWorkDirRequirement
  listing:
    - entryname: pairedFastQsToUnmappedBAM.sh
      entry: |-
        set -euo pipefail

        echo "PairedFastQsToUnmappedBAM" >&2
        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

        bash_tool_available_mem_in_mb=$(inputs.docker_ram_in_mb - 2000)M
        echo bash_tool_available_mem_in_mb=$bash_tool_available_mem_in_mb >&2

        $(inputs.gatk_path) --java-options "-Dsamjdk.compression_level=$(inputs.compression_level) -Xmx$bash_tool_available_mem_in_mb" \
        FastqToSam \
        --FASTQ $(inputs.fastq_1.path) \
        --FASTQ2 $(inputs.fastq_2.path) \
        --OUTPUT $(inputs.platform + '.unmapped.bam') \
        --READ_GROUP_NAME $(inputs.read_group_name) \
        --PLATFORM $(inputs.platform) \
        --SAMPLE_NAME $(inputs.sample_name)

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

inputs:
  sample_name: string
  fastq_1: File
  fastq_2: File
  read_group_name: string
  platform: string
  compression_level: int

  gatk_docker: string
  gatk_path: string
  docker_ram_in_mb: int
  docker_cores: int

outputs:
  output_unmapped_bam:
    type: File
    outputBinding:
      glob: "*.unmapped.bam"

baseCommand: ["bash", "pairedFastQsToUnmappedBAM.sh"]