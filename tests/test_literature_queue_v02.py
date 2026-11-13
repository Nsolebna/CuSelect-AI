"""Regression checks for literature metadata queue."""
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from cuselect.discovery_queue_ui import (
    date_category, load_discovered_papers, score_relevance, update_status,
)


def test_recent_and_future_publication_flags():
    today = date.today()
    assert date_category(today.isoformat()) == "Published in last 30 days"
    assert date_category((today + timedelta(days=60)).isoformat()) == "Future-dated metadata"
    assert date_category("1987-07-01") == "Earlier publication"
    assert date_category("2026-11") in {"Incomplete/unknown date", "Future-dated metadata"}


def test_priority_is_heuristic_only():
    relevant = {"title": "Ag Cu tandem carbon dioxide electroreduction to ethylene"}
    unrelated = {"title": "Solar cell fabrication"}
    assert score_relevance(relevant) > score_relevance(unrelated)


def test_metadata_review_does_not_touch_approved_evidence(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    queue = data / "rag_discovery_queue.json"
    approved = data / "approved_evidence.json"
    original = [{"doi": "10.1234/example", "review_status": "pending_metadata_review"}]
    queue.write_text(json.dumps(original), encoding="utf-8")
    approved.write_text('[{"approved": true}]', encoding="utf-8")
    update_status(tmp_path, "10.1234/example", "shortlisted_for_full_text_review")
    assert load_discovered_papers(tmp_path)[0]["review_status"] == "shortlisted_for_full_text_review"
    assert approved.read_text(encoding="utf-8") == '[{"approved": true}]'
    with pytest.raises(ValueError):
        update_status(tmp_path, "10.1234/example", "approved")
