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
    - entryname: gatherBqsrReports.sh
      entry: |-
        # determine scratch size used
        set -euxo pipefail
        echo GatherBqsrReports >&2

        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

        bash_tool_available_mem_in_mb=$(inputs.docker_ram_in_mb - 2000)M
        echo bash_tool_available_mem_in_mb=$bash_tool_available_mem_in_mb >&2

        $(inputs.gatk_path) --java-options "-Xmx$bash_tool_available_mem_in_mb -XX:+UseShenandoahGC" \
        GatherBQSRReports \
        -I $(inputs.input_bqsr_reports.map( report => report.path).join(" -I ")) \
        -O $(inputs.output_report_filename)

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

inputs:
  input_bqsr_reports: File[]
  output_report_filename: string

  gatk_docker: string
  gatk_path: string
  docker_cores: int
  docker_ram_in_mb: int
outputs:
  output_bqsr_report:
    type: File
    outputBinding:
        glob: $(inputs.output_report_filename)

baseCommand: ["bash", "gatherBqsrReports.sh"]
