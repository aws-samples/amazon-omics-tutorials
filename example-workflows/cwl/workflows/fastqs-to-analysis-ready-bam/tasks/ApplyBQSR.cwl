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
    - entryname: applyBQSR.sh
      entry: |-
        set -euxo pipefail

        echo ApplyBQSR >&2
        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

        bash_tool_available_mem_in_mb=$(inputs.docker_ram_in_mb - 2000)M
        echo bash_tool_available_mem_in_mb=$bash_tool_available_mem_in_mb >&2

        $(inputs.gatk_path) --java-options "-Dsamjdk.compression_level=$(inputs.compression_level) -Xmx$bash_tool_available_mem_in_mb -XX:+UseShenandoahGC" \
        ApplyBQSR \
        -R $(inputs.ref_fasta.path) \
        -I $(inputs.input_bam.path) \
        -O $(inputs.output_bam_basename).bam \
        -L $(inputs.subgroup.join(" -L ")) \
        -bqsr $(inputs.recalibration_report.path) \
        --static-quantized-quals 10 --static-quantized-quals 20 --static-quantized-quals 30 \
        --add-output-sam-program-record \
        --create-output-bam-md5 \
        --use-original-qualities

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'
inputs:
  input_bam: 
    type: File
    secondaryFiles:
      - pattern: "^.fai"
  output_bam_basename:  string
  compression_level: int
  recalibration_report: File
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
  subgroup: string[]

  gatk_docker: string
  gatk_path: string
  docker_cores: int
  docker_ram_in_mb: int
outputs:
  recalibrated_bam:
    type: File
    outputBinding:
        glob: $(inputs.output_bam_basename + ".bam")

baseCommand: ["bash", "applyBQSR.sh"]