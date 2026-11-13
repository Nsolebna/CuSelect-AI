
# CuSelect-AI — Single-Product FE Tests
#
# PSEUDOCODE
# 1. Test ethylene FE extraction.
# 2. Test FE(C2H4) notation.
# 3. Test C2 product-class selectivity.
# 4. Reject comparative values.
# 5. Reject FE ratios and non-measurement numbers.
# 6. Preserve exact source text and provenance.
# 7. Reject ambiguous multi-product statements.

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.single_fe import extract_single_fe


def make_paper(abstract):
    return {
        "doi": "10.1234/test",
        "title": "CuAg electroreduction",
        "abstract": abstract,
        "abstract_source": "OpenAlex",
    }


def test_ethylene_fe():
    paper = make_paper(
        "The Faradaic efficiency for ethylene "
        "formation is enhanced to 42%, more than "
        "2 times that of pure Cu."
    )

    results = extract_single_fe(paper)

    assert len(results) == 1
    assert results[0]["product"] == "ethylene"
    assert results[0]["value"] == 42.0


def test_parenthesized_fe_formula():
    paper = make_paper(
        "The faradaic efficiency (FE C2H4 ) "
        "of 21.43% is higher than that of "
        "the reference catalyst (3.82%)."
    )

    results = extract_single_fe(paper)

    assert len(results) == 1
    assert results[0]["product"] == "ethylene"
    assert results[0]["value"] == 21.43


def test_c2_product_class():
    paper = make_paper(
        "The catalyst exhibits a Faradaic efficiency "
        "(FE) of 72.85% for C2 products."
    )

    results = extract_single_fe(paper)

    assert len(results) == 1
    assert results[0]["product"] == "c2_product_class"
    assert results[0]["value"] == 72.85


def test_multi_product_statement_is_not_guessed():
    paper = make_paper(
        "Faradaic efficiencies for ethylene and "
        "ethanol reached 60 and 25%, respectively."
    )

    assert extract_single_fe(paper) == []


def test_fe_ratio_not_treated_as_absolute_fe():
    paper = make_paper(
        "The ethanol/ethylene Faradaic efficiency "
        "ratio was 1.1 at −1.1 V vs RHE."
    )

    assert extract_single_fe(paper) == []


def test_nonmeasurement_numbers():
    paper = make_paper(
        "The Cu2O catalyst has Ag(111) facets "
        "and uses 3,5-diamino-1,2,4-triazole."
    )

    assert extract_single_fe(paper) == []


def test_provenance():
    paper = make_paper(
        "Faradaic efficiency for ethylene reached 42%."
    )

    result = extract_single_fe(paper)[0]

    assert result["doi"] == "10.1234/test"
    assert result["source_provider"] == "OpenAlex"
    assert result["review_status"] == "pending_human_review"
    assert result["conditions_verified"] is False

    start = result["source_start"]
    end = result["source_end"]

    assert paper["abstract"][start:end] == (
        result["exact_source_text"]
    )


def test_invalid_inputs():
    with pytest.raises(ValueError):
        extract_single_fe("invalid")

    with pytest.raises(ValueError):
        extract_single_fe({"doi": "", "abstract": "test"})
