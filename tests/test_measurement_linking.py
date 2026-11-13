
# CuSelect-AI — Measurement Linking Tests
#
# PSEUDOCODE
# 1. Verify explicit ethylene/ethanol FE assignment.
# 2. Verify qualifiers are preserved.
# 3. Reject ambiguous numerical relationships.
# 4. Reject chemical-formula and Miller-index numbers.
# 5. Preserve DOI, source text and review status.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.measurement_linking import (
    link_faradaic_efficiencies,
)


def make_paper(abstract):
    return {
        "doi": "10.1234/test",
        "title": "CuAg electroreduction study",
        "abstract": abstract,
        "abstract_source": "OpenAlex",
    }


def test_respectively_assigns_products():
    paper = make_paper(
        "The Faradaic efficiency for C 2 H 4 "
        "and C 2 H 5 OH production reaching "
        "nearly 60 and 25%, respectively."
    )

    results = link_faradaic_efficiencies(paper)

    assert len(results) == 2

    assert results[0]["product"] == "ethylene"
    assert results[0]["value"] == 60.0

    assert results[1]["product"] == "ethanol"
    assert results[1]["value"] == 25.0


def test_qualifier_is_preserved():
    paper = make_paper(
        "Faradaic efficiencies for ethylene and "
        "ethanol reached nearly 60 and 25%, respectively."
    )

    results = link_faradaic_efficiencies(paper)

    assert results[0]["qualifier"] == "nearly"
    assert results[1]["qualifier"] is None


def test_ambiguous_statement_is_rejected():
    paper = make_paper(
        "Faradaic efficiencies for ethylene and "
        "ethanol were measured at several potentials."
    )

    assert link_faradaic_efficiencies(paper) == []


def test_nonmeasurement_numbers_are_rejected():
    paper = make_paper(
        "Cu2O and Ag(111) catalysts were tested "
        "for CO2 reduction using 3,5-diamino-triazole."
    )

    assert link_faradaic_efficiencies(paper) == []


def test_provenance_and_review_status():
    paper = make_paper(
        "Faradaic efficiencies for ethylene and "
        "ethanol reached 60 and 25%, respectively."
    )

    results = link_faradaic_efficiencies(paper)

    for result in results:
        assert result["doi"] == "10.1234/test"
        assert result["source_provider"] == "OpenAlex"

        assert result["review_status"] == (
            "pending_human_review"
        )

        assert result["scientific_status"] == (
            "unverified_candidate"
        )

        assert result["conditions_verified"] is False

        start = result["source_start"]
        end = result["source_end"]

        assert paper["abstract"][start:end] == (
            result["exact_source_text"]
        )
