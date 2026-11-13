
# CuSelect-AI — Measurement Context Tests
#
# PSEUDOCODE
# 1. Test FE and operating conditions in one sentence.
# 2. Verify signed potential and current-density values.
# 3. Preserve reference electrode and Ag composition.
# 4. Avoid linking conditions from other sentences.
# 5. Reject conflicting potential values.
# 6. Reject mismatched DOIs.
# 7. Preserve unverified scientific status.

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.measurement_linking import (
    link_faradaic_efficiencies,
)

from cuselect.measurement_context import (
    link_measurement_context,
    link_corpus_context,
)


def make_paper(abstract):
    return {
        "doi": "10.1234/test",
        "title": "CuAg alloy catalyst",
        "abstract": abstract,
        "abstract_source": "OpenAlex",
    }


def make_linked_measurement(abstract):
    paper = make_paper(abstract)

    measurements = link_faradaic_efficiencies(paper)

    assert len(measurements) == 2

    return paper, measurements


def test_full_measurement_context():
    abstract = (
        "The alloy containing 6% Ag exhibits "
        "Faradaic efficiency for C 2 H 4 and "
        "C 2 H 5 OH production reaching nearly "
        "60 and 25%, respectively, at a cathode "
        "potential of −0.7 V vs RHE and a total "
        "current density of ∼ – 300 mA/cm 2."
    )

    paper, measurements = make_linked_measurement(
        abstract
    )

    results = link_corpus_context(
        measurements, [paper]
    )

    assert len(results) == 2

    for result in results:
        assert result["potential_v"] == -0.7
        assert result["reference_electrode"] == "RHE"

        assert result["current_density_ma_cm2"] == -300
        assert result["current_density_type"] == "total"

        assert result["ag_content_percent"] == 6.0
        assert result["ag_percentage_basis"] == "unknown"

        assert result["context_link_status"] == (
            "same_sentence_candidates"
        )

        assert result["conditions_verified"] is False


def test_conditions_not_transferred_between_sentences():
    abstract = (
        "Faradaic efficiencies for ethylene and "
        "ethanol reached 60 and 25%, respectively. "
        "A different electrode was operated at "
        "−1.2 V vs RHE."
    )

    paper, measurements = make_linked_measurement(
        abstract
    )

    result = link_measurement_context(
        measurements[0], paper
    )

    assert result["potential_v"] is None
    assert result["context_link_status"] == (
        "no_explicit_conditions"
    )


def test_multiple_potentials_are_ambiguous():
    abstract = (
        "Faradaic efficiencies for ethylene and "
        "ethanol reached 60 and 25%, respectively, "
        "at −0.7 V vs RHE and −1.0 V vs RHE."
    )

    paper, measurements = make_linked_measurement(
        abstract
    )

    result = link_measurement_context(
        measurements[0], paper
    )

    assert result["potential_v"] is None
    assert result["context_link_status"] == (
        "ambiguous_context"
    )


def test_doi_mismatch_is_rejected():
    paper, measurements = make_linked_measurement(
        "Faradaic efficiencies for ethylene and "
        "ethanol reached 60 and 25%, respectively."
    )

    paper["doi"] = "10.1234/different"

    with pytest.raises(ValueError):
        link_measurement_context(
            measurements[0], paper
        )


def test_invalid_source_offsets():
    paper, measurements = make_linked_measurement(
        "Faradaic efficiencies for ethylene and "
        "ethanol reached 60 and 25%, respectively."
    )

    measurement = dict(measurements[0])
    measurement["source_start"] = 9999

    result = link_measurement_context(
        measurement, paper
    )

    assert result["context_link_status"] == (
        "source_not_located"
    )
    assert result["potential_v"] is None


def test_original_measurement_is_preserved():
    paper, measurements = make_linked_measurement(
        "Faradaic efficiencies for ethylene and "
        "ethanol reached 60 and 25%, respectively."
    )

    original = dict(measurements[0])

    result = link_measurement_context(
        measurements[0], paper
    )

    assert measurements[0] == original
    assert result["value"] == original["value"]
    assert result["product"] == original["product"]
    assert result["measurement_id"] == (
        original["measurement_id"]
    )

    assert result["review_status"] == (
        "pending_human_review"
    )
    assert result["conditions_verified"] is False
