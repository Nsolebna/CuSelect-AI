"""Tests using synthetic reviewed evidence packages."""

import hashlib

import pytest

from cuselect.scientific_rag_adapter import (
    canonical_json,
    package_to_rag_document,
)
from cuselect.scientific_promotion import REQUIRED_CHECKS


def make_package():
    claim = {
        "evidence_id": "E-SYNTHETIC-001",
        "paper_id": "P-SYNTHETIC",
        "doi": "10.1234/synthetic",
        "claim_paraphrase": "Synthetic Cu catalyst produces ethylene.",
        "claim_type": "experimental_observation",
        "source_extent": "full_text",
        "exact_source_location": "Results, Figure 2",
        "catalyst_system": "Synthetic Cu",
        "target_or_observation": "Ethylene production",
        "conditions": "Synthetic electrolyte; synthetic potential",
        "review_status": "pending_source_review",
        "source_checked_by_human": False,
    }

    hashes = "a" * 64

    review = {
        "claim_id": claim["evidence_id"],
        "paper_id": claim["paper_id"],
        "doi": claim["doi"],
        "decision": "approve",
        "reviewer": "synthetic-reviewer@example.org",
        "timestamp": "2026-11-11T12:00:00+00:00",
        "reviewer_note": "Synthetic test fixture only.",
        "checks": {key: True for key in REQUIRED_CHECKS},
        "source_xml_sha256": hashes,
        "claim_sha256": hashes,
        "dossier_sha256": hashes,
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
        "source_sha256": hashes,
    }

    digest = hashlib.sha256(canonical_json(payload)).hexdigest()

    return {
        "package_type": "scientific_evidence",
        "package_version": digest[:16],
        "payload_sha256": digest,
        "payload": payload,
    }


def test_synthetic_package_generates_rag_document():
    document = package_to_rag_document(make_package())

    assert document["document_id"] == "E-SYNTHETIC-001"
    assert "Synthetic Cu" in document["text"]
    assert document["metadata"]["doi"] == "10.1234/synthetic"


def test_modified_package_is_rejected():
    package = make_package()
    package["payload"]["claim"]["catalyst_system"] = "Modified"

    with pytest.raises(ValueError, match="hash mismatch"):
        package_to_rag_document(package)


def test_unapproved_claim_is_rejected():
    package = make_package()
    package["payload"]["review"]["decision"] = "reject"

    digest = hashlib.sha256(
        canonical_json(package["payload"])
    ).hexdigest()

    package["payload_sha256"] = digest
    package["package_version"] = digest[:16]

    with pytest.raises(ValueError, match="not approved"):
        package_to_rag_document(package)


def test_missing_scientific_check_is_rejected():
    package = make_package()
    package["payload"]["review"]["checks"]["correct_catalyst"] = False

    digest = hashlib.sha256(
        canonical_json(package["payload"])
    ).hexdigest()

    package["payload_sha256"] = digest
    package["package_version"] = digest[:16]

    with pytest.raises(ValueError, match="Incomplete"):
        package_to_rag_document(package)
