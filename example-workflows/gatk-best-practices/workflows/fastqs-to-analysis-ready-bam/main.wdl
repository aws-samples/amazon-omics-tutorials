version 1.0

import "./sub-workflows/processing-for-variant-discovery-gatk4.wdl" as preprocess
import "./structs/structs.wdl" as structs

workflow FastqsToAnalysisReadyBam {
    input {
      String sample_name
      Array[FastqPair] fastq_pairs
      String ecr_registry
      String aws_region
    }

    call preprocess.PreProcessingForVariantDiscovery_GATK4 {
        input:
          sample_name = sample_name,
          fastq_pairs = fastq_pairs,
          unmapped_bam_suffix = ".bam",
          ecr_registry = ecr_registry,
          aws_region = aws_region
    }

    output {
        File duplication_metrics = PreProcessingForVariantDiscovery_GATK4.duplication_metrics
        File bqsr_report = PreProcessingForVariantDiscovery_GATK4.bqsr_report
        File analysis_ready_bam = PreProcessingForVariantDiscovery_GATK4.analysis_ready_bam
        File analysis_ready_bam_index = PreProcessingForVariantDiscovery_GATK4.analysis_ready_bam_index
        File analysis_ready_bam_md5 = PreProcessingForVariantDiscovery_GATK4.analysis_ready_bam_md5
    }
}