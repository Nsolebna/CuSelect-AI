"""Controlled live Scientific Critic benchmark execution.

Default: read-only dry run.
Live: requires explicit command-line authorization.
No automatic retries and no automatic recovery submissions.
"""

# PSEUDOCODE
# 1. Verify the benchmark plan and four prepared requests.
# 2. Default to dry run with no filesystem writes.
# 3. Require two explicit flags before live submission.
# 4. Reserve each case durably before any API request.
# 5. Request a structured ScientificCritique with zero retries.
# 6. Save the returned response and provider metadata exclusively.
# 7. Stop immediately if a submission or save fails.
# 8. Never automatically retry uncertain outcomes.

import argparse
import json
from pathlib import Path

from plan_live_critic_benchmark import build_plan
from prepare_critic_benchmark_requests import prepare_requests
from benchmark_execution_ledger import (
    initialize_ledger,
    reserve_request,
    write_new_json,
)
from verify_saved_benchmark_response import (
    make_record,
    verify_saved_response,
)
from cuselect.agents.llm_critic_agent import ScientificCritique

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_RUN_DIR = (
    ROOT
    / "data/agent_runs/benchmark_runs/scientific_critic_v1"
)

EXPECTED_IDS = ("B01", "B02", "B03", "B06")


def validate_execution_inputs():
    plan = build_plan()
    requests = prepare_requests()

    if tuple(r["id"] for r in requests) != EXPECTED_IDS:
        raise ValueError("Unexpected benchmark identities.")

    planned = {
        item["id"]: item
        for item in plan["requests"]
    }

    for request in requests:
        case_id = request["id"]

        if (
            request["request_sha256"]
            != planned[case_id]["request_sha256"]
        ):
            raise ValueError(
                f"Benchmark request changed: {case_id}"
            )

    if plan["maximum_model_requests"] != 4:
        raise ValueError("Request budget must be four.")

    if plan["automatic_retries"] != 0:
        raise ValueError("Retries must be disabled.")

    return plan, requests


def dry_run():
    plan, requests = validate_execution_inputs()

    return {
        "mode": "dry_run",
        "plan_sha256": plan["plan_sha256"],
        "planned_cases": [r["id"] for r in requests],
        "maximum_requests": 4,
        "actual_api_calls": 0,
        "files_modified": 0,
    }


def execute_live(run_dir, model, client=None):
    """Perform up to four explicitly authorized API requests.

    Never automatically resumes or retries a reserved request.
    """
    if not isinstance(model, str) or not model.strip():
        raise ValueError("A model identifier is required.")

    plan, requests = validate_execution_inputs()
    root = Path(run_dir)

    # PSEUDOCODE
    # 1. Validate the target before touching the filesystem.
    # 2. Refuse any prior or unexpected execution artifacts.
    # 3. Only then initialize the execution ledger.
    from preflight_live_critic_benchmark import check_preflight

    preflight_report = check_preflight(root)

    if preflight_report["plan_sha256"] != plan["plan_sha256"]:
        raise ValueError("Preflight plan fingerprint mismatch.")

    # PSEUDOCODE
    # 1. Prepare only the parent directory.
    # 2. Claim the run directory with exclusive creation.
    # 3. Reject an existing directory, even if it is empty.
    # 4. Never delete or reuse an interrupted run.
    root.parent.mkdir(parents=True, exist_ok=True)

    try:
        root.mkdir(exist_ok=False)
    except FileExistsError as error:
        raise ValueError(
            "Benchmark run directory already claimed. "
            "Manual review required; refusing execution."
        ) from error

    initialize_ledger(root, plan)

    responses_dir = root / "responses"
    responses_dir.mkdir(exist_ok=True)

    if client is None:
        from dotenv import load_dotenv
        from openai import OpenAI

        load_dotenv(
            Path(__file__).resolve().parents[1] / ".env"
        )

        client = OpenAI(
            max_retries=0,
            timeout=90.0,
        )

    successful = 0

    for request in requests:
        case_id = request["id"]

        # Persist reservation BEFORE contacting the provider.
        reserve_request(root, case_id, plan)

        print(
            f"{case_id}: reserved; submitting one request",
            flush=True,
        )

        # SDK retries must remain disabled on the real client.
        # The caller-supplied client is for controlled testing.
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
                    f"Missing structured response: {case_id}"
                )

            provider_id = getattr(response, "id", None)
            returned_model = getattr(response, "model", None)

            if not isinstance(provider_id, str) or not provider_id:
                raise ValueError(
                    "Provider response identifier missing."
                )

            if not isinstance(returned_model, str) or not returned_model:
                raise ValueError(
                    "Provider model identity missing."
                )

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
                raise ValueError(
                    "Saved response integrity not verified."
                )

            # Exclusively create the record; never overwrite.
            write_new_json(
                responses_dir / f"{case_id}.json",
                record,
            )

        except Exception:
            print(
                f"{case_id}: execution or saving failed. "
                "Reservation retained; automatic retry prohibited.",
                flush=True,
            )
            raise

        successful += 1
        print(
            f"{case_id}: response saved and verified",
            flush=True,
        )

    return {
        "mode": "live",
        "plan_sha256": plan["plan_sha256"],
        "successful_responses": successful,
        "maximum_requests": 4,
        "scientific_assessment": "not_evaluated",
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
    parser.add_argument("--model")
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=DEFAULT_RUN_DIR,
    )

    args = parser.parse_args()

    if not args.execute_live:
        if args.authorize_paid_requests:
            parser.error(
                "Authorization flag requires --execute-live."
            )

        result = dry_run()

        print("\nCUSELECT-AI — CONTROLLED CRITIC RUNNER")
        print("=" * 60)
        print("Mode: DRY RUN")
        print("Cases:", ", ".join(result["planned_cases"]))
        print("Maximum requests:", result["maximum_requests"])
        print("Plan SHA-256:", result["plan_sha256"])
        print("Actual API calls: 0")
        print("Files modified: 0")
        return

    if not args.authorize_paid_requests:
        parser.error(
            "Live execution requires "
            "--authorize-paid-requests."
        )

    if not args.model:
        parser.error("Live execution requires --model.")

    result = execute_live(
        run_dir=args.run_dir,
        model=args.model,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
