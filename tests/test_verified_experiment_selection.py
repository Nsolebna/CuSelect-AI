"""Fail-closed tests for verified experiment selection."""

# PSEUDOCODE
# 1. Create temporary gate-review records.
# 2. Verify pending gates need no experimental evidence.
# 3. Reject missing evidence registries.
# 4. Reject unknown evidence references.
# 5. Reject synthetic records as operational evidence.

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
    "verified_selector_tests",
    SCRIPTS / "select_verified_experiment.py",
)
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)

EXP1 = "Fabrication and stability qualification"


def write_json(path, value):
    path.write_text(
        json.dumps(value),
        encoding="utf-8",
    )


def gate_review():
    return {
        "experiment": EXP1,
        "status": "qualified",
        "reviewer": "SIMULATED REVIEWER",
        "evidence_reference": "TEST-EVIDENCE-001",
        "rationale": "Software test only",
    }


def test_pending_defaults_need_no_registry():
    result = selector.select_verified()

    assert result["recommendation"]["experiment"] == EXP1
    assert result["evidence_verification"] == (
        "no_qualification_claims"
    )


def test_missing_registry_rejected(tmp_path):
    gates = tmp_path / "gates.json"

    write_json(gates, {
        "schema_version": "1.0",
        "reviews": [gate_review()],
    })

    with pytest.raises(
        ValueError,
        match="Evidence registry required",
    ):
        selector.select_verified(
            gates_path=gates,
            registry_path=tmp_path / "missing_registry.json",
        )


def test_unknown_evidence_reference_rejected(tmp_path):
    gates = tmp_path / "gates.json"
    registry = tmp_path / "registry.json"

    write_json(gates, {
        "schema_version": "1.0",
        "reviews": [gate_review()],
    })

    write_json(registry, {
        "schema_version": "1.0",
        "records": [],
    })

    with pytest.raises(
        ValueError,
        match="Evidence reference not found",
    ):
        selector.select_verified(
            gates_path=gates,
            registry_path=registry,
            evidence_root=tmp_path,
        )


def test_synthetic_evidence_rejected(tmp_path):
    import hashlib

    source = tmp_path / "synthetic.json"

    write_json(source, {
        "synthetic_fixture": True,
        "notice": "Not real experimental evidence",
    })

    record = {
        "record_id": "TEST-EVIDENCE-001",
        "experiment": EXP1,
        "evidence_type": "experimental",
        "source_path": source.name,
        "source_sha256": hashlib.sha256(
            source.read_bytes()
        ).hexdigest(),
        "observations": ["Simulated observation"],
        "controls": ["Simulated control"],
        "limitations": ["Synthetic fixture"],
        "reviewer": "SIMULATED REVIEWER",
        "review_rationale": "Software test only",
        "review_decision": "qualified",
        "reviewed_at": "2026-11-09T00:00:00Z",
        "synthetic_fixture": True,
    }

    gates = tmp_path / "gates.json"
    registry = tmp_path / "registry.json"

    write_json(gates, {
        "schema_version": "1.0",
        "reviews": [gate_review()],
    })

    write_json(registry, {
        "schema_version": "1.0",
        "records": [record],
    })

    with pytest.raises(
        ValueError,
        match="not admitted",
    ):
        selector.select_verified(
            gates_path=gates,
            registry_path=registry,
            evidence_root=tmp_path,
        )
