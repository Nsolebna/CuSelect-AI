"""Live, source-grounded scientific explanation.

Uses provisional abstracts without approving experimental claims.
"""

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class SupportedPoint(BaseModel):
    doi: str
    source_quote: str
    interpretation: str


class ExplanationDraft(BaseModel):
    points: List[SupportedPoint]
    uncertainties: List[str] = Field(default_factory=list)
    next_question: str


INSTRUCTIONS = """
You are a careful scientific research assistant.

Answer the research question using ONLY supplied abstracts.
Produce a coherent set of explanatory points.

For every point:
- Identify the source DOI.
- Copy an exact supporting passage of no more than 20 words.
- Explain what the passage supports.
- Distinguish observations from mechanistic hypotheses.
- Never invent numbers, experiments or operating conditions.
- Do not infer that a proposed mechanism is proven.
- Do not claim literature screening is exhaustive.

If the abstracts do not support an explanation, return no points.
Provide uncertainties and one useful follow-up question.
"""


def generate_explanation(
    question,
    source_abstracts,
    *,
    client=None,
    model=None,
):
    question = str(question).strip()

    if not question:
        raise ValueError("A research question is required.")

    sources = {
        str(doi).strip().lower(): str(abstract).strip()
        for doi, abstract in source_abstracts.items()
        if str(doi).startswith("10.")
        and str(abstract).strip()
    }

    # Limit source volume and preserve the complete supplied
    # abstracts for exact quote verification.
    sources = dict(list(sources.items())[:5])

    if not sources:
        return {
            "status": "insufficient_source_text",
            "points": [],
            "uncertainties": [
                "No source abstracts are available."
            ],
            "next_question": "",
            "evidence_status": "provisional",
        }

    if client is None:
        load_dotenv(
            dotenv_path=(
                Path(__file__).resolve().parents[2] / ".env"
            )
        )
        from openai import OpenAI
        client = OpenAI(timeout=60, max_retries=1)

    model = model or os.getenv("OPENAI_MODEL", "gpt-5-mini")

    excerpts = "\n\n".join(
        f"DOI: {doi}\nABSTRACT:\n{abstract[:5000]}"
        for doi, abstract in sources.items()
    )

    response = client.responses.parse(
        model=model,
        instructions=INSTRUCTIONS,
        input=(
            f"RESEARCH QUESTION:\n{question}\n\n"
            f"SCIENTIFIC SOURCES:\n{excerpts}"
        ),
        text_format=ExplanationDraft,
        store=False,
    )

    draft = response.output_parsed

    if draft is None:
        raise RuntimeError(
            "No structured scientific explanation returned."
        )

    verified_points = []
    rejected_points = 0

    for point in draft.points:
        doi = point.doi.strip().lower()
        quote = point.source_quote.strip()

        # Fail closed on unsupported sources or quotations.
        if (
            doi not in sources
            or not quote
            or len(quote.split()) > 20
            or quote not in sources[doi]
        ):
            rejected_points += 1
            continue

        verified_points.append({
            "doi": doi,
            "source_quote": quote,
            "interpretation": point.interpretation,
            "evidence_status": "provisional_interpretation",
        })

    return {
        "status": (
            "source_grounded_draft"
            if verified_points
            else "insufficient_source_support"
        ),
        "points": verified_points,
        "rejected_points": rejected_points,
        "uncertainties": draft.uncertainties,
        "next_question": draft.next_question,
        "evidence_status": "provisional",
        "experimental_claims_verified": False,
    }
