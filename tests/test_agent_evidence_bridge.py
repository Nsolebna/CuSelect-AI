"""Experimental agent evidence integration tests."""

from cuselect.agent_evidence_bridge import (
    build_literature_agent_input,
    build_critic_agent_input,
)
from cuselect.scientific_retrieval import ScientificRetriever


def make_retriever():
    return ScientificRetriever([{
        "document_id": "E-SYNTHETIC-001",
        "text": (
            "Synthetic HOH Cu/Ag produced ethylene "
            "with 60.37% Faradaic efficiency at -1.3 V "
            "versus RHE."
        ),
        "metadata": {
            "evidence_id": "E-SYNTHETIC-001",
            "paper_id": "P-SYNTHETIC",
            "doi": "10.1234/synthetic",
            "source_location": "Synthetic Results, Figure 4d",
            "package_version": "synthetic-only",
        },
    }])


def test_literature_agent_receives_cited_evidence():
    result = build_literature_agent_input(
        make_retriever(),
        "HOH Cu/Ag ethylene 60.37% at -1.3 V",
    )

    assert result["agent"] == "literature"
    assert result["status"] == "evidence_available"
    assert len(result["citations"]) == 1
    assert "10.1234/synthetic" in result["evidence_context"]
    assert result["evidence_trust_level"] == "experimental"


def test_critic_agent_rejects_unsupported_number():
    result = build_critic_agent_input(
        make_retriever(),
        "HOH Cu/Ag ethylene 95% at -1.3 V",
    )

    assert result["agent"] == "critic"
    assert result["status"] == "insufficient_evidence"
    assert result["citations"] == []
    assert "evidence gap" in result["agent_instruction"]


def test_critic_agent_receives_review_instructions():
    result = build_critic_agent_input(
        make_retriever(),
        "HOH Cu/Ag ethylene 60.37% at -1.3 V",
    )

    assert result["status"] == "evidence_available"
    assert "operating conditions" in result["critic_instruction"]
    assert result["evidence_trust_level"] == "experimental"
