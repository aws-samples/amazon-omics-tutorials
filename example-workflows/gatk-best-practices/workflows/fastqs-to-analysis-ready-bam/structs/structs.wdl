version 1.0

struct FastqPair {
    String read_group
    # e.g. illumina or solid
    String platform
    File fastq_1
    File fastq_2
}