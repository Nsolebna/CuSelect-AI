"""Regression tests for saved Scientific Critic response integrity."""

# PSEUDOCODE
# 1. Generate synthetic structured Critic responses.
# 2. Verify the original records against the benchmark plan.
# 3. Reject modified response content.
# 4. Reject incorrect request fingerprints.
# 5. Reject invalid ScientificCritique structures.
# 6. Reject mock responses mislabeled as real model outputs.
# 7. Require a provider ID for declared live responses.

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

for folder in ("src", "scripts"):
    location = str(ROOT / folder)
    if location not in sys.path:
        sys.path.insert(0, location)

from capture_critic_benchmark_offline import (
    MockClient,
    capture_offline,
)
from plan_live_critic_benchmark import build_plan
from verify_saved_benchmark_response import (
    make_record,
    sha256_text,
    verify_saved_response,
)


@pytest.fixture(scope="module")
def example():
    plan = build_plan()
    capture = capture_offline(MockClient())

    records = [
        make_record(
            case_id=item["id"],
            response_text=item["response_text"],
            model="MOCK-NO-API",
            source_type="synthetic_test_fixture",
            plan=plan,
        )
        for item in capture["responses"]
    ]

    return plan, records


def test_all_four_mock_records_verify(example):
    plan, records = example

    assert len(records) == 4

    for record in records:
        result = verify_saved_response(record, plan)

        assert result["record_integrity_verified"] is True
        assert result["structured_schema_valid"] is True
        assert result["scientific_review"] == "not_evaluated"
        assert result["scientific_accuracy_established"] is False


def test_modified_response_rejected(example):
    plan, records = example
    record = copy.deepcopy(records[0])

    record["response_text"] += " UNAUTHORIZED CHANGE"

    with pytest.raises(
        ValueError,
        match="Response fingerprint mismatch",
    ):
        verify_saved_response(record, plan)


def test_wrong_request_fingerprint_rejected(example):
    plan, records = example
    record = copy.deepcopy(records[0])

    record["request_sha256"] = "0" * 64

    with pytest.raises(
        ValueError,
        match="request_sha256 mismatch",
    ):
        verify_saved_response(record, plan)


def test_invalid_structured_critique_rejected(example):
    plan, records = example
    record = copy.deepcopy(records[0])

    content = json.loads(record["response_text"])

    # Remove a required field and recalculate the hash.
    # A correct hash must not bypass schema validation.
    del content["recommended_disposition"]

    record["response_text"] = json.dumps(content)
    record["response_sha256"] = sha256_text(
        record["response_text"]
    )

    with pytest.raises(
        ValueError,
        match="Invalid structured ScientificCritique",
    ):
        verify_saved_response(record, plan)


def test_mock_response_cannot_be_relabeled_as_live(example):
    plan, records = example
    record = copy.deepcopy(records[0])

    record["source_type"] = "captured_model_response"
    record["provider_response_id"] = "SYNTHETIC-FAKE-ID"

    with pytest.raises(
        ValueError,
        match="Mock model cannot be declared",
    ):
        verify_saved_response(record, plan)


def test_declared_live_response_requires_provider_id(example):
    plan, records = example
    record = copy.deepcopy(records[0])

    # This is only a test of metadata validation.
    # Changing the model string does not prove API origin.
    record["source_type"] = "captured_model_response"
    record["model"] = "SYNTHETIC-TEST-MODEL"
    record["provider_response_id"] = None

    with pytest.raises(
        ValueError,
        match="requires a provider response identifier",
    ):
        verify_saved_response(record, plan)
