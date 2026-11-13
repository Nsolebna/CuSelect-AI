"""Extract provisional claims from screened literature abstracts."""

from cuselect.global_research_pipeline import run_global_research
from cuselect.scientific_claim_extractor import extract_claims


def run_global_claim_extraction(
    question,
    *,
    max_papers=3,
    research_fn=None,
    extractor_fn=None,
):
    if not str(question).strip():
        raise ValueError("Research question is required.")

    research_fn = research_fn or run_global_research
    extractor_fn = extractor_fn or extract_claims

    research = research_fn(
        question,
        max_papers=max_papers,
    )

    # Assessments alone do not contain abstracts.
    # Reattach source text from the original discovery results
    # only when the research service supplies them.
    source_papers = research.get("source_publications", [])

    source_by_doi = {
        str(p.get("doi", "")).lower(): p
        for p in source_papers
        if isinstance(p, dict) and p.get("doi")
    }

    records = []
    failures = []
    skipped = []

    for paper in research.get("relevant_publications", []):
        assessment = paper.get("assessment") or {}

        if assessment.get("relevance") != "direct_evidence_candidate":
            continue

        doi = str(paper.get("doi") or "").lower()
        source = source_by_doi.get(doi, {})
        abstract = str(source.get("abstract") or "").strip()

        if not abstract:
            skipped.append({
                "doi": doi,
                "reason": "No abstract source text available",
            })
            continue

        try:
            extraction = extractor_fn(
                abstract,
                doi=doi,
                source_location="OpenAlex abstract",
            )

            for claim in extraction.get("claims", []):
                quote = claim.get("source_quote")

                if not quote or quote not in abstract:
                    raise RuntimeError(
                        "Extracted claim has no matching source quote."
                    )

                if claim.get("scientifically_verified") is not False:
                    raise RuntimeError(
                        "Provisional claim incorrectly marked verified."
                    )

                records.append({
                    **claim,
                    "doi": doi,
                    "source_type": "abstract",
                    "evidence_status": "provisional_extraction",
                    "scientifically_verified": False,
                    "approved_for_rag": False,
                })

        except Exception as exc:
            failures.append({
                "doi": doi,
                "error": type(exc).__name__ + ": " + str(exc)[:200],
            })

    return {
        "question": question,
        "claims": records,
        "claim_count": len(records),
        "skipped": skipped,
        "failures": failures,
        "evidence_status": "provisional_extraction",
        "approved_for_rag": False,
        "files_modified": False,
        "warning": (
            "Abstract-derived claims are provisional. "
            "Primary-source figures, experimental conditions "
            "and supplementary information require review."
        ),
    }
