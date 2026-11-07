# CuSelect-AI — Research Watcher History
#
# PSEUDOCODE
# 1. Load previously observed publication DOIs.
# 2. Treat the first successful scan as a baseline.
# 3. On later scans, identify never-before-seen DOIs.
# 4. Preserve first-seen timestamps.
# 5. Update last-seen timestamps.
# 6. Save history atomically.
# 7. Never change human review decisions or verified evidence.

import json
import os
import tempfile

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from .review_queue import normalize_doi


SCHEMA_VERSION = 1


class WatcherError(ValueError):
    pass


def empty_history():
    return {
        "schema_version": SCHEMA_VERSION,
        "initialized": False,
        "papers": {},
    }


def validate_history(history):
    if (
        not isinstance(history, dict)
        or history.get("schema_version") != SCHEMA_VERSION
        or type(history.get("initialized")) is not bool
        or not isinstance(history.get("papers"), dict)
    ):
        raise WatcherError("Invalid Research Watcher history")

    if not history["initialized"] and history["papers"]:
        raise WatcherError("Uninitialized history contains papers")

    for doi, record in history["papers"].items():
        if not isinstance(doi, str):
            raise WatcherError("Invalid DOI key")

        try:
            normalized = normalize_doi(doi)
        except ValueError as error:
            raise WatcherError("Invalid stored DOI") from error

        if normalized != doi:
            raise WatcherError("Noncanonical DOI in history")

        if (
            not isinstance(record, dict)
            or not isinstance(record.get("title"), str)
            or not record["title"].strip()
        ):
            raise WatcherError("Invalid publication metadata")

        for field in ("first_seen_utc", "last_seen_utc"):
            value = record.get(field)

            if not isinstance(value, str):
                raise WatcherError("Invalid observation timestamp")

            try:
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    raise ValueError("Timezone missing")
            except ValueError as error:
                raise WatcherError(
                    "Invalid observation timestamp"
                ) from error

    return deepcopy(history)


def observe_publications(history, publications, observed_at=None):
    """Compare publications against previously observed DOIs."""

    updated = validate_history(history)

    if observed_at is None:
        observed_at = datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        )

    if not isinstance(observed_at, str):
        raise WatcherError("Observation timestamp must be text")

    try:
        timestamp = datetime.fromisoformat(observed_at)
        if timestamp.tzinfo is None:
            raise ValueError("Timezone missing")
    except ValueError as error:
        raise WatcherError("Invalid observation timestamp") from error

    if not isinstance(publications, list):
        raise WatcherError("Publications must be a list")

    baseline = not updated["initialized"]
    baseline_dois = []
    new_dois = []
    previously_seen_dois = []
    processed = set()

    for paper in publications:
        if not isinstance(paper, dict):
            raise WatcherError("Invalid publication record")

        try:
            doi = normalize_doi(paper.get("doi"))
        except ValueError as error:
            raise WatcherError("Invalid publication DOI") from error

        title = paper.get("title")

        if not isinstance(title, str) or not title.strip():
            raise WatcherError("Publication title missing")

        if paper.get("scientific_status") != "unverified_discovery":
            raise WatcherError(
                "Watcher accepts only unverified discoveries"
            )

        if doi in processed:
            continue

        processed.add(doi)

        if doi in updated["papers"]:
            record = updated["papers"][doi]
            record["last_seen_utc"] = observed_at
            record["title"] = title
            previously_seen_dois.append(doi)

        else:
            updated["papers"][doi] = {
                "title": title,
                "first_seen_utc": observed_at,
                "last_seen_utc": observed_at,
            }

            if baseline:
                baseline_dois.append(doi)
            else:
                new_dois.append(doi)

    if processed:
        updated["initialized"] = True

    result = {
        "baseline_scan": baseline,
        "observed_count": len(processed),
        "baseline_dois": baseline_dois,
        "new_dois": new_dois,
        "previously_seen_dois": previously_seen_dois,
    }

    return validate_history(updated), result


def load_history(path):
    path = Path(path)

    if not path.exists():
        return empty_history()

    payload = json.loads(path.read_text(encoding="utf-8"))
    return validate_history(payload)


def save_history(path, history):
    """Safely replace only the Research Watcher history file."""

    validated = validate_history(history)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".watcher_history_",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(validated, handle, indent=2)
            handle.write("\n")

        os.replace(temporary_path, path)

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
