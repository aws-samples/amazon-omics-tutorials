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
  dockerPull: $(inputs.gotc_docker)
- class: InitialWorkDirRequirement
  listing:
    - entryname: bwaMemAlign.sh
      entry: |-
        set -euo pipefail
        echo BwaMemAlign >&2

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

        set -x
        $(inputs.gotc_path)$(inputs.bwa_commandline) \
        -Y $(inputs.ref_fasta.path) $(inputs.fastq_1.path) $(inputs.fastq_2.path) \
        | \
        samtools view -@ 4 -1 - > $(inputs.output_bam_basename).bam

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'
inputs:
  fastq_1: File 
  fastq_2: File

  output_bam_basename:  string
  bwa_commandline: string
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
  gotc_docker: string
  gotc_path: string
  docker_ram_in_mb: int
  docker_cores: int

outputs:
  output_bam:
    type: File
    outputBinding:
        glob: $(inputs.output_bam_basename + ".bam")

baseCommand: ["bash", "bwaMemAlign.sh"]
