"""CuSelect-AI — offline structured Critic response capture.

Synthetic testing only. No OpenAI SDK client or network access.
"""

# PSEUDOCODE
# 1. Prepare four isolated scientific benchmark requests.
# 2. Pass each request to a deterministic mock client.
# 3. Validate the mock's ScientificCritique structure.
# 4. Capture serialized responses with input fingerprints.
# 5. Label every response as synthetic.
# 6. Validate capture using the existing benchmark harness.
# 7. Make no persistent changes or paid API calls.

import json
from pathlib import Path

from prepare_critic_benchmark_requests import (
    prepare_requests,
)
from evaluate_scientific_reasoning import (
    DEFAULT_PACKETS,
    evaluate,
    load_json,
)

from cuselect.agents.llm_critic_agent import (
    ScientificCritique,
)


class MockResponses:
    """Synthetic replacement for the structured response API."""

    def __init__(self):
        self.calls = []

    def parse(self, *, model, input, text_format, store):
        if model != "MOCK-NO-API":
            raise ValueError("Only mock model permitted.")

        if text_format is not ScientificCritique:
            raise ValueError("Unexpected response schema.")

        if store is not False:
            raise ValueError("Response storage must be disabled.")

        if len(input) != 2:
            raise ValueError("Unexpected message count.")

        payload = json.loads(input[1]["content"])
        case_id = payload["benchmark_case_id"]

        self.calls.append(case_id)

        # Deliberately non-substantive output.
        # This must NEVER be counted as scientific reasoning.
        critique = ScientificCritique(
            candidate_name=f"SYNTHETIC-{case_id}",
            central_claim_under_review=(
                "Synthetic software test only"
            ),
            scientific_findings=[
                {
                    "category": "evidence",
                    "assessment": "unsupported_or_unverified",
                    "finding": (
                        f"SYNTHETIC-{case_id}: placeholder finding {i}"
                    ),
                    "reasoning": (
                        "No actual scientific reasoning was performed."
                    ),
                    "linked_measurement_ids": [],
                    "recommended_action": (
                        "Do not use this software fixture "
                        "for scientific decisions."
                    ),
                }
                for i in range(1, 6)
            ],
            most_serious_scientific_risk=(
                "No scientific assessment was performed."
            ),
            competing_mechanistic_explanations=[
                "SYNTHETIC PLACEHOLDER A",
                "SYNTHETIC PLACEHOLDER B",
            ],
            critical_experiments=[
                {
                    "experiment_name": (
                        f"SYNTHETIC TEST EXPERIMENT {i}"
                    ),
                    "hypothesis_tested": (
                        "No scientific hypothesis was tested."
                    ),
                    "controlled_variables": [
                        "Synthetic software test variable"
                    ],
                    "measurement_strategy": (
                        "No measurements are performed."
                    ),
                    "result_that_would_challenge_hypothesis": (
                        "Not applicable to synthetic fixtures."
                    ),
                }
                for i in range(1, 3)
            ],
            missing_information=[
                "No scientific evidence was evaluated."
            ],
            recommended_disposition=(
                "revise_before_advancing"
            ),
            disposition_reason=(
                "Placeholder decision for software testing."
            ),
            recommended_revision=(
                "Use genuine model output for scientific review."
            ),
        )

        class MockResult:
            output_parsed = critique

        return MockResult()


class MockClient:
    def __init__(self):
        self.responses = MockResponses()


def capture_offline(client):
    # Restrict this executable to its own mock-client type.
    if type(client) is not MockClient:
        raise TypeError(
            "Offline capture only accepts MockClient."
        )

    requests = prepare_requests()
    captured = []

    for request in requests:
        result = client.responses.parse(
            model="MOCK-NO-API",
            input=request["messages"],
            text_format=request["text_format"],
            store=False,
        )

        parsed = result.output_parsed

        if not isinstance(parsed, ScientificCritique):
            raise TypeError(
                "Invalid structured Critic response."
            )

        response_text = json.dumps(
            parsed.model_dump(mode="json"),
            sort_keys=True,
            ensure_ascii=False,
        )

        captured.append({
            "id": request["id"],
            "input_sha256": request["input_sha256"],
            "request_sha256": request["request_sha256"],
            "instruction_sha256": (
                request["instruction_sha256"]
            ),
            "response_text": response_text,
            "model": "MOCK-NO-API",
        })

    return {
        "schema_version": "1.0",
        "source_type": "synthetic_test_fixture",
        "model": "MOCK-NO-API",
        "actual_api_calls": 0,
        "responses": captured,
    }


def main():
    client = MockClient()
    capture = capture_offline(client)

    packets = load_json(DEFAULT_PACKETS)
    report = evaluate(packets, capture)

    expected = {"B01", "B02", "B03", "B06"}

    if set(client.responses.calls) != expected:
        raise AssertionError("Unexpected mock call identities.")

    if report["responses_captured"] != 4:
        raise AssertionError("Incorrect capture count.")

    if report["scientific_accuracy_established"]:
        raise AssertionError(
            "Synthetic responses cannot establish accuracy."
        )

    print("\nCUSELECT-AI — OFFLINE CRITIC CAPTURE")
    print("=" * 60)

    for item in report["results"]:
        print(
            f"{item['id']}: "
            "structured response captured | "
            "input verified"
        )

    print("\nMock calls:", len(client.responses.calls))
    print("Responses validated:", report["responses_captured"])
    print("Source: synthetic_test_fixture")
    print("Scientific reasoning evaluated: No")
    print("Scientific accuracy established: No")
    print("Actual API calls: 0")
    print("New DFT calculations: 0")
    print("Persistent files modified: 0")


if __name__ == "__main__":
    main()
