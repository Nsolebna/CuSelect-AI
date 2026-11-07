# CuSelect-AI — Literature Discovery tests
#
# PSEUDOCODE
# 1. Test chemical-title normalization and screening.
# 2. Test Crossref response handling without internet.
# 3. Verify DOI deduplication.
# 4. Reject invalid search parameters.
# 5. Confirm discovered papers remain unverified.
# 6. Confirm connection failures are not hidden.

import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cuselect.discovery as discovery


@pytest.mark.parametrize(
    "title, expected",
    [
        (
            "CO<sub>2</sub> Electroreduction on Copper",
            "manual_review",
        ),
        (
            "CO₂ electroreduction on Cu2O catalysts",
            "manual_review",
        ),
        (
            "Dynamic valence engineering of CuOx catalysts "
            "for CO2 electroreduction",
            "manual_review",
        ),
        (
            "CO2-to-ethylene electroreduction gets a boost",
            "manual_review",
        ),
        (
            "CO2 electroreduction on copper and silver",
            "high_priority",
        ),
        (
            "Oxygen Electroreduction on Silver/Copper",
            "out_of_scope_title",
        ),
        (
            "Conversion of ethanol into ethylene oxide "
            "on copper and silver",
            "out_of_scope_title",
        ),
    ],
)
def test_scientific_title_screening(title, expected):
    assert discovery.screen_title(title) == expected


@pytest.mark.parametrize("rows", [0, 101, True])
def test_invalid_result_counts_are_rejected(rows):
    with pytest.raises(ValueError):
        discovery.discover_crossref("CO2 electroreduction", rows=rows)


def test_empty_search_query_is_rejected():
    with pytest.raises(ValueError):
        discovery.discover_crossref("   ")


def test_crossref_deduplication_and_unverified_status(monkeypatch):
    # PSEUDOCODE
    # 1. Build a simulated Crossref response.
    # 2. Include duplicate DOIs and incomplete records.
    # 3. Run the real discovery parsing function.
    # 4. Check that only valid unique records remain.

    payload = {
        "message": {
            "items": [
                {
                    "DOI": "10.1234/ABC",
                    "title": [
                        "CO2 electroreduction on copper and silver"
                    ],
                    "published": {"date-parts": [[2024]]},
                    "container-title": ["Example Journal"],
                },
                {
                    "DOI": "10.1234/abc",
                    "title": ["Duplicate publication"],
                },
                {
                    "DOI": "10.5678/DEF",
                    "title": [
                        "CO<sub>2</sub> electroreduction on CuOx"
                    ],
                    "published": {"date-parts": [[2025]]},
                    "container-title": ["Another Journal"],
                },
                {
                    "DOI": "",
                    "title": ["Missing DOI"],
                },
                {
                    "DOI": "10.9999/EMPTY",
                    "title": [""],
                },
            ]
        }
    }

    def fake_urlopen(request, timeout):
        assert "api.crossref.org/works" in request.full_url
        assert timeout == 20

        return io.BytesIO(
            json.dumps(payload).encode("utf-8")
        )

    monkeypatch.setattr(
        discovery,
        "urlopen",
        fake_urlopen,
    )

    papers = discovery.discover_crossref(
        "copper silver CO2 electroreduction",
        rows=10,
    )

    assert len(papers) == 2

    assert [paper["doi"] for paper in papers] == [
        "10.1234/abc",
        "10.5678/def",
    ]

    assert [paper["screening_status"] for paper in papers] == [
        "high_priority",
        "manual_review",
    ]

    assert all(
        paper["scientific_status"] == "unverified_discovery"
        for paper in papers
    )

    assert all(
        paper["metadata_source"] == "Crossref"
        for paper in papers
    )


def test_crossref_connection_failure_is_propagated(monkeypatch):
    def fake_failure(request, timeout):
        raise OSError("Simulated network failure")

    monkeypatch.setattr(
        discovery,
        "urlopen",
        fake_failure,
    )

    with pytest.raises(
        OSError,
        match="Simulated network failure",
    ):
        discovery.discover_crossref(
            "CO2 electroreduction",
            rows=5,
        )
