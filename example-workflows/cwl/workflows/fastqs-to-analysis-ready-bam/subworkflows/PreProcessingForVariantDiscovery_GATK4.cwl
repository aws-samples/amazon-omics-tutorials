cwlVersion: v1.2
class: Workflow
requirements:
  - class: SubworkflowFeatureRequirement
  - class: ScatterFeatureRequirement
  - class: StepInputExpressionRequirement
  - class: InlineJavascriptRequirement

inputs:
  sample_name: string
  fastq_pair:
    type:
      type: record
      fields:
        - name: read_group
          type: string
        - name: platform
          type: string
        - name: fastq_1
          type: File
        - name: fastq_2
          type: File
  ref_name: string
  ref_fasta: File
  dbSNP_vcf: File
  known_indels_sites_VCFs: File[]

  gatk_docker: string
  gotc_docker: string
  python_docker: string
  gatk_path: string
  gotc_path: string
  bwa_commandline: string

outputs:
  duplication_metrics:
    type: File
    outputSource: MarkDuplicates/duplication_metrics
  bqsr_report:
    type: File
    outputSource: GatherBqsrReports/output_bqsr_report
  analysis_ready_bam:
    type: File
    outputSource: GatherBamFiles/output_bam
    secondaryFiles:
      - pattern: "^.bai"
      - pattern: ".md5"

steps:
  PairedFastQsToUnmappedBAM:
    run: ../tasks/PairedFastQsToUnmappedBAM.cwl
    in:
      fastq_pair: fastq_pair
      sample_name: sample_name
      platform:
        valueFrom: "$(inputs.fastq_pair.platform)"
      fastq_1:
        valueFrom: "$(inputs.fastq_pair.fastq_1)"
      fastq_2:
        valueFrom: "$(inputs.fastq_pair.fastq_2)"
      read_group_name:
        valueFrom: "$(inputs.fastq_pair.read_group)"
      compression_level:
        valueFrom: $(2)
      gatk_docker: gatk_docker
      gatk_path: gatk_path
      docker_cores:
        valueFrom: $(2)
      docker_ram_in_mb:
        valueFrom: $(8000)
    out:
      - output_unmapped_bam

  BwaMemAlign:
    run: ../tasks/BwaMemAlign.cwl
    in:
      fastq_pair: fastq_pair
      fastq_1:
        valueFrom: "$(inputs.fastq_pair.fastq_1)"
      fastq_2:
        valueFrom: "$(inputs.fastq_pair.fastq_2)"

      ref_name: ref_name
      bam_basename:
        valueFrom: "$(inputs.fastq_pair.read_group + '.' + inputs.ref_name)"
      output_bam_basename:
        valueFrom: "$(inputs.fastq_pair.read_group + '.' + inputs.ref_name + '.unmerged')"
      ref_fasta: ref_fasta

      bwa_commandline: bwa_commandline
      gotc_path: gotc_path
      gotc_docker: gotc_docker
      docker_cores:
        valueFrom: $(16)
      docker_ram_in_mb:
        valueFrom: $(32000)
    out:
      - output_bam

  MergeBamAlignment:
    run: ../tasks/MergeBamAlignment.cwl
    in:
      ref_fasta: ref_fasta
      unmapped_bam: PairedFastQsToUnmappedBAM/output_unmapped_bam
      aligned_bam: BwaMemAlign/output_bam

      fastq_pair: fastq_pair
      ref_name: ref_name
      bam_basename:
        valueFrom: "$(inputs.fastq_pair.read_group + '.' + inputs.ref_name)"
      output_bam_basename:
        valueFrom: "$(inputs.fastq_pair.read_group + '.' + inputs.ref_name + '.aligned.unsorted')"

      compression_level:
        valueFrom: $(2)
      bwa_version:
        valueFrom: "0.7.15-r1140"
      bwa_commandline: bwa_commandline

      gatk_docker: gatk_docker
      gatk_path: gatk_path
      docker_cores:
        valueFrom: $(2)
      docker_ram_in_mb:
        valueFrom: $(8000)
    out:
      - output_bam

  MarkDuplicates:
    run: ../tasks/MarkDuplicates.cwl
    in:
      ref_name: ref_name
      fastq_pair: fastq_pair
      sample_name: sample_name
      input_bams: MergeBamAlignment/output_bam
      output_bam_basename:
        valueFrom: "$(inputs.fastq_pair.read_group + '.' + inputs.ref_name + '.aligned.unsorted.duplicates_marked')"
      metrics_filename:
        valueFrom: "$(inputs.sample_name + '.' + inputs.ref_name +  '.duplicate_metrics')"
      ref_fasta: ref_fasta
      compression_level:
        valueFrom: $(2)

      gatk_docker: gatk_docker
      gatk_path: gatk_path
      docker_cores:
        valueFrom: $(4)
      docker_ram_in_mb:
        valueFrom: $(64000)
    out:
      - output_bam
      - duplication_metrics

  SortAndFixTags:
    run: ../tasks/SortAndFixTags.cwl
    in:
      input_bam: MarkDuplicates/output_bam
      ref_fasta: ref_fasta
      compression_level:
        valueFrom: $(2)

      fastq_pair: fastq_pair
      ref_name: ref_name
      output_bam_basename:
        valueFrom: "$(inputs.fastq_pair.read_group + '.' + inputs.ref_name + '.aligned.duplicate_marked.sorted')"

      gatk_docker: gatk_docker
      gatk_path: gatk_path
      docker_cores:
        valueFrom: $(4)
      docker_ram_in_mb:
        valueFrom: $(64000)
    out:
      - output_bam

  CreateSequenceGroupingTSV:
    run: ../tasks/CreateSequenceGroupingTSV.cwl
    in:
      ref_fasta: ref_fasta
      docker_image: python_docker
      docker_cores:
        valueFrom: $(2)
      docker_ram_in_mb:
        valueFrom: $(2000)
    out:
      - sequence_grouping
      - sequence_grouping_with_unmapped

  BaseRecalibrator:
    run: ../tasks/BaseRecalibrator.cwl
    scatter: sequence_grouping
    scatterMethod: dotproduct
    in:
      ref_fasta: ref_fasta
      input_bam: SortAndFixTags/output_bam
      sequence_grouping: CreateSequenceGroupingTSV/sequence_grouping

      ref_name: ref_name
      sample_name: sample_name
      recalibration_report_filename:
        valueFrom: "$(inputs.sample_name + '.' + inputs.ref_name + '.recal_data.csv')"
      dbSNP_vcf: dbSNP_vcf
      known_indels_sites_VCFs: known_indels_sites_VCFs

      gatk_docker: gatk_docker
      gatk_path: gatk_path
      docker_cores:
        valueFrom: $(2)
      docker_ram_in_mb:
        valueFrom: $(16000)
    out:
      - recalibration_report

  GatherBqsrReports:
    run: ../tasks/GatherBqsrReports.cwl
    in:
      input_bqsr_reports: BaseRecalibrator/recalibration_report

      ref_name: ref_name
      sample_name: sample_name
      output_report_filename:
        valueFrom: "$(inputs.sample_name + '.' + inputs.ref_name + '.recal_data.csv')"

      gatk_docker: gatk_docker
      gatk_path: gatk_path
      docker_cores:
        valueFrom: $(2)
      docker_ram_in_mb:
        valueFrom: $(8000)
    out:
      - output_bqsr_report

  ApplyBQSR:
    run: ../tasks/ApplyBQSR.cwl
    scatter: subgroup
    scatterMethod: dotproduct
    in:
      input_bam: SortAndFixTags/output_bam

      ref_name: ref_name
      sample_name: sample_name
      output_bam_basename:
        valueFrom: "$(inputs.sample_name + '.' + inputs.ref_name + '.aligned.duplicates_marked.recalibrated')"
      recalibration_report: GatherBqsrReports/output_bqsr_report

      ref_fasta: ref_fasta
      subgroup: CreateSequenceGroupingTSV/sequence_grouping_with_unmapped
      compression_level:
        valueFrom: $(2)

      gatk_docker: gatk_docker
      gatk_path: gatk_path
      docker_cores:
        valueFrom: $(2)
      docker_ram_in_mb:
        valueFrom: $(8000)
    out:
      - recalibrated_bam

  GatherBamFiles:
    run: ../tasks/GatherBamFiles.cwl
    in:
      input_bams: ApplyBQSR/recalibrated_bam
      ref_name: ref_name
      sample_name: sample_name
      output_bam_basename:
        valueFrom: "$(inputs.sample_name + '.' + inputs.ref_name)"
      compression_level:
        valueFrom: $(6)

      gatk_docker: gatk_docker
      gatk_path: gatk_path
      docker_cores:
        valueFrom: $(2)
      docker_ram_in_mb:
        valueFrom: $(8000)
    out:
      - output_bam
