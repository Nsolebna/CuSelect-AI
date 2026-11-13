"""End-to-end OFFLINE benchmark execution.

Uses only a mock client and temporary files.
No live API functionality is provided.
"""

# PSEUDOCODE
# 1. Build the deterministic four-case benchmark plan.
# 2. Initialize a temporary persistent execution ledger.
# 3. Reserve each request BEFORE invoking the mock client.
# 4. Capture a structured ScientificCritique response.
# 5. Save each response exclusively; never overwrite.
# 6. Verify every response against its original plan.
# 7. Inspect recovery states and reject duplicate reservations.
# 8. Report software validation only, not scientific accuracy.

import json
import tempfile
from pathlib import Path

from plan_live_critic_benchmark import build_plan
from prepare_critic_benchmark_requests import prepare_requests

from benchmark_execution_ledger import (
    initialize_ledger,
    reserve_request,
    write_new_json,
)

from capture_critic_benchmark_offline import MockClient

from verify_saved_benchmark_response import (
    make_record,
    verify_saved_response,
)

from inspect_completed_benchmark_recovery import (
    inspect_completed_recovery,
)

from cuselect.agents.llm_critic_agent import ScientificCritique


def run_offline_execution():
    plan = build_plan()
    requests = prepare_requests()

    expected_ids = ("B01", "B02", "B03", "B06")

    if tuple(r["id"] for r in requests) != expected_ids:
        raise ValueError("Unexpected benchmark request order.")

    client = MockClient()

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "benchmark_execution"

        initialize_ledger(root, plan)

        responses_dir = root / "responses"
        responses_dir.mkdir()

        for request in requests:
            case_id = request["id"]

            # Persistent reservation always comes first.
            reserve_request(root, case_id, plan)

            result = client.responses.parse(
                model="MOCK-NO-API",
                input=request["messages"],
                text_format=request["text_format"],
                store=False,
            )

            critique = result.output_parsed

            if not isinstance(critique, ScientificCritique):
                raise TypeError(
                    f"Invalid mock critique: {case_id}"
                )

            response_text = json.dumps(
                critique.model_dump(mode="json"),
                sort_keys=True,
                ensure_ascii=False,
            )

            record = make_record(
                case_id=case_id,
                response_text=response_text,
                model="MOCK-NO-API",
                source_type="synthetic_test_fixture",
                plan=plan,
            )

            # File creation fails if the response already exists.
            write_new_json(
                responses_dir / f"{case_id}.json",
                record,
            )

            verified = verify_saved_response(
                record, plan
            )

            assert verified["record_integrity_verified"]
            assert verified["structured_schema_valid"]
            assert not verified["scientific_accuracy_established"]

        report = inspect_completed_recovery(root, plan)

        assert report["response_integrity_verified"] == 4
        assert report["not_reserved"] == 0
        assert report["uncertain"] == 0
        assert report["invalid_records"] == 0
        assert not report["scientific_accuracy_established"]

        for case in report["cases"]:
            assert case["state"] == (
                "response_integrity_verified"
            )
            assert case["source_type"] == (
                "synthetic_test_fixture"
            )
            assert not case["automatically_retryable"]

        # Restart simulation: already-reserved requests
        # must remain blocked rather than being retried.
        initialize_ledger(root, plan)

        try:
            reserve_request(root, "B01", plan)
        except ValueError as error:
            if "Duplicate reservation blocked" not in str(error):
                raise
        else:
            raise AssertionError(
                "Duplicate execution was not blocked."
            )

        assert client.responses.calls == list(expected_ids)

        return {
            "mock_requests": len(client.responses.calls),
            "verified_responses": (
                report["response_integrity_verified"]
            ),
            "invalid_records": report["invalid_records"],
            "duplicate_blocked": True,
            "real_api_calls": 0,
            "scientific_evaluations": 0,
        }


def main():
    result = run_offline_execution()

    print("\nCUSELECT-AI — END-TO-END OFFLINE BENCHMARK")
    print("=" * 60)
    print("Request reservations: 4 / 4")
    print(
        "Structured mock responses:",
        result["mock_requests"],
    )
    print(
        "Verified saved responses:",
        result["verified_responses"],
    )
    print("Invalid records:", result["invalid_records"])
    print("Duplicate execution blocked: Yes")
    print("Scientific evaluations: 0")
    print("Real API calls: 0")
    print("Automatic retries: 0")
    print("Persistent project files modified: 0")


if __name__ == "__main__":
    main()
