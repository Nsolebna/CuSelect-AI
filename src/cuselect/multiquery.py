# CuSelect-AI — Reliable Multi-Query Discovery
#
# PSEUDOCODE
# 1. Receive multiple scientific literature queries.
# 2. Load previous successful searches from a checkpoint.
# 3. Skip queries that have already been completed.
# 4. Wait between new Crossref requests.
# 5. Search Crossref using the existing discovery module.
# 6. Save each successful query immediately.
# 7. Combine results and remove duplicate DOIs.
# 8. Keep discovered publications scientifically unverified.
# 9. Return the combined literature records.

import json
import os
import time
from pathlib import Path

from cuselect.discovery import discover_crossref


def load_checkpoint(checkpoint_path):
    """Load previously completed searches."""

    path = Path(checkpoint_path)

    if not path.exists():
        return {"version": 1, "completed": []}

    with path.open("r", encoding="utf-8") as file:
        checkpoint = json.load(file)

    if (
        not isinstance(checkpoint, dict)
        or checkpoint.get("version") != 1
        or not isinstance(checkpoint.get("completed"), list)
    ):
        raise ValueError("Invalid discovery checkpoint format")

    return checkpoint


def save_checkpoint(checkpoint_path, checkpoint):
    """Save progress using an atomic file replacement."""

    path = Path(checkpoint_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_name(path.name + ".tmp")

    try:
        with temporary_path.open(
            "w", encoding="utf-8"
        ) as file:
            json.dump(checkpoint, file, indent=2)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary_path, path)

    finally:
        temporary_path.unlink(missing_ok=True)


def combine_unique_papers(completed):
    """Deduplicate publications across all completed queries."""

    papers = []
    seen_dois = set()

    for entry in completed:
        for paper in entry["papers"]:
            doi = paper["doi"].strip().lower()

            if doi in seen_dois:
                continue

            seen_dois.add(doi)
            papers.append(paper)

    return papers


def discover_multiple(
    queries,
    rows=20,
    checkpoint_path="data/discovery_checkpoint.json",
    delay_seconds=2.0,
):
    """
    Run multiple Crossref searches with checkpointing.

    Previously completed query/rows combinations are
    reused from the checkpoint.

    A failed request propagates its exception. Successful
    earlier searches remain saved on disk.
    """

    # PSEUDOCODE
    # 1. Validate queries and pacing settings.
    # 2. Load the checkpoint.
    # 3. Identify completed searches.
    # 4. Run only unfinished searches.
    # 5. Pause between new API requests.
    # 6. Save immediately after each successful search.
    # 7. Deduplicate all matching results.

    if isinstance(queries, (str, bytes)):
        raise ValueError("queries must be a list of strings")

    queries = list(queries)

    if not queries or any(
        not isinstance(query, str) or not query.strip()
        for query in queries
    ):
        raise ValueError("Provide non-empty search queries")

    if (
        not isinstance(rows, int)
        or isinstance(rows, bool)
        or not 1 <= rows <= 100
    ):
        raise ValueError("rows must be between 1 and 100")

    if (
        isinstance(delay_seconds, bool)
        or not isinstance(delay_seconds, (int, float))
        or not 0 <= delay_seconds <= 60
    ):
        raise ValueError(
            "delay_seconds must be between 0 and 60"
        )

    checkpoint = load_checkpoint(checkpoint_path)

    completed_keys = {
        (entry["query"], entry["rows"])
        for entry in checkpoint["completed"]
    }

    new_requests = 0

    for number, raw_query in enumerate(queries, start=1):
        query = raw_query.strip()
        key = (query, rows)

        print(f"\nQuery {number}: {query}")

        if key in completed_keys:
            print("Already completed — using saved results.")
            continue

        if new_requests > 0:
            print(f"Waiting {delay_seconds}s before next query...")
            time.sleep(delay_seconds)

        # The existing function handles HTTP 429 retries.
        papers = discover_crossref(query, rows=rows)
        new_requests += 1

        checkpoint["completed"].append({
            "query": query,
            "rows": rows,
            "papers": papers,
        })

        save_checkpoint(checkpoint_path, checkpoint)
        completed_keys.add(key)

        print(f"Retrieved: {len(papers)}")
        print("Checkpoint saved.")

    # Include only the requested queries, not unrelated
    # searches that might exist in the checkpoint.
    requested_keys = {
        (query.strip(), rows) for query in queries
    }

    relevant_completed = [
        entry
        for entry in checkpoint["completed"]
        if (entry["query"], entry["rows"]) in requested_keys
    ]

    unique_papers = combine_unique_papers(
        relevant_completed
    )

    print("\nMULTI-QUERY DISCOVERY COMPLETE")
    print(f"Unique publications: {len(unique_papers)}")

    return unique_papers
