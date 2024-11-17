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
  dockerPull: $(inputs.docker_image)
- class: InitialWorkDirRequirement
  listing:
    - entryname: createSequenceGroupingTSV.sh
      entry: |-
        set -euxo pipefail
        echo CreateSequenceGroupingTSV >&2

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

        bash_sequence_grouping=$1
        bash_sequence_grouping_with_unmapped=$2

        python createSequenceGroupingTSV.py $bash_sequence_grouping $bash_sequence_grouping_with_unmapped
        python formatTsv.py $bash_sequence_grouping $bash_sequence_grouping_with_unmapped

        # determine scratch size used
        echo -n storage remaining: 
        df -Ph . | awk 'NR==2 {print $4}'

    - entryname: createSequenceGroupingTSV.py
      entry: |-
        import sys
        print(sys.argv)
        ref_fasta = "$(inputs.ref_fasta.path)"
        ref_dict_list = ref_fasta.split(".fasta")
        ref_dict_list[-1] = "dict"
        ref_dict = ".".join(ref_dict_list)

        with open(ref_dict, "r") as ref_dict_file:
            sequence_tuple_list = []
            longest_sequence = 0
            for line in ref_dict_file:
                if line.startswith("@SQ"):
                    line_split = line.split("\t")
                    # (Sequence_Name, Sequence_Length)
                    sequence_tuple_list.append((line_split[1].split("SN:")[1], int(line_split[2].split("LN:")[1])))
            longest_sequence = sorted(sequence_tuple_list, key=lambda x: x[1], reverse=True)[0][1]
        # We are adding this to the intervals because hg38 has contigs named with embedded colons (:) and a bug in
        # some versions of GATK strips off the last element after a colon, so we add this as a sacrificial element.
        hg38_protection_tag = ":1+"
        # initialize the tsv string with the first sequence
        tsv_string = sequence_tuple_list[0][0] + hg38_protection_tag
        temp_size = sequence_tuple_list[0][1]
        for sequence_tuple in sequence_tuple_list[1:]:
            if temp_size + sequence_tuple[1] <= longest_sequence:
                temp_size += sequence_tuple[1]
                tsv_string += "\t" + sequence_tuple[0] + hg38_protection_tag
            else:
                tsv_string += "\n" + sequence_tuple[0] + hg38_protection_tag
                temp_size = sequence_tuple[1]
        # add the unmapped sequences as a separate line to ensure that they are recalibrated as well
        sequence_grouping = sys.argv[1]
        with open(f"{sequence_grouping}.txt","w") as tsv_file:
          tsv_file.write(tsv_string)
          tsv_file.close()

        tsv_string += '\n' + "unmapped"

        sequence_grouping_with_unmapped = sys.argv[2]
        with open(f"{sequence_grouping_with_unmapped}.txt","w") as tsv_file_with_unmapped:
          tsv_file_with_unmapped.write(tsv_string)
          tsv_file_with_unmapped.close()

    - entryname: formatTsv.py
      entry: |-
        import json
        import sys
        output_names = sys.argv[1:]
        object = {}
        for output_name in output_names:
          tsv = output_name + '.txt'
          with open(tsv, "r") as tsv_file:
              rows = [line.rstrip().split("\t") for line in tsv_file]
              object[output_name] = rows
              tsv_file.close()
        with open("cwl.output.json", "w") as output_file:
          json.dump(object, output_file, indent = 0)
          output_file.close()

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

  docker_image: string
  docker_cores: int
  docker_ram_in_mb: int
outputs:
  sequence_grouping:
    type:
      type: array
      items: 
          type: array
          items: string

  sequence_grouping_with_unmapped:
    type:
      type: array
      items: 
          type: array
          items: string

baseCommand: ["bash", "createSequenceGroupingTSV.sh"]
arguments:
  - $("sequence_grouping")
  - $("sequence_grouping_with_unmapped")
