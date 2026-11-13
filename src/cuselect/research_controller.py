"""Controlled research execution for CuSelect-AI.

Routes questions using the existing LLM router.
Only verified, extractive RAG is executable in v1.
No file writes, DFT jobs, or autonomous catalyst design.
"""

from pathlib import Path

from cuselect.research_router import route_question
from cuselect.evidence_store import load_verified_corpus
from cuselect.rag import run_rag_question


RAG_ROUTES = {
    "literature_research",
    "scientific_explanation",
}

PLANNED_ROUTES = {
    "catalyst_discovery",
    "catalyst_comparison",
    "computational_planning",
    "general_scientific_question",
}


def execute_research(
    question,
    *,
    project_root=None,
    router=None,
    corpus_loader=None,
    rag_runner=None,
):
    """Execute only currently authorized scientific capabilities."""

    question = str(question).strip()

    if not question:
        raise ValueError("Research question cannot be empty.")

    if len(question) > 12000:
        raise ValueError("Research question exceeds length limit.")

    root = (
        Path(project_root)
        if project_root is not None
        else Path(__file__).resolve().parents[2]
    )

    router = router if router is not None else route_question

    # LLM classification is advisory, not execution authority.
    route = router(question)
    workflow = route.workflow

    if workflow not in RAG_ROUTES | PLANNED_ROUTES:
        raise ValueError("Unauthorized workflow.")

    base = {
        "question": question,
        "workflow": workflow,
        "research_goal": route.research_goal,
        "required_capabilities": route.required_capabilities,
        "missing_information": route.missing_information,
        "scientific_constraints": route.scientific_constraints,
        "routing_reason": route.routing_reason,
        "files_modified": False,
        "computation_executed": False,
    }

    if workflow in PLANNED_ROUTES:
        return {
            **base,
            "status": "planning_only",
            "answer": (
                "The research request was understood, but "
                "automatic execution of this workflow is not "
                "yet authorized in the Research Controller."
            ),
            "citations": [],
            "citation_audit_passed": False,
            "execution_mode": "route_only",
        }

    loader = (
        corpus_loader
        if corpus_loader is not None
        else load_verified_corpus
    )
    runner = (
        rag_runner
        if rag_runner is not None
        else run_rag_question
    )

    # The evidence loader checks registry and snapshot integrity.
    verified_records = loader(root)

    # Deterministic RAG performs its own citation consistency audit.
    result = runner(
        question,
        verified_records,
        top_k=3,
    )

    if result.get("citation_audit_passed") is not True:
        raise RuntimeError("RAG citation audit did not pass.")

    decision = result.get("decision")

    # Accept actual RAG decision values while enforcing
    # citation consistency and explicit abstention.
    if decision not in {"evidence_found", "answer", "abstain"}:
        raise RuntimeError(
            f"Unexpected RAG decision: {decision!r}"
        )

    if decision == "abstain" and result.get("cited_ids"):
        raise RuntimeError(
            "An abstention must not contain evidence citations."
        )

    if decision in {"evidence_found", "answer"}:
        if not result.get("cited_ids"):
            raise RuntimeError(
                "Evidence response must contain citations."
            )

    cited_ids = result.get("cited_ids", [])

    if not isinstance(cited_ids, list):
        raise RuntimeError("Unexpected RAG citation format.")

    known_ids = {
        record["evidence_id"]
        for record in verified_records
    }

    if not set(cited_ids).issubset(known_ids):
        raise RuntimeError("RAG referenced unknown evidence.")

    citations = [
        {
            "evidence_id": record["evidence_id"],
            "doi": record.get("doi"),
            "source_location": record.get("source_location"),
        }
        for record in verified_records
        if record["evidence_id"] in cited_ids
    ]

    return {
        **base,
        "status": (
            "evidence_response"
            if cited_ids else "evidence_abstention"
        ),
        "answer": result["answer"],
        "reason": result.get("reason"),
        "citations": citations,
        "citation_audit_passed": True,
        "execution_mode": "verified_extractive_rag",
        "retrieved_count": result.get("retrieved_count", 0),
    }
