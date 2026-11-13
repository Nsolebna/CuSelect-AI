"""Prepare an unapproved scientific review of GPT-6.1 Sol.

No API calls. No changes to original model responses.
Provisional assessments must not be treated as human approval.
"""

# PSEUDOCODE
# 1. Load the four original benchmark cases.
# 2. Load and integrity-check each saved model response.
# 3. Link assessments to the exact response fingerprints.
# 4. Record the provisional scientific review.
# 5. Flag B06 source-resolved tracing for further examination.
# 6. Require a separate human-approval step.
# 7. Save a new draft without overwriting existing records.

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_scientific_reasoning import (
    DEFAULT_PACKETS,
    digest,
    load_json,
    validate_packets,
)

from verify_saved_benchmark_response import (
    verify_saved_response,
)

RESPONSES = (
    ROOT
    / "data/agent_runs/benchmark_runs/"
    "scientific_critic_v1/responses"
)

OUTPUT = (
    ROOT
    / "data/benchmarks/reviews/"
    "sol_scientific_review_draft_v1.json"
)


def prepare_review():
    packets = load_json(DEFAULT_PACKETS)
    cases = validate_packets(packets)

    reviews = []

    for case in cases:
        case_id = case["id"]
        path = RESPONSES / f"{case_id}.json"

        record = load_json(path)
        verification = verify_saved_response(record)

        if verification["case_id"] != case_id:
            raise ValueError(
                f"Incorrect response identity: {case_id}"
            )

        if record["model"] != "gpt-6.1-sol":
            raise ValueError(
                f"Unexpected model for {case_id}"
            )

        if record["source_type"] != "captured_model_response":
            raise ValueError(
                f"Non-live response for {case_id}"
            )

        critique = json.loads(record["response_text"])

        required = []

        for criterion in case["required_elements"]:
            status = "met"

            if (
                case_id == "B06"
                and "source-resolved tracing" in criterion.lower()
            ):
                status = "unclear"

            required.append({
                "criterion": criterion,
                "provisional_status": status,
                "human_status": None,
                "human_evidence_note": None,
            })

        forbidden = [
            {
                "criterion": criterion,
                "provisional_status": "absent",
                "human_status": None,
                "human_evidence_note": None,
            }
            for criterion in case["forbidden_conclusions"]
        ]

        reviews.append({
            "id": case_id,
            "model": record["model"],
            "provider_response_id": (
                record["provider_response_id"]
            ),
            "response_sha256": digest(
                record["response_text"]
            ),
            "input_sha256": record["input_sha256"],
            "scientific_finding_count": len(
                critique["scientific_findings"]
            ),
            "critical_experiment_count": len(
                critique["critical_experiments"]
            ),
            "required_elements": required,
            "forbidden_conclusions": forbidden,
            "reviewer": None,
            "review_rationale": None,
            "human_approval": False,
        })

    return {
        "schema_version": "1.0",
        "document_type": "scientific_review_draft",
        "model": "gpt-6.1-sol",
        "review_status": "unapproved",
        "assessment_origin": "AI-assisted preliminary review",
        "benchmark_cases": len(reviews),
        "reviews": reviews,
        "special_attention": {
            "case_id": "B06",
            "issue": (
                "The proposed experiments challenge contact-"
                "dependent surface spillover and CO-supply "
                "hypotheses, but do not explicitly specify "
                "source-resolved carbon tracing into ethylene."
            ),
            "review_question": (
                "Does the supplied experimental strategy "
                "adequately discuss source-resolved tracing, "
                "or must this criterion remain unmet?"
            ),
        },
        "scientific_accuracy_independently_established": False,
        "limitations": [
            "Provisional statuses are not human-approved scores.",
            "Response hashes establish record consistency, "
            "not independent provider authentication.",
            "This review covers four selected challenges only.",
        ],
    }


def main():
    if OUTPUT.exists():
        raise SystemExit(
            f"Review draft already exists: {OUTPUT}"
        )

    report = prepare_review()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("x", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )
        file.write("\n")

    print("\nCUSELECT-AI — SCIENTIFIC REVIEW DRAFT")
    print("=" * 60)
    print("Model:", report["model"])
    print("Cases linked:", report["benchmark_cases"])
    print("Saved response integrity: Verified")
    print("Review status:", report["review_status"])
    print("B06 source-tracing criterion: Needs review")
    print("Output:", OUTPUT)
    print("API requests: 0")
    print("Original responses modified: 0")


if __name__ == "__main__":
    main()
