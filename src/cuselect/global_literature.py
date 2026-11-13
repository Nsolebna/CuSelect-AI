"""Global literature discovery with provisional relevance screening."""

import html
import re

from cuselect.discovery import discover_crossref


def clean_text(value):
    text = re.sub(r"<[^>]*>", " ", str(value or ""))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def normalize_doi(doi):
    doi = str(doi or "").strip().lower()
    doi = re.sub(
        r"^https?://(?:dx\.)?doi\.org/",
        "",
        doi,
    )
    return doi


def screen_ethylene_paper(record):
    """Title-based screening, NOT scientific claim verification."""

    title = clean_text(record.get("title"))
    t = title.lower()

    ethylene = bool(
        re.search(r"\b(ethylene|ethene|c2h4)\b", t)
    )
    copper = bool(
        re.search(r"\b(copper|cu-based|cu-ag|ag-cu|agcu)\b", t)
    )
    electrochemistry = bool(
        re.search(
            r"electroreduction|electrochemical|co2|carbon dioxide",
            t,
        )
    )

    co_only = bool(
        re.search(r"\b(to co|to carbon monoxide)\b", t)
    ) and not ethylene

    score = (
        5 * ethylene
        + 3 * copper
        + 2 * electrochemistry
        - 5 * co_only
    )

    if ethylene and copper:
        relevance = "direct_title_match"
    elif ethylene:
        relevance = "ethylene_related"
    elif copper and electrochemistry and not co_only:
        relevance = "background_or_related"
    else:
        relevance = "low_title_relevance"

    return {
        **record,
        "title": title,
        "doi": normalize_doi(record.get("doi")),
        "relevance": relevance,
        "relevance_score": score,
        "evidence_status": "provisional_metadata_only",
        "experimental_claims_verified": False,
    }


def search_global_ethylene_literature(
    query,
    *,
    rows=20,
    limit=10,
    search_fn=None,
):
    """Search Crossref, deduplicate and screen titles."""

    if not str(query).strip():
        raise ValueError("Search query cannot be empty.")

    search_fn = search_fn or discover_crossref
    results = search_fn(query, rows=rows)

    if not isinstance(results, list):
        raise ValueError("Expected a list of publication records.")

    unique = {}

    for record in results:
        if not isinstance(record, dict):
            continue

        screened = screen_ethylene_paper(record)
        doi = screened["doi"]

        if not doi:
            continue

        previous = unique.get(doi)

        if (
            previous is None
            or screened["relevance_score"]
            > previous["relevance_score"]
        ):
            unique[doi] = screened

    ranked = sorted(
        unique.values(),
        key=lambda item: (
            item["relevance_score"],
            int(item.get("year") or 0),
        ),
        reverse=True,
    )

    return {
        "query": query,
        "source": "Crossref",
        "screening_method": "title_keyword_heuristics",
        "total_unique": len(ranked),
        "papers": ranked[:limit],
        "warning": (
            "Publication metadata only. Titles and relevance scores "
            "do not verify experimental performance, novelty, "
            "paper quality, or state-of-the-art claims."
        ),
    }
