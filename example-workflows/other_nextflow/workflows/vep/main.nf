nextflow.enable.dsl = 2

include { ENSEMBLVEP  } from './modules/ensemblvep/main'

vep_cache_version  = params.vep_cache_version  ?: Channel.empty()
vep_genome         = params.vep_genome         ?: Channel.empty()
vep_species        = params.vep_species        ?: Channel.empty()

// Initialize files channels based on params, not defined within the params.genomes[params.genome] scope
vep_cache          = params.vep_cache          ? Channel.fromPath(params.vep_cache).collect()                : []

vep_fasta = (params.vep_include_fasta) ? fasta : []

vep_extra_files = []


workflow {
    ENSEMBLVEP( [[ id: params.id], file(params.vcf, checkIfExists:true) ], vep_genome, vep_species, vep_cache_version, vep_cache, vep_fasta, vep_extra_files)
}