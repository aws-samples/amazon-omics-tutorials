include { HAPPY } from "./processes/happy.nf"
include { NO_CONTAINER } from "./processes/no_container.nf"
include { FOO, BAR } from "./processes/multiple.nf"

workflow MAIN {
    HAPPY()
    NO_CONTAINER()
    FOO()
    BAR()
}

workflow {
    MAIN()
}