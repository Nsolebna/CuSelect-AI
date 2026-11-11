"""Tests for read-only scientific evidence promotion."""

from cuselect.evidence_promotion import assess_promotion


def sample_claim():
    return {
        "evidence_id": "E-TEST-001",
        "paper_id": "P001",
        "doi": "10.1234/example",
        "claim_paraphrase": "Ethylene production was observed experimentally.",
        "claim_type": "experimental_observation",
        "source_extent": "full_text",
        "exact_source_location": "Figure 3, page 5",
        "catalyst_system": "Cu",
        "target_or_observation": "Ethylene production",
        "conditions": "Reported experimental conditions",
        "review_status": "pending_source_review",
    }


def sample_review():
    return {
        "evidence_id": "E-TEST-001",
        "doi": "10.1234/example",
        "status": "source_checked",
        "confirmed": True,
        "reviewer_email": "reviewer@example.org",
        "reviewed_at": "2026-11-11T10:00:00+00:00",
        "source_location": "Figure 3, page 5",
        "source_excerpt": (
            "The original publication reports the experimental "
            "observation of ethylene production using this catalyst."
        ),
    }


def test_matching_review_is_eligible_for_human_approval():
    result = assess_promotion(sample_claim(), sample_review())
    assert result["eligible_for_human_approval"] is True
    assert result["scientifically_verified"] is False
    assert result["rag_ingestion_status"] == "not_ingested"


def test_doi_only_review_cannot_authorize_a_claim():
    review = sample_review()
    del review["evidence_id"]

    result = assess_promotion(sample_claim(), review)

    assert result["eligible_for_human_approval"] is False
    assert "claim_identity_mismatch" in result["reasons"]


def test_unconfirmed_review_is_blocked():
    review = sample_review()
    review["confirmed"] = False

    result = assess_promotion(sample_claim(), review)

    assert result["eligible_for_human_approval"] is False
    assert "human_confirmation_missing" in result["reasons"]


def test_multiple_passages_have_distinct_identifiers():
    from cuselect.evidence_promotion import identify_candidate_passages

    candidate = {
        "doi": "10.1234/example",
        "candidate_passages": [
            {
                "source_excerpt": "Ethylene was detected.",
                "source_location": "abstract:1",
                "verified": False,
            },
            {
                "source_excerpt": "Ethanol was detected.",
                "source_location": "abstract:2",
                "verified": False,
            },
        ],
    }

    result = identify_candidate_passages(candidate)

    assert len(result) == 2
    assert result[0]["evidence_id"] != result[1]["evidence_id"]
    assert result[0]["scientific_status"] == "unverified_candidate"
    assert result[1]["scientific_status"] == "unverified_candidate"

    assert "evidence_id" not in candidate["candidate_passages"][0]


def test_passage_identifiers_are_deterministic():
    from cuselect.evidence_promotion import identify_candidate_passages

    candidate = {
        "doi": "10.1234/example",
        "candidate_passages": [
            {
                "source_excerpt": "A reported experimental observation.",
                "source_location": "abstract:1",
            }
        ],
    }

    first = identify_candidate_passages(candidate)
    second = identify_candidate_passages(candidate)

    assert first == second


def test_changed_source_produces_different_identifier():
    from cuselect.evidence_promotion import identify_candidate_passages

    candidate = {
        "doi": "10.1234/example",
        "candidate_passages": [
            {
                "source_excerpt": "Original experimental observation.",
                "source_location": "abstract:1",
            }
        ],
    }

    original = identify_candidate_passages(candidate)[0]["evidence_id"]

    candidate["candidate_passages"][0][
        "source_excerpt"
    ] = "Revised experimental observation."

    revised = identify_candidate_passages(candidate)[0]["evidence_id"]

    assert original != revised


def test_one_passage_review_does_not_authorize_another():
    from cuselect.evidence_promotion import get_passage_review

    first = {"evidence_id": "E-001", "doi": "10.1234/example"}
    second = {"evidence_id": "E-002", "doi": "10.1234/example"}

    reviews = {
        "E-001": {
            "evidence_id": "E-001",
            "doi": "10.1234/example",
            "status": "source_checked",
        }
    }

    assert get_passage_review(first, reviews) is not None
    assert get_passage_review(second, reviews) is None


def test_legacy_doi_review_cannot_authorize_passage():
    from cuselect.evidence_promotion import get_passage_review

    passage = {
        "evidence_id": "E-001",
        "doi": "10.1234/example",
    }

    legacy_reviews = {
        "10.1234/example": {"status": "source_checked"}
    }

    assert get_passage_review(passage, legacy_reviews) is None


def test_mismatched_doi_blocks_review_lookup():
    from cuselect.evidence_promotion import get_passage_review

    passage = {
        "evidence_id": "E-001",
        "doi": "10.1234/example",
    }

    reviews = {
        "E-001": {
            "evidence_id": "E-001",
            "doi": "10.5678/another",
            "status": "source_checked",
        }
    }

    assert get_passage_review(passage, reviews) is None


def test_claim_review_preserves_individual_identity():
    from cuselect.evidence_promotion import prepare_claim_review

    passage = {
        "evidence_id": "E-001",
        "doi": "10.1234/example",
    }

    review = prepare_claim_review(
        passage,
        decision="needs_full_text",
        reviewer_email="scientist@example.org",
    )

    assert review["evidence_id"] == "E-001"
    assert review["status"] == "needs_full_text"
    assert review["rag_ingestion_status"] == "not_ingested"


def test_source_checked_requires_confirmation():
    from cuselect.evidence_promotion import prepare_claim_review
    import pytest

    passage = {
        "evidence_id": "E-001",
        "doi": "10.1234/example",
    }

    with pytest.raises(ValueError):
        prepare_claim_review(
            passage,
            decision="source_checked",
            reviewer_email="scientist@example.org",
            source_location="Figure 2",
            source_excerpt="This publication reports experimental results for the studied copper catalyst.",
            confirmed=False,
        )


def test_source_checked_requires_supporting_excerpt():
    from cuselect.evidence_promotion import prepare_claim_review
    import pytest

    passage = {
        "evidence_id": "E-001",
        "doi": "10.1234/example",
    }

    with pytest.raises(ValueError):
        prepare_claim_review(
            passage,
            decision="source_checked",
            reviewer_email="scientist@example.org",
            source_location="Figure 2",
            source_excerpt="",
            confirmed=True,
        )


def test_claim_review_persists_independently(tmp_path):
    import json
    from cuselect.evidence_promotion import (
        prepare_claim_review,
        save_claim_review,
    )

    first = prepare_claim_review(
        {"evidence_id": "E-001", "doi": "10.1234/example"},
        "needs_full_text",
        "scientist@example.org",
    )

    second = prepare_claim_review(
        {"evidence_id": "E-002", "doi": "10.1234/example"},
        "needs_full_text",
        "scientist@example.org",
    )

    save_claim_review(tmp_path, first, "scientist@example.org")
    save_claim_review(tmp_path, second, "scientist@example.org")

    path = tmp_path / "data/evidence_claim_reviews.json"
    ledger = json.loads(path.read_text())

    assert set(ledger) == {"E-001", "E-002"}
    assert ledger["E-001"]["status"] == "needs_full_text"
    assert ledger["E-002"]["status"] == "needs_full_text"


def test_review_history_is_preserved(tmp_path):
    import json
    from cuselect.evidence_promotion import save_claim_review

    original = {
        "evidence_id": "E-001",
        "doi": "10.1234/example",
        "status": "needs_full_text",
        "reviewer_email": "scientist@example.org",
    }

    revised = {
        **original,
        "status": "rejected",
    }

    save_claim_review(tmp_path, original, "scientist@example.org")
    save_claim_review(tmp_path, revised, "scientist@example.org")

    path = tmp_path / "data/evidence_claim_reviews.json"
    record = json.loads(path.read_text())["E-001"]

    assert record["status"] == "rejected"
    assert len(record["history"]) == 1
    assert record["history"][0]["status"] == "needs_full_text"


def test_unauthorized_reviewer_cannot_save(tmp_path):
    import pytest
    from cuselect.evidence_promotion import save_claim_review

    review = {
        "evidence_id": "E-001",
        "doi": "10.1234/example",
        "status": "needs_full_text",
        "reviewer_email": "scientist@example.org",
    }

    with pytest.raises(PermissionError):
        save_claim_review(
            tmp_path,
            review,
            "another@example.org",
        )

    assert not (
        tmp_path / "data/evidence_claim_reviews.json"
    ).exists()


def test_direct_save_rejects_unconfirmed_source(tmp_path):
    import pytest
    from cuselect.evidence_promotion import save_claim_review

    review = {
        "evidence_id": "E-001",
        "doi": "10.1234/example",
        "status": "source_checked",
        "reviewer_email": "scientist@example.org",
        "source_location": "Figure 2",
        "source_excerpt": "The publication reports experimental results.",
        "confirmed": False,
    }

    with pytest.raises(ValueError):
        save_claim_review(
            tmp_path, review, "scientist@example.org"
        )

    assert not (
        tmp_path / "data/evidence_claim_reviews.json"
    ).exists()


def test_direct_save_rejects_abstract_only_source(tmp_path):
    import pytest
    from cuselect.evidence_promotion import save_claim_review

    review = {
        "evidence_id": "E-001",
        "doi": "10.1234/example",
        "status": "source_checked",
        "reviewer_email": "scientist@example.org",
        "source_location": "abstract",
        "source_excerpt": (
            "The authors report ethylene production under "
            "the investigated electrochemical reaction conditions."
        ),
        "confirmed": True,
    }

    with pytest.raises(ValueError):
        save_claim_review(
            tmp_path, review, "scientist@example.org"
        )


def test_direct_save_cannot_set_rag_approval(tmp_path):
    from cuselect.evidence_promotion import save_claim_review

    review = {
        "evidence_id": "E-001",
        "doi": "10.1234/example",
        "status": "needs_full_text",
        "reviewer_email": "scientist@example.org",
        "scientific_status": "human_verified",
        "rag_ingestion_status": "approved",
    }

    result = save_claim_review(
        tmp_path, review, "scientist@example.org"
    )

    assert result["scientific_status"] == "pending_approval"
    assert result["rag_ingestion_status"] == "not_ingested"


def test_original_passage_identity_is_verified(tmp_path):
    import json
    from cuselect.evidence_promotion import (
        identify_candidate_passages,
        verify_candidate_identity,
    )

    candidate = {
        "doi": "10.1234/example",
        "candidate_passages": [{
            "source_excerpt": "The experiment produced ethylene.",
            "source_location": "abstract:1",
        }],
    }

    folder = tmp_path / "data"
    folder.mkdir()
    (folder / "evidence_extraction_candidates.json").write_text(
        json.dumps([candidate]), encoding="utf-8"
    )

    passage = identify_candidate_passages(candidate)[0]

    assert verify_candidate_identity(tmp_path, passage)

    modified = dict(passage)
    modified["source_excerpt"] = "Altered scientific claim."

    assert not verify_candidate_identity(tmp_path, modified)


def test_unknown_passage_cannot_match_extraction(tmp_path):
    from cuselect.evidence_promotion import verify_candidate_identity

    fabricated = {
        "evidence_id": "E-FAKE",
        "doi": "10.1234/example",
        "source_excerpt": "Unverified measurement.",
        "source_location": "Figure 2",
    }

    assert not verify_candidate_identity(tmp_path, fabricated)


def test_verified_passage_can_be_submitted(tmp_path):
    import json
    from cuselect.evidence_promotion import (
        identify_candidate_passages,
        submit_claim_review,
    )

    candidate = {
        "doi": "10.1234/example",
        "candidate_passages": [{
            "source_excerpt": "Ethylene production was observed.",
            "source_location": "abstract:1",
        }],
    }

    folder = tmp_path / "data"
    folder.mkdir()

    (folder / "evidence_extraction_candidates.json").write_text(
        json.dumps([candidate]), encoding="utf-8"
    )

    passage = identify_candidate_passages(candidate)[0]

    saved = submit_claim_review(
        tmp_path,
        passage,
        "needs_full_text",
        "scientist@example.org",
    )

    assert saved["evidence_id"] == passage["evidence_id"]
    assert saved["rag_ingestion_status"] == "not_ingested"


def test_fabricated_passage_cannot_be_submitted(tmp_path):
    import pytest
    from cuselect.evidence_promotion import submit_claim_review

    fabricated = {
        "evidence_id": "E-FABRICATED",
        "doi": "10.1234/example",
        "source_excerpt": "Unsupported scientific claim.",
        "source_location": "Figure 2",
    }

    with pytest.raises(ValueError):
        submit_claim_review(
            tmp_path,
            fabricated,
            "needs_full_text",
            "scientist@example.org",
        )

    assert not (
        tmp_path / "data/evidence_claim_reviews.json"
    ).exists()
