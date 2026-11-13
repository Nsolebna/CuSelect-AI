"""Read-only hybrid research: verified RAG + global literature."""

from cuselect.evidence_store import load_verified_corpus
from cuselect.checked_rag import run_checked_rag
from cuselect.rag import run_rag_question
from cuselect.global_research_pipeline import run_global_research


def run_hybrid_research(
    question,
    *,
    project_root=".",
    corpus_loader=None,
    rag_fn=None,
    global_fn=None,
    max_papers=5,
):
    question = str(question).strip()

    if not question:
        raise ValueError("Research question cannot be empty.")

    corpus_loader = corpus_loader or load_verified_corpus
    rag_fn = rag_fn or run_rag_question
    global_fn = global_fn or run_global_research

    verified = run_checked_rag(
        question,
        project_root=project_root,
        corpus_loader=corpus_loader,
        rag_fn=rag_fn,
    )

    if verified.get("citation_audit_passed") is not True:
        raise RuntimeError("RAG citation audit failed.")

    decision = verified.get("decision")
    cited_ids = verified.get("cited_ids") or []

    if decision not in {"evidence_found", "answer", "abstain"}:
        raise RuntimeError("Unexpected RAG decision.")

    if decision in {"evidence_found", "answer"} and not cited_ids:
        raise RuntimeError("Evidence answer missing citations.")

    if decision == "abstain" and cited_ids:
        raise RuntimeError("Abstention contains citations.")

    global_result = global_fn(question, max_papers=max_papers)

    publications = global_result.get("relevant_publications", [])

    for paper in global_result.get("screened_publications", publications):
        if paper.get("experimental_claims_verified") is not False:
            raise RuntimeError("Unreviewed publication marked verified.")

    # SOURCE TEXT BRIDGE
    # Preserve abstract text with DOI-based provenance.
    # These sources remain provisional.
    sources = global_result.get("source_publications") or []

    relevant_dois = {
        str(p.get("doi") or "").strip().lower()
        for p in publications
        if isinstance(p, dict)
    }

    source_abstracts = {}

    for paper in sources:
        if not isinstance(paper, dict):
            continue

        doi = str(paper.get("doi") or "").strip().lower()
        abstract = str(paper.get("abstract") or "").strip()

        if doi in relevant_dois and doi and abstract:
            source_abstracts[doi] = abstract

    return {
        "question": question,
        "verified_evidence": verified,
        "global_publications": publications,
        "source_abstracts": source_abstracts,
        "global_publication_count": global_result.get(
            "publication_count", 0
        ),
        "screening_complete": global_result.get(
            "screening_complete", False
        ),
        "verified_claims_available": (
            decision in {"evidence_found", "answer"}
        ),
        "global_claims_verified": False,
        "scientific_answer_ready": False,
        "files_modified": False,
        "computation_executed": False,
    }
