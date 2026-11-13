"""CuSelect-AI — read-only live benchmark planning."""

# PSEUDOCODE
# 1. Prepare the four validated benchmark requests.
# 2. Verify every request uses the same Critic instructions.
# 3. Record each request's cryptographic fingerprints.
# 4. Enforce an exact four-request budget.
# 5. Produce a deterministic plan fingerprint.
# 6. Never call an API, create a run or overwrite results.

import hashlib
import json

from prepare_critic_benchmark_requests import (
    prepare_requests,
)

EXPECTED_IDS = ("B01", "B02", "B03", "B06")
MAX_REQUESTS = 4


def sha256_text(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def build_plan():
    requests = prepare_requests()

    ids = tuple(item["id"] for item in requests)

    if ids != EXPECTED_IDS:
        raise ValueError(
            "Benchmark identities or ordering changed."
        )

    if len(requests) != MAX_REQUESTS:
        raise ValueError("Unexpected request count.")

    instruction_hashes = {
        item["instruction_sha256"] for item in requests
    }

    if len(instruction_hashes) != 1:
        raise ValueError(
            "Inconsistent Critic instructions."
        )

    planned = []

    for item in requests:
        # Verify hashes against the actual model-visible
        # messages, not just declared metadata.
        messages = item["messages"]

        serialized = json.dumps(
            messages,
            sort_keys=True,
            ensure_ascii=False,
        )

        actual_request_hash = sha256_text(serialized)

        if actual_request_hash != item["request_sha256"]:
            raise ValueError(
                f"Request fingerprint mismatch: {item['id']}"
            )

        payload = json.loads(messages[1]["content"])

        actual_input_hash = sha256_text(
            payload["scientific_challenge"]
        )

        if actual_input_hash != item["input_sha256"]:
            raise ValueError(
                f"Question fingerprint mismatch: {item['id']}"
            )

        planned.append({
            "id": item["id"],
            "input_sha256": item["input_sha256"],
            "request_sha256": item["request_sha256"],
            "status": "not_submitted",
        })

    plan = {
        "schema_version": "1.0",
        "run_type": "scientific_critic_benchmark",
        "mode": "dry_run_only",
        "maximum_model_requests": MAX_REQUESTS,
        "automatic_retries": 0,
        "actual_model_requests": 0,
        "instruction_sha256": next(
            iter(instruction_hashes)
        ),
        "requests": planned,
        "evaluation_status": "not_executed",
        "scientific_accuracy_established": False,
    }

    canonical = json.dumps(
        plan,
        sort_keys=True,
        ensure_ascii=False,
    )

    plan["plan_sha256"] = sha256_text(canonical)

    return plan


def main():
    plan = build_plan()

    print("\nCUSELECT-AI — LIVE BENCHMARK PLANNER")
    print("=" * 60)

    for request in plan["requests"]:
        print(
            f"{request['id']}: "
            f"{request['status']} | "
            f"hash={request['request_sha256'][:12]}..."
        )

    print("\nMaximum planned requests:",
          plan["maximum_model_requests"])
    print("Automatic retries:", plan["automatic_retries"])
    print("Plan SHA-256:", plan["plan_sha256"])
    print("Execution mode: Dry run only")
    print("Actual API requests: 0")
    print("Files modified: 0")
    print("Scientific evaluation performed: No")


if __name__ == "__main__":
    main()
