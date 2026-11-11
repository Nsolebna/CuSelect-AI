
# CuSelect-AI — Scientific Evidence Validation Tests
#
# PSEUDOCODE
# 1. Check valid FE measurement structure.
# 2. Reject values outside physical FE bounds.
# 3. Create a pending review queue.
# 4. Prevent automatic scientific approval.
# 5. Reject approval without a primary-source location.
# 6. Allow explicit, documented human approval.
# 7. Ensure the original evidence is unchanged.
# 8. Export only approved evidence.

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.evidence_validation import (
    validate_measurement,
    create_review_queue,
    record_review,
    get_approved_evidence,
)


def make_measurement():
    return {
        "measurement_id": "test-fe-001",
        "doi": "10.1234/example",
        "title": "CuAg electroreduction",
        "product": "ethylene",
        "measurement_type": "faradaic_efficiency",
        "value": 60.0,
        "unit": "%",
        "qualifier": "nearly",
        "exact_source_text": (
            "FE for ethylene reached nearly 60%."
        ),
        "source_type": "abstract",
        "source_provider": "OpenAlex",
        "potential_v": -0.7,
        "reference_electrode": "RHE",
        "current_density_ma_cm2": -300.0,
        "current_density_type": "total",
        "conditions_verified": False,
        "review_status": "pending_human_review",
    }


def review_kwargs():
    return {
        "decision": "approved",
        "reviewer": "Test Reviewer",
        "review_date": date.today().isoformat(),
        "source_location": "full_text:page 4, Figure 2",
        "supporting_excerpt": (
            "FE for ethylene reached nearly 60%."
        ),
        "justification": (
            "Value and product checked against the "
            "original publication."
        ),
        "human_confirmed": True,
    }


def test_valid_measurement():
    result = validate_measurement(make_measurement())

    assert result["passed_structural_checks"] is True
    assert result["scientifically_verified"] is False


def test_invalid_fe_range():
    measurement = make_measurement()
    measurement["value"] = 120.0

    result = validate_measurement(measurement)

    assert result["passed_structural_checks"] is False
    assert "invalid_fe_value" in result["errors"]


def test_queue_starts_unverified():
    queue = create_review_queue([make_measurement()])

    assert len(queue) == 1
    assert queue[0]["review_status"] == (
        "pending_human_review"
    )
    assert queue[0]["review"] is None


def test_automatic_approval_is_blocked():
    queue = create_review_queue([make_measurement()])

    kwargs = review_kwargs()
    kwargs["human_confirmed"] = False

    with pytest.raises(ValueError):
        record_review(queue[0], **kwargs)


def test_abstract_only_approval_is_blocked():
    queue = create_review_queue([make_measurement()])

    kwargs = review_kwargs()
    kwargs["source_location"] = "abstract:sentence 2"

    with pytest.raises(ValueError):
        record_review(queue[0], **kwargs)


def test_explicit_human_approval():
    original = create_review_queue(
        [make_measurement()]
    )[0]

    approved = record_review(
        original,
        **review_kwargs(),
    )

    assert approved["review_status"] == "approved"
    assert approved["review"]["human_confirmed"] is True

    # The input record must remain unchanged.
    assert original["review_status"] == (
        "pending_human_review"
    )
    assert original["review"] is None


def test_approved_export():
    queue = create_review_queue([make_measurement()])

    # Pending evidence is excluded.
    assert get_approved_evidence(queue) == []

    approved = record_review(
        queue[0],
        **review_kwargs(),
    )

    verified = get_approved_evidence([approved])

    assert len(verified) == 1
    assert verified[0]["product"] == "ethylene"
    assert verified[0]["review_status"] == "approved"


def test_rejected_measurement_is_not_exported():
    queue = create_review_queue([make_measurement()])

    rejected = record_review(
        queue[0],
        decision="rejected",
        reviewer="Test Reviewer",
        review_date=date.today().isoformat(),
        source_location="",
        supporting_excerpt="",
        justification="Insufficient supporting evidence.",
    )

    assert get_approved_evidence([rejected]) == []
