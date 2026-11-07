# CuSelect-AI — Research Watcher Scan & Digest
#
# PSEUDOCODE
# 1. Load the initialized Research Watcher history.
# 2. Discover current scientific publications.
# 3. Reject an incomplete or failed scan.
# 4. Compare retrieved DOIs against observation history.
# 5. Separate newly encountered and known publications.
# 6. Prioritize newly encountered papers for review.
# 7. Generate a readable research digest.
# 8. Do not change history, review decisions or verified evidence.

from pathlib import Path

from .discovery import discover_crossref
from .research_watcher import (
    load_history,
    observe_publications,
    save_history,
)


DEFAULT_QUERY = (
    "copper silver CO2 electroreduction "
    "ethylene ethanol"
)

PRIORITY = {
    "high_priority": 0,
    "manual_review": 1,
    "out_of_scope_title": 2,
}


class WatcherScanError(RuntimeError):
    pass


def scan_and_digest(
    history_path,
    query=DEFAULT_QUERY,
    rows=30,
    minimum_results=25,
    persist_history=False,
):
    """Run a validated scan, optionally saving DOI history."""

    if type(persist_history) is not bool:
        raise WatcherScanError(
            "persist_history must be a boolean"
        )


    path = Path(history_path)

    # PSEUDOCODE:
    # Require an existing monitoring baseline.
    if not path.is_file():
        raise WatcherScanError(
            "Research Watcher baseline does not exist"
        )

    original_bytes = path.read_bytes()
    history = load_history(path)

    if not history["initialized"]:
        raise WatcherScanError(
            "Research Watcher baseline is not initialized"
        )

    # Validate the expected result threshold.
    if (
        type(minimum_results) is not int
        or minimum_results < 1
        or minimum_results > rows
    ):
        raise WatcherScanError(
            "Invalid minimum-results threshold"
        )

    # Retrieve current publication metadata.
    # Network errors propagate; no history is modified.
    publications = discover_crossref(
        query=query,
        rows=rows,
    )

    if len(publications) < minimum_results:
        raise WatcherScanError(
            "Insufficient Crossref results. "
            "Scan rejected without changing history."
        )

    # Compare against persistent history in memory only.
    proposed_history, observation = observe_publications(
        history,
        publications,
    )

    if observation["baseline_scan"]:
        raise WatcherScanError(
            "Expected an existing monitoring baseline"
        )

    new_dois = set(observation["new_dois"])

    new_papers = [
        paper
        for paper in publications
        if paper["doi"] in new_dois
    ]

    # Prioritize papers without treating relevance
    # screening as scientific verification.
    new_papers.sort(
        key=lambda paper: (
            PRIORITY.get(
                paper["screening_status"], 3
            ),
            paper["doi"],
        )
    )

    digest = {
        "query": query,
        "retrieved_count": len(publications),
        "previously_seen_count": len(
            observation["previously_seen_dois"]
        ),
        "newly_seen_count": len(new_papers),
        "new_papers": new_papers,
        "existing_history_count": len(
            history["papers"]
        ),
        "proposed_history_count": len(
            proposed_history["papers"]
        ),
        "history_saved": False,
    }

    # PSEUDOCODE
    # Commit the proposed history only after all validation.
    # Refuse a stale update if another process changed the file.
    if persist_history:
        if path.read_bytes() != original_bytes:
            raise WatcherScanError(
                "Watcher history changed during the scan"
            )

        save_history(path, proposed_history)
        digest["history_saved"] = True

    return digest


def format_digest(digest):
    """Format a human-readable literature discovery report."""

    lines = [
        "CUSELECT-AI — SCIENTIFIC RESEARCH DIGEST",
        "=" * 60,
        f"Publications retrieved: {digest['retrieved_count']}",
        (
            "Previously encountered in this scan: "
            f"{digest['previously_seen_count']}"
        ),
        (
            "Newly encountered DOIs: "
            f"{digest['newly_seen_count']}"
        ),
        "",
        "NEW-TO-WATCHER PUBLICATIONS",
        "=" * 60,
    ]

    if not digest["new_papers"]:
        lines.append(
            "No previously unseen DOI was found in this scan."
        )

    for index, paper in enumerate(
        digest["new_papers"], start=1
    ):
        lines.extend([
            "",
            f"{index}. {paper['title']}",
            f"   Year: {paper['year']}",
            f"   DOI: {paper['doi']}",
            (
                "   Screening: "
                f"{paper['screening_status']}"
            ),
            "   Evidence status: UNVERIFIED",
        ])

    lines.extend([
        "",
        (
            "History saved: YES"
            if digest.get("history_saved")
            else "History saved: NO (read-only preview)"
        ),
        "Human review queue modified: NO",
        "Verified scientific evidence modified: NO",
    ])

    return "\n".join(lines)
