# CuSelect-AI — Research Watcher Lock Integration Tests
#
# PSEUDOCODE
# 1. Prepare an isolated watcher history.
# 2. Confirm a save scan holds the exclusive lock.
# 3. Reject overlapping save scans.
# 4. Allow read-only previews without writing history.
# 5. Release locks after discovery failures.
# 6. Release locks after incomplete scans.
# 7. Never modify the real research evidence.

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cuselect.watcher_scan as watcher_scan

from cuselect.watcher_lock import (
    WatcherLockError,
    exclusive_history_lock,
)

from cuselect.research_watcher import (
    empty_history,
    observe_publications,
    save_history,
    load_history,
)


KNOWN = {
    "doi": "10.1234/known",
    "title": "Known Cu-Ag CO2RR publication",
    "year": 2024,
    "screening_status": "high_priority",
    "scientific_status": "unverified_discovery",
}

NEW = {
    "doi": "10.1234/new",
    "title": "Newly encountered Cu-Ag CO2RR publication",
    "year": 2026,
    "screening_status": "high_priority",
    "scientific_status": "unverified_discovery",
}


@pytest.fixture
def history_path(tmp_path):
    path = tmp_path / "watcher_history.json"

    history, _ = observe_publications(
        empty_history(),
        [KNOWN],
        "2026-11-07T06:00:00+00:00",
    )

    save_history(path, history)
    return path


def test_overlapping_save_scan_is_rejected(
    history_path, monkeypatch
):
    # A second save scan must fail before discovery starts.
    def unexpected_discovery(query, rows):
        pytest.fail("Discovery should not begin while locked")

    monkeypatch.setattr(
        watcher_scan,
        "discover_crossref",
        unexpected_discovery,
    )

    before = history_path.read_bytes()

    with exclusive_history_lock(history_path):
        with pytest.raises(WatcherLockError):
            watcher_scan.scan_and_digest(
                history_path,
                rows=2,
                minimum_results=2,
                persist_history=True,
            )

    assert history_path.read_bytes() == before


def test_save_scan_holds_lock_during_discovery(
    history_path, monkeypatch
):
    # PSEUDOCODE:
    # While the scan is discovering papers, confirm
    # another operation cannot acquire its history lock.

    def simulated_discovery(query, rows):
        with pytest.raises(WatcherLockError):
            with exclusive_history_lock(history_path):
                pass

        return [KNOWN, NEW]

    monkeypatch.setattr(
        watcher_scan,
        "discover_crossref",
        simulated_discovery,
    )

    digest = watcher_scan.scan_and_digest(
        history_path,
        rows=2,
        minimum_results=2,
        persist_history=True,
    )

    assert digest["history_saved"] is True
    assert digest["newly_seen_count"] == 1

    stored = load_history(history_path)
    assert len(stored["papers"]) == 2

    # A successful scan must release its lock.
    with exclusive_history_lock(history_path):
        pass


def test_preview_does_not_modify_locked_history(
    history_path, monkeypatch
):
    monkeypatch.setattr(
        watcher_scan,
        "discover_crossref",
        lambda query, rows: [KNOWN, NEW],
    )

    before = history_path.read_bytes()

    with exclusive_history_lock(history_path):
        digest = watcher_scan.scan_and_digest(
            history_path,
            rows=2,
            minimum_results=2,
            persist_history=False,
        )

    assert digest["history_saved"] is False
    assert digest["newly_seen_count"] == 1
    assert history_path.read_bytes() == before


def test_network_failure_releases_lock(
    history_path, monkeypatch
):
    def failed_discovery(query, rows):
        raise OSError("Simulated Crossref outage")

    monkeypatch.setattr(
        watcher_scan,
        "discover_crossref",
        failed_discovery,
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

    # The lock must be available after the exception.
    with exclusive_history_lock(history_path):
        pass


def test_incomplete_scan_releases_lock(
    history_path, monkeypatch
):
    monkeypatch.setattr(
        watcher_scan,
        "discover_crossref",
        lambda query, rows: [NEW],
    )

    before = history_path.read_bytes()

    with pytest.raises(watcher_scan.WatcherScanError):
        watcher_scan.scan_and_digest(
            history_path,
            rows=3,
            minimum_results=2,
            persist_history=True,
        )

    assert history_path.read_bytes() == before

    with exclusive_history_lock(history_path):
        pass
