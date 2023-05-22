process NO_CONTAINER {
    input:
        path x
    
    output:
        path "out"
    
    script:
        """
        echo ${x}
        """
}