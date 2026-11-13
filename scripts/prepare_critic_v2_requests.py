"""Prepare versioned Scientific Critic v2 benchmark requests.

No API calls. Does not modify the original v1 benchmark.
"""

# PSEUDOCODE
# 1. Load the verified v1 requests.
# 2. Load the versioned v2 instructions.
# 3. Check original-instruction integrity.
# 4. Copy each v1 request.
# 5. Replace only the system-message content.
# 6. Verify that the user message is unchanged.
# 7. Save a versioned request manifest without overwriting.

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cuselect.agents.llm_critic_agent import (
    CRITIC_INSTRUCTIONS,
)
from prepare_critic_benchmark_requests import (
    prepare_requests,
)

INSTRUCTIONS_PATH = (
    ROOT / "data/benchmarks/critic_instructions_v2.json"
)

OUTPUT = (
    ROOT / "data/benchmarks/"
    "critic_v2_requests_manifest.json"
)

EXPECTED_CASES = {"B01", "B02", "B03", "B06"}


def fingerprint(value):
    if isinstance(value, str):
        payload = value
    else:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def prepare_v2():
    v2 = json.loads(
        INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    )

    original = CRITIC_INSTRUCTIONS
    combined = v2["combined_instructions"]

    assert fingerprint(original) == (
        v2["original_instructions_sha256"]
    )

    assert fingerprint(combined) == (
        v2["combined_instructions_sha256"]
    )

    assert combined == (
        original.rstrip()
        + "\n\n"
        + v2["extension"]
    )

    original_requests = prepare_requests()
    prepared = []
    seen = set()

    for original_request in original_requests:
        case_id = original_request["id"]

        assert case_id in EXPECTED_CASES
        assert case_id not in seen
        seen.add(case_id)

        source_messages = original_request["messages"]

        assert len(source_messages) == 2
        assert source_messages[0]["role"] == "system"
        assert source_messages[1]["role"] == "user"
        assert source_messages[0]["content"] == original

        messages = copy.deepcopy(source_messages)
        messages[0]["content"] = combined

        # Only system instructions may differ.
        assert messages[1] == source_messages[1]

        prepared.append({
            "id": case_id,
            "instruction_version": "2.0",
            "input_sha256": original_request[
                "input_sha256"
            ],
            "v1_messages_sha256": fingerprint(
                source_messages
            ),
            "v2_messages_sha256": fingerprint(
                messages
            ),
            "messages": messages,
        })

    assert seen == EXPECTED_CASES

    return {
        "schema_version": "1.0",
        "manifest_type": "critic_v2_benchmark_requests",
        "model_planned": "gpt-6.1-sol",
        "reasoning_effort_planned": "high",
        "evaluation_status": "not_executed",
        "original_instructions_sha256": v2[
            "original_instructions_sha256"
        ],
        "combined_instructions_sha256": v2[
            "combined_instructions_sha256"
        ],
        "request_count": len(prepared),
        "requests": prepared,
        "api_requests_executed": 0,
    }


def main():
    if OUTPUT.exists():
        raise SystemExit(
            f"Manifest already exists: {OUTPUT}"
        )

    manifest = prepare_v2()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("x", encoding="utf-8") as file:
        json.dump(
            manifest,
            file,
            indent=2,
            ensure_ascii=False,
        )
        file.write("\n")

    print("\nCUSELECT-AI — CRITIC V2 REQUEST GENERATION")
    print("=" * 60)
    print("Instruction version: 2.0")
    print("Model planned:", manifest["model_planned"])
    print("Cases:", manifest["request_count"])

    for item in manifest["requests"]:
        print(
            f"{item['id']}: "
            "Scientific input preserved; "
            "system instructions updated"
        )

    print("Original requests modified: No")
    print("API requests: 0")
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
