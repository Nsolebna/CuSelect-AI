"""Read-only, claim-level scientific evidence promotion assessment.

PSEUDOCODE
1. Validate the proposed claim with the existing EvidenceClaim model.
2. Require claim-level source verification, not DOI-only review.
3. Check source provenance and reviewer confirmation.
4. Return reasons for blocking or permitting human approval.
5. Never change approval status or write to the trusted RAG corpus.
"""

from cuselect.evidence import EvidenceClaim, normalize_doi


def assess_promotion(claim_data: dict, review: dict) -> dict:
    """Assess eligibility for human approval, without granting approval."""

    reasons = []

    if not isinstance(claim_data, dict) or not isinstance(review, dict):
        return {
            "eligible_for_human_approval": False,
            "reasons": ["invalid_input"],
        }

    try:
        claim = EvidenceClaim.model_validate(claim_data)
    except (ValueError, TypeError):
        return {
            "eligible_for_human_approval": False,
            "reasons": ["invalid_claim_schema"],
        }

    if claim.review_status != "pending_source_review":
        reasons.append("claim_not_pending")

    if not claim.evidence_id.strip():
        reasons.append("missing_evidence_id")

    if review.get("evidence_id") != claim.evidence_id:
        reasons.append("claim_identity_mismatch")

    try:
        review_doi = normalize_doi(review.get("doi"))
    except (ValueError, TypeError):
        review_doi = None

    if review_doi != claim.doi:
        reasons.append("doi_mismatch")

    if review.get("status") != "source_checked":
        reasons.append("source_not_checked")

    if review.get("confirmed") is not True:
        reasons.append("human_confirmation_missing")

    if not str(review.get("reviewer_email") or "").strip():
        reasons.append("reviewer_identity_missing")

    if not str(review.get("reviewed_at") or "").strip():
        reasons.append("review_timestamp_missing")

    if claim.source_extent not in {"full_text", "supplementary"}:
        reasons.append("primary_source_required")

    location = str(review.get("source_location") or "").strip()

    if not location or location != claim.exact_source_location.strip():
        reasons.append("source_location_mismatch")

    excerpt = str(review.get("source_excerpt") or "").strip()

    if len(excerpt.split()) < 8:
        reasons.append("supporting_excerpt_missing")

    if not claim.claim_paraphrase.strip():
        reasons.append("claim_text_missing")

    return {
        "evidence_id": claim.evidence_id,
        "doi": claim.doi,
        "eligible_for_human_approval": not reasons,
        "reasons": reasons,
        "scientifically_verified": False,
        "rag_ingestion_status": "not_ingested",
    }


def identify_candidate_passages(candidate: dict) -> list[dict]:
    """Create stable, claim-level identifiers without modifying input."""

    import hashlib
    import copy

    if not isinstance(candidate, dict):
        raise ValueError("Candidate must be a dictionary")

    doi = normalize_doi(candidate.get("doi"))
    passages = candidate.get("candidate_passages")

    if not isinstance(passages, list):
        raise ValueError("Candidate passages must be a list")

    identified = []
    seen = set()

    for index, passage in enumerate(passages):
        if not isinstance(passage, dict):
            raise ValueError("Invalid candidate passage")

        excerpt = passage.get("source_excerpt")
        location = passage.get("source_location")

        if not isinstance(excerpt, str) or not excerpt.strip():
            raise ValueError("Missing source excerpt")

        if not isinstance(location, str) or not location.strip():
            raise ValueError("Missing source location")

        identity = "\x1f".join((
            doi,
            str(index),
            location,
            excerpt,
        ))

        evidence_id = "E-" + hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()[:20].upper()

        if evidence_id in seen:
            raise ValueError("Duplicate evidence identifier")

        seen.add(evidence_id)

        record = copy.deepcopy(passage)
        record["evidence_id"] = evidence_id
        record["doi"] = doi
        record["passage_index"] = index
        record["scientific_status"] = "unverified_candidate"

        identified.append(record)

    return identified


def get_passage_review(passage: dict, reviews: dict) -> dict | None:
    """Return a review only if it belongs to this exact passage.

    PSEUDOCODE
    1. Read the passage evidence ID and DOI.
    2. Find the corresponding claim-level review.
    3. Verify that both identifiers match.
    4. Reject legacy DOI-only records.
    5. Never modify or approve anything.
    """

    if not isinstance(passage, dict) or not isinstance(reviews, dict):
        return None

    evidence_id = passage.get("evidence_id")
    doi = passage.get("doi")

    if not isinstance(evidence_id, str) or not evidence_id.strip():
        return None

    review = reviews.get(evidence_id)

    if not isinstance(review, dict):
        return None

    if review.get("evidence_id") != evidence_id:
        return None

    try:
        if normalize_doi(review.get("doi")) != normalize_doi(doi):
            return None
    except (ValueError, TypeError):
        return None

    return dict(review)


def prepare_claim_review(
    passage: dict,
    decision: str,
    reviewer_email: str,
    source_location: str = "",
    source_excerpt: str = "",
    confirmed: bool = False,
) -> dict:
    """Prepare an individual passage review without saving or approving it.

    PSEUDOCODE
    1. Require an identified scientific passage.
    2. Validate the review decision.
    3. Require a reviewer identity supplied by the authorized caller.
    4. Require primary-source evidence for a source-checked decision.
    5. Keep the reviewed passage identity attached.
    6. Never approve the claim or modify the trusted RAG corpus.
    """

    if not isinstance(passage, dict):
        raise ValueError("Passage must be a dictionary")

    evidence_id = passage.get("evidence_id")

    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("Passage evidence ID required")

    doi = normalize_doi(passage.get("doi"))

    if decision not in {
        "needs_full_text", "rejected", "source_checked"
    }:
        raise ValueError("Invalid review decision")

    if not isinstance(reviewer_email, str) or not reviewer_email.strip():
        raise ValueError("Reviewer identity required")

    if decision == "source_checked":
        if confirmed is not True:
            raise ValueError("Human source confirmation required")

        if not source_location.strip() or source_location.strip().lower() in {
            "abstract", "unknown", "n/a"
        }:
            raise ValueError("Specific primary-source location required")

        if len(source_excerpt.split()) < 8:
            raise ValueError("Supporting source excerpt required")

    return {
        "evidence_id": evidence_id,
        "doi": doi,
        "status": decision,
        "reviewer_email": reviewer_email.strip().lower(),
        "source_location": source_location.strip(),
        "source_excerpt": source_excerpt.strip(),
        "confirmed": confirmed is True,
        "scientific_status": "pending_approval",
        "rag_ingestion_status": "not_ingested",
    }


def save_claim_review(
    root,
    review: dict,
    authenticated_reviewer: str,
) -> dict:
    """Persist one prepared review with locking and history.

    PSEUDOCODE
    1. Require an authenticated reviewer's identity.
    2. Validate the prepared review.
    3. Lock the claim-level review ledger.
    4. Preserve existing reviews and previous decisions.
    5. Save the updated ledger atomically.
    6. Never modify approved RAG evidence.
    """
    import fcntl
    import json
    import os
    import tempfile
    from datetime import datetime, timezone
    from pathlib import Path

    if not isinstance(review, dict):
        raise ValueError("Review must be a dictionary")

    if not isinstance(authenticated_reviewer, str):
        raise PermissionError("Reviewer identity required")

    reviewer = authenticated_reviewer.strip().lower()

    if not reviewer or review.get("reviewer_email") != reviewer:
        raise PermissionError("Reviewer identity mismatch")

    evidence_id = review.get("evidence_id")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("Evidence ID required")

    # PSEUDOCODE
    # 1. Revalidate the entire review at the persistence boundary.
    # 2. Never trust a caller's prevalidated status.
    # 3. Permit only explicitly supported review decisions.
    # 4. Preserve the verified identity of the authenticated caller.

    validated = prepare_claim_review(
        passage={
            "evidence_id": evidence_id,
            "doi": review.get("doi"),
        },
        decision=review.get("status"),
        reviewer_email=reviewer,
        source_location=review.get("source_location") or "",
        source_excerpt=review.get("source_excerpt") or "",
        confirmed=review.get("confirmed") is True,
    )

    doi = validated["doi"]

    if review.get("reviewer_email") != validated["reviewer_email"]:
        raise PermissionError("Reviewer identity mismatch")

    root = Path(root)
    path = root / "data/evidence_claim_reviews.json"
    lock_path = root / "data/evidence_claim_reviews.lock"
    path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

        try:
            if path.exists():
                ledger = json.loads(path.read_text(encoding="utf-8"))
            else:
                ledger = {}

            if not isinstance(ledger, dict):
                raise ValueError("Invalid review ledger")

            previous = ledger.get(evidence_id)

            if previous is not None:
                if not isinstance(previous, dict):
                    raise ValueError("Invalid existing review")

                if previous.get("doi") != doi:
                    raise ValueError("Existing evidence ID belongs to another DOI")

            timestamp = datetime.now(timezone.utc).isoformat()

            entry = {
                **review,
                "doi": doi,
                "reviewed_at": timestamp,
                "scientific_status": "pending_approval",
                "rag_ingestion_status": "not_ingested",
            }

            history = list((previous or {}).get("history", []))
            if previous:
                history.append({
                    k: v for k, v in previous.items()
                    if k != "history"
                })

            entry["history"] = history
            ledger[evidence_id] = entry

            fd, temporary = tempfile.mkstemp(
                prefix=".claim_reviews_",
                suffix=".tmp",
                dir=path.parent,
            )

            try:
                with os.fdopen(fd, "w", encoding="utf-8") as file:
                    json.dump(ledger, file, indent=2, ensure_ascii=False)
                    file.flush()
                    os.fsync(file.fileno())

                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

            return entry

        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def verify_candidate_identity(root, passage: dict) -> bool:
    """Verify a passage against the original extraction snapshot.

    PSEUDOCODE
    1. Load the original extraction candidates.
    2. Reconstruct deterministic passage identifiers.
    3. Match the exact evidence ID and DOI.
    4. Compare source text and source location.
    5. Reject fabricated or changed passages.
    6. Never modify extraction or approved evidence.
    """
    import json
    from pathlib import Path

    if not isinstance(passage, dict):
        return False

    path = (
        Path(root)
        / "data/evidence_extraction_candidates.json"
    )

    if not path.is_file():
        return False

    try:
        candidates = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(candidates, list):
            return False

        for candidate in candidates:
            for original in identify_candidate_passages(candidate):
                if (
                    original["evidence_id"] == passage.get("evidence_id")
                    and original["doi"] == normalize_doi(passage.get("doi"))
                    and original["source_excerpt"]
                        == passage.get("source_excerpt")
                    and original["source_location"]
                        == passage.get("source_location")
                ):
                    return True

    except (ValueError, TypeError, KeyError, OSError):
        return False

    return False


def submit_claim_review(
    root,
    passage: dict,
    decision: str,
    authenticated_reviewer: str,
    source_location: str = "",
    source_excerpt: str = "",
    confirmed: bool = False,
) -> dict:
    """Verify passage identity before recording a claim-level review.

    PSEUDOCODE
    1. Verify the passage against the extraction snapshot.
    2. Prepare and validate the individual review.
    3. Use the authenticated reviewer identity.
    4. Save through the existing locked persistence function.
    5. Never approve or modify RAG evidence.
    """

    if not verify_candidate_identity(root, passage):
        raise ValueError(
            "Passage does not match the original extraction snapshot"
        )

    review = prepare_claim_review(
        passage=passage,
        decision=decision,
        reviewer_email=authenticated_reviewer,
        source_location=source_location,
        source_excerpt=source_excerpt,
        confirmed=confirmed,
    )

    return save_claim_review(
        root=root,
        review=review,
        authenticated_reviewer=authenticated_reviewer,
    )
