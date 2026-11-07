# CuSelect-AI — Research Watcher CLI Reporting Integration
#
# PSEUDOCODE
# 1. Verify default preview does not write reports.
# 2. Verify recorded previews save a digest and scan log.
# 3. Verify save mode requests history persistence.
# 4. Record failed scans.
# 5. Disclose partial failures after history updates.
# 6. Handle scan-log failures without losing reports.
# 7. Handle failure-logging errors.
# 8. Test the real scan, history, and reporting integration
#    using temporary data and mocked Crossref responses.

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cuselect.watcher_cli as cli
import cuselect.watcher_scan as watcher_scan

from cuselect.research_watcher import (
    empty_history,
    observe_publications,
    save_history,
    load_history,
)


KNOWN = {
    "doi": "10.1234/known",
    "title": "Known Cu-Ag CO2 electroreduction",
    "year": 2024,
    "screening_status": "high_priority",
    "scientific_status": "unverified_discovery",
}

NEW = {
    "doi": "10.1234/new",
    "title": "New Cu-Ag CO2 electroreduction study",
    "year": 2026,
    "screening_status": "high_priority",
    "scientific_status": "unverified_discovery",
}


@pytest.fixture
def simulated_scan(monkeypatch):
    calls = []

    def fake_scan(**kwargs):
        calls.append(kwargs)

        return {
            "retrieved_count": 2,
            "previously_seen_count": 1,
            "newly_seen_count": 1,
            "new_papers": [NEW],
            "history_saved": kwargs["persist_history"],
        }

    monkeypatch.setattr(cli, "scan_and_digest", fake_scan)

    return calls


def read_events(path):
    return [
        json.loads(line)
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
    ]


def test_default_preview_does_not_record(
    simulated_scan, monkeypatch
):
    # Reporting must be opt-in.

    def unexpected(*args, **kwargs):
        pytest.fail("Default preview attempted reporting")

    monkeypatch.setattr(cli, "save_digest", unexpected)
    monkeypatch.setattr(cli, "append_scan_event", unexpected)

    assert cli.main([]) == 0
    assert simulated_scan[0]["persist_history"] is False


def test_recorded_preview_saves_digest_and_log(
    tmp_path, simulated_scan
):
    report_dir = tmp_path / "reports"
    scan_log = tmp_path / "events.jsonl"

    result = cli.main([
        "--preview",
        "--record",
        "--report-dir", str(report_dir),
        "--scan-log", str(scan_log),
    ])

    assert result == 0
    assert simulated_scan[0]["persist_history"] is False

    reports = list(report_dir.glob("*.txt"))
    assert len(reports) == 1

    content = reports[0].read_text(encoding="utf-8")

    assert NEW["doi"] in content
    assert "History saved: NO" in content
    assert "Evidence status: UNVERIFIED" in content

    events = read_events(scan_log)

    assert len(events) == 1
    assert events[0]["status"] == "success"
    assert events[0]["mode"] == "preview"


def test_save_record_requests_persistence(
    tmp_path, simulated_scan
):
    report_dir = tmp_path / "reports"
    scan_log = tmp_path / "events.jsonl"

    result = cli.main([
        "--save",
        "--record",
        "--report-dir", str(report_dir),
        "--scan-log", str(scan_log),
    ])

    assert result == 0
    assert simulated_scan[0]["persist_history"] is True

    report = next(report_dir.glob("*.txt"))
    assert "History saved: YES" in report.read_text()

    events = read_events(scan_log)

    assert events[0]["status"] == "success"
    assert events[0]["mode"] == "save"
    assert events[0]["newly_seen_count"] == 1


def test_failed_scan_is_logged(
    tmp_path, monkeypatch, capsys
):
    def fail(**kwargs):
        raise OSError("Simulated Crossref outage")

    monkeypatch.setattr(cli, "scan_and_digest", fail)

    scan_log = tmp_path / "events.jsonl"
    report_dir = tmp_path / "reports"

    result = cli.main([
        "--save",
        "--record",
        "--report-dir", str(report_dir),
        "--scan-log", str(scan_log),
    ])

    assert result == 1

    events = read_events(scan_log)
    assert events[0]["status"] == "failure"
    assert events[0]["mode"] == "save"
    assert "Crossref outage" in events[0]["error"]

    assert not list(report_dir.glob("*.txt"))
    assert "RESEARCH WATCHER FAILED" in capsys.readouterr().err


def test_report_failure_discloses_saved_history(
    tmp_path, simulated_scan, monkeypatch, capsys
):
    # The simulated scan reports that history was saved.
    # A subsequent reporting failure must disclose that.

    def fail_report(*args, **kwargs):
        raise OSError("Simulated report disk error")

    monkeypatch.setattr(
        cli, "save_digest", fail_report
    )

    scan_log = tmp_path / "events.jsonl"

    result = cli.main([
        "--save",
        "--record",
        "--scan-log", str(scan_log),
    ])

    assert result == 2

    error_output = capsys.readouterr().err

    assert "REPORTING FAILED" in error_output
    assert "Watcher history saved: YES" in error_output

    events = read_events(scan_log)

    assert events[0]["status"] == "failure"
    assert "history_saved=True" in events[0]["error"]


def test_scan_log_failure_preserves_digest(
    tmp_path, simulated_scan, monkeypatch, capsys
):
    def fail_logging(*args, **kwargs):
        raise OSError("Simulated scan log failure")

    monkeypatch.setattr(
        cli, "append_scan_event", fail_logging
    )

    report_dir = tmp_path / "reports"

    result = cli.main([
        "--save",
        "--record",
        "--report-dir", str(report_dir),
    ])

    assert result == 2
    assert len(list(report_dir.glob("*.txt"))) == 1

    error_output = capsys.readouterr().err

    assert "SCAN LOGGING FAILED" in error_output
    assert "Watcher history saved: YES" in error_output


def test_failed_scan_and_failed_logging(
    tmp_path, monkeypatch, capsys
):
    def fail_scan(**kwargs):
        raise OSError("Crossref unavailable")

    def fail_logging(*args, **kwargs):
        raise OSError("Log unavailable")

    monkeypatch.setattr(
        cli, "scan_and_digest", fail_scan
    )
    monkeypatch.setattr(
        cli, "append_scan_event", fail_logging
    )

    result = cli.main([
        "--preview",
        "--record",
        "--scan-log", str(tmp_path / "events.jsonl"),
    ])

    assert result == 1

    error_output = capsys.readouterr().err

    assert "RESEARCH WATCHER FAILED" in error_output
    assert "FAILURE LOGGING FAILED" in error_output


def test_real_engine_integration_with_temporary_history(
    tmp_path, monkeypatch
):
    # PSEUDOCODE
    # 1. Initialize a temporary watcher baseline.
    # 2. Mock Crossref with one known and one new DOI.
    # 3. Run the real CLI and scan engine in save mode.
    # 4. Check history, digest, and scan log.
    # 5. Never use real research data.

    history_path = tmp_path / "history.json"
    report_dir = tmp_path / "reports"
    scan_log = tmp_path / "events.jsonl"

    history, _ = observe_publications(
        empty_history(),
        [KNOWN],
        "2026-11-07T05:00:00+00:00",
    )

    save_history(history_path, history)

    monkeypatch.setattr(
        watcher_scan,
        "discover_crossref",
        lambda query, rows: [KNOWN, NEW],
    )

    result = cli.main([
        "--save",
        "--record",
        "--history", str(history_path),
        "--rows", "2",
        "--minimum-results", "2",
        "--report-dir", str(report_dir),
        "--scan-log", str(scan_log),
    ])

    assert result == 0

    stored = load_history(history_path)

    assert len(stored["papers"]) == 2
    assert NEW["doi"] in stored["papers"]

    reports = list(report_dir.glob("*.txt"))
    assert len(reports) == 1

    content = reports[0].read_text(encoding="utf-8")

    assert NEW["doi"] in content
    assert "History saved: YES" in content

    events = read_events(scan_log)

    assert len(events) == 1
    assert events[0]["status"] == "success"
    assert events[0]["newly_seen_count"] == 1
