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
    - entryname: gatherBamFiles.sh
      entry: |-
        set -euxo pipefail
        echo GatherBqsrReports >&2

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

        bash_tool_available_mem_in_mb=$(inputs.docker_ram_in_mb - 2000)M
        echo bash_tool_available_mem_in_mb=$bash_tool_available_mem_in_mb >&2

        $(inputs.gatk_path) --java-options "-Dsamjdk.compression_level=$(inputs.compression_level) -Xmx$bash_tool_available_mem_in_mb -XX:+UseShenandoahGC" \
        GatherBamFiles \
        --INPUT $(inputs.input_bams.map( bam => bam.path).join(" --INPUT ")) \
        --OUTPUT $(inputs.output_bam_basename).bam \
        --CREATE_INDEX true \
        --CREATE_MD5_FILE true

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

inputs:
  input_bams: File[]
  output_bam_basename: string
  compression_level: int

  gatk_docker: string
  gatk_path: string
  docker_cores: int
  docker_ram_in_mb: int
outputs:
  output_bam:
    type: File
    outputBinding:
        glob: $(inputs.output_bam_basename + '.bam')
    secondaryFiles:
       - pattern: "^.bai"
       - pattern: ".md5"

baseCommand: ["bash", "gatherBamFiles.sh"]