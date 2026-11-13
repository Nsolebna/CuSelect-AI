"""Offline tests for interrupted CuSelect-AI research runs."""

# PSEUDOCODE
# 1. Load the recovery validator.
# 2. Simulate a failed run in a temporary directory.
# 3. Verify a valid saved critique is recoverable.
# 4. Reject modified critiques, changed evidence and used budgets.
# 5. Reject recovery when a revision already exists.
# 6. Never contact an LLM or modify scientific source files.

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_research_recovery.py"

spec = importlib.util.spec_from_file_location(
    "cuselect_recovery_validator",
    SCRIPT,
)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def interrupted_run(tmp_path):
    """Simulate failure after the first LLM request."""

    run = tmp_path / "interrupted_cycle"
    run.mkdir()

    original = (
        ROOT / "data/agent_runs"
        / "llm_scientific_critique_with_dft_v3.json"
    )

    critique = load(original)

    # The controlled runner records source hashes in its
    # newly saved critique before invoking the Revision Agent.
    critique["source_sha256"] = {
        name: digest(path)
        for name, path in recovery.SOURCES.items()
    }

    critique_path = run / "scientific_critique.json"

    critique_path.write_text(
        json.dumps(critique, indent=2),
        encoding="utf-8",
    )

    failure = {
        "status": "failed",
        "failed_stage": "revision_agent",
        "llm_requests_attempted": 1,
        "saved_critique_available": True,
        "saved_critique_sha256": digest(critique_path),
        "saved_revision_available": False,
        "automatic_dft_execution": False,
    }

    (run / "failure.json").write_text(
        json.dumps(failure, indent=2),
        encoding="utf-8",
    )

    return run


def test_valid_interruption_is_recoverable(interrupted_run):
    result = recovery.check_recovery(interrupted_run)

    assert result["status"] == (
        "eligible_for_controlled_revision_resume"
    )
    assert result["existing_requests_attempted"] == 1
    assert result["remaining_request_allowance"] == 1
    assert result["human_approval_required"] is True
    assert result["automated_dft_allowed"] is False

    # Validation must not create a new revision.
    assert not (
        interrupted_run / "revised_candidate.json"
    ).exists()


def test_modified_critique_is_rejected(interrupted_run):
    path = interrupted_run / "scientific_critique.json"

    critique = load(path)
    critique["candidate_name"] = "Altered candidate"

    path.write_text(
        json.dumps(critique),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Saved scientific critique was modified",
    ):
        recovery.check_recovery(interrupted_run)


def test_used_request_budget_is_rejected(interrupted_run):
    path = interrupted_run / "failure.json"
    failure = load(path)

    failure["llm_requests_attempted"] = 2

    path.write_text(
        json.dumps(failure),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Revision request may already have been attempted",
    ):
        recovery.check_recovery(interrupted_run)


def test_existing_revision_blocks_recovery(interrupted_run):
    (interrupted_run / "revised_candidate.json").write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Existing output prevents recovery",
    ):
        recovery.check_recovery(interrupted_run)


def test_modified_source_is_rejected(
    interrupted_run, monkeypatch, tmp_path
):
    source = recovery.SOURCES["literature"]

    changed = load(source)
    changed["summary"] = "Changed after the original run."

    replacement = tmp_path / "altered_literature.json"
    replacement.write_text(
        json.dumps(changed),
        encoding="utf-8",
    )

    sources = dict(recovery.SOURCES)
    sources["literature"] = replacement

    monkeypatch.setattr(recovery, "SOURCES", sources)

    with pytest.raises(
        ValueError,
        match="Source fingerprint mismatch: literature",
    ):
        recovery.check_recovery(interrupted_run)
