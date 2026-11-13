"""Controlled live benchmark for Scientific Critic v2.

Default: read-only dry run.
Paid execution: requires two explicit authorization flags.
No automatic retries or automatic recovery submissions.
"""

# PSEUDOCODE
# 1. Verify the frozen v2 requests and plan.
# 2. Default to an offline dry run.
# 3. For live mode, require explicit authorization.
# 4. Exclusively claim a separate v2 execution directory.
# 5. Reserve each request before contacting the model.
# 6. Request a structured ScientificCritique.
# 7. Verify and exclusively save every response.
# 8. Stop on failure without retrying.

import argparse
import json
from pathlib import Path

from cuselect.agents.llm_critic_agent import ScientificCritique
from run_critic_v2_benchmark import (
    validate_execution_inputs,
    DEFAULT_RUN_DIR,
)
from benchmark_execution_ledger import (
    initialize_ledger,
    reserve_request,
    write_new_json,
)
from verify_saved_benchmark_response import (
    make_record,
    verify_saved_response,
)

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_IDS = ("B01", "B02", "B03", "B06")


def dry_run():
    plan, requests = validate_execution_inputs()

    return {
        "mode": "dry_run",
        "plan_sha256": plan["plan_sha256"],
        "cases": [r["id"] for r in requests],
        "maximum_requests": 4,
        "automatic_retries": 0,
        "actual_api_calls": 0,
    }


def execute_live(run_dir, model, client=None):
    """Submit at most four requests; never resume automatically."""

    if not isinstance(model, str) or not model.strip():
        raise ValueError("Model identifier required.")

    plan, requests = validate_execution_inputs()

    if tuple(r["id"] for r in requests) != EXPECTED_IDS:
        raise ValueError("Unexpected benchmark cases.")

    if plan["maximum_model_requests"] != 4:
        raise ValueError("Unexpected request limit.")

    if plan["automatic_retries"] != 0:
        raise ValueError("Automatic retries must be disabled.")

    root = Path(run_dir)

    # This runner is restricted to the designated v2 run path.
    if root != DEFAULT_RUN_DIR:
        raise ValueError("Only the designated v2 run path is allowed.")

    if root.is_symlink() or root.exists():
        raise ValueError(
            "Execution directory already claimed. "
            "Never reuse or automatically retry a previous run."
        )

    if root.parent.is_symlink():
        raise ValueError("Execution parent cannot be a symlink.")

    # Exclusive creation prevents another execution from
    # claiming the same run directory.
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(exist_ok=False)

    initialize_ledger(root, plan)

    responses_dir = root / "responses"
    responses_dir.mkdir(exist_ok=True)

    if client is None:
        from dotenv import load_dotenv
        from openai import OpenAI

        load_dotenv(ROOT / ".env")

        client = OpenAI(
            max_retries=0,
            timeout=90.0,
        )

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

            verified = verify_saved_response(record, plan)

            if not verified["record_integrity_verified"]:
                raise ValueError("Response integrity check failed.")

            write_new_json(
                responses_dir / f"{case_id}.json",
                record,
            )

        except Exception:
            print(
                f"{case_id}: execution stopped; "
                "reservation retained. DO NOT RETRY.",
                flush=True,
            )
            raise

        completed += 1

        print(
            f"{case_id}: response saved and verified",
            flush=True,
        )

    return {
        "mode": "live",
        "plan_sha256": plan["plan_sha256"],
        "completed": completed,
        "run_dir": str(root),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--execute-live",
        action="store_true",
    )
    parser.add_argument(
        "--authorize-paid-requests",
        action="store_true",
    )
    parser.add_argument(
        "--model",
        default="gpt-6.1-sol",
    )

    args = parser.parse_args()

    if not args.execute_live:
        if args.authorize_paid_requests:
            parser.error(
                "Authorization flag requires --execute-live."
            )

        report = dry_run()

        print("\nCUSELECT-AI — LIVE CRITIC V2")
        print("=" * 60)
        print("Mode: DRY RUN")
        print("Cases:", ", ".join(report["cases"]))
        print("Maximum requests:", report["maximum_requests"])
        print("Automatic retries:", report["automatic_retries"])
        print("Plan SHA-256:", report["plan_sha256"])
        print("Actual API calls: 0")
        print("Files modified: 0")
        return

    if not args.authorize_paid_requests:
        parser.error(
            "Paid execution requires "
            "--authorize-paid-requests."
        )

    result = execute_live(
        DEFAULT_RUN_DIR,
        model=args.model,
    )

    print("\nCompleted:", result["completed"])
    print("Results:", result["run_dir"])


if __name__ == "__main__":
    main()
