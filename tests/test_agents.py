
# CuSelect-AI — Phase II
# Tests: tests/test_agents.py
#
# PSEUDOCODE
# 1. Test the three supported literature questions.
# 2. Verify correct evidence IDs and publication counts.
# 3. Check unsupported scientific requests.
# 4. Reject incorrect catalyst/measurement combinations.
# 5. Check non-literature and invalid task types.
# 6. Ensure evidence integrity failures cannot be bypassed.

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cuselect.agents as agents
import cuselect.legacy_agents as legacy_agents
from cuselect.agents import ResearchTask, literature_agent
from cuselect.evidence_store import EvidenceIntegrityError


@pytest.mark.parametrize(
    "question,expected_id",
    [
        (
            "What ethylene FE was reported for AgCu NW?",
            "E-P005-FE-C2H4-001",
        ),
        (
            "What ethanol FE was reported for Ag1Cu NW?",
            "E-P005-FE-ETOH-001",
        ),
        (
            "What ethanol-to-ethylene product ratios were reported?",
            "E-DRAFT-001",
        ),
    ],
)
def test_supported_literature_questions(question, expected_id):
    task = ResearchTask(
        "L-TEST",
        "source_question",
        question,
    )

    result = literature_agent(task, project_root=ROOT)

    assert result.status == "matched_reviewed_observation"
    assert result.ids == (expected_id,)
    assert result.independent_publications == 1
    assert result.citation_audit_passed is True
    assert expected_id in result.answer


def test_unsupported_durability_question():
    task = ResearchTask(
        "L-04",
        "source_question",
        "What was the 100-hour durability of AgCu NW?",
    )

    result = literature_agent(task, project_root=ROOT)

    assert result.status == "unsupported_question"
    assert result.ids == ()


def test_wrong_catalyst_measurement_pair_abstains():
    task = ResearchTask(
        "L-05",
        "source_question",
        "What ethylene FE was reported for Ag1Cu NW?",
    )

    result = literature_agent(task, project_root=ROOT)

    assert result.status == "insufficient_retrieval_support"
    assert result.ids == ()


def test_non_literature_task_is_not_applicable():
    task = ResearchTask(
        "L-06",
        "structure_hypothesis",
        "Compare two Cu-Ag structures",
    )

    result = literature_agent(task, project_root=ROOT)

    assert result.status == "not_applicable"
    assert result.ids == ()


def test_unknown_task_type_is_rejected():
    task = ResearchTask(
        "L-07",
        "unknown_type",
        "Test question",
    )

    with pytest.raises(ValueError):
        literature_agent(task, project_root=ROOT)


def test_evidence_loader_failure_is_not_bypassed(monkeypatch):
    def reject_corrupted_evidence(_root):
        raise EvidenceIntegrityError("Evidence integrity failure")

    monkeypatch.setattr(
        legacy_agents,
        "load_verified_corpus",
        reject_corrupted_evidence,
    )

    task = ResearchTask(
        "L-08",
        "source_question",
        "What ethylene FE was reported for AgCu NW?",
    )

    with pytest.raises(EvidenceIntegrityError):
        literature_agent(task, project_root=ROOT)
