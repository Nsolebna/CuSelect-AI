"""Experimental citation-grounded scientific retrieval.

PSEUDOCODE
1. Receive retrieval-ready scientific documents.
2. Index their text and provenance metadata in memory.
3. Match a query against scientific terms and numeric values.
4. Return supporting indexed claims with citations.
5. Abstain if no document satisfies the retrieval checks.
"""

import re
from collections import Counter


STOPWORDS = {
    "a", "an", "and", "are", "at", "by", "did",
    "do", "does", "for", "from", "how", "in",
    "is", "of", "on", "or", "the", "to",
    "was", "were", "what", "which", "with",
}


def normalize(text):
    return (
        str(text)
        .lower()
        .replace("−", "-")
        .replace("–", "-")
        .replace("₂", "2")
        .replace("₄", "4")
        .replace("⁺", "+")
    )


def tokens(text):
    return [
        token
        for token in re.findall(
            r"-?\d+(?:\.\d+)?|[a-z][a-z0-9]*",
            normalize(text),
        )
        if token not in STOPWORDS
    ]


def numeric_tokens(text):
    return set(
        re.findall(
            r"(?<![a-z0-9])-?\d+(?:\.\d+)?",
            normalize(text),
        )
    )


class ScientificRetriever:
    """In-memory retrieval over explicitly supplied documents."""

    def __init__(self, documents):
        self.documents = []
        seen_ids = set()

        for doc in documents:
            document_id = str(doc.get("document_id", ""))
            content = str(doc.get("text", ""))
            metadata = doc.get("metadata", {})

            if not document_id or not content.strip():
                raise ValueError("Document identity or text missing")

            if document_id in seen_ids:
                raise ValueError("Duplicate evidence document ID")

            if not isinstance(metadata, dict):
                raise ValueError("Invalid evidence metadata")

            required = (
                "evidence_id",
                "paper_id",
                "doi",
                "source_location",
                "package_version",
            )

            if any(not metadata.get(k) for k in required):
                raise ValueError("Incomplete provenance metadata")

            if metadata["evidence_id"] != document_id:
                raise ValueError("Evidence identity mismatch")

            seen_ids.add(document_id)

            self.documents.append({
                "document_id": document_id,
                "text": content,
                "metadata": dict(metadata),
                "tokens": Counter(tokens(content)),
                "numbers": numeric_tokens(content),
            })

    def search(self, query, top_k=3):
        if top_k < 1:
            raise ValueError("top_k must be positive")

        query_terms = set(tokens(query))
        query_numbers = numeric_tokens(query)

        if not query_terms:
            return []

        results = []

        for doc in self.documents:
            # Do not match a numerical query to a claim
            # reporting different numerical values.
            if not query_numbers.issubset(doc["numbers"]):
                continue

            shared = query_terms.intersection(doc["tokens"])

            if len(shared) < 2:
                continue

            score = len(shared) / len(query_terms)

            results.append({
                "document_id": doc["document_id"],
                "score": round(score, 4),
                "text": doc["text"],
                "citation": {
                    "evidence_id": doc["metadata"]["evidence_id"],
                    "paper_id": doc["metadata"]["paper_id"],
                    "doi": doc["metadata"]["doi"],
                    "source_location": doc["metadata"]["source_location"],
                    "package_version": doc["metadata"]["package_version"],
                },
            })

        return sorted(
            results,
            key=lambda r: (-r["score"], r["document_id"]),
        )[:top_k]

    def retrieve_with_abstention(self, query, top_k=3):
        matches = self.search(query, top_k=top_k)

        return {
            "query": query,
            "status": (
                "evidence_retrieved"
                if matches else "insufficient_evidence"
            ),
            "results": matches,
            "generated_scientific_answer": None,
            "requires_claim_level_verification": True,
        }
