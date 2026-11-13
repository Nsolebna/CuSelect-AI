"""CuSelect-AI — read-only benchmark recovery inspection."""

# PSEUDOCODE
# 1. Load the original deterministic benchmark plan.
# 2. Verify the saved execution manifest.
# 3. Inspect every expected request reservation.
# 4. Check its case ID, plan hash and request fingerprint.
# 5. Classify unreserved and uncertain requests.
# 6. Flag malformed records without attempting repairs.
# 7. Never submit, retry or modify an API request.

import argparse
import json
import tempfile
from pathlib import Path

from benchmark_execution_ledger import (
    initialize_ledger,
    reserve_request,
    verify_ledger,
)
from plan_live_critic_benchmark import build_plan

EXPECTED_IDS = ("B01", "B02", "B03", "B06")


def inspect_recovery(root, plan=None):
    if plan is None:
        plan = build_plan()

    root = verify_ledger(root, plan)

    reservations = root / "reservations"

    if not reservations.is_dir():
        raise ValueError("Reservation directory missing.")

    unexpected = sorted(
        p.name
        for p in reservations.iterdir()
        if p.name not in {
            f"{case_id}.json"
            for case_id in EXPECTED_IDS
        }
    )

    if unexpected:
        raise ValueError(
            "Unexpected reservation files: "
            + ", ".join(unexpected)
        )

    planned = {
        item["id"]: item
        for item in plan["requests"]
    }

    results = []

    for case_id in EXPECTED_IDS:
        path = reservations / f"{case_id}.json"

        if not path.exists():
            results.append({
                "id": case_id,
                "state": "not_reserved",
                "requires_manual_review": False,
                "automatically_retryable": False,
                "detail": "No reservation recorded.",
            })
            continue

        try:
            record = json.loads(
                path.read_text(encoding="utf-8")
            )

            if not isinstance(record, dict):
                raise ValueError(
                    "Reservation must be an object."
                )

            expected = {
                "schema_version": "1.0",
                "case_id": case_id,
                "plan_sha256": plan["plan_sha256"],
                "request_sha256": (
                    planned[case_id]["request_sha256"]
                ),
                "state": (
                    "reserved_not_confirmed_submitted"
                ),
                "api_submission_confirmed": False,
                "automatic_retry_allowed": False,
                "scientific_result": None,
            }

            if record != expected:
                raise ValueError(
                    "Reservation does not match expected "
                    "plan and recovery state."
                )

        except (OSError, ValueError, TypeError) as error:
            results.append({
                "id": case_id,
                "state": "invalid_record",
                "requires_manual_review": True,
                "automatically_retryable": False,
                "detail": str(error),
            })
            continue

        results.append({
            "id": case_id,
            "state": "reserved_outcome_unknown",
            "requires_manual_review": True,
            "automatically_retryable": False,
            "detail": (
                "Reservation exists. API submission and "
                "completion are not established."
            ),
        })

    return {
        "schema_version": "1.0",
        "plan_sha256": plan["plan_sha256"],
        "cases": results,
        "not_reserved": sum(
            r["state"] == "not_reserved"
            for r in results
        ),
        "uncertain": sum(
            r["state"] == "reserved_outcome_unknown"
            for r in results
        ),
        "invalid_records": sum(
            r["state"] == "invalid_record"
            for r in results
        ),
        "automatic_retries_permitted": 0,
        "api_calls_made_by_inspector": 0,
    }


def self_test():
    plan = build_plan()

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "recovery_test"

        initialize_ledger(root, plan)

        initial = inspect_recovery(root, plan)

        assert initial["not_reserved"] == 4
        assert initial["uncertain"] == 0

        reserve_request(root, "B01", plan)

        interrupted = inspect_recovery(root, plan)

        assert interrupted["not_reserved"] == 3
        assert interrupted["uncertain"] == 1

        b01 = next(
            item for item in interrupted["cases"]
            if item["id"] == "B01"
        )

        assert b01["requires_manual_review"] is True
        assert b01["automatically_retryable"] is False

        # Tampering must not result in a retry.
        path = root / "reservations/B01.json"

        record = json.loads(
            path.read_text(encoding="utf-8")
        )
        record["request_sha256"] = "0" * 64

        path.write_text(
            json.dumps(record),
            encoding="utf-8",
        )

        damaged = inspect_recovery(root, plan)

        assert damaged["invalid_records"] == 1
        assert damaged["uncertain"] == 0

        damaged_b01 = next(
            item for item in damaged["cases"]
            if item["id"] == "B01"
        )

        assert damaged_b01["requires_manual_review"]
        assert not damaged_b01["automatically_retryable"]

    return True


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--self-test",
        action="store_true",
    )

    parser.add_argument(
        "--run-dir",
        type=Path,
        help="Inspect an existing saved benchmark run.",
    )

    args = parser.parse_args()

    if args.self_test == bool(args.run_dir):
        parser.error(
            "Specify exactly one of --self-test or --run-dir."
        )

    if args.self_test:
        self_test()

        print(
            "\nCUSELECT-AI — RECOVERY INSPECTOR SELF-TEST"
        )
        print("=" * 60)
        print("Unreserved request detection: PASSED")
        print("Interrupted reservation detection: PASSED")
        print("Corrupted reservation detection: PASSED")
        print("Automatic retries: 0")
        print("API requests: 0")
        print("Persistent project files modified: 0")
        return

    report = inspect_recovery(args.run_dir)

    print(
        "\nCUSELECT-AI — BENCHMARK RECOVERY REPORT"
    )
    print("=" * 60)

    for item in report["cases"]:
        print(f"{item['id']}: {item['state']}")
        print(f"  {item['detail']}")

    print("\nNot reserved:", report["not_reserved"])
    print("Uncertain:", report["uncertain"])
    print("Invalid records:", report["invalid_records"])
    print("Automatic retries: 0")
    print("API requests: 0")
    print("Files modified: 0")


if __name__ == "__main__":
    main()
