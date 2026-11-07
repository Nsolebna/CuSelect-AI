# CuSelect-AI — Human Literature Review Queue tests
#
# PSEUDOCODE
# 1. Normalize DOI identifiers.
# 2. Reject malformed DOIs and duplicate papers.
# 3. Create and update human literature-review decisions.
# 4. Preserve researcher notes across rediscovery.
# 5. Save and reload the review queue safely.
# 6. Prevent unauthorized scientific claim approval.
# 7. Never modify the actual reviewed evidence registry.

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.review_queue import (
    ReviewQueueError,
    normalize_doi,
    validate_queue,
    merge_discoveries,
    update_review,
    save_queue,
    load_queue,
)


@pytest.fixture
def discoveries():
    return [
        {
            "doi": "10.1234/example-one",
            "title": "Cu-Ag catalysts for CO2 reduction",
            "year": 2024,
            "journal": "Example Journal",
            "screening_status": "high_priority",
        },
        {
            "doi": "10.5678/example-two",
            "title": "Copper electrodes for CO2 reduction",
            "year": 2025,
            "journal": "Another Journal",
            "screening_status": "manual_review",
        },
    ]


@pytest.mark.parametrize(
    "source",
    [
        "10.1234/ABC",
        "doi:10.1234/ABC",
        "https://doi.org/10.1234/ABC",
    ],
)
def test_doi_normalization(source):
    assert normalize_doi(source) == "10.1234/abc"


@pytest.mark.parametrize(
    "source",
    ["", "not-a-doi", "10.1234", None],
)
def test_invalid_doi_is_rejected(source):
    with pytest.raises(ReviewQueueError):
        normalize_doi(source)


def test_discovered_papers_start_unverified(discoveries):
    queue = merge_discoveries(discoveries)

    assert len(queue) == 2
    assert all(p["review_status"] == "new" for p in queue)
    assert all(
        p["scientific_status"] == "unverified_discovery"
        for p in queue
    )


def test_duplicate_discoveries_are_not_repeated(discoveries):
    repeated = discoveries + [dict(discoveries[0])]

    queue = merge_discoveries(repeated)

    assert len(queue) == 2


def test_rediscovery_preserves_review_and_notes(discoveries):
    queue = merge_discoveries(discoveries)

    queue = update_review(
        queue,
        "10.1234/example-one",
        "review_further",
        "Inspect source figures and experimental conditions.",
    )

    merged = merge_discoveries(discoveries, queue)

    selected = next(
        p for p in merged
        if p["doi"] == "10.1234/example-one"
    )

    assert selected["review_status"] == "review_further"
    assert "source figures" in selected["notes"]


def test_paper_can_be_set_aside(discoveries):
    queue = merge_discoveries(discoveries)

    updated = update_review(
        queue,
        "10.5678/example-two",
        "set_aside",
    )

    selected = next(
        p for p in updated
        if p["doi"] == "10.5678/example-two"
    )

    assert selected["review_status"] == "set_aside"


def test_invalid_review_status_is_rejected(discoveries):
    queue = merge_discoveries(discoveries)

    with pytest.raises(ReviewQueueError):
        update_review(
            queue,
            "10.1234/example-one",
            "scientifically_approved",
        )


def test_unknown_paper_cannot_be_updated(discoveries):
    queue = merge_discoveries(discoveries)

    with pytest.raises(ReviewQueueError):
        update_review(
            queue,
            "10.9999/unknown",
            "review_further",
        )


def test_notes_must_be_text(discoveries):
    queue = merge_discoveries(discoveries)

    with pytest.raises(ReviewQueueError):
        update_review(
            queue,
            "10.1234/example-one",
            "review_further",
            notes=123,
        )


def test_update_does_not_mutate_original_queue(discoveries):
    original = merge_discoveries(discoveries)

    updated = update_review(
        original,
        "10.1234/example-one",
        "review_further",
    )

    original_by_doi = {p["doi"]: p for p in original}
    updated_by_doi = {p["doi"]: p for p in updated}

    assert original_by_doi["10.1234/example-one"][
        "review_status"
    ] == "new"

    assert updated_by_doi["10.1234/example-one"][
        "review_status"
    ] == "review_further"


def test_queue_can_be_saved_and_reloaded(tmp_path, discoveries):
    queue = merge_discoveries(discoveries)

    queue = update_review(
        queue,
        "10.1234/example-one",
        "review_further",
        "Read the supplementary information.",
    )

    path = tmp_path / "review_queue.json"

    save_queue(path, queue)
    restored = load_queue(path)

    assert restored == queue
    assert path.exists()


def test_missing_queue_returns_empty_list(tmp_path):
    path = tmp_path / "not_created.json"

    assert load_queue(path) == []


def test_unknown_queue_schema_is_rejected(tmp_path):
    path = tmp_path / "review_queue.json"

    path.write_text(
        json.dumps({
            "schema_version": 999,
            "entries": [],
        }),
        encoding="utf-8",
    )

    with pytest.raises(ReviewQueueError):
        load_queue(path)


def test_forged_scientific_approval_is_rejected(discoveries):
    queue = merge_discoveries(discoveries)

    queue[0]["scientific_status"] = "human_verified"

    with pytest.raises(ReviewQueueError):
        validate_queue(queue)


def test_duplicate_stored_entries_are_rejected(discoveries):
    queue = merge_discoveries(discoveries)

    queue.append(dict(queue[0]))

    with pytest.raises(ReviewQueueError):
        validate_queue(queue)


def test_discovery_requires_publication_title():
    with pytest.raises(ReviewQueueError):
        merge_discoveries([
            {
                "doi": "10.1234/missing-title",
            }
        ])
