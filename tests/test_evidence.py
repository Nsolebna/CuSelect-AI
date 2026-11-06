"""Evidence-ledger invariants: no claim without traceable human review."""
from pathlib import Path
import pandas as pd
import pytest
from pydantic import ValidationError
from cuselect.evidence import (
    EvidenceClaim, normalize_doi, audit_seed_bibliography, title_similarity,
    verify_metadata, check_claim_links, claims_frame,
)

PAPERS = pd.read_csv(Path(__file__).resolve().parents[1] / "data" / "papers.csv")

def make_claim(**updates):
    values = dict(evidence_id="E-001", paper_id="P005", doi="10.1038/s41467-024-54636-w",
                  claim_paraphrase="Ag form is associated with different C2 product distributions.",
                  claim_type="experimental_observation", source_extent="abstract")
    values.update(updates)
    return EvidenceClaim(**values)

def test_doi_normalization():
    assert normalize_doi("https://doi.org/10.1038/S41467-024-54636-W") == "10.1038/s41467-024-54636-w"
    assert normalize_doi("doi:10.1002/anie.5598898") == "10.1002/anie.5598898"
    with pytest.raises(ValueError):
        normalize_doi("10.abc/nope")

def test_bibliography_syntax_is_not_content_verification():
    audit = audit_seed_bibliography(PAPERS)
    assert len(audit) == 8
    assert audit.doi_syntax_valid.all()
    assert not audit.duplicate_doi.any()
    assert set(audit.bibliographic_status) == {"seed_not_verified"}

def test_online_disabled_is_safe_and_honest():
    metadata = verify_metadata(PAPERS, online=False)
    assert set(metadata.metadata_status) == {"not_queried"}
    assert set(metadata.claim_review_status) == {"not_started"}

def test_title_similarity_aids_review_only():
    assert title_similarity("Copper catalyst CO2", "Copper catalyst CO₂") > .80

def test_fe_requires_product_and_valid_range():
    with pytest.raises(ValidationError):
        make_claim(faradaic_efficiency_percent=90)
    with pytest.raises(ValidationError):
        make_claim(faradaic_efficiency_percent=101, fe_product="C2+")
    assert make_claim(faradaic_efficiency_percent=80, fe_product="C2+").fe_product == "C2+"

def test_claim_cannot_self_promote():
    with pytest.raises(ValidationError):
        make_claim(review_status="human_verified")
    record = make_claim(review_status="human_verified", source_checked_by_human=True,
                        exact_source_location="Abstract", reviewer_note="Checked against journal page")
    assert record.review_status == "human_verified"

def test_publication_holdout_group():
    assert make_claim().split_group == "10.1038/s41467-024-54636-w"
    with pytest.raises(ValidationError):
        make_claim(split_group="some_random_row")

def test_source_links_and_zero_claim_schema():
    claim = make_claim()
    check_claim_links([claim], PAPERS)
    assert list(claims_frame([]).columns) == list(EvidenceClaim.model_fields)
    with pytest.raises(ValueError):
        check_claim_links([claim, claim], PAPERS)
    with pytest.raises(ValueError):
        check_claim_links([make_claim(doi="10.1002/anie.202524612")], PAPERS)


def test_placeholder_source_location_cannot_be_approved():
    with pytest.raises(ValidationError):
        make_claim(review_status="human_verified", source_checked_by_human=True,
                   exact_source_location="Abstract (confirm independently)",
                   reviewer_note="Reviewed")


def test_crossref_mocked_metadata_match(monkeypatch):
    import cuselect.evidence as m
    def fake_lookup(doi):
        assert doi == "10.1038/s41467-024-54636-w"
        return {"doi":doi,"title":PAPERS.loc[PAPERS.paper_id=="P005","title"].iloc[0],
                "publisher":"Nature","journal":"Nature Communications","published_years":[2024],
                "license_metadata_present":True}
    monkeypatch.setattr(m, "crossref_lookup", fake_lookup)
    result = verify_metadata(PAPERS[PAPERS.paper_id=="P005"], online=True)
    assert result.iloc[0].metadata_status == "matching_metadata_needs_manual_review"
    assert result.iloc[0].claim_review_status == "not_started"


def test_failed_crossref_lookup_is_not_verification(monkeypatch):
    import cuselect.evidence as m
    def offline(doi):
        raise OSError("temporary network failure")
    monkeypatch.setattr(m, "crossref_lookup", offline)
    result = verify_metadata(PAPERS[PAPERS.paper_id=="P005"], online=True)
    assert result.iloc[0].metadata_status == "lookup_failed_not_verified"
