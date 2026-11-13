"""CuSelect-AI — persistent benchmark request ledger.

No API calls. No automatic retries. Explicit request reservations.
"""

# PSEUDOCODE
# 1. Load and validate the deterministic benchmark plan.
# 2. Create a persistent manifest when explicitly requested.
# 3. Verify saved manifest identity on subsequent access.
# 4. Reserve each benchmark request using exclusive file creation.
# 5. Reject duplicate reservations and unexpected case IDs.
# 6. Preserve uncertain interrupted requests instead of retrying.
# 7. Test the complete workflow in a temporary directory.

import argparse
import json
import tempfile
from pathlib import Path

from plan_live_critic_benchmark import build_plan

EXPECTED_IDS = ("B01", "B02", "B03", "B06")


def write_new_json(path, data):
    """Create a JSON file without replacing an existing one."""
    with path.open("x", encoding="utf-8") as file:
        json.dump(data, file, indent=2, sort_keys=True)
        file.write("\n")


def initialize_ledger(root, plan):
    root = Path(root)

    if plan.get("mode") != "dry_run_only":
        raise ValueError("Only validated dry-run plans accepted.")

    if plan.get("maximum_model_requests") != 4:
        raise ValueError("Unexpected request budget.")

    ids = tuple(
        entry["id"] for entry in plan["requests"]
    )

    if ids != EXPECTED_IDS:
        raise ValueError("Unexpected benchmark identities.")

    root.mkdir(parents=True, exist_ok=True)

    manifest = root / "manifest.json"

    if manifest.exists():
        saved = json.loads(
            manifest.read_text(encoding="utf-8")
        )

        if saved != plan:
            raise ValueError(
                "Existing manifest differs from current plan."
            )
    else:
        try:
            write_new_json(manifest, plan)
        except FileExistsError:
            saved = json.loads(
                manifest.read_text(encoding="utf-8")
            )

            if saved != plan:
                raise ValueError(
                    "Concurrent manifest differs."
                )

    (root / "reservations").mkdir(exist_ok=True)

    return manifest


def verify_ledger(root, plan):
    root = Path(root)
    manifest = root / "manifest.json"

    if not manifest.is_file():
        raise ValueError("Execution ledger not initialized.")

    saved = json.loads(
        manifest.read_text(encoding="utf-8")
    )

    if saved != plan:
        raise ValueError(
            "Execution plan changed since initialization."
        )

    return root


def reserve_request(root, case_id, plan):
    """Reserve once; ambiguous interruptions require human review."""

    root = verify_ledger(root, plan)

    if case_id not in EXPECTED_IDS:
        raise ValueError("Unknown benchmark case.")

    entry = next(
        item for item in plan["requests"]
        if item["id"] == case_id
    )

    directory = root / "reservations"

    if not directory.is_dir():
        raise ValueError("Reservation directory missing.")

    reservation = {
        "schema_version": "1.0",
        "case_id": case_id,
        "plan_sha256": plan["plan_sha256"],
        "request_sha256": entry["request_sha256"],
        "state": "reserved_not_confirmed_submitted",
        "api_submission_confirmed": False,
        "automatic_retry_allowed": False,
        "scientific_result": None,
    }

    path = directory / f"{case_id}.json"

    try:
        write_new_json(path, reservation)
    except FileExistsError as error:
        raise ValueError(
            f"Duplicate reservation blocked: {case_id}. "
            "Do not retry until manually reconciled."
        ) from error

    return reservation


def self_test():
    plan = build_plan()

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "offline_run"

        initialize_ledger(root, plan)

        # Reinitializing with the same plan is harmless.
        initialize_ledger(root, plan)

        first = reserve_request(root, "B01", plan)

        assert first["state"] == (
            "reserved_not_confirmed_submitted"
        )

        assert first["api_submission_confirmed"] is False
        assert first["automatic_retry_allowed"] is False

        # Simulate interrupted execution.
        # The reservation survives as a file.
        assert (
            root / "reservations/B01.json"
        ).is_file()

        # The same benchmark request must not be reserved twice.
        try:
            reserve_request(root, "B01", plan)
        except ValueError as error:
            assert "Duplicate reservation blocked" in str(error)
        else:
            raise AssertionError(
                "Duplicate request reservation was accepted."
            )

        # Another case can still be reserved independently.
        second = reserve_request(root, "B02", plan)
        assert second["case_id"] == "B02"

        # A changed plan cannot reuse this ledger.
        modified = dict(plan)
        modified["plan_sha256"] = "0" * 64

        try:
            verify_ledger(root, modified)
        except ValueError as error:
            assert "plan changed" in str(error)
        else:
            raise AssertionError(
                "Changed execution plan was accepted."
            )

    return True


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Test ledger behavior using temporary files.",
    )

    args = parser.parse_args()

    if not args.self_test:
        parser.error(
            "Only --self-test is available at this stage."
        )

    self_test()

    print("\nCUSELECT-AI — BENCHMARK EXECUTION LEDGER")
    print("=" * 60)
    print("Manifest initialization: PASSED")
    print("Request reservation: PASSED")
    print("Duplicate request blocked: PASSED")
    print("Interrupted reservation retained: PASSED")
    print("Independent case reservation: PASSED")
    print("Changed plan rejected: PASSED")
    print("\nExecution mode: Offline self-test")
    print("Real API calls: 0")
    print("Automatic retries: 0")
    print("Persistent project files modified: 0")


if __name__ == "__main__":
    main()
