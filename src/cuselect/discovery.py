# CuSelect-AI — Scientific Literature Discovery
#
# PSEUDOCODE
# 1. Receive scholarly publication metadata.
# 2. Normalize scientific terminology.
# 3. Screen titles for Cu, Ag, CO2 and electroreduction.
# 4. Assign a preliminary review category.
# 5. Retrieve live metadata from Crossref.
# 6. Deduplicate papers by DOI.
# 7. Never add publications to verified scientific evidence.

import re
import json
import unicodedata

from urllib.parse import urlencode
from urllib.request import Request, urlopen


def normalize_title(title):
    """Normalize chemical notation and publication-title markup."""

    from html import unescape

    text = unicodedata.normalize(
        "NFKC", unescape(str(title))
    )

    # Convert CO<sub>2</sub> into CO2 without separating
    # the chemical formula into unrelated tokens.
    text = re.sub(
        r"<\s*sub\s*>\s*([^<]+?)\s*<\s*/\s*sub\s*>",
        lambda match: match.group(1).strip(),
        text,
        flags=re.IGNORECASE,
    )

    # Remove remaining HTML tags.
    text = re.sub(r"<[^>]*>", " ", text)

    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"[\u2010-\u2015]", "-", text)

    return " ".join(text.split())


def screen_title(title):
    """Conservative preliminary screening, never scientific approval."""

    text = normalize_title(title)

    # Recognize elemental Cu, copper oxides and Cu-Ag formulas.
    copper = bool(re.search(
        r"\b(?:copper|cu|cuo[x0-9]*|cu[0-9]+o[x0-9]*"
        r"|ag[0-9]*cu|cu[0-9]*ag)\b",
        text,
    ))

    silver = bool(re.search(
        r"\b(?:silver|ag|ag[0-9]*cu|cu[0-9]*ag)\b",
        text,
    ))

    carbon_dioxide = bool(re.search(
        r"\b(?:co2|co2rr)\b|\bcarbon[\s-]+dioxide\b",
        text,
    ))

    electrochemical = bool(re.search(
        r"electroreduc|electrocatal|electrochem|electrolys|co2rr",
        text,
    ))

    if carbon_dioxide and electrochemical and copper and silver:
        return "high_priority"

    # Missing catalyst details in a title should not
    # automatically exclude CO2 electroreduction papers.
    if carbon_dioxide and (
        electrochemical or copper or silver
    ):
        return "manual_review"

    return "out_of_scope_title"


def discover_crossref(query, rows=20):
    """Discover publication metadata without modifying the corpus."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("A non-empty research query is required")

    if not isinstance(rows, int) or isinstance(rows, bool):
        raise ValueError("rows must be an integer")

    if not 1 <= rows <= 100:
        raise ValueError("rows must be between 1 and 100")

    params = {
        "query.bibliographic": query,
        "filter": "type:journal-article",
        "rows": rows,
        "select": "DOI,title,published,container-title,URL",
    }

    url = (
        "https://api.crossref.org/works?"
        + urlencode(params)
    )

    request = Request(
        url,
        headers={
            "User-Agent": (
                "CuSelect-AI/0.1 "
                "(scientific metadata discovery prototype)"
            ),
        },
    )

    with urlopen(request, timeout=20) as response:
        payload = json.load(response)

    candidates = []
    seen_dois = set()

    for item in payload.get("message", {}).get("items", []):
        doi = str(item.get("DOI", "")).strip().lower()

        if not doi.startswith("10.") or doi in seen_dois:
            continue

        titles = item.get("title") or []

        if not titles or not str(titles[0]).strip():
            continue

        seen_dois.add(doi)

        title = str(titles[0]).strip()
        dates = item.get("published", {}).get("date-parts", [])
        year = dates[0][0] if dates and dates[0] else None

        journal = item.get("container-title") or []

        candidates.append({
            "doi": doi,
            "title": title,
            "year": year,
            "journal": journal[0] if journal else "",
            "screening_status": screen_title(title),
            "scientific_status": "unverified_discovery",
            "metadata_source": "Crossref",
            "publication_url": "https://doi.org/" + doi,
        })

    return candidates
