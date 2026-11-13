"""Deterministic, read-only Critic v2 benchmark planner.

No API calls. No filesystem writes.
"""

# PSEUDOCODE
# 1. Load the original benchmark requests.
# 2. Load the saved v2 request manifest.
# 3. Verify the original and extended instructions.
# 4. Verify that all scientific inputs are unchanged.
# 5. Compute request fingerprints using the v1 convention.
# 6. Build a separate four-request execution plan.
# 7. Compute and report the v2 plan fingerprint.

import hashlib
import json
from pathlib import Path

from cuselect.agents.llm_critic_agent import (
    CRITIC_INSTRUCTIONS,
)
from prepare_critic_benchmark_requests import (
    prepare_requests,
)

ROOT = Path(__file__).resolve().parents[1]

MANIFEST_PATH = (
    ROOT / "data/benchmarks/"
    "critic_v2_requests_manifest.json"
)

INSTRUCTIONS_PATH = (
    ROOT / "data/benchmarks/"
    "critic_instructions_v2.json"
)

EXPECTED_IDS = ("B01", "B02", "B03", "B06")


def sha256_text(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def canonical_json(value):
    # Deliberately matches the original v1 planner.
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
    )


def build_v2_plan():
    manifest = json.loads(
        MANIFEST_PATH.read_text(encoding="utf-8")
    )
    instructions = json.loads(
        INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    )

    original = CRITIC_INSTRUCTIONS
    combined = instructions["combined_instructions"]

    if combined != (
        original.rstrip()
        + "\n\n"
        + instructions["extension"]
    ):
        raise ValueError("V2 instructions changed.")

    if sha256_text(original) != (
        instructions["original_instructions_sha256"]
    ):
        raise ValueError("V1 instruction hash mismatch.")

    if sha256_text(combined) != (
        instructions["combined_instructions_sha256"]
    ):
        raise ValueError("V2 instruction hash mismatch.")

    originals = prepare_requests()
    prepared = manifest["requests"]

    if tuple(r["id"] for r in originals) != EXPECTED_IDS:
        raise ValueError("V1 case identities changed.")

    if tuple(r["id"] for r in prepared) != EXPECTED_IDS:
        raise ValueError("V2 case identities changed.")

    if manifest["request_count"] != 4:
        raise ValueError("Unexpected v2 request count.")

    if manifest["evaluation_status"] != "not_executed":
        raise ValueError("Unexpected manifest status.")

    if manifest["combined_instructions_sha256"] != (
        sha256_text(combined)
    ):
        raise ValueError("Manifest instruction hash mismatch.")

    planned = []

    for v1, v2 in zip(originals, prepared):
        messages = v2["messages"]
        original_messages = v1["messages"]

        if len(messages) != 2:
            raise ValueError("Unexpected message count.")

        if messages[0] != {
            "role": "system",
            "content": combined,
        }:
            raise ValueError(
                f"Invalid system instructions: {v2['id']}"
            )

        if messages[1] != original_messages[1]:
            raise ValueError(
                f"Scientific input changed: {v2['id']}"
            )

        if v2["input_sha256"] != v1["input_sha256"]:
            raise ValueError(
                f"Input fingerprint changed: {v2['id']}"
            )

        # Verify the existing compact manifest fingerprint.
        compact = json.dumps(
            messages,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        if sha256_text(compact) != (
            v2["v2_messages_sha256"]
        ):
            raise ValueError(
                f"Manifest fingerprint mismatch: {v2['id']}"
            )

        # Recalculate using the original execution convention.
        request_hash = sha256_text(
            canonical_json(messages)
        )

        planned.append({
            "id": v2["id"],
            "input_sha256": v2["input_sha256"],
            "request_sha256": request_hash,
            "status": "not_submitted",
        })

    plan = {
        "schema_version": "1.0",
        "run_type": "scientific_critic_benchmark",
        "mode": "dry_run_only",
        "maximum_model_requests": 4,
        "automatic_retries": 0,
        "actual_model_requests": 0,
        "instruction_sha256": sha256_text(combined),
        "requests": planned,
        "evaluation_status": "not_executed",
        "scientific_accuracy_established": False,
    }

    plan["plan_sha256"] = sha256_text(
        canonical_json(plan)
    )

    return plan


if __name__ == "__main__":
    plan = build_v2_plan()

    print("\nCUSELECT-AI — CRITIC V2 EXECUTION PLAN")
    print("=" * 60)
    print("Version: 2.0")
    print("Cases:", ", ".join(
        r["id"] for r in plan["requests"]
    ))
    print("Maximum requests:", plan["maximum_model_requests"])
    print("Automatic retries:", plan["automatic_retries"])
    print("V2 plan SHA-256:", plan["plan_sha256"])
    print("Mode: DRY RUN")
    print("API requests: 0")
    print("Files modified: 0")
