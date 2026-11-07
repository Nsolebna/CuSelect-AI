
# CuSelect-AI — Phase II
# Tests: tests/test_orchestrator.py
#
# PSEUDOCODE
# 1. Test an approved literature request.
# 2. Test a source-supported product-ratio request.
# 3. Test an approved structural-hypothesis request.
# 4. Reject unsupported selectivity and durability claims.
# 5. Verify bounded, genuine agent execution traces.
# 6. Verify deterministic run digests.
# 7. Reject invalid task types and corrupted evidence.

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cuselect.orchestrator as orchestrator

from cuselect.agents import ResearchTask
from cuselect.evidence_store import EvidenceIntegrityError
from cuselect.orchestrator import run_research_workflow


def run(task):
    return run_research_workflow(task, project_root=ROOT)


def test_literature_workflow():
    task = ResearchTask(
        "ORCH-01",
        "source_question",
        "What ethylene FE was reported for AgCu NW?",
    )

    result = run(task)

    assert result["decision"] == "evidence_only"
    assert len(result["citations"]) == 1
    assert result["citations"][0]["evidence_id"] == (
        "E-P005-FE-C2H4-001"
    )
    assert result["citations"][0]["doi"]
    assert result["citations"][0]["source_location"]


def test_product_ratio_workflow():
    task = ResearchTask(
        "ORCH-02",
        "source_question",
        "What ethanol-to-ethylene product ratios were reported?",
    )

    result = run(task)

    assert result["decision"] == "evidence_only"
    assert result["citations"][0]["evidence_id"] == "E-DRAFT-001"


def test_geometry_hypothesis_workflow():
    task = ResearchTask(
        "ORCH-03",
        "structure_hypothesis",
        "Investigate adjacent versus separated Ag pairs on Cu(100)",
        (
            "CU-001-100-AG2-NN",
            "CU-001-100-AG2-SEP",
        ),
    )

    result = run(task)

    assert result["decision"] == "hypothesis_only"
    assert len(result["candidate_ids"]) == 2
    assert result["citations"] == []
    assert result["scientific_modeling_approved"] is False


def test_selectivity_prediction_abstains():
    task = ResearchTask(
        "ORCH-04",
        "predict_selectivity",
        "Predict which catalyst has higher ethylene FE",
    )

    result = run(task)

    assert result["decision"] == "abstain"
    assert result["predicted_selectivity"] is False


def test_unsupported_durability_abstains():
    task = ResearchTask(
        "ORCH-05",
        "source_question",
        "What is the 100-hour durability of AgCu NW?",
    )

    result = run(task)

    assert result["decision"] == "abstain"
    assert result["citations"] == []


def test_exact_three_step_trace():
    task = ResearchTask(
        "ORCH-06",
        "source_question",
        "What ethylene FE was reported for AgCu NW?",
    )

    result = run(task)

    assert len(result["trace"]) == 3

    assert [step["agent"] for step in result["trace"]] == [
        "literature_agent",
        "design_agent",
        "scientific_critic",
    ]

    assert all(
        len(step["input_sha256"]) == 64
        and len(step["output_sha256"]) == 64
        for step in result["trace"]
    )

    assert result["external_api_called"] is False


def test_workflow_is_deterministic():
    task = ResearchTask(
        "ORCH-07",
        "source_question",
        "What ethanol FE was reported for Ag1Cu NW?",
    )

    first = run(task)
    second = run(task)

    assert first == second
    assert len(first["run_sha256"]) == 64


def test_evidence_integrity_failure_stops_workflow(monkeypatch):
    def reject_evidence(_root):
        raise EvidenceIntegrityError("Corrupted evidence")

    monkeypatch.setattr(
        orchestrator,
        "load_verified_corpus",
        reject_evidence,
    )

    task = ResearchTask(
        "ORCH-08",
        "source_question",
        "What ethylene FE was reported for AgCu NW?",
    )

    with pytest.raises(EvidenceIntegrityError):
        run(task)


# PSEUDOCODE
# 1. Reject malformed research requests.
# 2. Refuse unsupported catalyst/measurement combinations.
# 3. Fail closed when the geometry registry is corrupted.
# 4. Reject forged Scientific Critic citations.
# 5. Reject mismatched geometry approvals.
# 6. Verify the complete workflow digest.

from cuselect.geometry_store import GeometryIntegrityError
from cuselect.scientific_critic import CriticDecision


@pytest.mark.parametrize(
    "task",
    [
        ResearchTask("", "source_question", "Ethylene FE?"),
        ResearchTask("ADV-02", "source_question", "  "),
        ResearchTask("ADV-03", "invalid_type", "Test"),
        ResearchTask(
            "ADV-04", "structure_hypothesis", "Test",
            ("A", "A"),
        ),
        ResearchTask(
            "ADV-05", "structure_hypothesis", "Test",
            ("A", "B", "C"),
        ),
    ],
)
def test_invalid_requests_are_rejected(task):
    with pytest.raises(ValueError):
        run(task)


def test_wrong_catalyst_question_abstains():
    result = run(
        ResearchTask(
            "ADV-06",
            "source_question",
            "What ethylene FE was reported for Ag1Cu NW?",
        )
    )

    assert result["decision"] == "abstain"
    assert result["citations"] == []


def test_geometry_integrity_failure_stops_workflow(monkeypatch):
    def reject_geometry(_root):
        raise GeometryIntegrityError("Invalid structure")

    monkeypatch.setattr(
        orchestrator,
        "load_geometry_registry",
        reject_geometry,
    )

    task = ResearchTask(
        "ADV-07",
        "structure_hypothesis",
        "Investigate Ag pair configurations",
        ("CU-001-100-AG2-NN",),
    )

    with pytest.raises(GeometryIntegrityError):
        run(task)


def test_forged_critic_citation_is_rejected(monkeypatch):
    def forged_review(assertion, *, project_root):
        return CriticDecision(
            assertion_id=assertion.assertion_id,
            decision="evidence_only",
            reason_codes=("forged",),
            cited_ids=("E-FAKE-001",),
            canonical_response="Unsupported result",
        )

    monkeypatch.setattr(
        orchestrator,
        "review_scientific_assertion",
        forged_review,
    )

    task = ResearchTask(
        "ADV-08",
        "source_question",
        "What ethylene FE was reported for AgCu NW?",
    )

    with pytest.raises(RuntimeError):
        run(task)


def test_forged_geometry_decision_is_rejected(monkeypatch):
    def forged_review(assertion, *, project_root):
        return CriticDecision(
            assertion_id=assertion.assertion_id,
            decision="hypothesis_only",
            reason_codes=("forged",),
            candidate_ids=("CU-FAKE-001",),
        )

    monkeypatch.setattr(
        orchestrator,
        "review_scientific_assertion",
        forged_review,
    )

    task = ResearchTask(
        "ADV-09",
        "structure_hypothesis",
        "Investigate Ag arrangements",
        ("CU-001-100-AG2-NN",),
    )

    with pytest.raises(RuntimeError):
        run(task)


def test_run_digest_matches_workflow_payload():
    result = run(
        ResearchTask(
            "ADV-10",
            "source_question",
            "What ethanol FE was reported for Ag1Cu NW?",
        )
    )

    payload = {
        key: value
        for key, value in result.items()
        if key != "run_sha256"
    }

    assert orchestrator.digest(payload) == result["run_sha256"]
