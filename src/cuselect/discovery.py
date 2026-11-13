
# CuSelect-AI — Scientific Literature Discovery
#
# PSEUDOCODE
# 1. Receive a scientific literature search query.
# 2. Validate the search query and number of results.
# 3. Normalize chemical notation in publication titles.
# 4. Screen titles for Cu, Ag, CO2 and electroreduction.
# 5. Request scholarly metadata from Crossref.
# 6. If Crossref returns HTTP 429, wait and retry.
# 7. Deduplicate publications by DOI.
# 8. Assign a preliminary scientific screening category.
# 9. Keep every discovered publication unverified.
# 10. Return structured publication metadata.

import json
import random
import re
import time
import unicodedata

from html import unescape
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# ============================================================
# 1. SCIENTIFIC TITLE NORMALIZATION
# ============================================================

def normalize_title(title):
    """
    Normalize scientific publication titles.

    Examples:
        CO<sub>2</sub> -> CO2
        CO₂ -> CO2
        Cu₂O -> Cu2O
    """

    # PSEUDOCODE
    # 1. Convert the input to text.
    # 2. Decode HTML entities.
    # 3. Convert HTML subscripts into normal characters.
    # 4. Remove remaining HTML tags.
    # 5. Normalize Unicode characters.
    # 6. Convert to lowercase and normalize whitespace.

    text = unicodedata.normalize(
        "NFKC",
        unescape(str(title)),
    )

    text = re.sub(
        r"<\s*sub\s*>\s*([^<]+?)\s*<\s*/\s*sub\s*>",
        lambda match: match.group(1).strip(),
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"<[^>]*>", " ", text)

    text = unicodedata.normalize("NFKC", text).lower()

    text = re.sub(r"[\u2010-\u2015]", "-", text)

    return " ".join(text.split())


# ============================================================
# 2. SCIENTIFIC TITLE SCREENING
# ============================================================

def screen_title(title):
    """
    Assign a preliminary screening category.

    Categories:
        high_priority
        manual_review
        out_of_scope_title

    This function does not verify scientific claims.
    """

    # PSEUDOCODE
    # 1. Normalize the publication title.
    # 2. Detect copper-containing terminology.
    # 3. Detect silver-containing terminology.
    # 4. Detect carbon dioxide terminology.
    # 5. Detect electrochemical terminology.
    # 6. Assign a preliminary screening category.

    text = normalize_title(title)

    copper = bool(
        re.search(
            r"\b(?:copper|cu|cuo[x0-9]*|cu[0-9]+o[x0-9]*"
            r"|ag[0-9]*cu|cu[0-9]*ag)\b",
            text,
        )
    )

    silver = bool(
        re.search(
            r"\b(?:silver|ag|ag[0-9]*cu|cu[0-9]*ag)\b",
            text,
        )
    )

    carbon_dioxide = bool(
        re.search(
            r"\b(?:co2|co2rr)\b|\bcarbon[\s-]+dioxide\b",
            text,
        )
    )

    electrochemical = bool(
        re.search(
            r"electroreduc|electrocatal|electrochem|electrolys|co2rr",
            text,
        )
    )

    if (
        carbon_dioxide
        and electrochemical
        and copper
        and silver
    ):
        return "high_priority"

    if carbon_dioxide and (
        electrochemical or copper or silver
    ):
        return "manual_review"

    return "out_of_scope_title"


# ============================================================
# 3. CROSSREF LITERATURE DISCOVERY
# ============================================================

def discover_crossref(query, rows=20):
    """
    Retrieve publication metadata from Crossref.

    Parameters
    ----------
    query : str
        Scientific literature search query.

    rows : int
        Number of requested records (1–100).

    Returns
    -------
    list[dict]
        Deduplicated publication metadata.

    Important
    ---------
    Discovery does not imply scientific verification.
    """

    # --------------------------------------------------------
    # STEP 1: VALIDATE INPUTS
    # --------------------------------------------------------

    if not isinstance(query, str) or not query.strip():
        raise ValueError(
            "A non-empty research query is required"
        )

    if not isinstance(rows, int) or isinstance(rows, bool):
        raise ValueError(
            "rows must be an integer"
        )

    if not 1 <= rows <= 100:
        raise ValueError(
            "rows must be between 1 and 100"
        )

    # --------------------------------------------------------
    # STEP 2: BUILD CROSSREF API REQUEST
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # STEP 3: REQUEST DATA WITH AUTOMATIC RETRIES
    # --------------------------------------------------------

    # PSEUDOCODE
    # 1. Request Crossref data.
    # 2. If successful, decode the JSON response.
    # 3. If HTTP 429 occurs, calculate a waiting period.
    # 4. Respect Crossref's Retry-After header when present.
    # 5. Retry up to five total attempts.
    # 6. Propagate persistent or unrelated errors.

    max_retries = 5

    for attempt in range(max_retries):

        try:
            with urlopen(request, timeout=20) as response:
                payload = json.load(response)

            break

        except HTTPError as error:

            if error.code != 429:
                raise

            if attempt == max_retries - 1:
                raise

            retry_after = error.headers.get("Retry-After")

            try:
                delay = max(
                    0,
                    float(retry_after),
                )
            except (TypeError, ValueError):
                delay = min(
                    60,
                    2 ** (attempt + 1),
                )

            # Add a small random delay to avoid
            # synchronized retry attempts.
            delay += random.uniform(0, 0.5)

            print(
                "Crossref rate limit reached. "
                f"Retrying in {delay:.1f} seconds..."
            )

            time.sleep(delay)

    # --------------------------------------------------------
    # STEP 4: PREPARE DOI DEDUPLICATION
    # --------------------------------------------------------

    candidates = []
    seen_dois = set()

    # --------------------------------------------------------
    # STEP 5: PROCESS CROSSREF PUBLICATION METADATA
    # --------------------------------------------------------

    for item in payload.get("message", {}).get("items", []):

        # Normalize DOI.
        doi = str(
            item.get("DOI", "")
        ).strip().lower()

        # Skip missing, malformed or duplicate DOIs.
        if not doi.startswith("10.") or doi in seen_dois:
            continue

        titles = item.get("title") or []

        # Skip publications without usable titles.
        if not titles or not str(titles[0]).strip():
            continue

        seen_dois.add(doi)

        title = str(titles[0]).strip()

        # Extract publication year.
        dates = (
            item.get("published", {})
            .get("date-parts", [])
        )

        year = (
            dates[0][0]
            if dates and dates[0]
            else None
        )

        # Extract journal.
        journal = item.get("container-title") or []

        # ----------------------------------------------------
        # STEP 6: BUILD STRUCTURED PUBLICATION RECORD
        # ----------------------------------------------------

        candidates.append(
            {
                "doi": doi,
                "title": title,
                "year": year,
                "journal": (
                    journal[0] if journal else ""
                ),
                "screening_status": screen_title(title),
                "scientific_status": "unverified_discovery",
                "metadata_source": "Crossref",
                "publication_url": (
                    "https://doi.org/" + doi
                ),
            }
        )

    # --------------------------------------------------------
    # STEP 7: RETURN DISCOVERED PUBLICATIONS
    # --------------------------------------------------------

    return candidates
