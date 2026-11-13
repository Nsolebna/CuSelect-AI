"""Regression tests for adaptive research decision gates."""

# PSEUDOCODE
# 1. Start from the saved scientific experiment plan.
# 2. Simulate different human review decisions.
# 3. Check that prerequisites control progression.
# 4. Reject incomplete or contradictory reviews.
# 5. Never modify actual scientific evidence.

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location(
    "adaptive_selector_tests",
    SCRIPTS / "adaptive_experiment_selector.py",
)
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)

EXP1, EXP2, EXP3 = selector.EXPECTED


def review(experiment, status):
    return {
        "experiment": experiment,
        "status": status,
        "reviewer": "SIMULATED REVIEWER",
        "evidence_reference": "SIMULATED-ONLY",
        "rationale": "Software test, not experimental evidence.",
    }


def gates_file(tmp_path, reviews):
    path = tmp_path / "simulated_reviews.json"
    path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "reviews": reviews,
        }),
        encoding="utf-8",
    )
    return path


def test_default_recommends_fabrication(monkeypatch, tmp_path):
    monkeypatch.setattr(
        selector,
        "DEFAULT_GATES",
        tmp_path / "nonexistent_default.json",
    )

    result = selector.select_next()

    assert result["recommendation"]["experiment"] == EXP1
    assert result["recommendation"]["action"] == (
        "ready_for_protocol_review"
    )


def test_qualified_fabrication_unlocks_electrolysis(tmp_path):
    path = gates_file(
        tmp_path,
        [review(EXP1, "qualified")],
    )

    result = selector.select_next(path)

    assert result["recommendation"]["experiment"] == EXP2
    assert result["sequence"][1]["action"] == (
        "ready_for_protocol_review"
    )
    assert result["sequence"][2]["action"] == (
        "blocked_by_prerequisites"
    )


def test_all_qualified_ends_sequence(tmp_path):
    path = gates_file(
        tmp_path,
        [
            review(EXP1, "qualified"),
            review(EXP2, "qualified"),
            review(EXP3, "qualified"),
        ],
    )

    result = selector.select_next(path)

    assert result["recommendation"]["experiment"] is None
    assert result["recommendation"]["action"] == (
        "all_qualifications_recorded"
    )


def test_failed_fabrication_requires_remediation(tmp_path):
    path = gates_file(
        tmp_path,
        [review(EXP1, "failed")],
    )

    result = selector.select_next(path)

    assert result["recommendation"]["experiment"] == EXP1
    assert result["recommendation"]["action"] == (
        "review_and_remediate"
    )
    assert result["sequence"][1]["action"] == (
        "blocked_by_prerequisites"
    )


def test_missing_reviewer_evidence_rejected(tmp_path):
    incomplete = review(EXP1, "qualified")
    incomplete.pop("evidence_reference")

    path = gates_file(tmp_path, [incomplete])

    with pytest.raises(
        ValueError,
        match="require reviewer",
    ):
        selector.select_next(path)


def test_qualification_without_prerequisites_rejected(tmp_path):
    path = gates_file(
        tmp_path,
        [review(EXP2, "qualified")],
    )

    with pytest.raises(
        ValueError,
        match="unqualified prerequisites",
    ):
        selector.select_next(path)
