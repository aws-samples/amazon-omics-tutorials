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
    - entryname: mergeBamAlignment.sh
      entry: |-
        set -euxo pipefail
        echo MarkDuplicates >&2

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

        bash_tool_available_mem_in_mb=$(inputs.docker_ram_in_mb - 1000)M
        echo bash_tool_available_mem_in_mb=$bash_tool_available_mem_in_mb >&2

        $(inputs.gatk_path) --java-options "-Dsamjdk.compression_level=$(inputs.compression_level) -Xmx$bash_tool_available_mem_in_mb" \
        MarkDuplicates \
        --INPUT $(inputs.input_bams.map( bam => bam.path).join(" --INPUT ")) \
        --OUTPUT $(inputs.output_bam_basename).bam \
        --METRICS_FILE $(inputs.metrics_filename) \
        --VALIDATION_STRINGENCY SILENT \
        --OPTICAL_DUPLICATE_PIXEL_DISTANCE 2500 \
        --ASSUME_SORT_ORDER "queryname" \
        --CREATE_MD5_FILE false

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

inputs:
  sample_name: string
  ref_name: string
  input_bams: File[]
  output_bam_basename:  string
  metrics_filename: string
  compression_level: int
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

  gatk_docker: string
  gatk_path: string
  docker_cores: int
  docker_ram_in_mb: int
outputs:
  output_bam:
    type: File
    outputBinding:
        glob: $(inputs.output_bam_basename + ".bam")
  duplication_metrics:
    type: File
    outputBinding:
      glob: $(inputs.metrics_filename)

baseCommand: ["bash", "mergeBamAlignment.sh"]