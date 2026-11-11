"""Regression tests for the live trusted multi-agent workflow."""

from cuselect.evidence_store import load_verified_corpus
from cuselect.legacy_agents import ResearchTask
from cuselect.orchestrator import run_research_workflow


def run_question(question, task_id):
    return run_research_workflow(
        ResearchTask(
            task_id=task_id,
            task_type="source_question",
            question=question,
        ),
        project_root=".",
    )


def test_existing_verified_evidence_reaches_critic():
    result = run_question(
        "What is the ethylene Faradaic efficiency for AgCu NW?",
        "TRUSTED-RAG-001",
    )

    assert result["decision"] == "evidence_only"
    assert isinstance(result["response"], str)
    assert result["response"].strip()

    assert len(result["citations"]) == 1
    assert (
        result["citations"][0]["evidence_id"]
        == "E-P005-FE-C2H4-001"
    )


def test_unapproved_p009_is_not_trusted():
    records = load_verified_corpus(".")

    assert records
    assert all(
        record["paper_id"] != "P009"
        for record in records
    )


def test_unapproved_p009_question_does_not_gain_evidence():
    result = run_question(
        "What is the ethylene Faradaic efficiency of HOH Cu/Ag?",
        "TRUSTED-RAG-002",
    )

    assert result["decision"] == "abstain"
    assert result["citations"] == []
