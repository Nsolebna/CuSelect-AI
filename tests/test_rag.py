
# CuSelect-AI — Phase II
# Tests: tests/test_rag.py
#
# PSEUDOCODE
# 1. Load the existing human-reviewed RAG snapshot.
# 2. Verify chemical-text normalization.
# 3. Verify retrieval finds relevant evidence.
# 4. Verify evidence identifiers and metadata are preserved.
# 5. Verify deterministic ranking and tie-breaking.
# 6. Verify unsupported queries return no matches.
# 7. Verify invalid retrieval limits are rejected.

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.rag import lexical_tokens, lexical_retrieve


@pytest.fixture
def verified_records():
    path = (
        ROOT
        / "data/processed/06_rag_prototype"
        / "06_retrieval_corpus.jsonl"
    )

    records = [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]

    assert len(records) == 3
    assert all(
        record["review_status"] == "human_verified"
        for record in records
    )

    return records


def test_chemical_notation_normalization():
    assert lexical_tokens("CO₂ electroreduction") == [
        "co2",
        "electroreduction",
    ]
    assert lexical_tokens("CO₂") == lexical_tokens("CO2")


def test_retrieval_finds_ethanol_evidence(verified_records):
    results = lexical_retrieve(
        "ethanol faradaic efficiency",
        verified_records,
        top_k=3,
    )

    ids = [result["evidence_id"] for result in results]

    assert "E-P005-FE-ETOH-001" in ids


def test_retrieval_preserves_source_metadata(verified_records):
    results = lexical_retrieve(
        "ethylene",
        verified_records,
    )

    original = {
        record["evidence_id"]: record
        for record in verified_records
    }

    assert results

    for result in results:
        evidence_id = result["evidence_id"]
        assert result["record"] == original[evidence_id]
        assert result["record"]["doi"]
        assert result["record"]["source_location"]


def test_retrieval_is_deterministic(verified_records):
    first = lexical_retrieve(
        "Cu Ag ethanol ethylene",
        verified_records,
    )

    second = lexical_retrieve(
        "Cu Ag ethanol ethylene",
        verified_records,
    )

    assert first == second


def test_unsupported_query_has_no_matches(verified_records):
    results = lexical_retrieve(
        "zzzxxyy unsupportedkeyword",
        verified_records,
    )

    assert results == []


def test_empty_corpus_returns_no_matches():
    assert lexical_retrieve("ethylene", []) == []


def test_equal_scores_use_evidence_id_tiebreak():
    records = [
        {"evidence_id": "E-B", "text": "copper"},
        {"evidence_id": "E-A", "text": "copper"},
    ]

    results = lexical_retrieve(
        "copper",
        records,
    )

    assert [r["evidence_id"] for r in results] == [
        "E-A",
        "E-B",
    ]


@pytest.mark.parametrize("top_k", [0, -1, True, 2.5])
def test_invalid_top_k_is_rejected(top_k):
    with pytest.raises(ValueError):
        lexical_retrieve(
            "ethylene",
            [{"evidence_id": "E-1", "text": "ethylene"}],
            top_k=top_k,
        )


# PSEUDOCODE
# 1. Check correct product-specific FE retrieval.
# 2. Ensure unsupported durability claims are rejected.
# 3. Ensure unsupported catalyst rankings are rejected.
# 4. Ensure non-reviewed records cannot enter answers.
# 5. Preserve existing retrieval tests.

from cuselect.rag import answer_from_verified


def test_answer_ethylene_fe(verified_records):
    result = answer_from_verified(
        "What ethylene Faradaic efficiency was reported?",
        verified_records,
    )

    assert result["decision"] == "evidence_found"
    assert "E-P005-FE-C2H4-001" in result["cited_ids"]
    assert "E-P005-FE-ETOH-001" not in result["cited_ids"]


def test_answer_ethanol_fe(verified_records):
    result = answer_from_verified(
        "What ethanol FE was reported?",
        verified_records,
    )

    assert result["decision"] == "evidence_found"
    assert "E-P005-FE-ETOH-001" in result["cited_ids"]
    assert "E-P005-FE-C2H4-001" not in result["cited_ids"]


def test_durability_question_abstains(verified_records):
    result = answer_from_verified(
        "What is the 100-hour durability of AgCu NW?",
        verified_records,
    )

    assert result["decision"] == "abstain"
    assert result["cited_ids"] == []


def test_ranking_question_abstains(verified_records):
    result = answer_from_verified(
        "Which catalyst is best for ethylene?",
        verified_records,
    )

    assert result["decision"] == "abstain"
    assert result["cited_ids"] == []


def test_unreviewed_records_are_excluded(verified_records):
    unreviewed = [
        {**record, "review_status": "pending_review"}
        for record in verified_records
    ]

    result = answer_from_verified(
        "What ethylene FE was reported?",
        unreviewed,
    )

    assert result["decision"] == "abstain"
    assert result["cited_ids"] == []


# PSEUDOCODE
# 1. Accept a valid source-grounded answer.
# 2. Reject fabricated citations and modified FE values.
# 3. Reject modified DOI and retrieved-record metadata.
# 4. Reject added unsupported scientific statements.
# 5. Accept legitimate abstention but reject fabricated abstentions.

from copy import deepcopy

from cuselect.rag import verify_extractive_answer


def _sample_verified_answer(records):
    return answer_from_verified(
        "What ethylene Faradaic efficiency was reported?",
        records,
    )


def test_audit_accepts_valid_response(verified_records):
    result = _sample_verified_answer(verified_records)

    assert verify_extractive_answer(result, verified_records)


def test_audit_rejects_forged_citation(verified_records):
    result = _sample_verified_answer(verified_records)

    result["answer"] = result["answer"].replace(
        "[E-P005-FE-C2H4-001]",
        "[E-FAKE-001]",
    )

    assert not verify_extractive_answer(result, verified_records)


def test_audit_rejects_modified_fe(verified_records):
    result = _sample_verified_answer(verified_records)

    result["answer"] = result["answer"].replace(
        "FE: 54.9%",
        "FE: 99.9%",
    )

    assert not verify_extractive_answer(result, verified_records)


def test_audit_rejects_modified_doi(verified_records):
    result = _sample_verified_answer(verified_records)

    result["answer"] = result["answer"].replace(
        "DOI: ",
        "DOI: 10.0000/fake/",
    )

    assert not verify_extractive_answer(result, verified_records)


def test_audit_rejects_modified_hit(verified_records):
    result = deepcopy(
        _sample_verified_answer(verified_records)
    )

    result["hits"][0]["record"]["doi"] = "10.0000/fake"

    assert not verify_extractive_answer(result, verified_records)


def test_audit_rejects_added_claim(verified_records):
    result = _sample_verified_answer(verified_records)

    result["answer"] += (
        "\nThis catalyst has proven commercial durability."
    )

    assert not verify_extractive_answer(result, verified_records)


def test_audit_accepts_abstention(verified_records):
    result = answer_from_verified(
        "What is the 100-hour durability of AgCu NW?",
        verified_records,
    )

    assert result["decision"] == "abstain"
    assert verify_extractive_answer(result, verified_records)


def test_audit_rejects_forged_abstention(verified_records):
    result = answer_from_verified(
        "What is the 100-hour durability of AgCu NW?",
        verified_records,
    )

    result["answer"] = "Verified result [E-DRAFT-001]"

    assert not verify_extractive_answer(result, verified_records)


# PSEUDOCODE
# 1. Confirm the service returns cited evidence.
# 2. Confirm unsupported questions still abstain.
# 3. Confirm verification failures prevent answers.

import cuselect.rag as rag_module
from cuselect.rag import run_rag_question


def test_rag_service_returns_verified_extract(verified_records):
    response = run_rag_question(
        "What ethylene Faradaic efficiency was reported?",
        verified_records,
    )

    assert response["decision"] == "evidence_found"
    assert response["citation_audit_passed"] is True
    assert response["cited_ids"] == ["E-P005-FE-C2H4-001"]
    assert response["generation_mode"] == "deterministic_extractive"


def test_rag_service_abstains(verified_records):
    response = run_rag_question(
        "What is the 100-hour durability of AgCu NW?",
        verified_records,
    )

    assert response["decision"] == "abstain"
    assert response["cited_ids"] == []
    assert response["citation_audit_passed"] is True


def test_rag_service_fails_closed(monkeypatch, verified_records):
    monkeypatch.setattr(
        rag_module,
        "verify_extractive_answer",
        lambda result, records: False,
    )

    with pytest.raises(RuntimeError):
        run_rag_question(
            "What ethylene FE was reported?",
            verified_records,
        )
