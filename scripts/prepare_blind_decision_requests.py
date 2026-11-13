"""Build blind Scientific Critic v2 decision requests.

No API requests. No production-agent modifications.
"""

# PSEUDOCODE
# 1. Load the synthetic decision benchmark.
# 2. Load and verify Critic v2 instructions.
# 3. Extract only the scientific challenge for each case.
# 4. Keep expected decisions and rubrics out of prompts.
# 5. Fingerprint every model-visible request.
# 6. Save without overwriting existing files.

import hashlib
import json
from pathlib import Path

from cuselect.agents.llm_critic_agent import CRITIC_INSTRUCTIONS

ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "data/benchmarks/scientific_decisions_v1.json"
INSTRUCTIONS = ROOT / "data/benchmarks/critic_instructions_v2.json"
OUTPUT = ROOT / "data/benchmarks/blind_decision_requests_v1.json"

EXPECTED_IDS = ("B07", "B08", "B09")


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
    )


def prepare():
    benchmark = json.loads(SOURCE.read_text(encoding="utf-8"))
    config = json.loads(INSTRUCTIONS.read_text(encoding="utf-8"))

    combined = config["combined_instructions"]

    assert combined == (
        CRITIC_INSTRUCTIONS.rstrip()
        + "\n\n"
        + config["extension"]
    )

    assert digest(combined) == config["combined_instructions_sha256"]

    cases = benchmark["cases"]
    assert tuple(case["id"] for case in cases) == EXPECTED_IDS

    requests = []

    for case in cases:
        case_id = case["id"]
        challenge = case["scientific_challenge"]

        # Do NOT pass expected_disposition, required_reasoning
        # or forbidden_conclusions to the model.
        model_input = {
            "benchmark_id": case_id,
            "scientific_challenge": challenge,
        }

        messages = [
            {"role": "system", "content": combined},
            {
                "role": "user",
                "content": canonical(model_input),
            },
        ]

        # Verify the model-visible scientific payload.
        visible = json.loads(messages[1]["content"])

        assert set(visible) == {
            "benchmark_id",
            "scientific_challenge",
        }
        assert visible["scientific_challenge"] == challenge

        requests.append({
            "id": case_id,
            "input_sha256": digest(challenge),
            "request_sha256": digest(canonical(messages)),
            "messages": messages,
        })

    return {
        "schema_version": "1.0",
        "benchmark_type": "blind_scientific_decisions",
        "instruction_version": "2.0",
        "model_planned": "gpt-6.1-sol",
        "reasoning_effort_planned": "high",
        "output_schema": "ScientificCritique",
        "execution_status": "not_executed",
        "requests": requests,
    }


def main():
    if OUTPUT.exists():
        raise SystemExit(
            f"Refusing to overwrite: {OUTPUT}"
        )

    manifest = prepare()

    with OUTPUT.open("x", encoding="utf-8") as file:
        json.dump(
            manifest,
            file,
            indent=2,
            ensure_ascii=False,
        )
        file.write("\n")

    print("\nCUSELECT-AI — BLIND DECISION REQUESTS")
    print("=" * 60)

    for request in manifest["requests"]:
        print(f"{request['id']}: REQUEST VERIFIED")

    print("Critic instructions: v2")
    print("Expected decisions exposed: NO")
    print("Evaluation rubrics exposed: NO")
    print("Structured response schema: ScientificCritique")
    print("API calls: 0")
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
