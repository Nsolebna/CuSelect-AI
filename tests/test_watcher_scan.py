# CuSelect-AI — Research Watcher Scan & Digest tests
#
# PSEUDOCODE
# 1. Create an isolated watcher history for testing.
# 2. Simulate Crossref publication responses.
# 3. Confirm known publications are not reported as new.
# 4. Prioritize previously unseen publications.
# 5. Reject incomplete scans and invalid parameters.
# 6. Propagate network failures.
# 7. Reject scientifically approved records.
# 8. Verify readable research digests.
# 9. Confirm that scanning does not save history.

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
)


def paper(
    doi="10.1234/known",
    title="Cu-Ag CO2 electroreduction",
    screening="high_priority",
):
    return {
        "doi": doi,
        "title": title,
        "year": 2024,
        "screening_status": screening,
        "scientific_status": "unverified_discovery",
    }


@pytest.fixture
def history_path(tmp_path):
    path = tmp_path / "watcher_history.json"

    history, _ = observe_publications(
        empty_history(),
        [paper()],
        "2026-11-07T06:00:00+00:00",
    )

    save_history(path, history)

    return path


def test_missing_baseline_is_rejected(tmp_path):
    path = tmp_path / "missing.json"

    with pytest.raises(
        watcher_scan.WatcherScanError,
        match="does not exist",
    ):
        watcher_scan.scan_and_digest(path)


def test_uninitialized_baseline_is_rejected(tmp_path):
    path = tmp_path / "empty.json"

    save_history(path, empty_history())

    with pytest.raises(
        watcher_scan.WatcherScanError,
        match="not initialized",
    ):
        watcher_scan.scan_and_digest(path)


def test_known_publication_is_not_new(
    history_path, monkeypatch
):
    monkeypatch.setattr(
        watcher_scan,
        "discover_crossref",
        lambda query, rows: [paper()],
    )

    before = history_path.read_bytes()

    digest = watcher_scan.scan_and_digest(
        history_path,
        rows=1,
        minimum_results=1,
    )

    assert digest["retrieved_count"] == 1
    assert digest["previously_seen_count"] == 1
    assert digest["newly_seen_count"] == 0
    assert digest["new_papers"] == []
    assert digest["history_saved"] is False

    # Read-only guarantee.
    assert history_path.read_bytes() == before


def test_new_papers_are_prioritized(
    history_path, monkeypatch
):
    manual = paper(
        "10.1234/manual",
        "Copper CO2 electroreduction",
        "manual_review",
    )

    high = paper(
        "10.1234/high",
        "Silver-copper tandem CO2 electroreduction",
        "high_priority",
    )

    monkeypatch.setattr(
        watcher_scan,
        "discover_crossref",
        lambda query, rows: [manual, paper(), high],
    )

    digest = watcher_scan.scan_and_digest(
        history_path,
        rows=3,
        minimum_results=2,
    )

    assert digest["retrieved_count"] == 3
    assert digest["previously_seen_count"] == 1
    assert digest["newly_seen_count"] == 2

    assert [
        item["doi"] for item in digest["new_papers"]
    ] == [
        "10.1234/high",
        "10.1234/manual",
    ]

    assert digest["existing_history_count"] == 1
    assert digest["proposed_history_count"] == 3


def test_incomplete_scan_is_rejected(
    history_path, monkeypatch
):
    monkeypatch.setattr(
        watcher_scan,
        "discover_crossref",
        lambda query, rows: [paper()],
    )

    before = history_path.read_bytes()

    with pytest.raises(
        watcher_scan.WatcherScanError,
        match="Insufficient Crossref results",
    ):
        watcher_scan.scan_and_digest(
            history_path,
            rows=5,
            minimum_results=3,
        )

    assert history_path.read_bytes() == before


@pytest.mark.parametrize(
    "minimum",
    [0, 4, True, 1.5],
)
def test_invalid_minimum_results_is_rejected(
    history_path, minimum
):
    with pytest.raises(
        watcher_scan.WatcherScanError,
        match="Invalid minimum-results",
    ):
        watcher_scan.scan_and_digest(
            history_path,
            rows=3,
            minimum_results=minimum,
        )


def test_network_failure_is_propagated(
    history_path, monkeypatch
):
    def fail_crossref(query, rows):
        raise OSError("Simulated connection failure")

    monkeypatch.setattr(
        watcher_scan,
        "discover_crossref",
        fail_crossref,
    )

    before = history_path.read_bytes()

    with pytest.raises(
        OSError,
        match="Simulated connection failure",
    ):
        watcher_scan.scan_and_digest(
            history_path,
            rows=1,
            minimum_results=1,
        )

    assert history_path.read_bytes() == before


def test_forged_scientific_approval_is_rejected(
    history_path, monkeypatch
):
    candidate = paper("10.1234/forged")

    candidate["scientific_status"] = "human_verified"

    monkeypatch.setattr(
        watcher_scan,
        "discover_crossref",
        lambda query, rows: [candidate],
    )

    with pytest.raises(ValueError):
        watcher_scan.scan_and_digest(
            history_path,
            rows=1,
            minimum_results=1,
        )


def test_digest_reports_no_new_publications():
    digest = {
        "retrieved_count": 1,
        "previously_seen_count": 1,
        "newly_seen_count": 0,
        "new_papers": [],
    }

    report = watcher_scan.format_digest(digest)

    assert "Newly encountered DOIs: 0" in report
    assert "No previously unseen DOI" in report
    assert "History saved: NO" in report
    assert "Verified scientific evidence modified: NO" in report


def test_digest_displays_new_publication():
    candidate = paper("10.1234/new")

    digest = {
        "retrieved_count": 2,
        "previously_seen_count": 1,
        "newly_seen_count": 1,
        "new_papers": [candidate],
    }

    report = watcher_scan.format_digest(digest)

    assert candidate["title"] in report
    assert candidate["doi"] in report
    assert "Evidence status: UNVERIFIED" in report
    assert "Screening: high_priority" in report
