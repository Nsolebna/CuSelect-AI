# CuSelect-AI — Research Watcher Reporting Tests
#
# PSEUDOCODE
# 1. Validate unique research scan identifiers.
# 2. Reject unsafe report identifiers.
# 3. Save readable scientific digests.
# 4. Prevent report overwrites.
# 5. Record successful and failed scans.
# 6. Append multiple scan events without losing records.
# 7. Reject invalid log metadata.
# 8. Keep tests isolated from real research data.

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.watcher_reporting import (
    WatcherReportingError,
    new_run_id,
    validate_run_id,
    save_digest,
    append_scan_event,
)


@pytest.fixture
def sample_digest():
    return {
        "retrieved_count": 2,
        "previously_seen_count": 1,
        "newly_seen_count": 1,
        "history_saved": False,
        "new_papers": [
            {
                "title": "Example Cu-Ag CO2RR paper",
                "doi": "10.1234/example-paper",
                "year": 2026,
                "screening_status": "high_priority",
                "scientific_status": "unverified_discovery",
            }
        ],
    }


def test_run_ids_are_unique_and_valid():
    first = new_run_id()
    second = new_run_id()

    assert first != second
    assert validate_run_id(first) == first
    assert re.fullmatch(
        r"[A-Za-z0-9_-]{8,80}",
        first,
    )


@pytest.mark.parametrize(
    "invalid_id",
    [
        "",
        "../unsafe",
        "contains spaces",
        "x" * 81,
        None,
    ],
)
def test_invalid_run_ids_are_rejected(invalid_id):
    with pytest.raises(WatcherReportingError):
        validate_run_id(invalid_id)


def test_digest_is_saved_with_unverified_label(
    tmp_path, sample_digest
):
    run_id = new_run_id()

    path = save_digest(
        tmp_path / "reports",
        run_id,
        sample_digest,
    )

    content = path.read_text(encoding="utf-8")

    assert path.name == f"{run_id}.txt"
    assert "SCIENTIFIC RESEARCH DIGEST" in content
    assert "Example Cu-Ag CO2RR paper" in content
    assert "Evidence status: UNVERIFIED" in content
    assert "History saved: NO" in content


def test_existing_digest_cannot_be_overwritten(
    tmp_path, sample_digest
):
    run_id = new_run_id()

    first_path = save_digest(
        tmp_path,
        run_id,
        sample_digest,
    )

    original = first_path.read_bytes()

    with pytest.raises(FileExistsError):
        save_digest(
            tmp_path,
            run_id,
            sample_digest,
        )

    assert first_path.read_bytes() == original


def test_invalid_digest_type_is_rejected(tmp_path):
    with pytest.raises(WatcherReportingError):
        save_digest(
            tmp_path,
            new_run_id(),
            "not a dictionary",
        )


def test_success_event_is_recorded(tmp_path):
    path = tmp_path / "scan_log.jsonl"
    run_id = new_run_id()

    event = append_scan_event(
        path,
        run_id=run_id,
        status="success",
        mode="save",
        retrieved_count=30,
        newly_seen_count=2,
    )

    records = [
        json.loads(line)
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
    ]

    assert len(records) == 1
    assert records[0] == event
    assert event["run_id"] == run_id
    assert event["status"] == "success"
    assert event["mode"] == "save"
    assert event["newly_seen_count"] == 2
    assert event["timestamp_utc"]


def test_failure_event_is_recorded(tmp_path):
    path = tmp_path / "scan_log.jsonl"

    event = append_scan_event(
        path,
        run_id=new_run_id(),
        status="failure",
        mode="save",
        error="Simulated Crossref outage",
    )

    assert event["status"] == "failure"
    assert event["retrieved_count"] == 0
    assert event["error"] == "Simulated Crossref outage"


def test_multiple_events_are_appended(tmp_path):
    path = tmp_path / "scan_log.jsonl"

    for _ in range(3):
        append_scan_event(
            path,
            run_id=new_run_id(),
            status="success",
            mode="preview",
            retrieved_count=10,
        )

    records = [
        json.loads(line)
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
    ]

    assert len(records) == 3
    assert all(
        record["mode"] == "preview"
        for record in records
    )


@pytest.mark.parametrize(
    "status, mode",
    [
        ("approved", "save"),
        ("success", "automatic"),
    ],
)
def test_invalid_status_or_mode_is_rejected(
    tmp_path, status, mode
):
    with pytest.raises(WatcherReportingError):
        append_scan_event(
            tmp_path / "events.jsonl",
            run_id=new_run_id(),
            status=status,
            mode=mode,
        )


@pytest.mark.parametrize(
    "retrieved, newly_seen",
    [
        (True, 0),
        (0, -1),
        (1, 2),
    ],
)
def test_invalid_counts_are_rejected(
    tmp_path, retrieved, newly_seen
):
    with pytest.raises(WatcherReportingError):
        append_scan_event(
            tmp_path / "events.jsonl",
            run_id=new_run_id(),
            status="success",
            mode="preview",
            retrieved_count=retrieved,
            newly_seen_count=newly_seen,
        )


def test_error_message_must_be_text(tmp_path):
    with pytest.raises(WatcherReportingError):
        append_scan_event(
            tmp_path / "events.jsonl",
            run_id=new_run_id(),
            status="failure",
            mode="save",
            error=123,
        )
