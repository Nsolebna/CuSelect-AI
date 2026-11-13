"""Read-only execution planner for B07-B09.

No API calls. No filesystem writes.
"""

# PSEUDOCODE
# 1. Read the frozen benchmark and blind request manifest.
# 2. Verify the freeze fingerprint.
# 3. Validate all three case identities.
# 4. Validate the model-visible request fingerprints.
# 5. Ensure the grading fields are not in the user payload.
# 6. Build a deterministic execution plan.
# 7. Report the plan fingerprint without executing requests.

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/benchmarks"
EXPECTED_IDS = ("B07", "B08", "B09")


def sha256(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
    )


def load(name):
    return json.loads(
        (DATA / name).read_text(encoding="utf-8")
    )


def build_plan():
    freeze = load("scientific_evaluation_freeze_v1.json")
    manifest = load("blind_decision_requests_v2.json")
    instructions = load("critic_instructions_v2.json")

    if sha256(canonical(manifest)) != (
        freeze["decision_requests_sha256"]
    ):
        raise ValueError("Frozen request manifest changed.")

    if freeze["decision_cases"] != list(EXPECTED_IDS):
        raise ValueError("Frozen case identities changed.")

    requests = manifest["requests"]

    if tuple(item["id"] for item in requests) != EXPECTED_IDS:
        raise ValueError("Unexpected case ordering.")

    combined = instructions["combined_instructions"]
    planned = []

    for item in requests:
        messages = item["messages"]

        if len(messages) != 2:
            raise ValueError("Unexpected message count.")

        if messages[0] != {
            "role": "system",
            "content": combined,
        }:
            raise ValueError("System instructions changed.")

        if messages[1].get("role") != "user":
            raise ValueError("Invalid user message.")

        payload = json.loads(messages[1]["content"])

        if set(payload) != {
            "benchmark_id",
            "scientific_challenge",
        }:
            raise ValueError("Possible grading leakage.")

        if payload["benchmark_id"] != item["id"]:
            raise ValueError("Case identity mismatch.")

        if sha256(payload["scientific_challenge"]) != (
            item["input_sha256"]
        ):
            raise ValueError("Scientific input changed.")

        if sha256(canonical(messages)) != (
            item["request_sha256"]
        ):
            raise ValueError("Request fingerprint changed.")

        planned.append({
            "id": item["id"],
            "input_sha256": item["input_sha256"],
            "request_sha256": item["request_sha256"],
            "status": "not_submitted",
        })

    plan = {
        "schema_version": "1.0",
        "run_type": "blind_scientific_decision_benchmark",
        "mode": "dry_run_only",
        "maximum_model_requests": 3,
        "automatic_retries": 0,
        "actual_model_requests": 0,
        "instruction_sha256": sha256(combined),
        "requests": planned,
        "evaluation_status": "not_executed",
        "scientific_accuracy_established": False,
    }

    plan["plan_sha256"] = sha256(canonical(plan))
    return plan


if __name__ == "__main__":
    plan = build_plan()

    print("\nCUSELECT-AI — SCIENTIFIC DECISION PLAN")
    print("=" * 60)
    print("Cases:", ", ".join(
        item["id"] for item in plan["requests"]
    ))
    print("Maximum requests:", plan["maximum_model_requests"])
    print("Automatic retries:", plan["automatic_retries"])
    print("Plan SHA-256:", plan["plan_sha256"])
    print("Mode: DRY RUN")
    print("API requests: 0")
    print("Files modified: 0")
