process FOO {
    container "foo:fizz"
    input:
        val x
    
    output:
        val y

    script:
        """
        echo foo
        """
}

process BAR {
    container "bar:buzz"
    input:
        val x
    
    output:
        val y
    
    script:
        """
        echo bar
        """
}