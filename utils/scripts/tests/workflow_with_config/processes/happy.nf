process HAPPY {
    container "image:tag"

    input:
        path x
    
    output:
        path "out"
    
    script:
        """
        echo ${x}
        """
}