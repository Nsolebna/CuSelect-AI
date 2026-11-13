"""Offline tests for the CuSelect-AI replay orchestrator."""

# PSEUDOCODE
# 1. Import the existing replay orchestrator.
# 2. Validate the complete saved research workflow.
# 3. Tamper with temporary copies of input files.
# 4. Verify inconsistent sources and candidates are rejected.
# 5. Never call an LLM or change original research records.

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_research_orchestrator.py"

spec = importlib.util.spec_from_file_location(
    "cuselect_replay_orchestrator", SCRIPT
)
orchestrator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orchestrator)


def replace_input(monkeypatch, tmp_path, name, change):
    """Redirect one source to a modified temporary JSON file."""

    original = orchestrator.FILES[name]
    record = json.loads(original.read_text(encoding="utf-8"))

    change(record)

    replacement = tmp_path / f"{name}.json"
    replacement.write_text(
        json.dumps(record, indent=2),
        encoding="utf-8",
    )

    updated = dict(orchestrator.FILES)
    updated[name] = replacement
    monkeypatch.setattr(orchestrator, "FILES", updated)


def test_valid_research_cycle():
    record = orchestrator.build_replay()

    assert record["run_mode"] == "replay"
    assert len(record["workflow"]) == 5

    assert record["outcomes"]["scientific_findings"] == 6
    assert record["outcomes"]["findings_addressed"] == 6

    assert (
        record["outcomes"]["proposed_controlled_experiments"]
        == 3
    )

    assert record["scientific_status"] == (
        "pending_human_review"
    )

    assert record["execution_policy"][
        "llm_calls_allowed"
    ] is False


def test_modified_literature_rejected(monkeypatch, tmp_path):
    def change(record):
        record["summary"] = "Tampered scientific summary."

    replace_input(
        monkeypatch,
        tmp_path,
        "literature",
        change,
    )

    with pytest.raises(
        ValueError,
        match="Critic source mismatch: literature",
    ):
        orchestrator.build_replay()


def test_candidate_mismatch_rejected(monkeypatch, tmp_path):
    def change(record):
        record["proposal"]["candidate_name"] = (
            "Unrelated catalyst candidate"
        )

    replace_input(
        monkeypatch,
        tmp_path,
        "design",
        change,
    )

    with pytest.raises(
        ValueError,
        match="candidate mismatch",
    ):
        orchestrator.build_replay()


def test_missing_source_rejected(monkeypatch, tmp_path):
    updated = dict(orchestrator.FILES)

    updated["computational_context"] = (
        tmp_path / "missing_context.json"
    )

    monkeypatch.setattr(
        orchestrator,
        "FILES",
        updated,
    )

    with pytest.raises(
        ValueError,
        match="Missing computational_context",
    ):
        orchestrator.build_replay()
