"""Regression tests for benchmark execution reservations."""

# PSEUDOCODE
# 1. Create a fresh ledger in a temporary directory.
# 2. Verify initialization and manifest consistency.
# 3. Reserve one scientific benchmark request.
# 4. Reject duplicate reservations.
# 5. Preserve reservations after simulated interruption.
# 6. Reject unknown requests and changed execution plans.

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

from benchmark_execution_ledger import (
    initialize_ledger,
    reserve_request,
    verify_ledger,
)
from plan_live_critic_benchmark import build_plan


@pytest.fixture
def ledger(tmp_path):
    plan = build_plan()
    root = tmp_path / "benchmark_run"

    initialize_ledger(root, plan)

    return root, plan


def test_manifest_initialized(ledger):
    root, plan = ledger

    manifest = root / "manifest.json"

    assert manifest.is_file()
    assert json.loads(
        manifest.read_text(encoding="utf-8")
    ) == plan


def test_reinitialization_preserves_manifest(ledger):
    root, plan = ledger

    before = (
        root / "manifest.json"
    ).read_bytes()

    initialize_ledger(root, plan)

    after = (
        root / "manifest.json"
    ).read_bytes()

    assert before == after


def test_single_reservation_created(ledger):
    root, plan = ledger

    result = reserve_request(root, "B01", plan)

    assert result["case_id"] == "B01"
    assert result["api_submission_confirmed"] is False
    assert result["automatic_retry_allowed"] is False

    assert (
        root / "reservations/B01.json"
    ).is_file()


def test_duplicate_reservation_rejected(ledger):
    root, plan = ledger

    reserve_request(root, "B01", plan)

    with pytest.raises(
        ValueError,
        match="Duplicate reservation blocked",
    ):
        reserve_request(root, "B01", plan)


def test_interrupted_reservation_remains_blocked(ledger):
    root, plan = ledger

    reserve_request(root, "B02", plan)

    # Simulate restarting the program.
    initialize_ledger(root, plan)

    saved = json.loads(
        (root / "reservations/B02.json").read_text(
            encoding="utf-8"
        )
    )

    assert saved["state"] == (
        "reserved_not_confirmed_submitted"
    )
    assert saved["automatic_retry_allowed"] is False

    with pytest.raises(
        ValueError,
        match="Duplicate reservation blocked",
    ):
        reserve_request(root, "B02", plan)


def test_unknown_case_rejected(ledger):
    root, plan = ledger

    with pytest.raises(
        ValueError,
        match="Unknown benchmark case",
    ):
        reserve_request(root, "B99", plan)


def test_changed_plan_rejected(ledger):
    root, plan = ledger

    modified = copy.deepcopy(plan)
    modified["plan_sha256"] = "0" * 64

    with pytest.raises(
        ValueError,
        match="Execution plan changed",
    ):
        verify_ledger(root, modified)
