"""Question-aware screening of provisional scientific publications."""

import os

from pydantic import BaseModel, Field
from typing import Literal


class RelevanceAssessment(BaseModel):
    relevance: Literal[
        "direct_evidence_candidate",
        "relevant_background",
        "not_relevant",
    ]
    explanation: str
    addresses_requested_quantity: bool
    requires_full_text_verification: bool = True
    measurement_warning: str = ""


SYSTEM_INSTRUCTIONS = """
You are a scientific literature-screening assistant.

Assess whether a paper addresses the researcher's actual question.

Distinguish:
- Direct experimental measurements from background discussion.
- Different chemical products and catalyst systems.
- Faradaic efficiency from current density, yield and conversion.
- Single-electrode FE from system-level or combined FE.
- Reports of a measurement from claims of a worldwide record.

Use only the supplied title and abstract. Do not invent
results, numbers, experimental conditions or publication contents.

Classify as:
direct_evidence_candidate: potentially answers the question.
relevant_background: useful context, but not a direct answer.
not_relevant: insufficient connection to the question.

A direct match is a candidate for further verification,
not an approved experimental claim.

If uncertain, explicitly explain the uncertainty.
"""


def evaluate_paper(
    question,
    paper,
    *,
    client=None,
    model=None,
):
    """LLM screening only. Does not validate scientific claims."""

    question = str(question).strip()

    if not question:
        raise ValueError("Research question cannot be empty.")

    title = str(paper.get("title") or "").strip()
    abstract = str(paper.get("abstract") or "").strip()

    if not title:
        raise ValueError("Publication title is required.")

    if client is None:
        from dotenv import load_dotenv
        from pathlib import Path

        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(dotenv_path=project_root / ".env")

        from openai import OpenAI
        client = OpenAI(timeout=45, max_retries=1)

    model = model or os.getenv("OPENAI_MODEL", "gpt-5-mini")

    content = (
        f"Research question:\n{question}\n\n"
        f"Publication title:\n{title}\n\n"
        f"Abstract:\n{abstract or '[Unavailable]'}\n\n"
        "Assess relevance using only the supplied information."
    )

    response = client.responses.parse(
        model=model,
        instructions=SYSTEM_INSTRUCTIONS,
        input=content,
        text_format=RelevanceAssessment,
        store=False,
    )

    assessment = response.output_parsed

    if assessment is None:
        raise RuntimeError("No structured relevance assessment returned.")

    return {
        "doi": paper.get("doi"),
        "title": title,
        "assessment": assessment.model_dump(),
        "evidence_status": "provisional",
        "experimental_claims_verified": False,
    }


def evaluate_publications(
    question,
    papers,
    *,
    evaluator=evaluate_paper,
):
    """Evaluate publications without silently treating errors as results."""

    output = []

    for paper in papers:
        try:
            output.append(evaluator(question, paper))
        except Exception as exc:
            output.append({
                "doi": paper.get("doi"),
                "title": paper.get("title"),
                "assessment": None,
                "screening_error": (
                    type(exc).__name__ + ": " + str(exc)[:180]
                ),
                "evidence_status": "provisional",
                "experimental_claims_verified": False,
            })

    order = {
        "direct_evidence_candidate": 0,
        "relevant_background": 1,
        "not_relevant": 2,
    }

    return sorted(
        output,
        key=lambda item: order.get(
            (item.get("assessment") or {}).get("relevance"),
            3,
        ),
    )
