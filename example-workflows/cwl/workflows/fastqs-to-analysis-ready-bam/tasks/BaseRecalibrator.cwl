cwlVersion: v1.2
class: CommandLineTool
requirements:
- class: SubworkflowFeatureRequirement
- class: InlineJavascriptRequirement
- class: ShellCommandRequirement
- class: ResourceRequirement
  ramMin: $(inputs.docker_ram_in_mb)
  coresMin: $(inputs.docker_cores)
- class: DockerRequirement
  dockerPull: $(inputs.gatk_docker)
- class: InitialWorkDirRequirement
  listing:
    - entryname: baseRecalibrator.sh
      entry: |-
        set -euxo pipefail
        echo BaseRecalibrator >&2

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

        bash_tool_available_mem_in_mb=$(inputs.docker_ram_in_mb - 4000)M
        echo bash_tool_available_mem_in_mb=$bash_tool_available_mem_in_mb >&2

        $(inputs.gatk_path) --java-options "-Xmx$bash_tool_available_mem_in_mb" \
        BaseRecalibrator \
        -R $(inputs.ref_fasta.path) \
        -I $(inputs.input_bam.path) \
        -O $(inputs.recalibration_report_filename) \
        --use-original-qualities \
        --known-sites $(inputs.dbSNP_vcf.path) \
        --known-sites $(inputs.known_indels_sites_VCFs.map( vcf => vcf.path).join(" --known-sites ")) \
        -L $(inputs.sequence_grouping.join(" -L "))

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

inputs:
  ref_fasta: 
    type: File
    secondaryFiles:
      - pattern: "^.dict"
      - pattern: ".fai"
      - pattern: ".64.alt"
      - pattern: ".64.amb"
      - pattern: ".64.ann"
      - pattern: ".64.bwt"
      - pattern: ".64.pac"
      - pattern: ".64.sa"
  input_bam: 
    type: File
    secondaryFiles:
      - pattern: "^.bai"
  sequence_grouping: string[]
  recalibration_report_filename: string
  dbSNP_vcf:
    type: File
    secondaryFiles:
      - pattern: ".idx"
  known_indels_sites_VCFs: 
    type: File[]
    secondaryFiles:
      - pattern: ".tbi"

  gatk_docker: string
  gatk_path: string
  docker_cores: int
  docker_ram_in_mb: int
outputs:
  recalibration_report:
    type: File
    outputBinding:
        glob: $(inputs.recalibration_report_filename)

baseCommand: ["bash", "baseRecalibrator.sh"]