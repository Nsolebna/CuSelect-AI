
# CuSelect-AI — Scientific Abstract Retrieval
#
# PSEUDOCODE
# 1. Load classified scientific publications.
# 2. Prioritize Cu/Ag-related publications.
# 3. Retrieve abstracts from Crossref using DOI.
# 4. Retry temporary API rate-limit errors.
# 5. Clean abstract markup into readable text.
# 6. Record missing abstracts without inventing content.
# 7. Save successful retrieval progress after every paper.
# 8. Reuse cached results when restarting.
# 9. Preserve original scientific metadata and status.

import json
import os
import random
import re
import time

from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


class AbstractParser(HTMLParser):
    """Extract readable text from Crossref abstract markup."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def clean_abstract(raw_abstract):
    """Remove XML/HTML markup from abstract text."""

    if not raw_abstract:
        return ""

    parser = AbstractParser()
    parser.feed(str(raw_abstract))
    parser.close()

    return re.sub(
        r"\s+", " ", " ".join(parser.parts)
    ).strip()


def fetch_crossref_abstract(doi, max_attempts=5):
    """
    Retrieve a single DOI record from Crossref.

    Returns:
        Dictionary containing abstract and retrieval status.

    HTTP 404 means no Crossref record was found.
    HTTP 429 triggers bounded retries.
    Other request failures are propagated.
    """

    if not isinstance(doi, str) or not doi.strip():
        raise ValueError("A valid DOI is required")

    if (
        not isinstance(max_attempts, int)
        or isinstance(max_attempts, bool)
        or max_attempts < 1
    ):
        raise ValueError("max_attempts must be positive")

    normalized_doi = doi.strip().lower()

    url = (
        "https://api.crossref.org/works/"
        + quote(normalized_doi, safe="")
    )

    request = Request(
        url,
        headers={
            "User-Agent": (
                "CuSelect-AI/0.1 "
                "(scientific literature research prototype)"
            ),
            "Accept": "application/json",
        },
    )

    for attempt in range(max_attempts):
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.load(response)

            message = payload.get("message", {})
            raw_abstract = message.get("abstract") or ""
            abstract = clean_abstract(raw_abstract)

            return {
                "doi": normalized_doi,
                "abstract": abstract,
                "abstract_status": (
                    "available" if abstract else "missing"
                ),
                "abstract_source": "Crossref",
            }

        except HTTPError as error:
            if error.code == 404:
                return {
                    "doi": normalized_doi,
                    "abstract": "",
                    "abstract_status": "record_not_found",
                    "abstract_source": "Crossref",
                }

            if error.code != 429:
                raise

            if attempt == max_attempts - 1:
                raise

            retry_after = error.headers.get("Retry-After")

            try:
                delay = max(0, float(retry_after))
            except (TypeError, ValueError):
                delay = min(60, 2 ** (attempt + 1))

            delay += random.uniform(0, 0.5)

            print(
                f"Crossref rate limit for {normalized_doi}. "
                f"Retrying in {delay:.1f}s..."
            )

            time.sleep(delay)


def load_abstract_cache(cache_path):
    """Load saved abstract retrieval results."""

    path = Path(cache_path)

    if not path.exists():
        return {"version": 1, "records": {}}

    with path.open(encoding="utf-8") as file:
        cache = json.load(file)

    if (
        not isinstance(cache, dict)
        or cache.get("version") != 1
        or not isinstance(cache.get("records"), dict)
    ):
        raise ValueError("Invalid abstract cache format")

    return cache


def save_abstract_cache(cache_path, cache):
    """Save abstract cache using atomic replacement."""

    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_name(path.name + ".tmp")

    try:
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(
                cache,
                file,
                indent=2,
                ensure_ascii=False,
            )
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary, path)

    finally:
        temporary.unlink(missing_ok=True)


def retrieve_abstracts(
    papers,
    cache_path="data/abstract_cache.json",
    delay_seconds=3.0,
    limit=None,
):
    """
    Retrieve abstracts with caching and request pacing.

    The returned records preserve original publication
    metadata and include abstract retrieval information.

    limit restricts the number of input publications
    processed during a run.
    """

    if (
        isinstance(delay_seconds, bool)
        or not isinstance(delay_seconds, (int, float))
        or not 0 <= delay_seconds <= 60
    ):
        raise ValueError("Invalid delay_seconds")

    if limit is not None and (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < 1
    ):
        raise ValueError("limit must be a positive integer")

    cache = load_abstract_cache(cache_path)
    enriched = []
    requests_made = 0
    seen_dois = set()

    selected = papers if limit is None else papers[:limit]

    for number, paper in enumerate(selected, start=1):
        doi = str(paper.get("doi") or "").strip().lower()

        if not doi or doi in seen_dois:
            continue

        seen_dois.add(doi)

        print(f"\nPaper {number}: {doi}")

        if doi in cache["records"]:
            print("Using cached abstract result.")
            result = cache["records"][doi]

        else:
            if requests_made > 0:
                time.sleep(delay_seconds)

            result = fetch_crossref_abstract(doi)
            requests_made += 1

            cache["records"][doi] = result
            save_abstract_cache(cache_path, cache)

            print(
                "Abstract status:",
                result["abstract_status"],
            )

        enriched_paper = dict(paper)
        enriched_paper.update(result)

        enriched.append(enriched_paper)

    return enriched
