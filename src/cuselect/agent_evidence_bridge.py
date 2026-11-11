"""Experimental evidence interface for CuSelect-AI agents.

PSEUDOCODE
1. Receive a scientific question from an agent.
2. Retrieve supporting scientific evidence.
3. Return citation-linked context or explicit abstention.
4. Separate retrieved evidence from agent-generated hypotheses.
5. Never claim that experimental evidence is production-approved.
"""


def build_agent_evidence_context(retriever, question, top_k=3):
    """Return structured evidence for literature and critic agents."""

    result = retriever.retrieve_with_abstention(
        question, top_k=top_k
    )

    if result["status"] != "evidence_retrieved":
        return {
            "question": question,
            "status": "insufficient_evidence",
            "evidence_context": "",
            "citations": [],
            "agent_instruction": (
                "No adequate supporting evidence was retrieved. "
                "Do not invent numerical results, source references, "
                "or experimental conclusions. "
                "Identify the evidence gap explicitly."
            ),
            "evidence_trust_level": "experimental",
        }

    passages = []
    citations = []

    for index, match in enumerate(result["results"], 1):
        citation = match["citation"]

        passages.append(
            f"[SOURCE {index}]\n"
            f"Evidence ID: {citation['evidence_id']}\n"
            f"DOI: {citation['doi']}\n"
            f"Source location: {citation['source_location']}\n"
            f"Evidence text: {match['text']}"
        )

        citations.append(citation)

    return {
        "question": question,
        "status": "evidence_available",
        "evidence_context": "\n\n".join(passages),
        "citations": citations,
        "agent_instruction": (
            "Use the cited evidence as retrieved context, not as "
            "independent proof of scientific correctness. "
            "Distinguish reported observations, hypotheses, "
            "predictions, and unsupported claims. "
            "Do not fabricate citations or experimental conditions."
        ),
        "evidence_trust_level": "experimental",
    }


def build_literature_agent_input(retriever, question):
    """Prepare evidence for literature-analysis reasoning."""
    return {
        "agent": "literature",
        **build_agent_evidence_context(retriever, question),
    }


def build_critic_agent_input(retriever, claim_to_check):
    """Prepare evidence for critical scientific assessment."""
    return {
        "agent": "critic",
        **build_agent_evidence_context(retriever, claim_to_check),
        "critic_instruction": (
            "Check catalyst identity, product selectivity, "
            "operating conditions, numerical consistency, "
            "and evidence limitations. "
            "A retrieved match does not by itself establish "
            "that a scientific claim is true."
        ),
    }
