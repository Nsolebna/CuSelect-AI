
# CuSelect-AI — Evidence Candidate Extraction Tests
#
# PSEUDOCODE
# 1. Detect Faradaic efficiency candidates.
# 2. Detect current density and potential.
# 3. Detect catalyst composition.
# 4. Preserve source sentences and DOI.
# 5. Avoid assigning ambiguous numbers to products.
# 6. Handle missing abstracts.
# 7. Verify deterministic evidence identifiers.
# 8. Reject invalid inputs.

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.evidence_candidates import (
    extract_evidence_candidates,
    extract_corpus_candidates,
)


def make_paper(abstract):
    return {
        "doi": "10.1234/example",
        "title": "CuAg electroreduction study",
        "abstract": abstract,
        "abstract_source": "OpenAlex",
    }


def test_faradaic_efficiency_candidate():
    paper = make_paper(
        "The Faradaic efficiency for ethylene "
        "reached 60%."
    )

    results = extract_evidence_candidates(paper)

    assert len(results) == 1

    candidate = results[0]

    assert "faradaic_efficiency" in (
        candidate["evidence_type_indicators"]
    )

    assert "ethylene" in candidate["product_mentions"]
    assert candidate["assigned_product"] is None
    assert candidate["measurement_value"] is None
    assert candidate["review_status"] == (
        "pending_human_review"
    )


def test_current_density_and_potential():
    paper = make_paper(
        "The cathode potential was −0.7 V vs RHE "
        "at a current density of −300 mA/cm2."
    )

    results = extract_evidence_candidates(paper)

    assert len(results) == 1

    types = results[0]["evidence_type_indicators"]

    assert "current_density" in types
    assert "electrode_potential" in types


def test_catalyst_composition():
    paper = make_paper(
        "The CuAg alloy contained 6% Ag."
    )

    results = extract_evidence_candidates(paper)

    assert len(results) == 1

    assert "catalyst_composition" in (
        results[0]["evidence_type_indicators"]
    )


def test_ambiguous_multi_product_statement():
    paper = make_paper(
        "Faradaic efficiencies for ethylene and "
        "ethanol reached 60% and 25%, respectively."
    )

    results = extract_evidence_candidates(paper)

    assert len(results) == 1

    candidate = results[0]

    assert "ethylene" in candidate["product_mentions"]
    assert "ethanol" in candidate["product_mentions"]

    assert candidate["assigned_product"] is None
    assert candidate["measurement_value"] is None
    assert candidate["conditions_verified"] is False


def test_missing_abstract():
    assert extract_evidence_candidates(
        make_paper("")
    ) == []


def test_exact_source_text():
    sentence = (
        "The Faradaic efficiency reached 58.5%."
    )

    results = extract_evidence_candidates(
        make_paper(sentence)
    )

    assert results[0]["exact_source_text"] == sentence
    assert results[0]["doi"] == "10.1234/example"
    assert results[0]["source_provider"] == "OpenAlex"


def test_deterministic_identifiers():
    paper = make_paper(
        "Faradaic efficiency reached 60%."
    )

    first = extract_evidence_candidates(paper)
    second = extract_evidence_candidates(paper)

    assert first == second


def test_duplicate_corpus_records():
    paper = make_paper(
        "Faradaic efficiency reached 60%."
    )

    results = extract_corpus_candidates(
        [paper, paper]
    )

    assert len(results) == 1


def test_invalid_input():
    with pytest.raises(ValueError):
        extract_evidence_candidates("invalid")

    with pytest.raises(ValueError):
        extract_corpus_candidates("invalid")

def test_potential_applications_not_voltage():
    # PSEUDOCODE
    # 1. Provide a sentence containing "potential applications".
    # 2. Confirm that it is not treated as a voltage measurement.

    paper = make_paper(
        "These materials have potential applications "
        "in CO2 reduction."
    )

    results = extract_evidence_candidates(paper)

    assert results == []