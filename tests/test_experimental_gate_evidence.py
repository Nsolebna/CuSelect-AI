"""Tests for experimental evidence provenance validation."""

# PSEUDOCODE
# 1. Create temporary synthetic evidence.
# 2. Verify source integrity and gate references.
# 3. Reject tampered or mismatched evidence.
# 4. Reject unsafe paths.
# 5. Never treat synthetic evidence as a real qualification.

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_experimental_gate_evidence.py"

spec = importlib.util.spec_from_file_location(
    "gate_evidence_validator", SCRIPT
)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

EXP1, EXP2, _ = validator.EXPERIMENTS


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def example(tmp_path):
    source = tmp_path / "synthetic_observations.json"

    write_json(source, {
        "synthetic_fixture": True,
        "notice": "Software test only; no experiment performed.",
    })

    record = {
        "record_id": "SYNTHETIC-001",
        "experiment": EXP1,
        "evidence_type": "experimental",
        "source_path": source.name,
        "source_sha256": hashlib.sha256(
            source.read_bytes()
        ).hexdigest(),
        "observations": ["Synthetic observation"],
        "controls": ["Synthetic control"],
        "limitations": ["Not real scientific evidence"],
        "reviewer": "SIMULATED REVIEWER",
        "review_rationale": "Software validation only",
        "review_decision": "qualified",
        "reviewed_at": "2026-11-09T00:00:00Z",
    }

    registry = {
        "schema_version": "1.0",
        "records": [record],
    }

    review = {
        "experiment": EXP1,
        "status": "qualified",
        "reviewer": record["reviewer"],
        "evidence_reference": record["record_id"],
        "rationale": record["review_rationale"],
    }

    return source, registry, review, tmp_path


def test_valid_provenance(example):
    _, registry, review, root = example

    result = validator.verify_gate_reference(
        review, registry, root
    )

    assert result["provenance_verified"] is True
    assert (
        result["scientific_truth_independently_verified"]
        is False
    )


def test_tampered_source_rejected(example):
    source, registry, review, root = example

    source.write_text(
        '{"synthetic_fixture":true,"modified":true}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hash mismatch"):
        validator.verify_gate_reference(
            review, registry, root
        )


def test_unknown_reference_rejected(example):
    _, registry, review, root = example

    review["evidence_reference"] = "NONEXISTENT"

    with pytest.raises(ValueError, match="not found"):
        validator.verify_gate_reference(
            review, registry, root
        )


def test_wrong_experiment_rejected(example):
    _, registry, review, root = example

    review["experiment"] = EXP2

    with pytest.raises(
        ValueError, match="another experiment"
    ):
        validator.verify_gate_reference(
            review, registry, root
        )


def test_conflicting_decision_rejected(example):
    _, registry, review, root = example

    review["status"] = "failed"

    with pytest.raises(
        ValueError, match="differs from evidence"
    ):
        validator.verify_gate_reference(
            review, registry, root
        )


def test_unsafe_source_path_rejected(example):
    _, registry, review, root = example

    registry["records"][0]["source_path"] = (
        "../outside_source.json"
    )

    with pytest.raises(
        ValueError, match="Unsafe evidence source path"
    ):
        validator.verify_gate_reference(
            review, registry, root
        )
