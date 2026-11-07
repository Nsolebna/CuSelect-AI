# CuSelect-AI — Controlled Research Watcher Persistence
#
# PSEUDOCODE
# 1. Create a temporary history containing one known DOI.
# 2. Simulate successful discovery of a second DOI.
# 3. Confirm persistence only when explicitly enabled.
# 4. Confirm repeated scans do not rediscover the same DOI.
# 5. Preserve history after failed or incomplete scans.
# 6. Reject changes detected during a scan.
# 7. Keep verified scientific evidence untouched.

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cuselect.watcher_scan as watcher_scan

from cuselect.research_watcher import (
    empty_history,
    observe_publications,
    save_history,
    load_history,
)


def paper(doi, title):
    return {
        "doi": doi,
        "title": title,
        "year": 2026,
        "screening_status": "high_priority",
        "scientific_status": "unverified_discovery",
    }


KNOWN = paper(
    "10.1234/known",
    "Known Cu-Ag CO2 electroreduction paper",
)

NEW = paper(
    "10.1234/new",
    "Newly encountered Cu-Ag catalyst paper",
)


@pytest.fixture
def history_path(tmp_path):
    path = tmp_path / "history.json"

    history, _ = observe_publications(
        empty_history(),
        [KNOWN],
        "2026-11-07T06:00:00+00:00",
    )

    save_history(path, history)
    return path


def mock_discovery(monkeypatch, publications):
    def fake_discovery(query, rows):
        return publications

    monkeypatch.setattr(
        watcher_scan,
        "discover_crossref",
        fake_discovery,
    )


def test_successful_scan_saves_new_doi(
    history_path, monkeypatch
):
    mock_discovery(monkeypatch, [KNOWN, NEW])

    digest = watcher_scan.scan_and_digest(
        history_path,
        rows=2,
        minimum_results=2,
        persist_history=True,
    )

    stored = load_history(history_path)

    assert digest["history_saved"] is True
    assert digest["newly_seen_count"] == 1
    assert len(stored["papers"]) == 2
    assert "10.1234/new" in stored["papers"]

    report = watcher_scan.format_digest(digest)
    assert "History saved: YES" in report


def test_repeated_scan_does_not_repeat_discovery(
    history_path, monkeypatch
):
    mock_discovery(monkeypatch, [KNOWN, NEW])

    first = watcher_scan.scan_and_digest(
        history_path,
        rows=2,
        minimum_results=2,
        persist_history=True,
    )

    first_seen = load_history(history_path)[
        "papers"
    ]["10.1234/new"]["first_seen_utc"]

    second = watcher_scan.scan_and_digest(
        history_path,
        rows=2,
        minimum_results=2,
        persist_history=True,
    )

    stored = load_history(history_path)

    assert first["newly_seen_count"] == 1
    assert second["newly_seen_count"] == 0
    assert len(stored["papers"]) == 2
    assert stored["papers"]["10.1234/new"][
        "first_seen_utc"
    ] == first_seen


def test_preview_never_saves(
    history_path, monkeypatch
):
    mock_discovery(monkeypatch, [KNOWN, NEW])

    before = history_path.read_bytes()

    digest = watcher_scan.scan_and_digest(
        history_path,
        rows=2,
        minimum_results=2,
    )

    assert digest["newly_seen_count"] == 1
    assert digest["history_saved"] is False
    assert history_path.read_bytes() == before


def test_network_failure_never_saves(
    history_path, monkeypatch
):
    def fail(query, rows):
        raise OSError("Simulated Crossref outage")

    monkeypatch.setattr(
        watcher_scan,
        "discover_crossref",
        fail,
    )

    before = history_path.read_bytes()

    with pytest.raises(OSError):
        watcher_scan.scan_and_digest(
            history_path,
            rows=2,
            minimum_results=2,
            persist_history=True,
        )

    assert history_path.read_bytes() == before


def test_incomplete_scan_never_saves(
    history_path, monkeypatch
):
    mock_discovery(monkeypatch, [NEW])

    before = history_path.read_bytes()

    with pytest.raises(
        watcher_scan.WatcherScanError
    ):
        watcher_scan.scan_and_digest(
            history_path,
            rows=3,
            minimum_results=2,
            persist_history=True,
        )

    assert history_path.read_bytes() == before


def test_history_change_during_scan_is_detected(
    history_path, monkeypatch
):
    def concurrent_change(query, rows):
        # Simulate another process modifying the file.
        history_path.write_text(
            '{"external_change": true}',
            encoding="utf-8",
        )
        return [KNOWN, NEW]

    monkeypatch.setattr(
        watcher_scan,
        "discover_crossref",
        concurrent_change,
    )

    with pytest.raises(
        watcher_scan.WatcherScanError,
        match="changed during the scan",
    ):
        watcher_scan.scan_and_digest(
            history_path,
            rows=2,
            minimum_results=2,
            persist_history=True,
        )

    # The watcher did not overwrite the external change.
    assert "external_change" in history_path.read_text()


def test_persistence_flag_must_be_boolean(
    history_path
):
    with pytest.raises(
        watcher_scan.WatcherScanError,
        match="persist_history must be a boolean",
    ):
        watcher_scan.scan_and_digest(
            history_path,
            persist_history="yes",
        )
