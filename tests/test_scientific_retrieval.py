"""Tests for experimental citation-grounded retrieval."""

import pytest

from cuselect.scientific_retrieval import ScientificRetriever


def synthetic_documents():
    return [{
        "document_id": "E-SYNTHETIC-001",
        "text": (
            "Scientific claim: HOH Cu/Ag produced ethylene "
            "with 60.37% Faradaic efficiency at -1.3 V "
            "versus RHE. Flow cell with 0.1 M KHCO3."
        ),
        "metadata": {
            "evidence_id": "E-SYNTHETIC-001",
            "paper_id": "P-SYNTHETIC",
            "doi": "10.1234/synthetic",
            "source_location": "Results, Figure 4d",
            "package_version": "synthetic-test",
        },
    }]


def test_retrieves_relevant_claim_with_citation():
    retriever = ScientificRetriever(synthetic_documents())

    result = retriever.retrieve_with_abstention(
        "HOH Cu/Ag ethylene 60.37% at -1.3 V"
    )

    assert result["status"] == "evidence_retrieved"
    assert len(result["results"]) == 1

    citation = result["results"][0]["citation"]

    assert citation["evidence_id"] == "E-SYNTHETIC-001"
    assert citation["source_location"] == "Results, Figure 4d"
    assert citation["doi"] == "10.1234/synthetic"


def test_different_faradaic_efficiency_is_rejected():
    retriever = ScientificRetriever(synthetic_documents())

    result = retriever.retrieve_with_abstention(
        "HOH Cu/Ag ethylene 90% at -1.3 V"
    )

    assert result["status"] == "insufficient_evidence"
    assert result["results"] == []


def test_different_potential_is_rejected():
    retriever = ScientificRetriever(synthetic_documents())

    result = retriever.retrieve_with_abstention(
        "HOH Cu/Ag ethylene 60.37% at -2.5 V"
    )

    assert result["status"] == "insufficient_evidence"


def test_unrelated_question_abstains():
    retriever = ScientificRetriever(synthetic_documents())

    result = retriever.retrieve_with_abstention(
        "What is the capital city of Ghana?"
    )

    assert result["status"] == "insufficient_evidence"
    assert result["generated_scientific_answer"] is None


def test_missing_provenance_is_rejected():
    docs = synthetic_documents()
    del docs[0]["metadata"]["doi"]

    with pytest.raises(ValueError, match="provenance"):
        ScientificRetriever(docs)


def test_duplicate_evidence_is_rejected():
    doc = synthetic_documents()[0]

    with pytest.raises(ValueError, match="Duplicate"):
        ScientificRetriever([doc, dict(doc)])
