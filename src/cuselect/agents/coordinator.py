"""CuSelect-AI — Optimization Coordinator v1.

Combines evidence-grounded hypotheses, critiques, and research
readiness scores into an auditable candidate-development report.
"""

# PSEUDOCODE
# 1. Load the Design, Critic, and Scoring Agent outputs.
# 2. Check that candidate identities match across agents.
# 3. Preserve the original hypothesis and its evidence.
# 4. Create a revised research plan addressing the critique.
# 5. Attach research-readiness scores without predicting FE.
# 6. Export a reproducible record of candidate evolution.

import json
from pathlib import Path

from cuselect.agents.literature_package_agent import atomic_write

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "data" / "agent_runs"

DESIGNS = RUNS / "design_proposals_v1.json"
CRITIQUES = RUNS / "scientific_critiques_v1.json"
SCORES = RUNS / "research_readiness_scores_v1.json"
OUTPUT = RUNS / "coordinated_designs_v1.json"


def read_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def index_unique(records, key):
    result = {}

    for record in records:
        identifier = record[key]

        if identifier in result:
            raise ValueError(f"Duplicate {key}: {identifier}")

        result[identifier] = record

    return result


def coordinate(designs, critiques, scores):
    if designs.get("agent") != "design_agent":
        raise ValueError("Unexpected design input")

    if critiques.get("agent") != "scientific_critic":
        raise ValueError("Unexpected critique input")

    if scores.get("agent") != "scoring_agent":
        raise ValueError("Unexpected scoring input")

    design_by_id = index_unique(
        designs["candidates"], "id"
    )
    critique_by_id = index_unique(
        critiques["critiques"], "candidate_id"
    )
    score_by_id = index_unique(
        scores["candidates"], "candidate_id"
    )

    ids = set(design_by_id)

    if ids != set(critique_by_id) or ids != set(score_by_id):
        raise ValueError(
            "Candidate sets do not match across agents. "
            "Regenerate all outputs before coordinating."
        )

    coordinated = []

    for candidate_id in sorted(ids):
        design = design_by_id[candidate_id]
        critique = critique_by_id[candidate_id]
        score = score_by_id[candidate_id]

        if (
            critique["supporting_doi"] != design["source_doi"]
            or score["supporting_doi"] != design["source_doi"]
        ):
            raise ValueError(
                f"Evidence DOI mismatch: {candidate_id}"
            )

        if set(critique["validated_evidence_ids"]) != set(
            design["evidence_measurement_ids"]
        ):
            raise ValueError(
                f"Evidence ID mismatch: {candidate_id}"
            )

        if score.get("predicted_fe_percent") is not None:
            raise ValueError(
                "A research-readiness score must not "
                "contain a predicted FE."
            )

        # Revision improves the experimental research plan.
        # No catalyst performance improvement is assumed.
        revised_plan = {
            "hypothesis": design["hypothesis"],
            "original_experiment": design["proposed_experiment"],
            "added_control_experiment": (
                critique["discriminating_experiment"]
            ),
            "alternative_explanation_to_test": (
                critique["alternative_explanation"]
            ),
            "main_risk_to_monitor": critique["primary_risk"],
            "revision_type": "research_plan_refinement",
            "status": "proposed_not_experimentally_tested",
        }

        coordinated.append({
            "candidate_id": candidate_id,
            "candidate_name": design["name"],
            "supporting_doi": design["source_doi"],
            "evidence_measurement_ids": (
                design["evidence_measurement_ids"]
            ),
            "evolution": [
                {
                    "stage": "initial_design",
                    "agent": "design_agent",
                    "hypothesis": design["hypothesis"],
                    "experimental_plan": (
                        design["proposed_experiment"]
                    ),
                    "status": "untested",
                },
                {
                    "stage": "scientific_critique",
                    "agent": "scientific_critic",
                    "primary_risk": critique["primary_risk"],
                    "alternative_explanation": (
                        critique["alternative_explanation"]
                    ),
                    "status": "rule_based_review",
                },
                {
                    "stage": "revised_research_plan",
                    "agent": "optimization_coordinator",
                    **revised_plan,
                },
            ],
            "research_readiness": score["scores"],
            "presentation_order": score["presentation_order"],
            "predicted_fe_percent": None,
            "recommended_next_experiment": (
                critique["discriminating_experiment"]
            ),
        })

    coordinated.sort(
        key=lambda item: (
            -item["research_readiness"]["total"],
            item["candidate_id"],
        )
    )

    return {
        "schema_version": "1.0",
        "agent": "optimization_coordinator",
        "workflow_type": "deterministic_research_plan_refinement",
        "candidate_count": len(coordinated),
        "candidates": coordinated,
        "limitations": [
            "No experimental catalyst optimization performed.",
            "No validated catalyst-performance predictions.",
            "Readiness scores measure documentation and "
            "research planning, not intrinsic activity.",
            "Proposed revisions require scientific validation.",
        ],
    }


def main():
    designs = read_json(DESIGNS)
    critiques = read_json(CRITIQUES)
    scores = read_json(SCORES)

    output = coordinate(designs, critiques, scores)
    atomic_write(OUTPUT, output)

    print("\nCUSELECT-AI — OPTIMIZATION COORDINATOR v1")
    print("=" * 65)

    for candidate in output["candidates"]:
        print("\nCandidate:", candidate["candidate_id"])
        print(
            "Research readiness:",
            candidate["research_readiness"]["total"],
            "/ 100",
        )
        print(
            "Development stages:",
            len(candidate["evolution"]),
        )
        print(
            "Next experiment:",
            candidate["recommended_next_experiment"],
        )

    print("\nCandidates:", output["candidate_count"])
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
