
"""Read-only multi-query Crossref discovery for scientific research."""

import html
import re

from cuselect.discovery import discover_crossref


def normalize_doi(value):
    doi = str(value or "").strip().lower()
    return re.sub(
        r"^https?://(?:dx\.)?doi\.org/", "", doi
    )


def clean_title(value):
    text = re.sub(r"<[^>]*>", " ", str(value or ""))
    return " ".join(html.unescape(text).split())


def build_queries(question):
    """Generate a small, deterministic terminology expansion."""
    q = " ".join(str(question).strip().split())

    if not q:
        raise ValueError("Research question is required.")

    base = re.sub(
        r"^(what|which|how|find|show|identify|compare|"
        r"summarize)\b.*?\b(in|for|about|on)\b\s*",
        "",
        q,
        flags=re.I,
    )

    variants = [q, base]

    substitutions = [
        (r"\bCO₂\b|\bCO2\b", "carbon dioxide"),
        (r"\bcarbon dioxide\b", "CO2"),
        (r"\bethylene\b", "C2H4"),
        (r"\bC2H4\b", "ethylene"),
        (r"\bfaradaic efficiency\b", "selectivity"),
        (r"\belectroreduction\b", "electrochemical reduction"),
    ]

    for pattern, replacement in substitutions:
        if re.search(pattern, base, flags=re.I):
            variants.append(
                re.sub(pattern, replacement, base, flags=re.I)
            )

    # Keep original and expanded searches short and reproducible.
    unique = []
    for query in variants:
        query = query.strip(" ?.")
        if query and query.casefold() not in {
            x.casefold() for x in unique
        }:
            unique.append(query)

    return unique[:5]


def multiquery_discover(
    query,
    rows=20,
    *,
    search_fn=None,
):
    """Return unique Crossref records, compatible with discover_crossref.

    Does not verify experimental measurements.
    """
    search_fn = search_fn or discover_crossref
    queries = build_queries(query)

    # 'rows' is the total result budget, not per-query budget.
    per_query = max(1, (rows + len(queries) - 1) // len(queries))

    unique = {}
    errors = []
    successful_queries = 0

    for search_query in queries:
        try:
            results = search_fn(search_query, rows=per_query)
            if not isinstance(results, list):
                raise TypeError("Expected publication list")
            successful_queries += 1
        except Exception as exc:
            errors.append(
                f"{search_query}: {type(exc).__name__}: {exc}"
            )
            continue

        for item in results:
            if not isinstance(item, dict):
                continue

            doi = normalize_doi(item.get("doi"))
            title = clean_title(item.get("title"))

            if not doi or not title:
                continue

            if doi not in unique:
                unique[doi] = {
                    **item,
                    "doi": doi,
                    "title": title,
                    "screening_status": "not_screened",
                    "scientific_status": "provisional",
                }

    if successful_queries == 0:
        raise RuntimeError(
            "Every Crossref query failed: " + "; ".join(errors)
        )

    # Rank by query-title overlap only; scientific LLM screening
    # must still determine whether a paper is relevant.
    stop = {
        "what", "which", "the", "for", "have", "been",
        "reported", "during", "with", "from", "about",
        "highest", "current", "state", "art", "are",
    }

    terms = set(
        re.findall(r"[a-z0-9]+", query.lower())
    ) - stop

    def title_score(item):
        title_terms = set(
            re.findall(r"[a-z0-9]+", item["title"].lower())
        )
        return len(terms & title_terms)

    return sorted(
        unique.values(),
        key=lambda p: (
            title_score(p),
            int(p.get("year") or 0),
        ),
        reverse=True,
    )[:rows]
