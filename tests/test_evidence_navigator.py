# PSEUDOCODE
# 1. Verify a legitimate scientific evidence card.
# 2. Reject altered DOI and source metadata.
# 3. Reject fabricated and duplicate citations.
# 4. Reject invalid citation formats.
# 5. Allow an empty citation list without inventing evidence.

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.evidence_navigator import build_evidence_cards
from cuselect.evidence_store import (
    EvidenceIntegrityError,
    load_verified_corpus,
)


@pytest.fixture
def valid_citation():
    records = load_verified_corpus(ROOT)

    record = next(
        r for r in records
        if r["evidence_id"] == "E-P005-FE-C2H4-001"
    )

    return {
        "evidence_id": record["evidence_id"],
        "doi": record["doi"],
        "source_location": record["source_location"],
        "source_extent": record["source_extent"],
    }


def test_valid_evidence_card(valid_citation):
    cards = build_evidence_cards([valid_citation], ROOT)

    assert len(cards) == 1
    assert cards[0]["review_status"] == "human_verified"
    assert cards[0]["publication_url"].startswith(
        "https://doi.org/"
    )
    assert "54.9%" in cards[0]["claim"]


@pytest.mark.parametrize(
    "field, replacement",
    [
        ("doi", "10.9999/fabricated"),
        ("source_location", "Fake Figure 99"),
        ("source_extent", "unknown"),
    ],
)
def test_tampered_metadata_is_rejected(
    valid_citation, field, replacement
):
    altered = dict(valid_citation)
    altered[field] = replacement

    with pytest.raises(EvidenceIntegrityError):
        build_evidence_cards([altered], ROOT)


def test_fabricated_evidence_id_is_rejected(valid_citation):
    altered = dict(valid_citation)
    altered["evidence_id"] = "E-FAKE-001"

    with pytest.raises(EvidenceIntegrityError):
        build_evidence_cards([altered], ROOT)


def test_duplicate_citation_is_rejected(valid_citation):
    with pytest.raises(EvidenceIntegrityError):
        build_evidence_cards(
            [valid_citation, valid_citation],
            ROOT,
        )


def test_invalid_citation_format_is_rejected():
    with pytest.raises(EvidenceIntegrityError):
        build_evidence_cards(["invalid citation"], ROOT)


def test_empty_citations_produce_no_cards():
    assert build_evidence_cards([], ROOT) == []
