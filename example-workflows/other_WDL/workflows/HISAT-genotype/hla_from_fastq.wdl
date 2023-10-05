version 1.1

task wes_hla {
    input {
        File reads1
        File reads2
        File index
        String locus_list
        String container
    }

    # Basing most of the estimate off ~4x Exome BAM size + some slack for memory
    runtime {
        container: container
        cpu: 18
        memory: "25 GiB"
        disks: 20
    }

    command <<<
        set -exo pipefail
        pwd
        tar -xvf ~{index}
        echo ~{basename(reads1)}
        echo ~{basename(reads2)}
        H1="_miniwdl_inputs/0/"
        R1=~{basename(reads1)}
        R2=~{basename(reads2)}
        F1="${H1}${R1}"
        F2="${H1}${R2}"
        ls -a

        hisatgenotype -p 18 \
            -1 ${F1} \
            -2 ${F2} \
            --base hla \
            --locus-list ~{locus_list} \
            --index_dir ~{basename(index, ".tar.gz")} \
            --verbose \
            --out-dir output
    >>>

    output {
        Array[File] report = glob("output/assembly_graph-hla.*.report")
    }
}

# A primary workflow declaration is needed for Amazon Omics
workflow main {
    input {
        File reads1
        File reads2
        File index
        String locus_list

        # workflow container image uris are parameterized for portability
        # they must come from ECR private repositories in the same region
        String ecr_registry
        String aws_region
    }

    call wes_hla {
        input:
	    reads1 = reads1,
	    reads2 = reads2,
	    index = index,
	    locus_list = locus_list,
        container = ecr_registry +  "/hisat-genotype:latest"
    }

    output {
        Array[File] report = wes_hla.report
    }
}
