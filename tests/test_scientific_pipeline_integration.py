"""End-to-end experimental scientific RAG tests."""

import hashlib
import json

import pytest

from cuselect.scientific_rag_pipeline import (
    build_experimental_index,
    retrieve_scientific_evidence,
)
from cuselect.scientific_promotion import REQUIRED_CHECKS


def make_test_package():
    """Create a clearly synthetic approval fixture."""

    claim = {
        "evidence_id": "E-SYNTHETIC-001",
        "paper_id": "P-SYNTHETIC",
        "doi": "10.1234/synthetic",
        "claim_paraphrase": (
            "Synthetic HOH Cu/Ag achieved 60.37% "
            "ethylene FE at -1.3 V vs RHE."
        ),
        "claim_type": "experimental_observation",
        "source_extent": "full_text",
        "exact_source_location": "Synthetic Results, Figure 4d",
        "catalyst_system": "Synthetic HOH Cu/Ag",
        "target_or_observation": "ethylene",
        "conditions": "Synthetic flow-cell conditions",
        "review_status": "pending_source_review",
        "source_checked_by_human": False,
    }

    review = {
        "claim_id": claim["evidence_id"],
        "paper_id": claim["paper_id"],
        "doi": claim["doi"],
        "decision": "approve",
        "reviewer": "synthetic-reviewer@example.org",
        "timestamp": "2026-11-11T12:00:00+00:00",
        "reviewer_note": "Synthetic integration test only",
        "checks": {
            key: True for key in REQUIRED_CHECKS
        },
        "source_xml_sha256": "a" * 64,
        "claim_sha256": "b" * 64,
        "dossier_sha256": "c" * 64,
        "promotion_status": "pending_controlled_promotion",
        "rag_ingestion_status": "not_ingested",
    }

    payload = {
        "schema_version": "1.0",
        "evidence_id": claim["evidence_id"],
        "paper_id": claim["paper_id"],
        "doi": claim["doi"],
        "claim": claim,
        "review": review,
        "source_sha256": review["source_xml_sha256"],
    }

    digest = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    return {
        "package_type": "scientific_evidence",
        "package_version": digest[:16],
        "payload_sha256": digest,
        "payload": payload,
    }


def test_end_to_end_retrieval():
    package = make_test_package()

    result = retrieve_scientific_evidence(
        [package],
        "HOH Cu/Ag ethylene 60.37% at -1.3 V",
    )

    assert result["status"] == "evidence_retrieved"
    assert len(result["results"]) == 1

    citation = result["results"][0]["citation"]

    assert citation["evidence_id"] == "E-SYNTHETIC-001"
    assert citation["doi"] == "10.1234/synthetic"
    assert citation["paper_id"] == "P-SYNTHETIC"

    assert result["generated_scientific_answer"] is None


def test_unsupported_number_abstains():
    result = retrieve_scientific_evidence(
        [make_test_package()],
        "HOH Cu/Ag ethylene 95% at -1.3 V",
    )

    assert result["status"] == "insufficient_evidence"
    assert result["results"] == []


def test_tampered_package_is_rejected():
    package = make_test_package()

    package["payload"]["claim"]["catalyst_system"] = (
        "Different catalyst"
    )

    with pytest.raises(ValueError, match="hash mismatch"):
        build_experimental_index([package])


def test_rejected_evidence_cannot_be_indexed():
    package = make_test_package()
    package["payload"]["review"]["decision"] = "reject"

    # Even when the package checksum is recalculated,
    # the scientific decision must remain a rejection.
    digest = hashlib.sha256(
        json.dumps(
            package["payload"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    package["payload_sha256"] = digest
    package["package_version"] = digest[:16]

    with pytest.raises(ValueError, match="not approved"):
        build_experimental_index([package])


def test_duplicate_documents_are_rejected():
    package = make_test_package()

    with pytest.raises(ValueError, match="Duplicate"):
        build_experimental_index([package, package])


def test_no_evidence_causes_abstention():
    result = retrieve_scientific_evidence(
        [],
        "Which Cu catalyst gives the highest ethylene FE?",
    )

    assert result["status"] == "insufficient_evidence"
    assert result["results"] == []
