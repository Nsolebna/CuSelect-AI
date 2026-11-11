"""Convert validated scientific evidence packages into RAG documents.

PSEUDOCODE
1. Verify the package content hash.
2. Verify the recorded human-review decision and checks.
3. Require source provenance and experimental metadata.
4. Generate a traceable retrieval document.
5. Never write to the trusted production RAG corpus.
"""

import hashlib
import json

from cuselect.evidence import EvidenceClaim
from cuselect.scientific_promotion import REQUIRED_CHECKS


def canonical_json(obj):
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def validate_package(package):
    if not isinstance(package, dict):
        raise ValueError("Invalid evidence package")

    payload = package.get("payload")

    if not isinstance(payload, dict):
        raise ValueError("Missing evidence payload")

    expected = hashlib.sha256(canonical_json(payload)).hexdigest()

    if package.get("payload_sha256") != expected:
        raise ValueError("Evidence package hash mismatch")

    if package.get("package_version") != expected[:16]:
        raise ValueError("Evidence package version mismatch")

    if payload.get("schema_version") != "1.0":
        raise ValueError("Unsupported evidence schema")

    claim = EvidenceClaim.model_validate(payload["claim"])
    review = payload["review"]

    if (
        claim.evidence_id != payload.get("evidence_id")
        or claim.paper_id != payload.get("paper_id")
        or claim.doi != payload.get("doi")
    ):
        raise ValueError("Claim identity mismatch")

    if (
        review.get("claim_id") != claim.evidence_id
        or review.get("paper_id") != claim.paper_id
        or review.get("doi") != claim.doi
    ):
        raise ValueError("Review identity mismatch")

    if review.get("decision") != "approve":
        raise ValueError("Scientific claim is not approved")

    checks = review.get("checks", {})

    if not isinstance(checks, dict) or not all(
        checks.get(key) is True for key in REQUIRED_CHECKS
    ):
        raise ValueError("Incomplete scientific review")

    if not review.get("reviewer") or not review.get("timestamp"):
        raise ValueError("Missing reviewer identity or timestamp")

    if not str(review.get("reviewer_note", "")).strip():
        raise ValueError("Missing scientific justification")

    if (
        review.get("rag_ingestion_status") != "not_ingested"
        or review.get("promotion_status")
        != "pending_controlled_promotion"
    ):
        raise ValueError("Unexpected evidence lifecycle state")

    for field in (
        "source_xml_sha256",
        "claim_sha256",
        "dossier_sha256",
    ):
        value = review.get(field)

        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"Missing provenance hash: {field}")

        try:
            bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError(
                f"Invalid provenance hash: {field}"
            ) from exc

    if payload.get("source_sha256") != review["source_xml_sha256"]:
        raise ValueError("Source provenance mismatch")

    if not claim.exact_source_location:
        raise ValueError("Missing exact source location")

    return claim, review


def package_to_rag_document(package):
    """Build a retrieval record, without writing to disk."""

    claim, review = validate_package(package)

    retrieval_text = "\n".join([
        f"Scientific claim: {claim.claim_paraphrase}",
        f"Catalyst: {claim.catalyst_system}",
        f"Observation: {claim.target_or_observation}",
        f"Experimental conditions: {claim.conditions or 'Not specified'}",
        f"Source location: {claim.exact_source_location}",
        f"DOI: {claim.doi}",
    ])

    return {
        "document_id": claim.evidence_id,
        "text": retrieval_text,
        "metadata": {
            "evidence_id": claim.evidence_id,
            "paper_id": claim.paper_id,
            "doi": claim.doi,
            "source_location": claim.exact_source_location,
            "source_sha256": package["payload"]["source_sha256"],
            "package_version": package["package_version"],
            "reviewer": review["reviewer"],
            "review_timestamp": review["timestamp"],
            "scientific_review_decision": review["decision"],
        },
    }
