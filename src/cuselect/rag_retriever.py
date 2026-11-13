
"""Provisional evidence semantic retrieval for CuSelect-AI."""

import json
from pathlib import Path

from sentence_transformers import SentenceTransformer, util

MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def search_evidence(root: Path, question: str, top_k: int = 3):
    """Retrieve source records, never certify scientific validity."""
    path = root / "data/approved_evidence.json"
    records = json.loads(path.read_text(encoding="utf-8"))

    # Only administratively approved records are indexed.
    records = [
        r for r in records
        if r.get("review_status") == "approved"
        and r.get("doi")
        and r.get("exact_source_text")
    ]

    if not records or not question.strip():
        return []

    passages = [
        " ".join([
            str(r.get("title") or ""),
            str(r.get("product") or ""),
            str(r.get("measurement_type") or ""),
            str(r["exact_source_text"]),
        ])
        for r in records
    ]

    model = SentenceTransformer(MODEL)
    document_vectors = model.encode_document(passages)
    query_vector = model.encode_query([question])

    hits = util.semantic_search(
        query_vector,
        document_vectors,
        top_k=min(top_k, len(records)),
    )[0]

    results = []

    for hit in hits:
        r = records[hit["corpus_id"]]

        results.append({
            "measurement_id": r.get("measurement_id"),
            "title": r.get("title"),
            "doi": r.get("doi"),
            "source_excerpt": r["exact_source_text"],
            "similarity": round(float(hit["score"]), 3),
            "scientific_status": r.get("scientific_status"),
            "conditions_review_status": r.get(
                "conditions_review_status"
            ),
            "warning": (
                "Provisional evidence: scientific and "
                "experimental-condition verification pending."
            ),
        })

    return results
