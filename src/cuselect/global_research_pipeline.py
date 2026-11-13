"""Read-only global literature discovery and relevance screening."""

from cuselect.global_research_service import research_literature
from cuselect.literature_relevance import evaluate_publications


def run_global_research(
    question,
    *,
    max_papers=5,
    research_fn=None,
    evaluation_fn=None,
):
    """Search, screen and return provisional publications."""

    if not str(question).strip():
        raise ValueError("Research question is required.")

    research_fn = research_fn or research_literature
    evaluation_fn = evaluation_fn or evaluate_publications

    discovery = research_fn(
        question,
        max_papers=max_papers,
    )

    papers = discovery.get("papers", [])

    assessments = evaluation_fn(question, papers)

    relevant = [
        item for item in assessments
        if (
            item.get("assessment") or {}
        ).get("relevance") in {
            "direct_evidence_candidate",
            "relevant_background",
        }
    ]

    return {
        "question": question,
        "publication_count": len(papers),
        "relevant_count": len(relevant),
        "screened_publications": assessments,
        "source_publications": papers,
        "relevant_publications": relevant,
        "screening_complete": all(
            item.get("assessment") is not None
            for item in assessments
        ),
        "evidence_status": "provisional",
        "experimental_claims_verified": False,
        "warning": (
            "Relevance screening is not experimental "
            "claim verification. Worldwide performance "
            "records cannot be established from these "
            "results alone."
        ),
    }
