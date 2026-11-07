# CuSelect-AI — Research Watcher Command-Line Interface
#
# PSEUDOCODE
# 1. Read command-line arguments.
# 2. Select preview or explicit save mode.
# 3. Load the Research Watcher baseline.
# 4. Discover and validate scholarly publications.
# 5. Compare publications against historical DOIs.
# 6. Save history only when explicitly requested.
# 7. Display a scientific literature digest.
# 8. Never modify human-review decisions or verified claims.

import argparse
import sys

from .watcher_scan import (
    DEFAULT_QUERY,
    scan_and_digest,
    format_digest,
)


DEFAULT_HISTORY = (
    "data/interim/research_watcher_history.json"
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "CuSelect-AI scientific literature Research Watcher"
        )
    )

    mode = parser.add_mutually_exclusive_group()

    mode.add_argument(
        "--preview",
        action="store_true",
        help="Run without saving watcher history (default)",
    )

    mode.add_argument(
        "--save",
        action="store_true",
        help="Update watcher history after a successful scan",
    )

    parser.add_argument(
        "--history",
        default=DEFAULT_HISTORY,
        help="Path to initialized watcher history",
    )

    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help="Scholarly publication search query",
    )

    parser.add_argument(
        "--rows",
        type=int,
        default=30,
        help="Maximum Crossref records to request",
    )

    parser.add_argument(
        "--minimum-results",
        type=int,
        default=25,
        help="Minimum accepted number of records",
    )

    args = parser.parse_args(argv)

    try:
        digest = scan_and_digest(
            history_path=args.history,
            query=args.query,
            rows=args.rows,
            minimum_results=args.minimum_results,
            persist_history=args.save,
        )

    except Exception as error:
        print(
            f"RESEARCH WATCHER FAILED: "
            f"{type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1

    print()
    print(format_digest(digest))
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
