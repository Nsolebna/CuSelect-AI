"""Read-only global scholarly literature research service."""

import html
import re

from cuselect.multiquery_discovery import multiquery_discover
from cuselect.multi_source_abstracts import fetch_openalex_abstract


def clean(value):
    return re.sub(
        r"\s+", " ",
        html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    ).strip()


def normalize_doi(value):
    return re.sub(
        r"^https?://(?:dx\.)?doi\.org/",
        "",
        str(value or "").strip().lower(),
    )


def research_literature(
    question,
    *,
    max_papers=5,
    search_fn=None,
    abstract_fn=None,
):
    """Discover and enrich publications; never approve claims."""

    if not question.strip():
        raise ValueError("Research question cannot be empty.")

    search_fn = search_fn or multiquery_discover
    abstract_fn = abstract_fn or fetch_openalex_abstract

    publications = search_fn(
        question,
        rows=max(10, max_papers * 4),
    )

    if not isinstance(publications, list):
        raise TypeError("Crossref must return a list.")

    seen = set()
    results = []

    for paper in publications:
        if not isinstance(paper, dict):
            continue

        doi = normalize_doi(paper.get("doi"))

        if not doi or doi in seen:
            continue

        seen.add(doi)

        title = clean(paper.get("title"))

        record = {
            "doi": doi,
            "title": title,
            "year": paper.get("year"),
            "journal": clean(paper.get("journal")),
            "url": f"https://doi.org/{doi}",
            "abstract": "",
            "abstract_available": False,
            "metadata_source": "Crossref",
            "abstract_source": None,
            "evidence_status": "provisional",
            "experimental_claims_verified": False,
        }

        try:
            enrichment = abstract_fn(doi)

            if isinstance(enrichment, dict):
                # Only accept a plainly identified abstract field.
                abstract = enrichment.get("abstract")

                if isinstance(abstract, str) and abstract.strip():
                    record["abstract"] = clean(abstract)
                    record["abstract_available"] = True
                    record["abstract_source"] = "OpenAlex"

        except Exception as exc:
            record["enrichment_warning"] = (
                type(exc).__name__ + ": " + str(exc)[:180]
            )

        results.append(record)

        if len(results) >= max_papers:
            break

    return {
        "question": question,
        "papers": results,
        "paper_count": len(results),
        "evidence_status": "provisional",
        "claim_verification": "not_performed",
        "warning": (
            "These are discovered publications, not verified "
            "experimental claims. No global performance record "
            "can be established from metadata alone."
        ),
    }
