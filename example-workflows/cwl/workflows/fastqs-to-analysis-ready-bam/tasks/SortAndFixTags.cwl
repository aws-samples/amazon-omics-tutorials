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
        echo SortAndFixTags >&2

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

        INTERMEDIATE_FILE=SORTED_TMP_FILE.BAM

        $(inputs.gatk_path) --java-options "-Dsamjdk.compression_level=$(inputs.compression_level) -Xmx50G" \
        SortSam \
        --INPUT $(inputs.input_bam.path) \
        --OUTPUT $INTERMEDIATE_FILE \
        --SORT_ORDER "coordinate" \
        --CREATE_INDEX false \
        --CREATE_MD5_FILE false

        $(inputs.gatk_path) --java-options "-Dsamjdk.compression_level=$(inputs.compression_level) -Xmx8G" \
        SetNmMdAndUqTags \
        --INPUT $INTERMEDIATE_FILE \
        --OUTPUT $(inputs.output_bam_basename).bam \
        --CREATE_INDEX true \
        --CREATE_MD5_FILE false \
        --REFERENCE_SEQUENCE $(inputs.ref_fasta.path)

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

inputs:
  input_bam: File
  output_bam_basename:  string
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
  compression_level: int

  gatk_docker: string
  gatk_path: string
  docker_ram_in_mb: int
  docker_cores: int

outputs:
  output_bam:
    type: File
    outputBinding:
        glob: $(inputs.output_bam_basename + ".bam")
    secondaryFiles:
      - pattern: "^.bai"

baseCommand: ["bash", "mergeBamAlignment.sh"]