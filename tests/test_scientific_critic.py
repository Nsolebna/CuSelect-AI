
# PSEUDOCODE
# 1. Accept an exact human-reviewed FE observation.
# 2. Reject an altered FE or electrode potential.
# 3. Reject rewritten scientific assertions.
# 4. Permit the reviewed product ratio without inventing FE.
# 5. Accept registered geometries as hypotheses only.
# 6. Reject performance claims, predictions and fake references.

from dataclasses import replace
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.scientific_critic import (
    ScientificAssertion,
    review_scientific_assertion,
)


@pytest.fixture
def fe_assertion():
    return ScientificAssertion(
        assertion_id="SC-001",
        kind="reported_fe",
        evidence_ids=("E-P005-FE-C2H4-001",),
        catalyst="AgCu NW",
        product="C2H4",
        fe_percent=54.9,
        potential_v_rhe=-1.1,
    )


def review(assertion):
    return review_scientific_assertion(
        assertion,
        project_root=ROOT,
    )


def test_correct_fe_is_evidence_only(fe_assertion):
    result = review(fe_assertion)

    assert result.decision == "evidence_only"
    assert result.cited_ids == fe_assertion.evidence_ids
    assert result.scientific_modeling_approved is False


def test_fabricated_fe_is_rejected(fe_assertion):
    result = review(
        replace(fe_assertion, fe_percent=99.9)
    )

    assert result.decision == "abstain"
    assert "faradaic_efficiency_mismatch" in result.reason_codes


def test_wrong_potential_is_rejected(fe_assertion):
    result = review(
        replace(fe_assertion, potential_v_rhe=-0.8)
    )

    assert result.decision == "abstain"


def test_rewritten_scientific_claim_is_rejected(fe_assertion):
    result = review(
        replace(
            fe_assertion,
            statement="This catalyst is guaranteed to be superior.",
        )
    )

    assert result.decision == "abstain"


def test_reported_ratio_is_evidence_only():
    assertion = ScientificAssertion(
        assertion_id="SC-002",
        kind="reported_ratio",
        evidence_ids=("E-DRAFT-001",),
    )

    result = review(assertion)

    assert result.decision == "evidence_only"
    assert result.cited_ids == ("E-DRAFT-001",)
    assert result.scientific_modeling_approved is False


def test_valid_geometry_is_hypothesis_only():
    assertion = ScientificAssertion(
        assertion_id="SC-003",
        kind="structure_hypothesis",
        candidate_ids=(
            "CU-001-100-AG2-NN",
            "CU-001-100-AG2-SEP",
        ),
        statement="Investigate differences in Ag arrangement.",
    )

    result = review(assertion)

    assert result.decision == "hypothesis_only"
    assert result.candidate_ids == assertion.candidate_ids
    assert result.scientific_modeling_approved is False


def test_geometry_performance_claim_is_rejected():
    assertion = ScientificAssertion(
        assertion_id="SC-004",
        kind="structure_hypothesis",
        candidate_ids=("CU-001-100-AG2-NN",),
        statement="This structure has higher FE.",
    )

    assert review(assertion).decision == "abstain"


def test_selectivity_prediction_is_rejected():
    assertion = ScientificAssertion(
        assertion_id="SC-005",
        kind="catalyst_superiority",
        statement="This catalyst will outperform the reference.",
    )

    result = review(assertion)

    assert result.decision == "abstain"
    assert result.scientific_modeling_approved is False


def test_fabricated_citation_is_rejected(fe_assertion):
    assertion = replace(
        fe_assertion,
        evidence_ids=("E-FAKE-001",),
    )

    result = review(assertion)

    assert result.decision == "abstain"
    assert result.cited_ids == ()


def test_unknown_geometry_is_rejected():
    assertion = ScientificAssertion(
        assertion_id="SC-006",
        kind="structure_hypothesis",
        candidate_ids=("CU-FAKE-001",),
    )

    assert review(assertion).decision == "abstain"
