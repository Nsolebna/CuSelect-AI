"""Execution ledger for the three-case decision benchmark.

No API requests. No automatic retries.
Does not modify the original four-case ledger.
"""

# PSEUDOCODE
# 1. Accept only the frozen three-case decision plan.
# 2. Create the execution manifest without overwriting.
# 3. Verify that the saved manifest matches the supplied plan.
# 4. Reserve each case exclusively before model submission.
# 5. Refuse duplicate reservations and changed plans.

import json
from pathlib import Path

from benchmark_execution_ledger import write_new_json
from plan_blind_decision_benchmark import build_plan

EXPECTED_IDS = ("B07", "B08", "B09")


def validate_plan(plan):
    expected = build_plan()

    if plan != expected:
        raise ValueError(
            "Decision plan does not match the frozen benchmark."
        )

    if plan["mode"] != "dry_run_only":
        raise ValueError("Invalid execution mode.")

    if plan["maximum_model_requests"] != 3:
        raise ValueError("Expected exactly three requests.")

    if plan["automatic_retries"] != 0:
        raise ValueError("Automatic retries must be disabled.")

    ids = tuple(
        item["id"] for item in plan["requests"]
    )

    if ids != EXPECTED_IDS:
        raise ValueError("Unexpected decision benchmark cases.")

    return plan


def initialize_ledger(root, plan):
    validate_plan(plan)
    root = Path(root)

    if root.is_symlink():
        raise ValueError("Execution directory cannot be a symlink.")

    if not root.is_dir():
        raise ValueError(
            "Execution directory must already be claimed."
        )

    if list(root.iterdir()):
        raise ValueError(
            "Execution directory must be empty."
        )

    manifest = root / "manifest.json"
    write_new_json(manifest, plan)

    (root / "reservations").mkdir(exist_ok=False)

    return manifest


def verify_ledger(root, plan):
    validate_plan(plan)
    root = Path(root)

    manifest = root / "manifest.json"

    if not manifest.is_file():
        raise ValueError("Execution manifest missing.")

    saved = json.loads(
        manifest.read_text(encoding="utf-8")
    )

    if saved != plan:
        raise ValueError("Execution plan changed.")

    return root


def reserve_request(root, case_id, plan):
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
            "Manual review required before any resubmission."
        ) from error

    return reservation
