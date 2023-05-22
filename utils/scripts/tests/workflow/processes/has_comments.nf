process HAS_COMMENTS {
    // line comment above container directive
    container "foo:fizz"
    cpus 1 // inline comment

    /*  BLOCK COMMENT
        above the input stanza
     */
    input:
        val x
    
    output:
        val "output"
    
    script:
        """
        echo ${x}
        """
}