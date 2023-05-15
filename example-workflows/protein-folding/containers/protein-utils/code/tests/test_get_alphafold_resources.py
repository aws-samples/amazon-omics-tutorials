from putils import get_alphafold_resources
import pytest

def test_basic():
    assert 1 == 1

def test_filter_fasta_monomer():
    fasta = 'tests/data/3d06.fasta'
    seq = get_alphafold_resources.filter_fasta(fasta, 1)
    assert len(seq) == 1
    assert seq[0].id == "3D06_1|Chain"

def test_filter_fasta_multimer():
    fasta = 'tests/data/4zqk.fasta'
    seq = get_alphafold_resources.filter_fasta(fasta, 2)
    assert len(seq) == 2
    assert seq[0].id == "4ZQK_1|Chain"
    assert seq[1].id == "4ZQK_2|Chain"

    seq = get_alphafold_resources.filter_fasta(fasta, 1)
    assert len(seq) == 1
    assert seq[0].id == "4ZQK_1|Chain"

def test_get_monomer_sequence_metrics():
    fasta = 'tests/data/3d06.fasta'
    filtered_fasta = get_alphafold_resources.filter_fasta(fasta)
    assert get_alphafold_resources.get_sequence_metrics(filtered_fasta) == ('3D06', 200,1)

def test_get_multimer_sequence_metrics():
    fasta = 'tests/data/4zqk.fasta'
    filtered_fasta = get_alphafold_resources.filter_fasta(fasta, 2)
    assert get_alphafold_resources.get_sequence_metrics(filtered_fasta) == ('4ZQK', 233,2)

def test_get_alphafold_resources():
    fasta = 'tests/data/3d06.fasta'
    results = get_alphafold_resources.get_alphafold_resources(fasta)
    assert results['id'] == '3D06'
    assert results['seq_length'] == "200"
    assert results['seq_count'] == "1"
    
    assert results['template_cpu'] == "2"
    assert results['template_memory'] == "4 GiB"

    assert results['feature_cpu'] == "2"
    assert results['feature_memory'] == "4 GiB"

    assert results['predict_cpu'] == "8"
    assert results['predict_memory'] == "32 GiB"

    assert results['uniref90_cpu'] == "8"
    assert results['uniref90_memory'] == "16 GiB"

    assert results['mgnify_cpu'] == "8"
    assert results['mgnify_memory'] == "16 GiB"

    assert results['bfd_cpu'] == "16"
    assert results['bfd_memory'] == "32 GiB"
