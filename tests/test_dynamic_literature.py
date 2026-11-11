"""Trust-boundary tests for dynamic literature retrieval."""

from cuselect.dynamic_literature import dynamic_literature_agent
from cuselect.evidence_store import load_verified_corpus
from cuselect.legacy_agents import ResearchTask


def ask(question, identifier):
    return dynamic_literature_agent(
        ResearchTask(
            task_id=identifier,
            task_type="source_question",
            question=question,
        ),
        project_root=".",
    )


def test_dynamic_agent_never_cites_untrusted_records():
    trusted_ids = {
        r["evidence_id"]
        for r in load_verified_corpus(".")
    }

    result = ask(
        "What is the ethylene Faradaic efficiency for AgCu NW?",
        "DYNAMIC-001",
    )

    assert set(result.ids) <= trusted_ids

    if result.ids:
        assert result.citation_audit_passed is True


def test_unapproved_p009_cannot_be_cited():
    result = ask(
        "What is the ethylene Faradaic efficiency for HOH Cu/Ag?",
        "DYNAMIC-002",
    )

    assert result.ids == ()
    assert result.citation_audit_passed is False


def test_unverified_numerical_claim_abstains():
    result = ask(
        "Did AgCu NW achieve 99% ethylene Faradaic efficiency?",
        "DYNAMIC-003",
    )

    assert result.ids == ()


def test_unsupported_scientific_prediction_abstains():
    result = ask(
        "Predict the best Cu catalyst for ethylene production",
        "DYNAMIC-004",
    )

    assert result.ids == ()


def test_explicit_potential_requires_stronger_validation():
    result = ask(
        "What is the ethylene FE for AgCu NW at -1.3 V vs RHE?",
        "DYNAMIC-005",
    )

    assert result.ids == ()
