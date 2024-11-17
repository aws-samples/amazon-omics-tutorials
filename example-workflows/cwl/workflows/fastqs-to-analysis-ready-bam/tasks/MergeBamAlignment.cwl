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

        echo MergeBamAlignment >&2
        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

        bash_tool_available_mem_in_mb=$(inputs.docker_ram_in_mb - 1000)M
        echo bash_tool_available_mem_in_mb=$bash_tool_available_mem_in_mb >&2

        $(inputs.gatk_path) --java-options "-Dsamjdk.compression_level=$(inputs.compression_level) -Xmx$bash_tool_available_mem_in_mb -XX:+UseShenandoahGC" \
        MergeBamAlignment \
        --VALIDATION_STRINGENCY SILENT \
        --EXPECTED_ORIENTATIONS FR \
        --ATTRIBUTES_TO_RETAIN X0 \
        --ALIGNED_BAM $(inputs.aligned_bam.path) \
        --UNMAPPED_BAM $(inputs.unmapped_bam.path) \
        --OUTPUT $(inputs.output_bam_basename).bam \
        --REFERENCE_SEQUENCE $(inputs.ref_fasta.path) \
        --PAIRED_RUN true \
        --SORT_ORDER "unsorted" \
        --IS_BISULFITE_SEQUENCE false \
        --ALIGNED_READS_ONLY false \
        --CLIP_ADAPTERS false \
        --ADD_MATE_CIGAR true \
        --MAX_INSERTIONS_OR_DELETIONS -1 \
        --PRIMARY_ALIGNMENT_STRATEGY MostDistant \
        --PROGRAM_RECORD_ID "bwamem" \
        --PROGRAM_GROUP_VERSION "$(inputs.bwa_version)" \
        --PROGRAM_GROUP_COMMAND_LINE "$(inputs.bwa_commandline) -Y $(inputs.ref_fasta.path)" \
        --PROGRAM_GROUP_NAME "bwamem" \
        --UNMAPPED_READ_STRATEGY COPY_TO_TAG \
        --ALIGNER_PROPER_PAIR_FLAGS true \
        --UNMAP_CONTAMINANT_READS true

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'
inputs:
  unmapped_bam: File
  aligned_bam: File
  output_bam_basename:  string
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
  bwa_version: string
  bwa_commandline: string
  docker_cores: int
  docker_ram_in_mb: int

outputs:
  output_bam:
    type: File[]
    outputBinding:
        glob: $(inputs.output_bam_basename + ".bam")

baseCommand: ["bash", "mergeBamAlignment.sh"]