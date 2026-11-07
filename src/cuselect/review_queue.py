# CuSelect-AI — Human Literature Review Queue
#
# PSEUDOCODE
# 1. Receive papers from the Literature Discovery Agent.
# 2. Deduplicate publications using normalized DOIs.
# 3. Give new papers an initial "new" review status.
# 4. Allow researchers to mark papers for further review.
# 5. Preserve existing decisions and notes on rediscovery.
# 6. Save and reload the queue as structured JSON.
# 7. Never modify the authoritative evidence corpus.
# 8. Never turn paper review into scientific claim approval.

import json
import os
import re
import tempfile
from pathlib import Path


SCHEMA_VERSION = 1

REVIEW_STATUSES = {
    "new",
    "review_further",
    "set_aside",
}


class ReviewQueueError(ValueError):
    pass


def normalize_doi(value):
    """Normalize and validate a publication DOI."""

    if not isinstance(value, str):
        raise ReviewQueueError("DOI must be a string")

    doi = value.strip().lower()

    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "doi:",
    ):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]

    if not re.fullmatch(
        r"10\.\d{4,9}/[a-z0-9._;()/:\-+]+",
        doi,
    ):
        raise ReviewQueueError("Invalid DOI")

    return doi


def validate_queue(entries):
    """Check every stored paper before accepting the queue."""

    if not isinstance(entries, list):
        raise ReviewQueueError("Queue must be a list")

    seen = set()
    validated = []

    for entry in entries:
        if not isinstance(entry, dict):
            raise ReviewQueueError("Invalid queue entry")

        doi = normalize_doi(entry.get("doi"))

        if doi in seen:
            raise ReviewQueueError("Duplicate DOI in queue")

        seen.add(doi)

        if entry.get("review_status") not in REVIEW_STATUSES:
            raise ReviewQueueError("Invalid review status")

        if entry.get("scientific_status") != "unverified_discovery":
            raise ReviewQueueError(
                "Review queue cannot authorize scientific claims"
            )

        if (
            not isinstance(entry.get("title"), str)
            or not entry["title"].strip()
            or not isinstance(entry.get("notes"), str)
        ):
            raise ReviewQueueError("Invalid paper metadata")

        validated.append(dict(entry, doi=doi))

    return validated


def merge_discoveries(discoveries, existing=None):
    """Merge new papers while preserving human review decisions."""

    queue = validate_queue(
        list(existing) if existing is not None else []
    )

    by_doi = {
        entry["doi"]: entry
        for entry in queue
    }

    for paper in discoveries:
        if not isinstance(paper, dict):
            raise ReviewQueueError("Invalid discovery record")

        doi = normalize_doi(paper.get("doi"))

        if doi in by_doi:
            continue

        title = paper.get("title")

        if not isinstance(title, str) or not title.strip():
            raise ReviewQueueError("Publication title missing")

        by_doi[doi] = {
            "doi": doi,
            "title": title.strip(),
            "year": paper.get("year"),
            "journal": paper.get("journal", ""),
            "screening_status": paper.get(
                "screening_status", "manual_review"
            ),
            "scientific_status": "unverified_discovery",
            "review_status": "new",
            "notes": "",
            "publication_url": "https://doi.org/" + doi,
        }

    return validate_queue(
        sorted(by_doi.values(), key=lambda item: item["doi"])
    )


def update_review(entries, doi, status, notes=None):
    """Update human triage without approving scientific claims."""

    if status not in REVIEW_STATUSES:
        raise ReviewQueueError("Unsupported review decision")

    if notes is not None and not isinstance(notes, str):
        raise ReviewQueueError("Notes must be text")

    target = normalize_doi(doi)
    updated = validate_queue(entries)

    for entry in updated:
        if entry["doi"] == target:
            entry["review_status"] = status

            if notes is not None:
                entry["notes"] = notes

            return validate_queue(updated)

    raise ReviewQueueError("DOI not found in queue")


def save_queue(path, entries):
    """Atomically save the separate, unverified review queue."""

    path = Path(path)
    validated = validate_queue(entries)

    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "entries": validated,
    }

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".review_queue_",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(payload, handle, indent=2)
            handle.write("\n")

        os.replace(temporary_path, path)

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def load_queue(path):
    """Load the review queue without modifying its contents."""

    path = Path(path)

    if not path.exists():
        return []

    payload = json.loads(path.read_text(encoding="utf-8"))

    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != SCHEMA_VERSION
    ):
        raise ReviewQueueError("Unknown queue format")

    return validate_queue(payload.get("entries"))
