"""Controlled B07-B09 Scientific Decision Benchmark.

Default: read-only dry run.
Offline execution: requires an explicitly supplied fake client.
Paid API execution is not enabled.
"""

# PSEUDOCODE
# 1. Validate the frozen three-case benchmark plan.
# 2. Verify all model-visible request fingerprints.
# 3. Keep the answer key separate from model requests.
# 4. Reserve every case before simulated submission.
# 5. Validate and save structured synthetic responses.
# 6. Stop on errors and retain uncertain reservations.
# 7. Never overwrite existing execution records.

import json
from pathlib import Path

from cuselect.agents.llm_critic_agent import ScientificCritique
from plan_blind_decision_benchmark import (
    build_plan,
    canonical,
    sha256,
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

REQUESTS_PATH = (
    ROOT / "data/benchmarks/"
    "blind_decision_requests_v2.json"
)

DEFAULT_RUN_DIR = (
    ROOT / "data/agent_runs/benchmark_runs/"
    "scientific_decisions_v2"
)

EXPECTED_IDS = ("B07", "B08", "B09")


def validate_execution_inputs():
    plan = build_plan()

    manifest = json.loads(
        REQUESTS_PATH.read_text(encoding="utf-8")
    )

    requests = manifest["requests"]

    if tuple(r["id"] for r in requests) != EXPECTED_IDS:
        raise ValueError("Unexpected decision benchmark cases.")

    if plan["maximum_model_requests"] != 3:
        raise ValueError("Expected three requests.")

    if plan["automatic_retries"] != 0:
        raise ValueError("Automatic retries must be disabled.")

    planned = plan["requests"]

    for request, entry in zip(requests, planned):
        if request["id"] != entry["id"]:
            raise ValueError("Case identity mismatch.")

        actual_hash = sha256(
            canonical(request["messages"])
        )

        if actual_hash != entry["request_sha256"]:
            raise ValueError(
                f"Request fingerprint changed: {request['id']}"
            )

        if request["input_sha256"] != entry["input_sha256"]:
            raise ValueError(
                f"Scientific input changed: {request['id']}"
            )

    return plan, requests


def dry_run():
    plan, requests = validate_execution_inputs()

    return {
        "mode": "dry_run",
        "plan_sha256": plan["plan_sha256"],
        "cases": [r["id"] for r in requests],
        "maximum_requests": 3,
        "automatic_retries": 0,
        "actual_api_calls": 0,
    }


def execute_with_test_client(run_dir, client):
    """Execute synthetic tests only; never contact the API."""

    if client is None:
        raise ValueError("A fake test client is required.")

    plan, requests = validate_execution_inputs()
    root = Path(run_dir)

    # Prevent accidental use of production benchmark directories.
    target = root.resolve()

    protected = [
        DEFAULT_RUN_DIR.resolve(),
        (
            ROOT / "data/agent_runs/benchmark_runs/"
            "scientific_critic_v1"
        ).resolve(),
        (
            ROOT / "data/agent_runs/benchmark_runs/"
            "scientific_critic_v2"
        ).resolve(),
    ]

    if any(
        target == item or item in target.parents
        for item in protected
    ):
        raise ValueError("Protected benchmark directory.")

    if root.is_symlink() or root.exists():
        raise ValueError("Execution directory already exists.")

    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(exist_ok=False)

    initialize_ledger(root, plan)

    responses_dir = root / "responses"
    responses_dir.mkdir(exist_ok=False)

    completed = 0

    for request in requests:
        case_id = request["id"]

        reserve_request(root, case_id, plan)

        try:
            response = client.responses.parse(
                model="MOCK-NO-API",
                input=request["messages"],
                text_format=ScientificCritique,
                reasoning={"effort": "high"},
                store=False,
            )

            if getattr(response, "model", None) != "MOCK-NO-API":
                raise ValueError("Synthetic model identity required.")

            critique = response.output_parsed

            if not isinstance(critique, ScientificCritique):
                raise ValueError("Invalid structured critique.")

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
                provider_response_id=None,
            )

            verify_saved_response(record, plan)

            write_new_json(
                responses_dir / f"{case_id}.json",
                record,
            )

        except Exception:
            print(
                f"{case_id}: execution stopped; "
                "reservation retained.",
                flush=True,
            )
            raise

        completed += 1
        print(f"{case_id}: saved and verified", flush=True)

    return {
        "mode": "offline_test",
        "completed": completed,
        "plan_sha256": plan["plan_sha256"],
        "api_requests": 0,
        "run_dir": str(root),
    }


def main():
    report = dry_run()

    print("\nCUSELECT-AI — SCIENTIFIC DECISION RUNNER")
    print("=" * 60)
    print("Mode: DRY RUN ONLY")
    print("Cases:", ", ".join(report["cases"]))
    print("Maximum requests:", report["maximum_requests"])
    print("Automatic retries:", report["automatic_retries"])
    print("Plan SHA-256:", report["plan_sha256"])
    print("API requests: 0")
    print("Files modified: 0")
    print("Live execution enabled: NO")


if __name__ == "__main__":
    main()
