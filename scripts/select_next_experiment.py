"""CuSelect-AI — prerequisite-aware experiment selection."""

# PSEUDOCODE
# 1. Load the evidence-aware revised candidate.
# 2. Confirm that the expected experiments exist.
# 3. Define scientific dependencies between experiments.
# 4. Separate planning readiness from experimental validation.
# 5. Recommend the next qualification step.
# 6. Never invent experimental outcomes or numeric scores.
# 7. Make no API calls or file changes.

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT / "data/agent_runs"
    / "llm_revised_candidate_with_dft_v3.json"
)

EXPECTED = [
    "Fabrication and stability qualification",
    "Matched-pattern electrolysis and transport accounting",
    "External-CO response and source-resolved tracing",
]

DEPENDENCIES = {
    EXPECTED[0]: [],
    EXPECTED[1]: [EXPECTED[0]],
    EXPECTED[2]: [EXPECTED[0], EXPECTED[1]],
}

QUESTIONS = {
    EXPECTED[0]: (
        "Are distinct, sufficiently matched patterns "
        "fabricable and stable?"
    ),
    EXPECTED[1]: (
        "Does patterning change ethylene production "
        "under qualified comparison conditions?"
    ),
    EXPECTED[2]: (
        "Can Ag-derived CO be specifically linked "
        "to ethylene carbon?"
    ),
}

LIMITATIONS = {
    EXPECTED[0]: (
        "Matching tolerances and characterization "
        "methods require human validation."
    ),
    EXPECTED[1]: (
        "A pattern-dependent response does not "
        "independently prove CO transfer."
    ),
    EXPECTED[2]: (
        "External labeled CO incorporation alone "
        "does not prove Ag-to-Cu CO transfer."
    ),
}


def build_decision():
    """Build an advisory plan from saved scientific records."""

    record = json.loads(
        SOURCE.read_text(encoding="utf-8")
    )

    if record.get("agent") != "llm_revision_agent":
        raise ValueError("Unexpected revision source.")

    if record.get("scientific_validation") != (
        "pending_human_review"
    ):
        raise ValueError(
            "Unexpected scientific validation status."
        )

    experiments = record["revision"]["controlled_experiments"]

    by_name = {
        item["name"]: item
        for item in experiments
    }

    if len(by_name) != len(experiments):
        raise ValueError("Duplicate experiment names.")

    if set(by_name) != set(EXPECTED):
        raise ValueError(
            "Experiment list differs from the reviewed plan."
        )

    plan = []

    for index, name in enumerate(EXPECTED, start=1):
        dependencies = DEPENDENCIES[name]

        plan.append({
            "priority_order": index,
            "experiment": name,
            "research_question": QUESTIONS[name],
            "dependencies": dependencies,
            "planning_status": (
                "ready_for_protocol_review"
                if not dependencies
                else "pending_prerequisite_evidence"
            ),
            "experimental_validation": "not_assessed",
            "decision_limitation": LIMITATIONS[name],
            "falsification_criterion": (
                by_name[name]["outcome_challenging_hypothesis"]
            ),
            "interpretation_limitations": (
                by_name[name]["interpretation_limitations"]
            ),
        })

    return {
        "schema_version": "1.0",
        "engine": "deterministic_prerequisite_selector",
        "source": str(SOURCE.relative_to(ROOT)),
        "candidate": record["revision"]["candidate_name"],
        "recommended_next_step": EXPECTED[0],
        "recommendation_type": "prerequisite_based",
        "human_review_required": True,
        "performance_prediction_available": False,
        "experimental_results_available": False,
        "sequence": plan,
        "parallel_note": (
            "Isotope-method feasibility and analytical "
            "calibration may be investigated in parallel. "
            "A pattern-specific mechanistic conclusion "
            "requires applicable earlier qualifications."
        ),
        "limitations": [
            "No experimental outcomes were supplied.",
            "Priority order is based on dependencies, not measured information gain.",
            "Feasibility, cost and scientific value have not been numerically scored.",
            "This plan is advisory and requires expert review.",
        ],
    }


def main():
    decision = build_decision()

    print("\nCUSELECT-AI — EXPERIMENT DECISION ENGINE")
    print("=" * 65)

    print("Candidate:", decision["candidate"])
    print("Method: Prerequisite-based selection")
    print("Experimental data: Not available")
    print("Human review: Required")

    for item in decision["sequence"]:
        print(
            f"\n{item['priority_order']}. "
            f"{item['experiment']}"
        )
        print("Status:", item["planning_status"])
        print("Question:", item["research_question"])

        if item["dependencies"]:
            print(
                "Requires:",
                "; ".join(item["dependencies"])
            )

    print("\nRECOMMENDED NEXT STEP")
    print(decision["recommended_next_step"])

    print("\nNo API calls.")
    print("No DFT calculations.")
    print("No files modified.")


if __name__ == "__main__":
    main()
