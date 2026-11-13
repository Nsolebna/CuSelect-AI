"""Controlled Scientific Critic v2 benchmark runner.

Current implementation: dry run only.
No API calls or filesystem writes.
"""

# PSEUDOCODE
# 1. Load the validated v2 execution plan.
# 2. Load the saved v2 requests.
# 3. Recalculate their execution fingerprints.
# 4. Verify that every request matches the v2 plan.
# 5. Reject an incorrect case, fingerprint or instruction.
# 6. Confirm that v2 is separate from v1.
# 7. Report readiness without submitting API requests.

import json
from pathlib import Path

from plan_critic_v2_benchmark import (
    build_v2_plan,
    canonical_json,
    sha256_text,
)
from plan_live_critic_benchmark import build_plan

ROOT = Path(__file__).resolve().parents[1]

MANIFEST_PATH = (
    ROOT
    / "data/benchmarks/critic_v2_requests_manifest.json"
)

DEFAULT_RUN_DIR = (
    ROOT
    / "data/agent_runs/benchmark_runs/"
    "scientific_critic_v2"
)

EXPECTED_IDS = ("B01", "B02", "B03", "B06")


def validate_execution_inputs():
    plan = build_v2_plan()

    manifest = json.loads(
        MANIFEST_PATH.read_text(encoding="utf-8")
    )

    requests = manifest["requests"]

    if tuple(r["id"] for r in requests) != EXPECTED_IDS:
        raise ValueError("Unexpected v2 benchmark cases.")

    if plan["maximum_model_requests"] != 4:
        raise ValueError("Incorrect request limit.")

    if plan["automatic_retries"] != 0:
        raise ValueError("Automatic retries must be disabled.")

    if plan["plan_sha256"] == build_plan()["plan_sha256"]:
        raise ValueError("V2 plan unexpectedly matches v1.")

    if len(requests) != len(plan["requests"]):
        raise ValueError("Request count mismatch.")

    for request, entry in zip(
        requests, plan["requests"]
    ):
        if request["id"] != entry["id"]:
            raise ValueError("Case identity mismatch.")

        actual_hash = sha256_text(
            canonical_json(request["messages"])
        )

        if actual_hash != entry["request_sha256"]:
            raise ValueError(
                f"V2 request changed: {request['id']}"
            )

        if (
            request["input_sha256"]
            != entry["input_sha256"]
        ):
            raise ValueError(
                f"Scientific input changed: {request['id']}"
            )

    return plan, requests


def dry_run():
    plan, requests = validate_execution_inputs()

    return {
        "mode": "dry_run",
        "instruction_version": "2.0",
        "plan_sha256": plan["plan_sha256"],
        "planned_cases": [r["id"] for r in requests],
        "maximum_requests": 4,
        "automatic_retries": 0,
        "actual_api_calls": 0,
        "files_modified": 0,
    }


def main():
    report = dry_run()

    print("\nCUSELECT-AI — CRITIC V2 RUNNER")
    print("=" * 60)
    print("Mode: DRY RUN ONLY")
    print(
        "Cases:",
        ", ".join(report["planned_cases"])
    )
    print(
        "Maximum requests:",
        report["maximum_requests"]
    )
    print(
        "Automatic retries:",
        report["automatic_retries"]
    )
    print("Plan SHA-256:", report["plan_sha256"])
    print("Actual API calls:", report["actual_api_calls"])
    print("Files modified:", report["files_modified"])
    print("Live execution enabled: NO")



def execute_with_test_client(run_dir, client):
    """Run four benchmark cases with a synthetic test client only."""
    from cuselect.agents.llm_critic_agent import ScientificCritique
    from benchmark_execution_ledger import (
        initialize_ledger, reserve_request, write_new_json,
    )
    from verify_saved_benchmark_response import (
        make_record, verify_saved_response,
    )

    if client is None:
        raise ValueError("Offline fake client required.")

    plan, requests = validate_execution_inputs()
    root = Path(run_dir)

    protected = (
        DEFAULT_RUN_DIR.resolve(),
        (
            ROOT / "data/agent_runs/benchmark_runs/"
            "scientific_critic_v1"
        ).resolve(),
    )

    target = root.resolve()

    if any(
        target == item or item in target.parents
        for item in protected
    ):
        raise ValueError("Protected benchmark directory.")

    if root.is_symlink() or root.exists():
        raise ValueError("Existing run directory cannot be reused.")

    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(exist_ok=False)

    initialize_ledger(root, plan)
    responses_dir = root / "responses"
    responses_dir.mkdir(exist_ok=True)

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
                raise ValueError("Synthetic model required.")

            critique = response.output_parsed

            if not isinstance(critique, ScientificCritique):
                raise ValueError("Invalid structured response.")

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
                f"{case_id}: execution stopped; reservation retained.",
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

if __name__ == "__main__":
    main()
