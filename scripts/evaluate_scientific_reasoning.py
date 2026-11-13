"""CuSelect-AI — offline scientific reasoning response evaluator."""

# PSEUDOCODE
# 1. Load the benchmark input packets.
# 2. Check all expected cases and input integrity.
# 3. Load independently captured response records.
# 4. Match one response to each benchmark case.
# 5. Reject missing, duplicate or modified case identities.
# 6. Report capture validity, not scientific correctness.
# 7. Keep synthetic responses separate from actual model output.

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKETS = (
    ROOT / "data/benchmarks/reasoning_evaluation_v1.json"
)
EXPECTED_IDS = {"B01", "B02", "B03", "B06"}


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_packets(data):
    if data.get("schema_version") != "1.0":
        raise ValueError("Unexpected benchmark schema.")

    cases = data.get("cases")
    if not isinstance(cases, list) or len(cases) != 4:
        raise ValueError("Expected four benchmark cases.")

    ids = [item.get("id") for item in cases]
    if len(set(ids)) != 4 or set(ids) != EXPECTED_IDS:
        raise ValueError("Invalid benchmark case identities.")

    for item in cases:
        if not isinstance(item.get("scientific_input"), str):
            raise ValueError("Missing scientific input.")

        if not item["scientific_input"].strip():
            raise ValueError("Empty scientific input.")

        for field in (
            "required_elements",
            "forbidden_conclusions",
        ):
            values = item.get(field)
            if (
                not isinstance(values, list)
                or not values
                or any(
                    not isinstance(v, str) or not v.strip()
                    for v in values
                )
            ):
                raise ValueError(f"Invalid {field}.")

    return cases


def evaluate(packets, responses):
    cases = validate_packets(packets)

    if responses.get("schema_version") != "1.0":
        raise ValueError("Unexpected response schema.")

    source_type = responses.get("source_type")
    if source_type not in {
        "synthetic_test_fixture",
        "captured_model_response",
    }:
        raise ValueError("Missing valid response source type.")

    entries = responses.get("responses")
    if not isinstance(entries, list):
        raise ValueError("Responses must be a list.")

    response_ids = [item.get("id") for item in entries]

    if len(response_ids) != len(set(response_ids)):
        raise ValueError("Duplicate response IDs.")

    if set(response_ids) != EXPECTED_IDS:
        raise ValueError("Missing or unexpected response IDs.")

    by_id = {item["id"]: item for item in entries}

    report = []

    for case in cases:
        item = by_id[case["id"]]
        expected_hash = digest(case["scientific_input"])

        if item.get("input_sha256") != expected_hash:
            raise ValueError(
                f"Input fingerprint mismatch: {case['id']}"
            )

        content = item.get("response_text")

        if not isinstance(content, str) or not content.strip():
            raise ValueError(
                f"Missing response content: {case['id']}"
            )

        report.append({
            "id": case["id"],
            "response_captured": True,
            "input_verified": True,
            "response_sha256": digest(content),
            "scientific_review": "not_evaluated",
            "required_elements_checked": False,
            "forbidden_conclusions_checked": False,
        })

    return {
        "schema_version": "1.0",
        "source_type": source_type,
        "responses_captured": len(report),
        "capture_validation_passed": True,
        "scientific_accuracy_established": False,
        "human_review_required": True,
        "results": report,
    }


def self_test(packets):
    cases = validate_packets(packets)

    with tempfile.TemporaryDirectory() as directory:
        response_path = Path(directory) / "mock_responses.json"

        fixture = {
            "schema_version": "1.0",
            "source_type": "synthetic_test_fixture",
            "responses": [
                {
                    "id": case["id"],
                    "input_sha256": digest(
                        case["scientific_input"]
                    ),
                    "response_text": (
                        "SYNTHETIC TEST RESPONSE ONLY. "
                        "No scientific reasoning was performed."
                    ),
                }
                for case in cases
            ],
        }

        response_path.write_text(
            json.dumps(fixture, indent=2),
            encoding="utf-8",
        )

        report = evaluate(
            packets,
            load_json(response_path),
        )

        assert report["responses_captured"] == 4
        assert report["capture_validation_passed"]
        assert not report["scientific_accuracy_established"]

        # Verify that a changed benchmark fingerprint
        # is rejected rather than silently accepted.
        fixture["responses"][0]["input_sha256"] = "0" * 64

        try:
            evaluate(packets, fixture)
        except ValueError as error:
            assert "fingerprint mismatch" in str(error)
        else:
            raise AssertionError(
                "Modified benchmark input was accepted."
            )

    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--packets",
        type=Path,
        default=DEFAULT_PACKETS,
    )
    parser.add_argument(
        "--responses",
        type=Path,
        help="An existing captured-response JSON file.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
    )

    args = parser.parse_args()
    packets = load_json(args.packets)

    if args.self_test and args.responses:
        parser.error(
            "Choose either --self-test or --responses."
        )

    if args.self_test:
        report = self_test(packets)
    elif args.responses:
        report = evaluate(
            packets,
            load_json(args.responses),
        )
    else:
        parser.error(
            "Specify --self-test or --responses."
        )

    print("\nCUSELECT-AI — REASONING EVALUATION HARNESS")
    print("=" * 60)
    print("Source:", report["source_type"])
    print("Responses captured:", report["responses_captured"])
    print("Input integrity: Verified")
    print("Capture validation: Passed")
    print("Scientific accuracy established: No")
    print("Human scientific review: Required")
    print("API requests: 0")
    print("Persistent files modified: 0")


if __name__ == "__main__":
    main()
