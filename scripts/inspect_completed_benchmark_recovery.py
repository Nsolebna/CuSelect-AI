"""CuSelect-AI — recovery inspection with saved-response integrity.

Read-only operation. Does not submit, retry, or authenticate API calls.
"""

# PSEUDOCODE
# 1. Inspect the original execution ledger.
# 2. Find saved response files.
# 3. Require a valid reservation before accepting a response.
# 4. Verify response identity, hashes and ScientificCritique schema.
# 5. Separate synthetic records from declared model captures.
# 6. Flag invalid or orphaned records for manual investigation.
# 7. Never retry an uncertain request.

import argparse
import json
import tempfile
from pathlib import Path

from inspect_benchmark_recovery import inspect_recovery
from benchmark_execution_ledger import (
    initialize_ledger,
    reserve_request,
)
from plan_live_critic_benchmark import build_plan
from verify_saved_benchmark_response import (
    make_record,
    verify_saved_response,
)
from capture_critic_benchmark_offline import (
    MockClient,
    capture_offline,
)

EXPECTED_IDS = ("B01", "B02", "B03", "B06")


def inspect_completed_recovery(root, plan=None):
    if plan is None:
        plan = build_plan()

    root = Path(root)
    base = inspect_recovery(root, plan)

    response_dir = root / "responses"

    if response_dir.exists() and not response_dir.is_dir():
        raise ValueError("Response path is not a directory.")

    if response_dir.is_dir():
        expected_files = {
            f"{case_id}.json" for case_id in EXPECTED_IDS
        }

        unexpected = sorted(
            path.name
            for path in response_dir.iterdir()
            if path.name not in expected_files
        )

        if unexpected:
            raise ValueError(
                "Unexpected response files: "
                + ", ".join(unexpected)
            )

    results = []

    for original in base["cases"]:
        case_id = original["id"]
        item = dict(original)

        path = response_dir / f"{case_id}.json"

        if not path.exists():
            results.append(item)
            continue

        # A response without a valid reservation must never
        # establish completion.
        if original["state"] != "reserved_outcome_unknown":
            item.update({
                "state": "invalid_record",
                "requires_manual_review": True,
                "automatically_retryable": False,
                "detail": (
                    "Response exists without a valid "
                    "matching reservation."
                ),
            })
            results.append(item)
            continue

        try:
            record = json.loads(
                path.read_text(encoding="utf-8")
            )

            verified = verify_saved_response(
                record, plan
            )

            if verified["case_id"] != case_id:
                raise ValueError(
                    "Response file and case identity differ."
                )

        except (OSError, ValueError, TypeError) as error:
            item.update({
                "state": "invalid_record",
                "requires_manual_review": True,
                "automatically_retryable": False,
                "detail": (
                    "Saved response verification failed: "
                    + str(error)
                ),
            })
            results.append(item)
            continue

        source_type = verified["source_type"]

        item.update({
            "state": "response_integrity_verified",
            "source_type": source_type,
            "model": verified["model"],
            "requires_manual_review": True,
            "automatically_retryable": False,
            "scientific_review": "not_evaluated",
            "provider_origin_independently_verified": False,
            "scientific_accuracy_established": False,
            "detail": (
                "Synthetic test response; not a genuine model run."
                if source_type == "synthetic_test_fixture"
                else (
                    "Declared model response passed record "
                    "integrity checks; origin and scientific "
                    "correctness are not independently verified."
                )
            ),
        })

        results.append(item)

    return {
        "schema_version": "1.0",
        "plan_sha256": plan["plan_sha256"],
        "cases": results,
        "not_reserved": sum(
            r["state"] == "not_reserved" for r in results
        ),
        "uncertain": sum(
            r["state"] == "reserved_outcome_unknown"
            for r in results
        ),
        "response_integrity_verified": sum(
            r["state"] == "response_integrity_verified"
            for r in results
        ),
        "invalid_records": sum(
            r["state"] == "invalid_record" for r in results
        ),
        "automatic_retries_permitted": 0,
        "api_calls_made_by_inspector": 0,
        "scientific_accuracy_established": False,
    }


def self_test():
    plan = build_plan()
    mock = capture_offline(MockClient())

    captured = {
        item["id"]: item
        for item in mock["responses"]
    }

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "benchmark_run"

        initialize_ledger(root, plan)

        initial = inspect_completed_recovery(root, plan)

        assert initial["not_reserved"] == 4

        reserve_request(root, "B01", plan)
        reserve_request(root, "B02", plan)

        interrupted = inspect_completed_recovery(root, plan)
        assert interrupted["uncertain"] == 2

        responses = root / "responses"
        responses.mkdir()

        # Valid synthetic response linked to B01.
        source = captured["B01"]

        record = make_record(
            case_id="B01",
            response_text=source["response_text"],
            model="MOCK-NO-API",
            source_type="synthetic_test_fixture",
            plan=plan,
        )

        (responses / "B01.json").write_text(
            json.dumps(record, indent=2),
            encoding="utf-8",
        )

        # Invalid B02 response with altered fingerprint.
        bad = make_record(
            case_id="B02",
            response_text=captured["B02"]["response_text"],
            model="MOCK-NO-API",
            source_type="synthetic_test_fixture",
            plan=plan,
        )

        bad["response_sha256"] = "0" * 64

        (responses / "B02.json").write_text(
            json.dumps(bad, indent=2),
            encoding="utf-8",
        )

        result = inspect_completed_recovery(root, plan)

        assert result["response_integrity_verified"] == 1
        assert result["invalid_records"] == 1
        assert result["not_reserved"] == 2
        assert result["uncertain"] == 0

        b01 = next(
            r for r in result["cases"] if r["id"] == "B01"
        )

        assert b01["source_type"] == "synthetic_test_fixture"
        assert b01["scientific_review"] == "not_evaluated"
        assert not b01["automatically_retryable"]

        # A response without a reservation is not completion.
        orphan = make_record(
            case_id="B03",
            response_text=captured["B03"]["response_text"],
            model="MOCK-NO-API",
            source_type="synthetic_test_fixture",
            plan=plan,
        )

        (responses / "B03.json").write_text(
            json.dumps(orphan, indent=2),
            encoding="utf-8",
        )

        final = inspect_completed_recovery(root, plan)

        b03 = next(
            r for r in final["cases"] if r["id"] == "B03"
        )

        assert b03["state"] == "invalid_record"
        assert b03["requires_manual_review"]
        assert not b03["automatically_retryable"]

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--run-dir", type=Path)

    args = parser.parse_args()

    if args.self_test == bool(args.run_dir):
        parser.error(
            "Choose exactly one of --self-test or --run-dir."
        )

    if args.self_test:
        self_test()

        print(
            "\nCUSELECT-AI — COMPLETED RESPONSE RECOVERY"
        )
        print("=" * 60)
        print("Unreserved requests detected: PASSED")
        print("Interrupted requests detected: PASSED")
        print("Valid synthetic response verified: PASSED")
        print("Corrupted response rejected: PASSED")
        print("Orphaned response rejected: PASSED")
        print("Scientific assessments performed: 0")
        print("API requests: 0")
        print("Persistent project files modified: 0")
        return

    report = inspect_completed_recovery(args.run_dir)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
