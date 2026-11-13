
# CuSelect-AI — Abstract Screening Tests
#
# PSEUDOCODE
# 1. Test experimental terminology.
# 2. Test computational terminology.
# 3. Test mixed-method indicators.
# 4. Test product and architecture identification.
# 5. Test missing abstract handling.
# 6. Test source and DOI preservation.
# 7. Confirm results remain unverified.

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.abstract_screening import (
    screen_abstract,
    screen_publications,
)


def make_paper(abstract):
    return {
        "doi": "10.1234/example",
        "title": "CuAg CO2 electroreduction",
        "abstract": abstract,
        "abstract_source": "OpenAlex",
        "scientific_status": "unverified_discovery",
    }


def test_experimental_indicators():
    paper = make_paper(
        "CuAg alloys prepared by electrodeposition "
        "produced ethylene and ethanol. "
        "Faradaic efficiency was measured using "
        "electrolysis and Raman spectroscopy."
    )

    result = screen_abstract(paper)

    assert result["study_type_indicator"] == (
        "experimental_indicators"
    )

    assert "ethylene" in result["product_indicators"]
    assert "ethanol" in result["product_indicators"]
    assert "alloy" in result["architecture_indicators"]


def test_computational_indicators():
    paper = make_paper(
        "Density functional theory calculations "
        "investigated CO adsorption on a CuAg interface."
    )

    result = screen_abstract(paper)

    assert result["study_type_indicator"] == (
        "computational_indicators"
    )

    assert "adsorption" in result["mechanism_indicators"]


def test_mixed_indicators():
    paper = make_paper(
        "Raman spectroscopy and DFT calculations "
        "were used to investigate a tandem catalyst."
    )

    result = screen_abstract(paper)

    assert result["study_type_indicator"] == (
        "mixed_indicators"
    )

    assert "tandem" in result["architecture_indicators"]


def test_missing_abstract():
    result = screen_abstract(make_paper(""))

    assert result["abstract_screening_status"] == (
        "abstract_unavailable"
    )

    assert result["study_type_indicator"] == "unknown"
    assert result["product_indicators"] == []


def test_provenance_is_preserved():
    result = screen_abstract(
        make_paper("Electrodeposition of CuAg alloys.")
    )

    assert result["doi"] == "10.1234/example"
    assert result["abstract_source"] == "OpenAlex"
    assert result["scientific_status"] == (
        "unverified_discovery"
    )
    assert result["requires_human_review"] is True


def test_multiple_publications():
    papers = [
        make_paper("Raman spectroscopy of CuAg."),
        make_paper("DFT study of CO adsorption."),
    ]

    results = screen_publications(papers)

    assert len(results) == 2
    assert all(
        paper["abstract_screening_status"] == "screened"
        for paper in results
    )


def test_invalid_input():
    with pytest.raises(ValueError):
        screen_abstract("not a dictionary")


def test_spaced_chemical_formulas():
    # PSEUDOCODE
    # 1. Simulate an abstract containing spaced formulas.
    # 2. Screen the abstract.
    # 3. Verify ethylene and ethanol are detected.

    paper = make_paper(
        "The Faradaic efficiency for C 2 H 4 "
        "and C 2 H 5 OH reached 60 and 25%, "
        "respectively."
    )

    result = screen_abstract(paper)

    assert "ethylene" in result["product_indicators"]
    assert "ethanol" in result["product_indicators"]
