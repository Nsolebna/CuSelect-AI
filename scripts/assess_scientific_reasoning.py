"""CuSelect-AI — validate and summarize human scientific assessments."""

# PSEUDOCODE
# 1. Load benchmark cases and response-capture records.
# 2. Require one human assessment per case.
# 3. Require an assessment for every rubric element.
# 4. Reject unknown or incomplete assessments.
# 5. Identify missing scientific reasoning and critical violations.
# 6. Report descriptive rubric outcomes, not scientific truth.

import argparse
import json
from pathlib import Path

from evaluate_scientific_reasoning import (
    DEFAULT_PACKETS,
    digest,
    evaluate,
    load_json,
    validate_packets,
)

REQUIRED_STATES = {"met", "unmet", "unclear"}
FORBIDDEN_STATES = {"absent", "present", "unclear"}


def summarize_assessments(packets, responses, assessments):
    capture = evaluate(packets, responses)
    cases = validate_packets(packets)

    if capture["source_type"] != "captured_model_response":
        raise ValueError(
            "Scientific assessment requires captured model "
            "responses, not synthetic fixtures."
        )

    if assessments.get("schema_version") != "1.0":
        raise ValueError("Invalid assessment schema.")

    entries = assessments.get("assessments")

    if not isinstance(entries, list):
        raise ValueError("Assessments must be a list.")

    ids = [item.get("id") for item in entries]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate assessment IDs.")

    if set(ids) != {case["id"] for case in cases}:
        raise ValueError("Missing or unexpected assessment cases.")

    by_id = {item["id"]: item for item in entries}
    response_by_id = {
        item["id"]: item for item in responses["responses"]
    }

    results = []

    for case in cases:
        identifier = case["id"]
        review = by_id[identifier]
        response = response_by_id[identifier]

        reviewer = review.get("reviewer")
        rationale = review.get("review_rationale")

        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ValueError(f"Missing reviewer: {identifier}")

        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(f"Missing rationale: {identifier}")

        if review.get("response_sha256") != digest(
            response["response_text"]
        ):
            raise ValueError(
                f"Assessment response hash mismatch: {identifier}"
            )

        required = review.get("required_elements")
        forbidden = review.get("forbidden_conclusions")

        if not isinstance(required, list) or not isinstance(
            forbidden, list
        ):
            raise ValueError(
                f"Missing rubric assessments: {identifier}"
            )

        if len(required) != len(case["required_elements"]):
            raise ValueError(
                f"Required rubric length mismatch: {identifier}"
            )

        if len(forbidden) != len(case["forbidden_conclusions"]):
            raise ValueError(
                f"Forbidden rubric length mismatch: {identifier}"
            )

        for actual, expected in zip(
            required, case["required_elements"]
        ):
            if (
                actual.get("criterion") != expected
                or actual.get("status") not in REQUIRED_STATES
            ):
                raise ValueError(
                    f"Invalid required assessment: {identifier}"
                )

        for actual, expected in zip(
            forbidden, case["forbidden_conclusions"]
        ):
            if (
                actual.get("criterion") != expected
                or actual.get("status") not in FORBIDDEN_STATES
            ):
                raise ValueError(
                    f"Invalid forbidden assessment: {identifier}"
                )

        met = sum(
            item["status"] == "met" for item in required
        )
        missing = sum(
            item["status"] == "unmet" for item in required
        )
        violations = sum(
            item["status"] == "present" for item in forbidden
        )
        unclear = sum(
            item["status"] == "unclear"
            for item in required + forbidden
        )

        if violations:
            outcome = "critical_failure"
        elif missing or unclear:
            outcome = "needs_improvement_or_review"
        else:
            outcome = "rubric_satisfied"

        results.append({
            "id": identifier,
            "required_met": met,
            "required_total": len(required),
            "required_unmet": missing,
            "forbidden_violations": violations,
            "unclear_items": unclear,
            "rubric_outcome": outcome,
        })

    return {
        "schema_version": "1.0",
        "evaluation_type": "human_scientific_rubric",
        "cases_assessed": len(results),
        "critical_failures": sum(
            r["rubric_outcome"] == "critical_failure"
            for r in results
        ),
        "rubric_satisfied": sum(
            r["rubric_outcome"] == "rubric_satisfied"
            for r in results
        ),
        "results": results,
        "scientific_truth_independently_established": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--packets", type=Path, default=DEFAULT_PACKETS
    )
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--assessments", type=Path, required=True)
    args = parser.parse_args()

    result = summarize_assessments(
        load_json(args.packets),
        load_json(args.responses),
        load_json(args.assessments),
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
