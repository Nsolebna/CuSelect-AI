"""Prepare isolated scientific-critic benchmark requests.

No API calls are made by this script.
"""

# PSEUDOCODE
# 1. Read the four benchmark challenges.
# 2. Import the existing Critic instructions and schema.
# 3. Build one isolated prompt for each scientific challenge.
# 4. Exclude scoring rubrics and forbidden-conclusion lists.
# 5. Fingerprint the exact input and instructions.
# 6. Check that the intended output schema is ScientificCritique.
# 7. Print validation results; do not send model requests.

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.agents.llm_critic_agent import (
    CRITIC_INSTRUCTIONS,
    ScientificCritique,
)

BENCHMARK = (
    ROOT / "data/benchmarks/reasoning_evaluation_v1.json"
)

EXPECTED_IDS = {"B01", "B02", "B03", "B06"}


def fingerprint(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def prepare_requests():
    data = json.loads(
        BENCHMARK.read_text(encoding="utf-8")
    )

    if data.get("schema_version") != "1.0":
        raise ValueError("Unsupported benchmark schema.")

    cases = data.get("cases")

    if not isinstance(cases, list) or len(cases) != 4:
        raise ValueError("Expected four benchmark cases.")

    identifiers = [case.get("id") for case in cases]

    if (
        len(set(identifiers)) != 4
        or set(identifiers) != EXPECTED_IDS
    ):
        raise ValueError("Invalid benchmark case identifiers.")

    if not isinstance(CRITIC_INSTRUCTIONS, str):
        raise ValueError("Critic instructions must be text.")

    if not CRITIC_INSTRUCTIONS.strip():
        raise ValueError("Empty Critic instructions.")

    requests = []

    for case in cases:
        identifier = case["id"]
        challenge = case.get("scientific_input")

        if not isinstance(challenge, str) or not challenge.strip():
            raise ValueError(
                f"Invalid scientific input: {identifier}"
            )

        # The benchmark-specific wrapper contains only
        # the scientific question and task instructions.
        # Ground-truth rubric criteria remain outside the prompt.
        user_payload = {
            "task": "scientific_evidence_critique",
            "benchmark_case_id": identifier,
            "candidate_name": f"Benchmark {identifier}",
            "scientific_challenge": challenge,
            "instructions": (
                "Assess only the supplied scientific information. "
                "Identify evidence limitations and uncertainties. "
                "Distinguish supported findings from hypotheses. "
                "Recommend appropriate discriminating experiments "
                "where relevant. Do not invent missing measurements. "
                "Return a ScientificCritique."
            ),
        }

        user_message = json.dumps(
            user_payload,
            sort_keys=True,
            ensure_ascii=False,
        )

        messages = [
            {
                "role": "system",
                "content": CRITIC_INSTRUCTIONS,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

        # Evaluate the actual serialized model-visible input
        # rather than assuming the criteria are hidden.
        serialized = json.dumps(
            messages,
            sort_keys=True,
            ensure_ascii=False,
        )

        for criterion in (
            case["required_elements"]
            + case["forbidden_conclusions"]
        ):
            if criterion in serialized:
                raise ValueError(
                    f"Benchmark criterion exposed: {identifier}"
                )

        requests.append({
            "id": identifier,
            "input_sha256": fingerprint(challenge),
            "request_sha256": fingerprint(serialized),
            "instruction_sha256": fingerprint(
                CRITIC_INSTRUCTIONS
            ),
            "messages": messages,
            "text_format": ScientificCritique,
        })

    return requests


def main():
    requests = prepare_requests()

    print("\nCUSELECT-AI — CRITIC BENCHMARK ADAPTER")
    print("=" * 60)

    for request in requests:
        print(
            f"{request['id']}: "
            f"prepared | "
            f"input_sha256={request['input_sha256'][:12]}..."
        )

    print("\nPrepared requests:", len(requests))
    print("Output schema: ScientificCritique")
    print("Benchmark rubrics included: No")
    print("Model responses generated: 0")
    print("API calls: 0")
    print("Persistent files modified: 0")


if __name__ == "__main__":
    main()
