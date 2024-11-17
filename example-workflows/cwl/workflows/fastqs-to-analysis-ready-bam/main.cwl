cwlVersion: v1.2
class: Workflow
requirements:
- class: SubworkflowFeatureRequirement
- class: ScatterFeatureRequirement
- class: StepInputExpressionRequirement
- class: InlineJavascriptRequirement
inputs:
  sample_name: string
  fastq_pairs: 
    type:
      type: array
      items: 
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

  ecr_registry: string
  gatk_repo: string
  gotc_repo: string
  python_repo: string
  ref_name: string
  ref_fasta: File
  dbSNP_vcf: File
  known_indels_sites_VCFs: File[]


outputs:
  duplication_metrics:
    type: File[]
    outputSource: PreProcessingForVariantDiscovery_GATK4/duplication_metrics
  bqsr_report:
    type: File[]
    outputSource: PreProcessingForVariantDiscovery_GATK4/bqsr_report
  analysis_ready_bam:
    type: File[]
    outputSource: PreProcessingForVariantDiscovery_GATK4/analysis_ready_bam
    secondaryFiles:
       - pattern: "^.bai"
       - pattern: ".md5"

steps:
  PreProcessingForVariantDiscovery_GATK4:
    run: subworkflows/PreProcessingForVariantDiscovery_GATK4.cwl
    scatter: fastq_pair
    scatterMethod: dotproduct
    in:
      
      fastq_pair: fastq_pairs
      sample_name: sample_name

      ref_name: ref_name
      ref_fasta: ref_fasta
      dbSNP_vcf: dbSNP_vcf
      known_indels_sites_VCFs: known_indels_sites_VCFs


      # Construct the docker repositories
      ecr_registry: ecr_registry
      gatk_repo: gatk_repo
      gotc_repo: gotc_repo
      python_repo: python_repo

      gatk_docker: 
        valueFrom: "$(inputs.ecr_registry + inputs.gatk_repo)"
      gotc_docker: 
        valueFrom: "$(inputs.ecr_registry + inputs.gotc_repo)"
      python_docker: 
        valueFrom: "$(inputs.ecr_registry + inputs.python_repo)"
      
      # Relevant binaries/commands
      bwa_commandline: 
        valueFrom: "$('bwa mem -K 100000000 -v 3 -t 14')"
      gatk_path: 
        valueFrom: "/gatk/gatk"
      gotc_path:
        valueFrom: "/usr/gitc/"
    out:
      - duplication_metrics
      - bqsr_report
      - analysis_ready_bam
