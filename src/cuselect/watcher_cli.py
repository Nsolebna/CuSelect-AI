# CuSelect-AI — Research Watcher CLI
#
# PSEUDOCODE
# 1. Read command-line settings.
# 2. Run a preview or a controlled save-mode scan.
# 3. Generate the research digest.
# 4. Optionally save the digest and scan log.
# 5. Distinguish scan failure from reporting failure.
# 6. Preserve the scientific human-verification boundary.

import argparse
import sys

from .watcher_scan import (
    DEFAULT_QUERY,
    scan_and_digest,
    format_digest,
)

from .watcher_reporting import (
    new_run_id,
    save_digest,
    append_scan_event,
)


DEFAULT_HISTORY = (
    "data/interim/research_watcher_history.json"
)

DEFAULT_REPORT_DIR = (
    "data/reports/research_watcher"
)

DEFAULT_SCAN_LOG = (
    "data/interim/research_watcher_scans.jsonl"
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "CuSelect-AI scientific literature Research Watcher"
        )
    )

    modes = parser.add_mutually_exclusive_group()

    modes.add_argument(
        "--preview",
        action="store_true",
        help="Run a read-only scan (default)",
    )

    modes.add_argument(
        "--save",
        action="store_true",
        help="Persist observed DOI history",
    )

    parser.add_argument(
        "--record",
        action="store_true",
        help="Save digest and append a scan event",
    )

    parser.add_argument(
        "--history",
        default=DEFAULT_HISTORY,
        help="Initialized watcher history path",
    )

    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help="Publication search query",
    )

    parser.add_argument(
        "--rows",
        type=int,
        default=30,
        help="Maximum Crossref results",
    )

    parser.add_argument(
        "--minimum-results",
        type=int,
        default=25,
        help="Minimum accepted scan results",
    )

    parser.add_argument(
        "--report-dir",
        default=DEFAULT_REPORT_DIR,
        help="Saved research digest directory",
    )

    parser.add_argument(
        "--scan-log",
        default=DEFAULT_SCAN_LOG,
        help="JSONL monitoring event log",
    )

    args = parser.parse_args(argv)

    mode = "save" if args.save else "preview"
    run_id = new_run_id() if args.record else None

    # PSEUDOCODE:
    # Run discovery and DOI history comparison.
    # Save history only when --save is selected.

    try:
        digest = scan_and_digest(
            history_path=args.history,
            query=args.query,
            rows=args.rows,
            minimum_results=args.minimum_results,
            persist_history=args.save,
        )

    except Exception as error:
        message = f"{type(error).__name__}: {error}"

        print(
            f"RESEARCH WATCHER FAILED: {message}",
            file=sys.stderr,
        )

        if args.record:
            try:
                append_scan_event(
                    args.scan_log,
                    run_id=run_id,
                    status="failure",
                    mode=mode,
                    error=message,
                )
            except Exception as log_error:
                print(
                    f"FAILURE LOGGING FAILED: {log_error}",
                    file=sys.stderr,
                )

        return 1

    print()
    print(format_digest(digest))
    print()

    # Default preview does not write any reports.
    if not args.record:
        return 0

    # PSEUDOCODE:
    # Persist the report after a completed scan.
    # If reporting fails, disclose whether DOI
    # history was already updated.

    try:
        report_path = save_digest(
            args.report_dir,
            run_id,
            digest,
        )

    except Exception as error:
        message = f"{type(error).__name__}: {error}"
        history_saved = bool(digest.get("history_saved"))

        print(
            f"REPORTING FAILED: {message}",
            file=sys.stderr,
        )

        print(
            "Watcher history saved: "
            + ("YES" if history_saved else "NO"),
            file=sys.stderr,
        )

        try:
            append_scan_event(
                args.scan_log,
                run_id=run_id,
                status="failure",
                mode=mode,
                retrieved_count=digest["retrieved_count"],
                newly_seen_count=digest["newly_seen_count"],
                error=(
                    f"Report failed: {message}; "
                    f"history_saved={history_saved}"
                ),
            )

        except Exception as log_error:
            print(
                f"FAILURE LOGGING FAILED: {log_error}",
                file=sys.stderr,
            )

        return 2

    # PSEUDOCODE:
    # Record success only when the report exists.
    # Report logging errors separately.

    try:
        append_scan_event(
            args.scan_log,
            run_id=run_id,
            status="success",
            mode=mode,
            retrieved_count=digest["retrieved_count"],
            newly_seen_count=digest["newly_seen_count"],
        )

    except Exception as error:
        print(
            f"SCAN LOGGING FAILED: {error}",
            file=sys.stderr,
        )

        print(
            f"Digest already saved: {report_path}",
            file=sys.stderr,
        )

        print(
            "Watcher history saved: "
            + (
                "YES" if digest.get("history_saved")
                else "NO"
            ),
            file=sys.stderr,
        )

        return 2

    print(f"Research digest saved: {report_path}")
    print(f"Scan event recorded: {args.scan_log}")
    print(f"Run ID: {run_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
