
# CuSelect-AI — Multi-Source Abstract Retrieval
#
# PSEUDOCODE
# 1. Load papers already enriched using Crossref.
# 2. Preserve existing abstracts and their provenance.
# 3. Identify publications still missing abstracts.
# 4. Query OpenAlex by DOI for missing abstracts only.
# 5. Reconstruct OpenAlex inverted-index abstracts.
# 6. Retry temporary API failures with backoff.
# 7. Cache each successful DOI lookup immediately.
# 8. Preserve the original scientific verification status.
# 9. Return the enriched publication records.

import json
import math
import os
import random
import time

from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def reconstruct_abstract(inverted_index):
    """Reconstruct an abstract from an OpenAlex word index."""

    if not isinstance(inverted_index, dict):
        return ""

    positions = {}

    for word, locations in inverted_index.items():
        if not isinstance(word, str):
            return ""

        if not isinstance(locations, list):
            return ""

        for position in locations:
            if (
                not isinstance(position, int)
                or isinstance(position, bool)
                or position < 0
                or position in positions
            ):
                return ""

            positions[position] = word

    if not positions:
        return ""

    # Reject missing token positions rather than silently
    # reconstructing an incomplete or corrupted abstract.
    if set(positions) != set(range(len(positions))):
        return ""

    return " ".join(
        positions[index]
        for index in range(len(positions))
    )


def empty_result(doi, status):
    """Represent an unsuccessful abstract lookup explicitly."""

    return {
        "doi": doi,
        "abstract": "",
        "abstract_status": status,
        "abstract_source": "OpenAlex",
        "openalex_id": None,
    }


def fetch_openalex_abstract(doi, max_attempts=5):
    """Retrieve an abstract from OpenAlex using its DOI."""

    # PSEUDOCODE
    # 1. Validate DOI and retry settings.
    # 2. Request the matching OpenAlex work.
    # 3. Extract its inverted-index abstract.
    # 4. Reconstruct the abstract in word order.
    # 5. Return its source and retrieval status.
    # 6. Retry HTTP 429 and temporary server errors.

    if not isinstance(doi, str) or not doi.strip():
        raise ValueError("A DOI is required")

    if (
        not isinstance(max_attempts, int)
        or isinstance(max_attempts, bool)
        or max_attempts < 1
    ):
        raise ValueError("max_attempts must be positive")

    doi = doi.strip().lower()

    url = (
        "https://api.openalex.org/works/"
        + quote("https://doi.org/" + doi, safe="")
    )

    request = Request(
        url,
        headers={
            "User-Agent": (
                "CuSelect-AI/0.1 "
                "(scientific abstract retrieval)"
            ),
            "Accept": "application/json",
        },
    )

    for attempt in range(max_attempts):
        try:
            with urlopen(request, timeout=20) as response:
                work = json.load(response)

            if not isinstance(work, dict):
                raise ValueError("Invalid OpenAlex response")

            returned_doi = work.get("doi")

            # Avoid assigning an abstract to the wrong DOI.
            if returned_doi:
                canonical = (
                    "https://doi.org/" + doi
                )

                if (
                    str(returned_doi).lower().rstrip("/")
                    != canonical
                ):
                    raise ValueError("OpenAlex DOI mismatch")

            abstract = reconstruct_abstract(
                work.get("abstract_inverted_index")
            )

            return {
                "doi": doi,
                "abstract": abstract,
                "abstract_status": (
                    "available" if abstract else "missing"
                ),
                "abstract_source": "OpenAlex",
                "openalex_id": work.get("id"),
            }

        except HTTPError as error:
            if error.code == 404:
                return empty_result(
                    doi, "record_not_found"
                )

            if error.code not in (429, 500, 502, 503, 504):
                raise

            if attempt == max_attempts - 1:
                raise

            retry_after = error.headers.get("Retry-After")

            try:
                delay = float(retry_after)

                if not math.isfinite(delay):
                    raise ValueError

                delay = max(0.0, delay)

            except (TypeError, ValueError):
                delay = min(60, 2 ** (attempt + 1))

            delay += random.uniform(0, 0.5)

            print(
                f"OpenAlex HTTP {error.code} for {doi}. "
                f"Retrying in {delay:.1f}s..."
            )

            time.sleep(delay)

        except (URLError, TimeoutError):
            if attempt == max_attempts - 1:
                raise

            delay = (
                min(60, 2 ** (attempt + 1))
                + random.uniform(0, 0.5)
            )

            time.sleep(delay)


def load_fallback_cache(path):
    """Load cached OpenAlex lookup results."""

    path = Path(path)

    if not path.exists():
        return {"version": 1, "records": {}}

    with path.open(encoding="utf-8") as file:
        cache = json.load(file)

    if (
        not isinstance(cache, dict)
        or cache.get("version") != 1
        or not isinstance(cache.get("records"), dict)
    ):
        raise ValueError("Invalid OpenAlex cache")

    return cache


def save_fallback_cache(path, cache):
    """Atomically save OpenAlex lookup results."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_name(path.name + ".tmp")

    try:
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(
                cache, file, indent=2, ensure_ascii=False
            )
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary, path)

    finally:
        temporary.unlink(missing_ok=True)


def enrich_with_openalex(
    papers,
    cache_path="data/openalex_abstract_cache.json",
    delay_seconds=3.0,
):
    """
    Recover missing abstracts using OpenAlex.

    Existing abstracts are preserved.
    Each successful DOI lookup is cached.
    Source provenance is retained.
    """

    if (
        isinstance(delay_seconds, bool)
        or not isinstance(delay_seconds, (int, float))
        or not math.isfinite(delay_seconds)
        or not 0 <= delay_seconds <= 60
    ):
        raise ValueError("Invalid delay_seconds")

    cache = load_fallback_cache(cache_path)

    enriched = []
    seen_dois = set()
    requests_made = 0

    for paper in papers:
        record = dict(paper)

        doi = str(record.get("doi") or "").strip().lower()

        if not doi or doi in seen_dois:
            continue

        seen_dois.add(doi)

        # Never overwrite an existing abstract.
        if (
            record.get("abstract_status") == "available"
            and str(record.get("abstract") or "").strip()
        ):
            enriched.append(record)
            continue

        if doi in cache["records"]:
            result = cache["records"][doi]
            print(f"Cached OpenAlex result: {doi}")

        else:
            if requests_made > 0:
                time.sleep(delay_seconds)

            print(f"Searching OpenAlex: {doi}")

            result = fetch_openalex_abstract(doi)
            requests_made += 1

            cache["records"][doi] = result
            save_fallback_cache(cache_path, cache)

        # Preserve a successful abstract from Crossref.
        # For missing results, record the fallback status.
        if result["abstract_status"] == "available":
            record["abstract"] = result["abstract"]
            record["abstract_status"] = "available"
            record["abstract_source"] = "OpenAlex"
        else:
            record["abstract"] = ""
            record["abstract_status"] = result[
                "abstract_status"
            ]
            record["abstract_source"] = "OpenAlex"

        record["openalex_id"] = result.get("openalex_id")

        # An abstract is not verified scientific evidence.
        record["scientific_status"] = (
            "unverified_discovery"
        )

        enriched.append(record)

    return enriched
