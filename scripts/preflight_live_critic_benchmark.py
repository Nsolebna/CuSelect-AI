"""CuSelect-AI — read-only live benchmark preflight.

Rejects existing execution artifacts before any API submission.
Does not initialize a ledger or make network requests.
"""

# PSEUDOCODE
# 1. Validate the current four-case benchmark plan.
# 2. Check the intended run directory.
# 3. Refuse directories with prior reservations or responses.
# 4. Refuse unexpected files or folders.
# 5. Report readiness without writing anything.

import argparse
from pathlib import Path

from plan_live_critic_benchmark import build_plan
from prepare_critic_benchmark_requests import prepare_requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = (
    ROOT / "data/agent_runs/benchmark_runs/scientific_critic_v1"
)


def validate_execution_inputs():
    plan = build_plan()
    requests = prepare_requests()

    if tuple(r["id"] for r in requests) != (
        "B01", "B02", "B03", "B06"
    ):
        raise ValueError("Unexpected benchmark identities.")

    if plan["maximum_model_requests"] != 4:
        raise ValueError("Invalid model request budget.")

    if plan["automatic_retries"] != 0:
        raise ValueError("Automatic retries are not permitted.")

    planned = {item["id"]: item for item in plan["requests"]}

    for request in requests:
        if request["request_sha256"] != planned[
            request["id"]
        ]["request_sha256"]:
            raise ValueError("Benchmark request fingerprint mismatch.")

    return plan, requests


def check_preflight(run_dir):
    plan, requests = validate_execution_inputs()
    root = Path(run_dir)

    if root.is_symlink():
        raise ValueError("Run directory cannot be a symlink.")

    if root.exists():
        if not root.is_dir():
            raise ValueError("Run path is not a directory.")

        entries = list(root.iterdir())

        # Conservative policy: no existing content is
        # permitted for a fresh paid benchmark run.
        if entries:
            names = sorted(entry.name for entry in entries)
            raise ValueError(
                "Existing run artifacts require manual review: "
                + ", ".join(names)
            )

    if len(requests) != 4:
        raise ValueError("Unexpected benchmark request count.")

    return {
        "status": "ready_for_new_run",
        "plan_sha256": plan["plan_sha256"],
        "planned_requests": 4,
        "automatic_retries": 0,
        "previous_execution_artifacts": 0,
        "api_requests_executed": 0,
        "files_modified": 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=DEFAULT_RUN_DIR,
    )
    args = parser.parse_args()

    report = check_preflight(args.run_dir)

    print("\nCUSELECT-AI — LIVE EXECUTION PREFLIGHT")
    print("=" * 60)
    print("Status:", report["status"])
    print("Planned requests:", report["planned_requests"])
    print("Automatic retries:", report["automatic_retries"])
    print("Plan SHA-256:", report["plan_sha256"])
    print("Existing execution artifacts: 0")
    print("API requests: 0")
    print("Files modified: 0")


if __name__ == "__main__":
    main()
