
# CuSelect-AI — Scientific Relevance Tests
#
# PSEUDOCODE
# 1. Test Cu/Ag ethylene classification.
# 2. Test other C2+ product classification.
# 3. Test mechanistic relevance.
# 4. Test broader scientific background.
# 5. Test insufficient information.
# 6. Confirm preservation of metadata and deduplication.
# 7. Confirm all classifications remain unverified.

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.relevance import (
    classify_relevance,
    classify_publications,
)


@pytest.mark.parametrize(
    "title, expected",
    [
        (
            "Silver/Copper Interface for Relay "
            "Electroreduction of Carbon Dioxide to Ethylene",
            "direct_ethylene",
        ),
        (
            "Copper Silver Catalysts for CO2 "
            "Electroreduction to Ethanol",
            "other_c2_products",
        ),
        (
            "Cu2O-Ag Tandem Catalysts for Selective "
            "Electrochemical Reduction of CO2 to C2 Products",
            "other_c2_products",
        ),
        (
            "Copper Silver Electrocatalysts for "
            "CO2 Reduction to C2+ Products",
            "other_c2_products",
        ),
        (
            "Silver Copper Tandem Electrocatalysis "
            "for CO2 Reduction to CO",
            "mechanistic_support",
        ),
        (
            "Copper Electrocatalysts for "
            "CO2 Reduction",
            "background",
        ),
        (
            "Advanced Nanomaterials for "
            "Environmental Applications",
            "insufficient_information",
        ),
    ],
)
def test_relevance_classification(title, expected):
    paper = {
        "doi": "10.1234/example",
        "title": title,
    }

    result = classify_relevance(paper)

    assert result["relevance_category"] == expected

    assert result["scientific_status"] == (
        "unverified_discovery"
    )

    assert result["classification_source"] == "title_only"

    assert result["requires_human_review"] is True


def test_missing_title():
    result = classify_relevance({
        "doi": "10.1234/empty",
        "title": "",
    })

    assert (
        result["relevance_category"]
        == "insufficient_information"
    )


def test_publication_deduplication():
    papers = [
        {
            "doi": "10.1234/ABC",
            "title": (
                "Silver Copper Electrocatalysis "
                "for CO2 Reduction to Ethylene"
            ),
            "journal": "Example Journal",
        },
        {
            "doi": "10.1234/abc",
            "title": "Duplicate Publication",
        },
    ]

    results = classify_publications(papers)

    assert len(results) == 1
    assert results[0]["doi"] == "10.1234/abc"

    assert results[0]["journal"] == "Example Journal"

    assert (
        results[0]["relevance_category"]
        == "direct_ethylene"
    )
