"""CuSelect-AI — adaptive, evidence-gated research selection."""

# PSEUDOCODE
# 1. Load the reviewed experiment plan.
# 2. Load recorded qualification decisions, if available.
# 3. Validate reviewer, evidence reference and decision status.
# 4. Respect dependencies before recommending experiments.
# 5. Stop progression when qualification fails or is inconclusive.
# 6. Never assume that a recorded decision proves scientific truth.
# 7. Do not make API requests or modify scientific records.

import argparse
import json
from pathlib import Path

from select_next_experiment import (
    build_decision,
    EXPECTED,
    DEPENDENCIES,
)

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_GATES = (
    ROOT / "data/agent_runs"
    / "experiment_gate_reviews_v1.json"
)

VALID_STATUSES = {
    "pending",
    "qualified",
    "failed",
    "inconclusive",
}


def load_gates(path=None):
    """Load reviewed gate decisions, or pending defaults."""

    if path is None:
        path = DEFAULT_GATES

    path = Path(path)

    if not path.exists():
        if path == DEFAULT_GATES:
            return {
                name: {"status": "pending"}
                for name in EXPECTED
            }

        raise FileNotFoundError(path)

    record = json.loads(
        path.read_text(encoding="utf-8")
    )

    if record.get("schema_version") != "1.0":
        raise ValueError("Unexpected gate schema version.")

    reviews = record.get("reviews")

    if not isinstance(reviews, list):
        raise ValueError("Gate reviews must be a list.")

    result = {
        name: {"status": "pending"}
        for name in EXPECTED
    }

    seen = set()

    for review in reviews:
        if not isinstance(review, dict):
            raise ValueError("Invalid review entry.")

        name = review.get("experiment")
        status = review.get("status")

        if name not in result:
            raise ValueError(
                "Unknown experiment in gate reviews."
            )

        if name in seen:
            raise ValueError(
                "Duplicate review for one experiment."
            )

        seen.add(name)

        if status not in VALID_STATUSES:
            raise ValueError("Invalid review status.")

        if status != "pending":
            reviewer = review.get("reviewer")
            reference = review.get("evidence_reference")
            explanation = review.get("rationale")

            if not all(
                isinstance(value, str) and value.strip()
                for value in (
                    reviewer,
                    reference,
                    explanation,
                )
            ):
                raise ValueError(
                    "Non-pending decisions require reviewer, "
                    "evidence reference and rationale."
                )

        result[name] = review

    return result


def select_next(gates_path=None):
    """Recommend the next action from reviewed gate statuses."""

    baseline = build_decision()
    gates = load_gates(gates_path)

    sequence = []
    recommendation = None

    for item in baseline["sequence"]:
        name = item["experiment"]
        review = gates[name]
        status = review["status"]

        prerequisites = DEPENDENCIES[name]

        unresolved = [
            dependency
            for dependency in prerequisites
            if gates[dependency]["status"] != "qualified"
        ]

        if status == "qualified" and unresolved:
            raise ValueError(
                "A qualification conflicts with its "
                f"unqualified prerequisites: {name}"
            )

        if status == "qualified":
            action = "qualification_recorded"

        elif status in {"failed", "inconclusive"}:
            action = "review_and_remediate"

            if recommendation is None:
                recommendation = {
                    "experiment": name,
                    "action": action,
                    "reason": (
                        "The qualification was not established. "
                        "Review evidence, limitations and "
                        "possible protocol revisions."
                    ),
                }

        elif unresolved:
            action = "blocked_by_prerequisites"

        else:
            action = "ready_for_protocol_review"

            if recommendation is None:
                recommendation = {
                    "experiment": name,
                    "action": action,
                    "reason": (
                        "Prerequisite gates are satisfied "
                        "or not required. Human protocol "
                        "approval is still necessary."
                    ),
                }

        sequence.append({
            "experiment": name,
            "recorded_status": status,
            "action": action,
            "unresolved_prerequisites": unresolved,
            "reviewer": review.get("reviewer"),
            "evidence_reference": review.get(
                "evidence_reference"
            ),
        })

    if recommendation is None:
        recommendation = {
            "experiment": None,
            "action": "all_qualifications_recorded",
            "reason": (
                "All planned qualifications are recorded. "
                "Independent scientific review is still required."
            ),
        }

    return {
        "schema_version": "1.0",
        "engine": "adaptive_evidence_gate_selector",
        "candidate": baseline["candidate"],
        "recommendation": recommendation,
        "sequence": sequence,
        "scientific_validation": (
            "pending_independent_review"
        ),
        "experimental_results_inferred": False,
        "human_approval_required": True,
        "limitations": [
            "Reviewer declarations are not independently verified.",
            "Evidence references are not automatically audited.",
            "Qualification statuses are not experimental measurements.",
            "No experimental costs or information gains are estimated.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--gates",
        type=Path,
        default=None,
        help="Optional JSON gate-review file.",
    )

    parser.add_argument(
        "--simulation-only",
        action="store_true",
        help="Allow legacy simulation without evidence verification.",
    )

    args = parser.parse_args()

    # PSEUDOCODE
    # Reject normal execution through this legacy CLI.
    # Allow only explicitly authorized software simulations.
    if not args.simulation_only:
        parser.error(
            "Legacy selector is simulation-only. "
            "Use select_verified_experiment.py for "
            "operational research decisions."
        )

    result = select_next(args.gates)

    print("\nCUSELECT-AI — ADAPTIVE EXPERIMENT SELECTOR")
    print("=" * 65)

    for index, step in enumerate(
        result["sequence"], start=1
    ):
        print(f"\n{index}. {step['experiment']}")
        print("Review:", step["recorded_status"])
        print("Action:", step["action"])

    next_step = result["recommendation"]

    print("\nRECOMMENDED ACTION")
    print(next_step["action"])
    print("Experiment:", next_step["experiment"])
    print("Reason:", next_step["reason"])

    print("\nHuman scientific approval: Required")
    print("API requests: 0")
    print("Files modified: 0")


if __name__ == "__main__":
    main()
