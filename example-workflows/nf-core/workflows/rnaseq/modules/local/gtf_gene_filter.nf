process GTF_GENE_FILTER {
    tag "$fasta"

    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/python:3.9--1' :
        'quay.io/biocontainers/python:3.9--1' }"

    input:
    path fasta
    path gtf

    output:
    path "*.gtf"       , emit: gtf
    path "versions.yml", emit: versions

    when:
    task.ext.when == null || task.ext.when

    script: // filter_gtf_for_genes_in_genome.py is bundled with the pipeline, in nf-core/rnaseq/bin/
    """
    python3 $projectDir/bin/filter_gtf_for_genes_in_genome.py \\
        --gtf $gtf \\
        --fasta $fasta \\
        -o ${fasta.baseName}_genes.gtf

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version | sed 's/Python //g')
    END_VERSIONS
    """
}
