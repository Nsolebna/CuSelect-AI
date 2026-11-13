"""Tests for CuSelect-AI prerequisite-aware experiment selection."""

# PSEUDOCODE
# 1. Load the experiment-selection engine.
# 2. Verify the recommended first experiment.
# 3. Verify later experiments have dependencies.
# 4. Reject missing or duplicated experiment descriptions.
# 5. Ensure no experimental validation is invented.

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/select_next_experiment.py"

spec = importlib.util.spec_from_file_location(
    "experiment_selector", SCRIPT
)
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)


def test_first_recommendation():
    result = selector.build_decision()

    assert result["recommended_next_step"] == (
        "Fabrication and stability qualification"
    )
    assert result["recommendation_type"] == (
        "prerequisite_based"
    )
    assert result["human_review_required"] is True


def test_dependencies():
    result = selector.build_decision()
    sequence = result["sequence"]

    assert len(sequence) == 3

    assert sequence[0]["dependencies"] == []
    assert len(sequence[1]["dependencies"]) == 1
    assert len(sequence[2]["dependencies"]) == 2

    assert sequence[0]["planning_status"] == (
        "ready_for_protocol_review"
    )

    assert all(
        step["planning_status"]
        == "pending_prerequisite_evidence"
        for step in sequence[1:]
    )


def test_no_experimental_validation_claimed():
    result = selector.build_decision()

    assert result["experimental_results_available"] is False
    assert result["performance_prediction_available"] is False

    assert all(
        step["experimental_validation"] == "not_assessed"
        for step in result["sequence"]
    )


@pytest.mark.parametrize(
    "change",
    ["remove", "duplicate"],
)
def test_modified_experiment_plan_rejected(
    monkeypatch, tmp_path, change
):
    original = json.loads(
        selector.SOURCE.read_text(encoding="utf-8")
    )

    altered = copy.deepcopy(original)
    experiments = altered["revision"]["controlled_experiments"]

    if change == "remove":
        experiments.pop()
    else:
        experiments[1]["name"] = experiments[0]["name"]

    source = tmp_path / "modified_revision.json"
    source.write_text(
        json.dumps(altered),
        encoding="utf-8",
    )

    monkeypatch.setattr(selector, "SOURCE", source)

    with pytest.raises(ValueError):
        selector.build_decision()
