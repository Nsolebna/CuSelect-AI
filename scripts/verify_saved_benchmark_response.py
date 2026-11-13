"""CuSelect-AI — saved benchmark response integrity verification.

Verifies record consistency, not scientific correctness or API origin.
No network access, API calls, or persistent writes.
"""

# PSEUDOCODE
# 1. Load the deterministic benchmark plan.
# 2. Match a saved response to a planned case.
# 3. Verify the request and response fingerprints.
# 4. Require a model identity and response-source declaration.
# 5. Validate the structured ScientificCritique.
# 6. Keep mock responses separate from captured model responses.
# 7. Report integrity without claiming scientific accuracy.

import argparse
import hashlib
import json
from pathlib import Path

from plan_live_critic_benchmark import build_plan
from cuselect.agents.llm_critic_agent import ScientificCritique


def sha256_text(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def make_record(
    case_id,
    response_text,
    model,
    source_type,
    plan=None,
    provider_response_id=None,
):
    """Construct a record; does not authenticate its origin."""

    if plan is None:
        plan = build_plan()

    matches = [
        item for item in plan["requests"]
        if item["id"] == case_id
    ]

    if len(matches) != 1:
        raise ValueError("Unknown or duplicate benchmark case.")

    entry = matches[0]

    return {
        "schema_version": "1.0",
        "case_id": case_id,
        "plan_sha256": plan["plan_sha256"],
        "input_sha256": entry["input_sha256"],
        "request_sha256": entry["request_sha256"],
        "model": model,
        "source_type": source_type,
        "provider_response_id": provider_response_id,
        "response_sha256": sha256_text(response_text),
        "response_text": response_text,
    }


def verify_saved_response(record, plan=None):
    if plan is None:
        plan = build_plan()

    if not isinstance(record, dict):
        raise ValueError("Response record must be an object.")

    if record.get("schema_version") != "1.0":
        raise ValueError("Unsupported response schema version.")

    case_id = record.get("case_id")

    matches = [
        item for item in plan["requests"]
        if item["id"] == case_id
    ]

    if len(matches) != 1:
        raise ValueError("Unknown benchmark case.")

    expected = matches[0]

    for field, value in (
        ("plan_sha256", plan["plan_sha256"]),
        ("input_sha256", expected["input_sha256"]),
        ("request_sha256", expected["request_sha256"]),
    ):
        if record.get(field) != value:
            raise ValueError(
                f"Response {field} mismatch."
            )

    model = record.get("model")

    if not isinstance(model, str) or not model.strip():
        raise ValueError("Missing model identity.")

    source_type = record.get("source_type")

    if source_type not in (
        "synthetic_test_fixture",
        "captured_model_response",
    ):
        raise ValueError("Invalid response source type.")

    provider_id = record.get("provider_response_id")

    if source_type == "captured_model_response":
        if (
            not isinstance(provider_id, str)
            or not provider_id.strip()
        ):
            raise ValueError(
                "Captured model response requires "
                "a provider response identifier."
            )

        if model == "MOCK-NO-API":
            raise ValueError(
                "Mock model cannot be declared a "
                "captured model response."
            )

    else:
        if model != "MOCK-NO-API":
            raise ValueError(
                "Synthetic fixtures require the mock model."
            )

        if provider_id is not None:
            raise ValueError(
                "Synthetic fixture cannot declare "
                "a provider response identifier."
            )

    content = record.get("response_text")

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Missing response content.")

    if sha256_text(content) != record.get("response_sha256"):
        raise ValueError("Response fingerprint mismatch.")

    try:
        parsed_json = json.loads(content)
        critique = ScientificCritique.model_validate(
            parsed_json
        )
    except (ValueError, TypeError) as error:
        raise ValueError(
            "Invalid structured ScientificCritique."
        ) from error

    return {
        "case_id": case_id,
        "model": model,
        "source_type": source_type,
        "record_integrity_verified": True,
        "structured_schema_valid": True,
        "scientific_review": "not_evaluated",
        "provider_origin_independently_verified": False,
        "scientific_accuracy_established": False,
        "finding_count": len(
            critique.scientific_findings
        ),
    }


def self_test():
    # Use the existing mock capture pipeline.
    # Its responses are synthetic and never considered
    # genuine model evaluations.
    from capture_critic_benchmark_offline import (
        MockClient,
        capture_offline,
    )

    capture = capture_offline(MockClient())
    plan = build_plan()

    for item in capture["responses"]:
        record = make_record(
            case_id=item["id"],
            response_text=item["response_text"],
            model="MOCK-NO-API",
            source_type="synthetic_test_fixture",
            plan=plan,
        )

        result = verify_saved_response(record, plan)

        assert result["record_integrity_verified"]
        assert result["structured_schema_valid"]
        assert not result["scientific_accuracy_established"]

    # Detect modification of the response after capture.
    original = capture["responses"][0]

    tampered = make_record(
        original["id"],
        original["response_text"],
        "MOCK-NO-API",
        "synthetic_test_fixture",
        plan,
    )

    tampered["response_text"] += " MODIFIED"

    try:
        verify_saved_response(tampered, plan)
    except ValueError as error:
        assert "fingerprint mismatch" in str(error)
    else:
        raise AssertionError(
            "Modified saved response was accepted."
        )

    # Prevent a synthetic fixture from being
    # relabeled as a real model response.
    relabeled = make_record(
        original["id"],
        original["response_text"],
        "MOCK-NO-API",
        "captured_model_response",
        plan,
        provider_response_id="FAKE-TEST-ID",
    )

    try:
        verify_saved_response(relabeled, plan)
    except ValueError as error:
        assert "Mock model" in str(error)
    else:
        raise AssertionError(
            "Mock response was accepted as live."
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()

    if args.self_test == bool(args.record):
        parser.error(
            "Choose exactly one of --self-test or --record."
        )

    if args.self_test:
        self_test()

        print(
            "\nCUSELECT-AI — SAVED RESPONSE VERIFICATION"
        )
        print("=" * 60)
        print("Four mock response records: PASSED")
        print("Structured schema validation: PASSED")
        print("Response tampering detection: PASSED")
        print("Mock-to-live relabeling rejection: PASSED")
        print("Scientific evaluation performed: No")
        print("API requests: 0")
        print("Persistent files modified: 0")
        return

    record = json.loads(
        args.record.read_text(encoding="utf-8")
    )

    result = verify_saved_response(record)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
