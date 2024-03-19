process INDEX {
    container '111111111111.dkr.ecr.us-east-1.amazonaws.com/rnaseq-nf:1.1.1'

    input:
    path transcriptome

    output:
    path 'index'

    script:
    """
    echo "Running salmon index"
    salmon index --threads $task.cpus -t $transcriptome -i index
    echo "Command done"
    ls -lR && sleep 60
    """
}