"""CuSelect-AI — Research Readiness Scoring Agent v1."""

# PSEUDOCODE
# 1. Load the literature evidence, proposals, and critiques.
# 2. Check that every candidate has matching scientific evidence.
# 3. Evaluate evidence traceability and condition documentation.
# 4. Evaluate whether the hypothesis can be experimentally tested.
# 5. Evaluate whether uncertainties and alternatives are identified.
# 6. Rank research readiness without predicting catalyst performance.
# 7. Save scores and explanations.

import json
from pathlib import Path

from cuselect.agents.literature_package_agent import atomic_write

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "data" / "agent_runs"

EVIDENCE_PATH = RUNS / "literature_evidence_v1.json"
DESIGNS_PATH = RUNS / "design_proposals_v1.json"
CRITIQUES_PATH = RUNS / "scientific_critiques_v1.json"
OUTPUT_PATH = RUNS / "research_readiness_scores_v1.json"

# Required for this prototype's condition-documentation score.
# Additional fields are valuable but not silently assumed complete.
CORE_CONDITION_FIELDS = {
    "potential_v",
    "current_density_ma_cm2",
    "electrolyte",
    "cell_configuration",
    "reference_electrode",
}


def read_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def score_candidate(candidate, critique, evidence_by_id):
    candidate_id = candidate["id"]

    if critique["candidate_id"] != candidate_id:
        raise ValueError(f"Critique mismatch: {candidate_id}")

    evidence_ids = candidate["evidence_measurement_ids"]

    if not evidence_ids:
        raise ValueError(f"No evidence for {candidate_id}")

    supporting = []

    for measurement_id in evidence_ids:
        if measurement_id not in evidence_by_id:
            raise ValueError(
                f"Missing evidence: {measurement_id}"
            )

        item = evidence_by_id[measurement_id]

        if item["doi"] != candidate["source_doi"]:
            raise ValueError(
                f"DOI mismatch for {candidate_id}"
            )

        supporting.append(item)

    # 1. Evidence traceability: 25 points maximum.
    traceable = all(
        item.get("fe_review", {}).get("status") == "approved"
        and bool(
            item.get("fe_review", {}).get("source_location")
        )
        for item in supporting
    )

    evidence_score = 25 if traceable else 0

    # 2. Condition documentation: maximum 25 points.
    # Count fields verified on at least one linked record.
    verified_fields = set()

    for item in supporting:
        verified_fields.update(
            item.get("verified_conditions", {}).keys()
        )

    condition_coverage = len(
        verified_fields & CORE_CONDITION_FIELDS
    )

    condition_score = round(
        25 * condition_coverage / len(CORE_CONDITION_FIELDS),
        1,
    )

    # 3. Testability: up to 25 points.
    testability_score = 0

    if candidate.get("hypothesis"):
        testability_score += 10

    if candidate.get("proposed_experiment"):
        testability_score += 10

    if critique.get("discriminating_experiment"):
        testability_score += 5

    # 4. Uncertainty management: up to 25 points.
    uncertainty_score = 0

    if candidate.get("key_uncertainty"):
        uncertainty_score += 5

    if critique.get("primary_risk"):
        uncertainty_score += 5

    if critique.get("alternative_explanation"):
        uncertainty_score += 5

    if critique.get("discriminating_experiment"):
        uncertainty_score += 5

    if critique.get("performance_prediction_available") is False:
        uncertainty_score += 5

    total = round(
        evidence_score
        + condition_score
        + testability_score
        + uncertainty_score,
        1,
    )

    return {
        "candidate_id": candidate_id,
        "candidate_name": candidate["name"],
        "supporting_doi": candidate["source_doi"],
        "scores": {
            "evidence_traceability": evidence_score,
            "condition_documentation": condition_score,
            "testability": testability_score,
            "uncertainty_management": uncertainty_score,
            "total": total,
        },
        "verified_core_condition_fields": sorted(
            verified_fields & CORE_CONDITION_FIELDS
        ),
        "missing_core_condition_fields": sorted(
            CORE_CONDITION_FIELDS - verified_fields
        ),
        "research_priority_note": (
            "This score measures documented research readiness, "
            "not predicted ethylene selectivity or catalytic activity."
        ),
        "key_scientific_risk": critique["primary_risk"],
        "recommended_validation": (
            critique["discriminating_experiment"]
        ),
        "predicted_fe_percent": None,
    }


def score_designs(designs, critiques, literature):
    if designs.get("agent") != "design_agent":
        raise ValueError("Incorrect Design Agent input")

    if critiques.get("agent") != "scientific_critic":
        raise ValueError("Incorrect Critic Agent input")

    if literature.get("agent") != "literature_agent":
        raise ValueError("Incorrect Literature Agent input")

    evidence_by_id = {
        item["measurement_id"]: item
        for item in literature["evidence"]
    }

    critique_by_id = {
        item["candidate_id"]: item
        for item in critiques["critiques"]
    }

    if len(critique_by_id) != len(critiques["critiques"]):
        raise ValueError("Duplicate critique IDs")

    scored = []

    for candidate in designs["candidates"]:
        candidate_id = candidate["id"]

        if candidate_id not in critique_by_id:
            raise ValueError(
                f"Missing critique for {candidate_id}"
            )

        result = score_candidate(
            candidate,
            critique_by_id[candidate_id],
            evidence_by_id,
        )

        scored.append(result)

    scored.sort(
        key=lambda item: (
            -item["scores"]["total"],
            item["candidate_id"],
        )
    )

    for rank, result in enumerate(scored, 1):
        result["presentation_order"] = rank

    return {
        "schema_version": "1.0",
        "agent": "scoring_agent",
        "scoring_method": "deterministic_research_readiness",
        "maximum_score": 100,
        "weights": {
            "evidence_traceability": 25,
            "condition_documentation": 25,
            "testability": 25,
            "uncertainty_management": 25,
        },
        "warning": (
            "Scores describe evidence and research readiness. "
            "They are not experimentally validated catalyst "
            "rankings or machine-learning predictions. "
            "Review completeness can change presentation order."
        ),
        "candidates": scored,
    }


def main():
    literature = read_json(EVIDENCE_PATH)
    designs = read_json(DESIGNS_PATH)
    critiques = read_json(CRITIQUES_PATH)

    result = score_designs(
        designs,
        critiques,
        literature,
    )

    atomic_write(OUTPUT_PATH, result)

    print("\nCUSELECT-AI — SCORING AGENT v1")
    print("=" * 65)

    for item in result["candidates"]:
        print(
            item["presentation_order"],
            item["candidate_id"],
            "| Readiness:",
            item["scores"]["total"],
            "/ 100",
        )
        print("  Evidence DOI:", item["supporting_doi"])
        print(
            "  Verified core conditions:",
            len(item["verified_core_condition_fields"]),
            "/",
            len(CORE_CONDITION_FIELDS),
        )
        print("  Prediction: Not available")

    print("\nSaved:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
