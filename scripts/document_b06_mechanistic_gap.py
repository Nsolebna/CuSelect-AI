"""Document B06's mechanistic evidence gap.

Scientific analysis only. No API calls or modification of
original responses, benchmark criteria or human-review status.
"""

# PSEUDOCODE
# 1. Read and verify the saved B06 model response.
# 2. Identify the proposed critical experiments.
# 3. Record which mechanistic questions remain unresolved.
# 4. Specify a possible discriminating tracing strategy.
# 5. Preserve this as an unapproved scientific review record.

import json
from pathlib import Path

from verify_saved_benchmark_response import verify_saved_response

ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT / "data/agent_runs/benchmark_runs/"
    "scientific_critic_v1/responses/B06.json"
)

OUTPUT = (
    ROOT / "data/benchmarks/reviews/"
    "b06_mechanistic_gap_v1.json"
)


def build_review():
    record = json.loads(
        SOURCE.read_text(encoding="utf-8")
    )

    verified = verify_saved_response(record)

    if verified["case_id"] != "B06":
        raise ValueError("Unexpected benchmark identity.")

    if record["model"] != "gpt-6.1-sol":
        raise ValueError("Unexpected model identity.")

    critique = json.loads(record["response_text"])

    names = [
        item["experiment_name"]
        for item in critique["critical_experiments"]
    ]

    return {
        "schema_version": "1.0",
        "review_type": "mechanistic_gap_analysis",
        "benchmark_id": "B06",
        "model": record["model"],
        "source_response_sha256": record["response_sha256"],
        "review_status": "provisional_unapproved",
        "original_experiments": names,
        "scientific_observations": [
            "The Critic proposes matched-pattern controls.",
            "The Critic proposes contacting versus noncontacting Ag/Cu.",
            "The Critic proposes external CO-supply interventions.",
            "The experiments challenge several competing mechanisms.",
            "Explicit source-resolved carbon tracing into "
            "ethylene is not specified.",
        ],
        "mechanistic_questions": {
            "co_mediation": (
                "Does CO availability contribute to the "
                "observed ethylene response?"
            ),
            "carbon_source_attribution": (
                "Does carbon originating from Ag-associated "
                "CO contribute to ethylene?"
            ),
            "transport_pathway": (
                "Is transport surface-mediated, gas-mediated "
                "or electrolyte-mediated?"
            ),
        },
        "proposed_improvement": {
            "approach": (
                "Evaluate feasibility of source-distinguishable "
                "carbon isotope experiments with appropriate "
                "Ag and Cu controls."
            ),
            "measurements": [
                "Isotopologue-resolved ethylene quantification",
                "CO production and isotopic composition",
                "Carbon balances and isotope background",
                "Time-dependent isotope incorporation",
            ],
            "critical_controls": [
                "Cu-only and Ag-only references",
                "Contacting and physically separated configurations",
                "Gas and liquid transport characterization",
                "Isotope exchange and carbonate-reservoir effects",
                "Matched Cu operating conditions",
            ],
            "interpretation_limits": [
                "Isotope incorporation alone does not prove "
                "surface spillover.",
                "Source attribution and transport-pathway "
                "identification require different controls.",
                "Tracer feasibility and analytical sensitivity "
                "must be established before interpretation.",
            ],
        },
        "human_approval": False,
        "scientific_accuracy_independently_established": False,
    }


def main():
    if OUTPUT.exists():
        raise SystemExit(
            f"Review already exists; refusing overwrite: {OUTPUT}"
        )

    review = build_review()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("x", encoding="utf-8") as file:
        json.dump(review, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print("\nCUSELECT-AI — B06 MECHANISTIC GAP REVIEW")
    print("=" * 60)
    print("Benchmark:", review["benchmark_id"])
    print("Model:", review["model"])
    print("Original experiments:", len(review["original_experiments"]))
    print("Review status:", review["review_status"])
    print("Source tracing: Improvement identified")
    print("Original response modified: No")
    print("API calls: 0")
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
