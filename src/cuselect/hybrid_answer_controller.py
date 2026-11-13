"""Unified scientific research endpoint for Discover."""

from cuselect.hybrid_research import run_hybrid_research
from cuselect.scientific_answer import synthesize_research_answer


def answer_research_question(
    question,
    *,
    project_root=".",
    max_papers=5,
    hybrid_fn=None,
    synthesis_fn=None,
):
    """Return a guarded hybrid scientific research answer."""

    question = str(question).strip()

    if not question:
        raise ValueError("Research question cannot be empty.")

    hybrid_fn = hybrid_fn or run_hybrid_research
    synthesis_fn = synthesis_fn or synthesize_research_answer

    research = hybrid_fn(
        question,
        project_root=project_root,
        max_papers=max_papers,
    )

    verified = research.get("verified_evidence") or {}

    if verified.get("draft_filter_passed") is not True:
        raise RuntimeError(
            "Checked RAG safeguard not confirmed."
        )

    if verified.get("citation_audit_passed") is not True:
        raise RuntimeError("Citation audit failed.")

    if research.get("global_claims_verified") is not False:
        raise RuntimeError(
            "Global evidence verification status is unsafe."
        )

    # LIVE SCIENTIFIC EXPLANATION INTEGRATION
    explanation_status = "not_attempted"
    explanation_points = []
    explanation_uncertainties = []
    explanation_next_question = ""

    source_abstracts = research.get("source_abstracts") or {}

    if source_abstracts:
        try:
            from cuselect.scientific_explanation import (
                generate_explanation,
            )

            explanation = generate_explanation(
                question,
                source_abstracts,
            )

            explanation_status = explanation.get(
                "status", "unknown"
            )
            explanation_points = explanation.get("points") or []
            explanation_uncertainties = (
                explanation.get("uncertainties") or []
            )
            explanation_next_question = str(
                explanation.get("next_question") or ""
            )

        except Exception:
            # Retain the audited extractive synthesis.
            # Never expose API credentials or request details.
            explanation_status = "unavailable"

    result = synthesis_fn(research)

    if result.get("citation_audit_passed") is not True:
        raise RuntimeError("Answer citation audit failed.")

    answer = result["answer"]

    if explanation_points:
        sections = [
            "**Source-grounded scientific interpretation**"
        ]

        for point in explanation_points:
            doi = str(point.get("doi") or "")
            quote = str(point.get("source_quote") or "")
            interpretation = str(
                point.get("interpretation") or ""
            )

            if not doi or not quote or not interpretation:
                continue

            sections.append(
                f"**DOI: {doi}**\n\n"
                f"Source excerpt: \"{quote}\"\n\n"
                f"Provisional interpretation: {interpretation}"
            )

        if len(sections) > 1:
            answer += "\n\n" + "\n\n".join(sections)

        if explanation_uncertainties:
            answer += (
                "\n\n**Scientific uncertainties**\n\n"
                + "\n".join(
                    "- " + str(item)
                    for item in explanation_uncertainties[:5]
                )
            )

        if explanation_next_question:
            answer += (
                "\n\n**Recommended next investigation**"
                "\n\n"
                + explanation_next_question
            )

        answer += (
            "\n\n*These interpretations are provisional "
            "and are not human-approved experimental findings.*"
        )

    return {
        "question": question,
        "answer": answer,
        "status": result["status"],
        "citations": result.get("verified_citation_ids", []),
        "global_publication_count": research.get(
            "global_publication_count", 0
        ),
        "screening_complete": research.get(
            "screening_complete", False
        ),
        "explanation_status": explanation_status,
        "explanation_point_count": len(explanation_points),
        "execution_mode": "hybrid_scientific_research",
        "global_claims_verified": False,
        "files_modified": False,
        "computation_executed": False,
    }
