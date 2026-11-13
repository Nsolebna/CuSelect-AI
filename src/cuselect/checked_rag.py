"""Conservative evidence filtering before RAG retrieval."""

from cuselect.evidence_store import load_verified_corpus
from cuselect.rag import run_rag_question


def is_draft(record):
    evidence_id = str(record.get("evidence_id") or "").lower()
    status = str(record.get("review_status") or "").lower()
    scientific_status = str(
        record.get("scientific_status") or ""
    ).lower()

    return (
        "draft" in evidence_id
        or status in {
            "draft", "pending", "rejected", "unreviewed"
        }
        or scientific_status in {
            "draft", "pending", "rejected", "unreviewed"
        }
    )


def run_checked_rag(
    question,
    *,
    project_root=".",
    corpus_loader=None,
    rag_fn=None,
):
    corpus_loader = corpus_loader or load_verified_corpus
    rag_fn = rag_fn or run_rag_question

    records = corpus_loader(str(project_root))

    eligible = [
        record for record in records
        if not is_draft(record)
    ]

    excluded = [
        str(record.get("evidence_id") or "unknown")
        for record in records
        if is_draft(record)
    ]

    result = rag_fn(question, eligible, top_k=5)

    if result.get("citation_audit_passed") is not True:
        raise RuntimeError("RAG citation audit failed.")

    cited_ids = result.get("cited_ids") or []
    eligible_ids = {
        str(record.get("evidence_id"))
        for record in eligible
    }

    if not set(cited_ids).issubset(eligible_ids):
        raise RuntimeError(
            "RAG cited evidence outside the eligible corpus."
        )

    decision = result.get("decision")

    if decision not in {
        "evidence_found", "answer", "abstain"
    }:
        raise RuntimeError("Unexpected RAG decision.")

    if decision in {"evidence_found", "answer"} and not cited_ids:
        raise RuntimeError("Answer has no evidence citations.")

    if decision == "abstain" and cited_ids:
        raise RuntimeError("Abstention contains citations.")

    return {
        **result,
        "total_records": len(records),
        "eligible_records": len(eligible),
        "excluded_draft_ids": excluded,
        "draft_filter_passed": True,
        "validation_scope": (
            "Draft exclusion and citation consistency only; "
            "not independent scientific claim verification."
        ),
    }
