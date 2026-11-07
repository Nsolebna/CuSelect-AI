# CuSelect-AI — Research Watcher tests
#
# PSEUDOCODE
# 1. Establish a baseline on the first successful scan.
# 2. Recognize previously observed DOI records.
# 3. Detect genuinely new-to-watcher DOI records.
# 4. Preserve first-seen timestamps.
# 5. Deduplicate publications within each scan.
# 6. Reject invalid or scientifically approved records.
# 7. Save and reload persistent monitoring history.
# 8. Never modify the human review queue or verified evidence.

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.research_watcher import (
    WatcherError,
    empty_history,
    validate_history,
    observe_publications,
    save_history,
    load_history,
)

T0 = "2026-11-07T06:00:00+00:00"
T1 = "2026-11-08T06:00:00+00:00"


def paper(doi="10.1234/example-a", title="Cu-Ag CO2RR"):
    return {
        "doi": doi,
        "title": title,
        "scientific_status": "unverified_discovery",
    }


def test_empty_history_defaults():
    history = empty_history()

    assert history["initialized"] is False
    assert history["papers"] == {}


def test_first_scan_establishes_baseline():
    history, result = observe_publications(
        empty_history(), [paper()], T0
    )

    assert result["baseline_scan"] is True
    assert result["baseline_dois"] == ["10.1234/example-a"]
    assert result["new_dois"] == []
    assert history["initialized"] is True


def test_repeated_doi_is_not_new():
    history, _ = observe_publications(
        empty_history(), [paper()], T0
    )

    history, result = observe_publications(
        history, [paper()], T1
    )

    assert result["new_dois"] == []
    assert result["previously_seen_dois"] == [
        "10.1234/example-a"
    ]


def test_new_doi_after_baseline():
    history, _ = observe_publications(
        empty_history(), [paper()], T0
    )

    second = paper("10.5678/example-b", "New catalyst paper")

    history, result = observe_publications(
        history, [paper(), second], T1
    )

    assert result["new_dois"] == ["10.5678/example-b"]
    assert len(history["papers"]) == 2


def test_first_seen_timestamp_is_preserved():
    history, _ = observe_publications(
        empty_history(), [paper()], T0
    )

    history, _ = observe_publications(
        history, [paper()], T1
    )

    record = history["papers"]["10.1234/example-a"]

    assert record["first_seen_utc"] == T0
    assert record["last_seen_utc"] == T1


def test_duplicate_doi_in_one_scan_is_collapsed():
    history, result = observe_publications(
        empty_history(),
        [paper(), paper("10.1234/EXAMPLE-A")],
        T0,
    )

    assert result["observed_count"] == 1
    assert len(history["papers"]) == 1


def test_observation_does_not_mutate_input():
    original = empty_history()

    updated, _ = observe_publications(
        original, [paper()], T0
    )

    assert original["papers"] == {}
    assert len(updated["papers"]) == 1


def test_empty_scan_does_not_initialize_history():
    history, result = observe_publications(
        empty_history(), [], T0
    )

    assert history["initialized"] is False
    assert result["observed_count"] == 0


def test_verified_claim_record_is_rejected():
    candidate = paper()
    candidate["scientific_status"] = "human_verified"

    with pytest.raises(WatcherError):
        observe_publications(
            empty_history(), [candidate], T0
        )


def test_invalid_title_is_rejected():
    candidate = paper(title="")

    with pytest.raises(WatcherError):
        observe_publications(
            empty_history(), [candidate], T0
        )


def test_invalid_doi_is_rejected():
    candidate = paper(doi="not-a-doi")

    with pytest.raises(WatcherError):
        observe_publications(
            empty_history(), [candidate], T0
        )


def test_publications_must_be_a_list():
    with pytest.raises(WatcherError):
        observe_publications(
            empty_history(), "invalid", T0
        )


def test_observation_timestamp_requires_timezone():
    with pytest.raises(WatcherError):
        observe_publications(
            empty_history(),
            [paper()],
            "2026-11-07T06:00:00",
        )


def test_history_can_be_saved_and_reloaded(tmp_path):
    history, _ = observe_publications(
        empty_history(), [paper()], T0
    )

    path = tmp_path / "watcher_history.json"

    save_history(path, history)
    restored = load_history(path)

    assert restored == history


def test_missing_history_returns_empty(tmp_path):
    path = tmp_path / "not_created.json"

    assert load_history(path) == empty_history()


def test_unknown_history_schema_is_rejected(tmp_path):
    path = tmp_path / "watcher_history.json"

    path.write_text(
        json.dumps({
            "schema_version": 999,
            "initialized": True,
            "papers": {},
        }),
        encoding="utf-8",
    )

    with pytest.raises(WatcherError):
        load_history(path)


def test_invalid_stored_timestamp_is_rejected():
    history, _ = observe_publications(
        empty_history(), [paper()], T0
    )

    history["papers"]["10.1234/example-a"][
        "first_seen_utc"
    ] = "invalid-timestamp"

    with pytest.raises(WatcherError):
        validate_history(history)
