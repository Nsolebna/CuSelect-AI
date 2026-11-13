"""Regression tests for scientific reasoning assessments."""

# PSEUDOCODE
# 1. Load the four benchmark cases.
# 2. Create synthetic responses for software tests.
# 3. Create assessment records linked to each response hash.
# 4. Check valid, incomplete, unsafe and inconsistent reviews.
# 5. Never interpret fixture results as real model performance.

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from evaluate_scientific_reasoning import (
    DEFAULT_PACKETS,
    digest,
    load_json,
)

from assess_scientific_reasoning import (
    summarize_assessments,
)


@pytest.fixture
def example():
    packets = load_json(DEFAULT_PACKETS)

    responses = {
        "schema_version": "1.0",
        "source_type": "captured_model_response",
        "responses": [],
    }

    assessments = {
        "schema_version": "1.0",
        "assessments": [],
    }

    for case in packets["cases"]:
        identifier = case["id"]

        # These are synthetic test strings, NOT
        # actual responses from a scientific LLM.
        response_text = (
            f"SYNTHETIC TEST RESPONSE {identifier}. "
            "No scientific reasoning was performed."
        )

        responses["responses"].append({
            "id": identifier,
            "input_sha256": digest(
                case["scientific_input"]
            ),
            "response_text": response_text,
        })

        assessments["assessments"].append({
            "id": identifier,
            "reviewer": "SYNTHETIC TEST REVIEWER",
            "review_rationale": (
                "Software rubric validation only."
            ),
            "response_sha256": digest(response_text),
            "required_elements": [
                {
                    "criterion": criterion,
                    "status": "met",
                }
                for criterion in case["required_elements"]
            ],
            "forbidden_conclusions": [
                {
                    "criterion": criterion,
                    "status": "absent",
                }
                for criterion in case["forbidden_conclusions"]
            ],
        })

    return packets, responses, assessments


def test_complete_rubric_records_accepted(example):
    packets, responses, assessments = example

    report = summarize_assessments(
        packets, responses, assessments
    )

    assert report["cases_assessed"] == 4
    assert report["rubric_satisfied"] == 4
    assert report["critical_failures"] == 0

    # This is a software fixture outcome, not
    # a genuine scientific accuracy result.
    assert (
        report["scientific_truth_independently_established"]
        is False
    )


def test_critical_violation_detected(example):
    packets, responses, assessments = copy.deepcopy(example)

    assessments["assessments"][0][
        "forbidden_conclusions"
    ][0]["status"] = "present"

    report = summarize_assessments(
        packets, responses, assessments
    )

    assert report["critical_failures"] == 1
    assert report["rubric_satisfied"] == 3
    assert (
        report["results"][0]["rubric_outcome"]
        == "critical_failure"
    )


def test_missing_scientific_element_detected(example):
    packets, responses, assessments = copy.deepcopy(example)

    assessments["assessments"][0][
        "required_elements"
    ][0]["status"] = "unmet"

    report = summarize_assessments(
        packets, responses, assessments
    )

    assert (
        report["results"][0]["rubric_outcome"]
        == "needs_improvement_or_review"
    )
    assert report["results"][0]["required_unmet"] == 1


def test_unclear_assessment_not_accepted_as_pass(example):
    packets, responses, assessments = copy.deepcopy(example)

    assessments["assessments"][0][
        "required_elements"
    ][0]["status"] = "unclear"

    report = summarize_assessments(
        packets, responses, assessments
    )

    assert report["results"][0]["unclear_items"] == 1
    assert report["rubric_satisfied"] == 3


def test_modified_response_hash_rejected(example):
    packets, responses, assessments = copy.deepcopy(example)

    responses["responses"][0]["response_text"] = (
        "Modified response after assessment."
    )

    with pytest.raises(
        ValueError, match="response hash mismatch"
    ):
        summarize_assessments(
            packets, responses, assessments
        )


def test_synthetic_response_source_rejected(example):
    packets, responses, assessments = copy.deepcopy(example)

    responses["source_type"] = "synthetic_test_fixture"

    with pytest.raises(
        ValueError, match="not synthetic fixtures"
    ):
        summarize_assessments(
            packets, responses, assessments
        )
