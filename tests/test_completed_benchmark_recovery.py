"""Tests for integrated benchmark recovery and saved responses."""

# PSEUDOCODE
# 1. Create a temporary benchmark ledger.
# 2. Generate synthetic Critic responses.
# 3. Test unreserved and interrupted request states.
# 4. Verify a correctly saved synthetic response.
# 5. Reject corrupted and orphaned responses.
# 6. Reject unexpected response files.
# 7. Never make API calls or modify actual research data.

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

for folder in ("src", "scripts"):
    location = str(ROOT / folder)
    if location not in sys.path:
        sys.path.insert(0, location)

from plan_live_critic_benchmark import build_plan
from benchmark_execution_ledger import (
    initialize_ledger,
    reserve_request,
)
from inspect_completed_benchmark_recovery import (
    inspect_completed_recovery,
)
from verify_saved_benchmark_response import make_record
from capture_critic_benchmark_offline import (
    MockClient,
    capture_offline,
)


@pytest.fixture
def example(tmp_path):
    plan = build_plan()
    root = tmp_path / "benchmark_run"

    initialize_ledger(root, plan)

    mock = capture_offline(MockClient())

    captured = {
        item["id"]: item
        for item in mock["responses"]
    }

    return root, plan, captured


def save_mock_response(root, plan, captured, case_id):
    directory = root / "responses"
    directory.mkdir(exist_ok=True)

    record = make_record(
        case_id=case_id,
        response_text=captured[case_id]["response_text"],
        model="MOCK-NO-API",
        source_type="synthetic_test_fixture",
        plan=plan,
    )

    path = directory / f"{case_id}.json"
    path.write_text(
        json.dumps(record, indent=2),
        encoding="utf-8",
    )

    return path


def get_case(report, case_id):
    return next(
        item for item in report["cases"]
        if item["id"] == case_id
    )


def test_all_cases_initially_unreserved(example):
    root, plan, _ = example

    report = inspect_completed_recovery(root, plan)

    assert report["not_reserved"] == 4
    assert report["uncertain"] == 0
    assert report["response_integrity_verified"] == 0
    assert report["invalid_records"] == 0
    assert report["automatic_retries_permitted"] == 0


def test_interrupted_request_stays_uncertain(example):
    root, plan, _ = example

    reserve_request(root, "B01", plan)

    report = inspect_completed_recovery(root, plan)
    case = get_case(report, "B01")

    assert case["state"] == "reserved_outcome_unknown"
    assert case["requires_manual_review"] is True
    assert case["automatically_retryable"] is False


def test_valid_synthetic_response_integrity(example):
    root, plan, captured = example

    reserve_request(root, "B01", plan)
    save_mock_response(root, plan, captured, "B01")

    report = inspect_completed_recovery(root, plan)
    case = get_case(report, "B01")

    assert report["response_integrity_verified"] == 1
    assert case["state"] == "response_integrity_verified"
    assert case["source_type"] == "synthetic_test_fixture"
    assert case["scientific_review"] == "not_evaluated"
    assert case["scientific_accuracy_established"] is False
    assert case["automatically_retryable"] is False


def test_corrupted_response_rejected(example):
    root, plan, captured = example

    reserve_request(root, "B02", plan)
    path = save_mock_response(
        root, plan, captured, "B02"
    )

    record = json.loads(path.read_text(encoding="utf-8"))
    record["response_sha256"] = "0" * 64

    path.write_text(
        json.dumps(record),
        encoding="utf-8",
    )

    report = inspect_completed_recovery(root, plan)
    case = get_case(report, "B02")

    assert report["invalid_records"] == 1
    assert case["state"] == "invalid_record"
    assert case["requires_manual_review"] is True
    assert case["automatically_retryable"] is False


def test_orphaned_response_rejected(example):
    root, plan, captured = example

    # B03 has no reservation.
    save_mock_response(root, plan, captured, "B03")

    report = inspect_completed_recovery(root, plan)
    case = get_case(report, "B03")

    assert case["state"] == "invalid_record"
    assert case["requires_manual_review"] is True
    assert case["automatically_retryable"] is False


def test_unexpected_response_file_rejected(example):
    root, plan, _ = example

    directory = root / "responses"
    directory.mkdir()

    (directory / "UNEXPECTED.json").write_text(
        '{"synthetic_fixture": true}',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Unexpected response files",
    ):
        inspect_completed_recovery(root, plan)
