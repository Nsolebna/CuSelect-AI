# CuSelect-AI — Research Watcher Reporting
#
# PSEUDOCODE
# 1. Generate a unique identifier for each scan.
# 2. Save a readable scientific research digest.
# 3. Prevent existing reports from being overwritten.
# 4. Record successful or failed scan events.
# 5. Include timestamps and discovery counts.
# 6. Keep reports separate from scientific evidence.
# 7. Never modify the human literature-review queue.

import fcntl
import json
import os
import re
import uuid

from datetime import datetime, timezone
from pathlib import Path

from .watcher_scan import format_digest


class WatcherReportingError(ValueError):
    pass


def new_run_id():
    """Create an identifier for one monitoring run."""

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    return f"{timestamp}_{uuid.uuid4().hex[:12]}"


def validate_run_id(run_id):
    if (
        not isinstance(run_id, str)
        or not re.fullmatch(
            r"[A-Za-z0-9_-]{8,80}",
            run_id,
        )
    ):
        raise WatcherReportingError("Invalid scan run ID")

    return run_id


def save_digest(directory, run_id, digest):
    """Save a report without overwriting existing reports."""

    validate_run_id(run_id)

    if not isinstance(digest, dict):
        raise WatcherReportingError("Digest must be a dictionary")

    # The existing formatter provides the scientific
    # labels and explicitly marks evidence as unverified.
    report_text = format_digest(digest)

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / f"{run_id}.txt"

    # Exclusive creation prevents accidental replacement
    # of an existing report with the same run ID.
    with path.open("x", encoding="utf-8") as handle:
        handle.write(report_text)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

    return path


def append_scan_event(
    path,
    *,
    run_id,
    status,
    mode,
    retrieved_count=0,
    newly_seen_count=0,
    error=None,
):
    """Append a timestamped monitoring event to JSONL."""

    validate_run_id(run_id)

    if status not in ("success", "failure"):
        raise WatcherReportingError("Invalid scan status")

    if mode not in ("preview", "save"):
        raise WatcherReportingError("Invalid scan mode")

    for count in (retrieved_count, newly_seen_count):
        if type(count) is not int or count < 0:
            raise WatcherReportingError("Invalid scan count")

    if newly_seen_count > retrieved_count:
        raise WatcherReportingError(
            "Newly seen count exceeds retrieved count"
        )

    if error is not None and not isinstance(error, str):
        raise WatcherReportingError("Error must be text")

    event = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds"),
        "status": status,
        "mode": mode,
        "retrieved_count": retrieved_count,
        "newly_seen_count": newly_seen_count,
        "error": error,
    }

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Lock the event file while appending to prevent
    # overlapping cooperative writers from interleaving.
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

        try:
            handle.write(json.dumps(event) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    return event
