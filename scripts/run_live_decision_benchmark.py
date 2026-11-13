"""Controlled live scientific decision benchmark: B07-B09.

Default: read-only dry run.
Live execution requires two explicit authorization flags.
Never automatically retries or resumes uncertain requests.
"""

# PSEUDOCODE
# 1. Validate frozen benchmark requests and execution plan.
# 2. Default to a read-only dry run.
# 3. Require explicit authorization before live execution.
# 4. Exclusively claim the designated decision-run directory.
# 5. Reserve each case before sending its API request.
# 6. Parse the structured ScientificCritique response.
# 7. Verify and exclusively save the response.
# 8. Stop on errors; never automatically resubmit.

import argparse
import hashlib
import json
from pathlib import Path

from cuselect.agents.llm_critic_agent import ScientificCritique
from run_decision_benchmark import (
    validate_execution_inputs,
    DEFAULT_RUN_DIR,
)
from decision_execution_ledger import (
    initialize_ledger,
    reserve_request,
)
from benchmark_execution_ledger import write_new_json
from verify_saved_benchmark_response import (
    make_record,
    verify_saved_response,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/benchmarks"
EXPECTED_IDS = ("B07", "B08", "B09")


def hash_json(value):
    serialized = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def check_frozen_inputs():
    freeze = json.loads(
        (DATA / "scientific_evaluation_freeze_v1.json")
        .read_text(encoding="utf-8")
    )

    files = (
        (
            "blind_decision_requests_v2.json",
            "decision_requests_sha256",
        ),
        (
            "scientific_decisions_v2.json",
            "evaluator_key_sha256",
        ),
    )

    for filename, hash_field in files:
        value = json.loads(
            (DATA / filename).read_text(encoding="utf-8")
        )
        if hash_json(value) != freeze[hash_field]:
            raise ValueError(
                f"Frozen benchmark changed: {filename}"
            )

    if freeze["decision_cases"] != list(EXPECTED_IDS):
        raise ValueError("Unexpected frozen cases.")


def validate_live_inputs():
    check_frozen_inputs()
    plan, requests = validate_execution_inputs()

    if tuple(r["id"] for r in requests) != EXPECTED_IDS:
        raise ValueError("Unexpected decision cases.")

    if plan["maximum_model_requests"] != 3:
        raise ValueError("Exactly three requests required.")

    if plan["automatic_retries"] != 0:
        raise ValueError("Automatic retries must be zero.")

    return plan, requests


def dry_run():
    plan, requests = validate_live_inputs()

    return {
        "mode": "dry_run",
        "cases": [r["id"] for r in requests],
        "maximum_requests": 3,
        "plan_sha256": plan["plan_sha256"],
        "actual_api_calls": 0,
    }


def execute_live(run_dir, model, client=None):
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Model identifier required.")

    plan, requests = validate_live_inputs()

    root = Path(run_dir)

    if root != DEFAULT_RUN_DIR:
        raise ValueError(
            "Only the designated decision-run directory is allowed."
        )

    if root.is_symlink() or root.exists():
        raise ValueError(
            "Execution directory already claimed. "
            "DO NOT RETRY."
        )

    if root.parent.is_symlink():
        raise ValueError("Execution parent cannot be a symlink.")

    # When no client is injected, construct the real client.
    # Client creation itself does not submit an API request.
    if client is None:
        from dotenv import load_dotenv
        from openai import OpenAI

        load_dotenv(ROOT / ".env")
        client = OpenAI(
            max_retries=0,
            timeout=90.0,
        )

    # Claim exclusively before any model submission.
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(exist_ok=False)

    initialize_ledger(root, plan)

    responses_dir = root / "responses"
    responses_dir.mkdir(exist_ok=False)

    completed = 0

    for request in requests:
        case_id = request["id"]

        reserve_request(root, case_id, plan)

        print(
            f"{case_id}: reserved; submitting one request",
            flush=True,
        )

        try:
            response = client.responses.parse(
                model=model,
                input=request["messages"],
                text_format=ScientificCritique,
                reasoning={"effort": "high"},
                store=False,
            )

            critique = response.output_parsed

            if not isinstance(critique, ScientificCritique):
                raise ValueError(
                    f"Invalid structured response: {case_id}"
                )

            provider_id = getattr(response, "id", None)
            returned_model = getattr(response, "model", None)

            if not isinstance(provider_id, str) or not provider_id:
                raise ValueError("Provider response ID missing.")

            if not isinstance(returned_model, str) or not returned_model:
                raise ValueError("Provider model identity missing.")

            response_text = json.dumps(
                critique.model_dump(mode="json"),
                sort_keys=True,
                ensure_ascii=False,
            )

            record = make_record(
                case_id=case_id,
                response_text=response_text,
                model=returned_model,
                source_type="captured_model_response",
                plan=plan,
                provider_response_id=provider_id,
            )

            record["requested_model"] = model

            verification = verify_saved_response(
                record, plan
            )

            if not verification["record_integrity_verified"]:
                raise ValueError("Response integrity failed.")

            write_new_json(
                responses_dir / f"{case_id}.json",
                record,
            )

        except Exception:
            print(
                f"{case_id}: stopped; reservation retained. "
                "DO NOT RETRY.",
                flush=True,
            )
            raise

        completed += 1
        print(
            f"{case_id}: response saved and verified",
            flush=True,
        )

    return {
        "completed": completed,
        "plan_sha256": plan["plan_sha256"],
        "run_dir": str(root),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--execute-live", action="store_true"
    )
    parser.add_argument(
        "--authorize-paid-requests", action="store_true"
    )
    parser.add_argument(
        "--model", default="gpt-6.1-sol"
    )

    args = parser.parse_args()

    if not args.execute_live:
        if args.authorize_paid_requests:
            parser.error(
                "Authorization requires --execute-live."
            )

        report = dry_run()

        print("\nCUSELECT-AI — LIVE DECISION BENCHMARK")
        print("=" * 60)
        print("Mode: DRY RUN")
        print("Cases:", ", ".join(report["cases"]))
        print("Maximum requests:", report["maximum_requests"])
        print("Automatic retries: 0")
        print("Plan SHA-256:", report["plan_sha256"])
        print("Actual API calls: 0")
        print("Files modified: 0")
        return

    if not args.authorize_paid_requests:
        parser.error(
            "Paid execution requires explicit authorization."
        )

    result = execute_live(
        DEFAULT_RUN_DIR,
        model=args.model,
    )

    print("\nCompleted:", result["completed"])
    print("Saved to:", result["run_dir"])


if __name__ == "__main__":
    main()
