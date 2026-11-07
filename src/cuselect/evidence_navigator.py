# CuSelect-AI — Scientific Evidence Navigator
#
# PSEUDOCODE
# 1. Load the trusted human-reviewed corpus.
# 2. Accept only evidence cited by the Scientific Critic.
# 3. Match displayed citations to authoritative metadata.
# 4. Reject fabricated or altered citation information.
# 5. Return source details and a safe publication URL.
# 6. Never generate new scientific claims.

import re
from pathlib import Path
from urllib.parse import quote

from .evidence_store import (
    EvidenceIntegrityError,
    load_verified_corpus,
)


def build_evidence_cards(citations, project_root="."):
    """Build evidence navigation cards from trusted records."""

    records = load_verified_corpus(Path(project_root))

    by_id = {
        record["evidence_id"]: record
        for record in records
    }

    cards = []
    seen = set()

    for citation in citations:
        if not isinstance(citation, dict):
            raise EvidenceIntegrityError(
                "Invalid citation format"
            )

        evidence_id = citation.get("evidence_id")

        if (
            not isinstance(evidence_id, str)
            or evidence_id not in by_id
            or evidence_id in seen
        ):
            raise EvidenceIntegrityError(
                "Unknown or duplicate evidence ID"
            )

        seen.add(evidence_id)
        record = by_id[evidence_id]

        # Never accept altered citation metadata.
        for field in (
            "doi",
            "source_location",
            "source_extent",
        ):
            if citation.get(field) != record[field]:
                raise EvidenceIntegrityError(
                    f"Citation metadata mismatch: {field}"
                )

        if record["review_status"] != "human_verified":
            raise EvidenceIntegrityError(
                "Evidence is not human verified"
            )

        doi = record["doi"].strip()

        if not re.fullmatch(
            r"10\.\d{4,9}/[A-Za-z0-9._;()/:\-]+",
            doi,
        ):
            raise EvidenceIntegrityError(
                "Invalid DOI format"
            )

        cards.append({
            "evidence_id": evidence_id,
            "claim": record["claim_paraphrase"],
            "catalyst": record["catalyst_system"],
            "conditions": record["conditions"],
            "source_location": record["source_location"],
            "source_extent": record["source_extent"],
            "review_status": record["review_status"],
            "doi": doi,
            "publication_url": (
                "https://doi.org/"
                + quote(doi, safe="/-._;():")
            ),
        })

    return cards
