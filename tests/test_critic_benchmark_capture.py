"""Tests for offline Scientific Critic benchmark capture."""

# PSEUDOCODE
# 1. Run the capture pipeline with a mock client.
# 2. Verify four independent response records.
# 3. Validate every structured response against ScientificCritique.
# 4. Check that source-question fingerprints are preserved.
# 5. Reject non-mock clients.
# 6. Never treat synthetic capture as scientific evaluation.

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
from prepare_critic_benchmark_requests import prepare_requests
from evaluate_scientific_reasoning import (
    DEFAULT_PACKETS,
    evaluate,
    load_json,
)
from cuselect.agents.llm_critic_agent import ScientificCritique


@pytest.fixture
def captured():
    client = MockClient()
    result = capture_offline(client)
    return client, result


def test_four_responses_captured(captured):
    client, result = captured

    assert len(result["responses"]) == 4
    assert set(client.responses.calls) == {
        "B01", "B02", "B03", "B06"
    }
    assert result["actual_api_calls"] == 0


def test_responses_satisfy_critic_schema(captured):
    _, result = captured

    for item in result["responses"]:
        data = json.loads(item["response_text"])
        critique = ScientificCritique.model_validate(data)

        assert len(critique.scientific_findings) >= 5
        assert len(critique.competing_mechanistic_explanations) >= 2
        assert len(critique.critical_experiments) >= 2


def test_input_fingerprints_preserved(captured):
    _, result = captured

    expected = {
        item["id"]: item
        for item in prepare_requests()
    }

    for item in result["responses"]:
        original = expected[item["id"]]

        assert item["input_sha256"] == original["input_sha256"]
        assert item["request_sha256"] == original["request_sha256"]
        assert (
            item["instruction_sha256"]
            == original["instruction_sha256"]
        )


def test_non_mock_client_rejected():
    class UnapprovedClient:
        pass

    with pytest.raises(TypeError, match="MockClient"):
        capture_offline(UnapprovedClient())


def test_synthetic_results_not_scored(captured):
    _, result = captured

    assert result["source_type"] == "synthetic_test_fixture"
    assert result["model"] == "MOCK-NO-API"

    report = evaluate(
        load_json(DEFAULT_PACKETS),
        result,
    )

    assert report["capture_validation_passed"] is True
    assert report["responses_captured"] == 4
    assert report["scientific_accuracy_established"] is False

    assert all(
        item["scientific_review"] == "not_evaluated"
        for item in report["results"]
    )
