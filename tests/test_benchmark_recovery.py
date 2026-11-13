"""Regression tests for CuSelect-AI benchmark recovery inspection."""

# PSEUDOCODE
# 1. Create a temporary execution ledger.
# 2. Check the status of unreserved requests.
# 3. Simulate an interrupted request.
# 4. Reject corrupted and unexpected reservation records.
# 5. Detect a benchmark plan mismatch.
# 6. Never execute or retry model requests.

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
)
from inspect_benchmark_recovery import inspect_recovery
from plan_live_critic_benchmark import build_plan


@pytest.fixture
def recovery_run(tmp_path):
    plan = build_plan()
    root = tmp_path / "benchmark_run"

    initialize_ledger(root, plan)

    return root, plan


def test_all_cases_initially_unreserved(recovery_run):
    root, plan = recovery_run

    report = inspect_recovery(root, plan)

    assert report["not_reserved"] == 4
    assert report["uncertain"] == 0
    assert report["invalid_records"] == 0
    assert report["automatic_retries_permitted"] == 0


def test_interrupted_request_requires_review(recovery_run):
    root, plan = recovery_run

    reserve_request(root, "B01", plan)

    report = inspect_recovery(root, plan)

    assert report["not_reserved"] == 3
    assert report["uncertain"] == 1

    b01 = next(
        item for item in report["cases"]
        if item["id"] == "B01"
    )

    assert b01["state"] == "reserved_outcome_unknown"
    assert b01["requires_manual_review"] is True
    assert b01["automatically_retryable"] is False


def test_corrupted_reservation_flagged(recovery_run):
    root, plan = recovery_run

    reserve_request(root, "B02", plan)

    path = root / "reservations/B02.json"

    record = json.loads(path.read_text(encoding="utf-8"))
    record["request_sha256"] = "0" * 64

    path.write_text(
        json.dumps(record),
        encoding="utf-8",
    )

    report = inspect_recovery(root, plan)

    assert report["invalid_records"] == 1

    b02 = next(
        item for item in report["cases"]
        if item["id"] == "B02"
    )

    assert b02["state"] == "invalid_record"
    assert b02["requires_manual_review"]
    assert not b02["automatically_retryable"]


def test_unexpected_reservation_file_rejected(recovery_run):
    root, plan = recovery_run

    unexpected = root / "reservations/UNKNOWN.json"
    unexpected.write_text(
        '{"unexpected": true}',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Unexpected reservation files",
    ):
        inspect_recovery(root, plan)


def test_changed_plan_rejected(recovery_run):
    root, plan = recovery_run

    changed = copy.deepcopy(plan)
    changed["plan_sha256"] = "0" * 64

    with pytest.raises(
        ValueError,
        match="Execution plan changed",
    ):
        inspect_recovery(root, changed)
