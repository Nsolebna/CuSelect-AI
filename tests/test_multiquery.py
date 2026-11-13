# CuSelect-AI — Multi-Query Discovery Tests
#
# PSEUDOCODE
# 1. Simulate Crossref without internet access.
# 2. Verify DOI deduplication across different queries.
# 3. Verify checkpoint creation.
# 4. Simulate an interrupted discovery.
# 5. Verify that restarting skips completed queries.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest
import cuselect.multiquery as multiquery


def make_paper(doi):
    return {
        "doi": doi,
        "scientific_status": "unverified_discovery",
    }


def test_multiquery_deduplication_and_checkpoint(
    monkeypatch, tmp_path
):
    calls = []
    delays = []

    def fake_discovery(query, rows):
        calls.append(query)

        if query == "query one":
            return [
                make_paper("10.1234/a"),
                make_paper("10.1234/b"),
            ]

        return [
            make_paper("10.1234/b"),
            make_paper("10.1234/c"),
        ]

    monkeypatch.setattr(
        multiquery, "discover_crossref", fake_discovery
    )
    monkeypatch.setattr(
        multiquery.time, "sleep", delays.append
    )

    checkpoint = tmp_path / "checkpoint.json"

    papers = multiquery.discover_multiple(
        ["query one", "query two"],
        rows=5,
        checkpoint_path=checkpoint,
        delay_seconds=2,
    )

    assert len(papers) == 3
    assert calls == ["query one", "query two"]
    assert delays == [2]
    assert checkpoint.exists()

    # Running again should use the checkpoint.
    papers_again = multiquery.discover_multiple(
        ["query one", "query two"],
        rows=5,
        checkpoint_path=checkpoint,
        delay_seconds=2,
    )

    assert len(papers_again) == 3
    assert len(calls) == 2


def test_multiquery_resume_after_failure(
    monkeypatch, tmp_path
):
    calls = []
    fail_second_query = True

    def fake_discovery(query, rows):
        calls.append(query)

        if query == "query two" and fail_second_query:
            raise OSError("Simulated Crossref failure")

        return [make_paper(f"10.1234/{query[-3:]}")]

    monkeypatch.setattr(
        multiquery, "discover_crossref", fake_discovery
    )
    monkeypatch.setattr(
        multiquery.time, "sleep", lambda seconds: None
    )

    checkpoint = tmp_path / "checkpoint.json"

    with pytest.raises(OSError):
        multiquery.discover_multiple(
            ["query one", "query two"],
            checkpoint_path=checkpoint,
            delay_seconds=0,
        )

    assert checkpoint.exists()

    saved = multiquery.load_checkpoint(checkpoint)
    assert len(saved["completed"]) == 1

    # Restore the simulated Crossref connection.
    fail_second_query = False

    papers = multiquery.discover_multiple(
        ["query one", "query two"],
        checkpoint_path=checkpoint,
        delay_seconds=0,
    )

    assert len(papers) == 2

    # Query one ran only once across both executions.
    assert calls.count("query one") == 1
    assert calls.count("query two") == 2
