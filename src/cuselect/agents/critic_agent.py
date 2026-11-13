"""CuSelect-AI — Scientific Critic Agent v1."""

# PSEUDOCODE
# 1. Load design proposals and the approved evidence package.
# 2. Check that every referenced measurement exists.
# 3. Identify scientific uncertainties for each design.
# 4. Recommend discriminating experiments.
# 5. Save a structured, auditable critique.

import json
from pathlib import Path

from cuselect.agents.literature_package_agent import atomic_write

ROOT = Path(__file__).resolve().parents[3]
DESIGNS = ROOT / "data/agent_runs/design_proposals_v1.json"
EVIDENCE = ROOT / "data/agent_runs/literature_evidence_v1.json"
OUTPUT = ROOT / "data/agent_runs/scientific_critiques_v1.json"

CRITIQUE_RULES = {
    "CUAG-001": {
        "primary_risk": (
            "Ag/Cu interface density may covary with Ag loading, "
            "particle size and exposed Cu surface area."
        ),
        "alternative_explanation": (
            "Changes in ethylene selectivity may originate from "
            "surface composition or catalyst restructuring "
            "rather than interface density alone."
        ),
        "discriminating_experiment": (
            "Compare catalysts at matched Ag fraction and "
            "electrochemical surface area while systematically "
            "varying interface length."
        ),
    },
    "CUAG-002": {
        "primary_risk": (
            "Pore morphology, wetting and local transport "
            "may change together."
        ),
        "alternative_explanation": (
            "Selectivity differences may arise from local CO2 "
            "availability, pH or Cu/Ag surface composition."
        ),
        "discriminating_experiment": (
            "Compare pore structures at controlled composition, "
            "loading and operating conditions; measure local "
            "transport and wetting indicators."
        ),
    },
    "CUAG-003": {
        "primary_risk": (
            "The Cu-containing framework may reconstruct "
            "during electrochemical operation."
        ),
        "alternative_explanation": (
            "The active state may differ from the synthesized "
            "framework-nanosheet structure."
        ),
        "discriminating_experiment": (
            "Perform operando or post-reaction characterization "
            "and compare controlled Ag nanoparticle distributions."
        ),
    },
}


def critique_designs(designs, evidence_package):
    if designs.get("agent") != "design_agent":
        raise ValueError("Unexpected design input.")

    if evidence_package.get("agent") != "literature_agent":
        raise ValueError("Unexpected evidence input.")

    evidence_by_id = {
        item["measurement_id"]: item
        for item in evidence_package["evidence"]
    }

    critiques = []

    for candidate in designs["candidates"]:
        candidate_id = candidate["id"]
        rules = CRITIQUE_RULES.get(candidate_id)
        review_source = "predefined_scientific_rules"

        if rules is None:
            rules = candidate.get("scientific_review")
            review_source = "candidate_supplied_review_draft"

            required_fields = (
                "primary_risk",
                "alternative_explanation",
                "discriminating_experiment",
            )

            if not isinstance(rules, dict) or any(
                not isinstance(rules.get(field), str)
                or not rules[field].strip()
                for field in required_fields
            ):
                raise ValueError(
                    f"Candidate {candidate_id} requires a complete "
                    "provisional scientific review."
                )

        ids = candidate["evidence_measurement_ids"]

        if not ids:
            raise ValueError(
                f"Candidate {candidate_id} has no evidence."
            )

        supporting_records = []

        for mid in ids:
            record = evidence_by_id.get(mid)

            if record is None:
                raise ValueError(
                    f"Missing evidence measurement: {mid}"
                )

            if record["doi"] != candidate["source_doi"]:
                raise ValueError(
                    f"DOI mismatch for measurement: {mid}"
                )

            supporting_records.append(record)

        incomplete_conditions = any(
            not item["conditions_complete"]
            for item in supporting_records
        )

        critiques.append({
            "candidate_id": candidate_id,
            "candidate_name": candidate["name"],
            "evaluation_method": review_source,
            "supporting_doi": candidate["source_doi"],
            "validated_evidence_ids": ids,
            "evidence_traceable": True,
            "primary_risk": rules["primary_risk"],
            "alternative_explanation": (
                rules["alternative_explanation"]
            ),
            "discriminating_experiment": (
                rules["discriminating_experiment"]
            ),
            "conditions_incomplete": incomplete_conditions,
            "performance_prediction_available": False,
            "assessment": "requires_experimental_validation",
            "scientific_note": (
                "This is a predefined critical assessment, "
                "not an independently validated mechanistic "
                "finding or an LLM-generated conclusion."
            ),
        })

    for critique in critiques:
        if critique["evaluation_method"] == "candidate_supplied_review_draft":
            critique["scientific_note"] = (
                "Candidate-supplied provisional scientific assessment. "
                "Requires independent expert review; this is not "
                "experimental or mechanistic validation."
            )

    return {
        "schema_version": "1.0",
        "agent": "scientific_critic",
        "method": "deterministic_scientific_rules",
        "critiques": critiques,
        "critique_count": len(critiques),
    }


def main():
    with DESIGNS.open(encoding="utf-8") as file:
        designs = json.load(file)

    with EVIDENCE.open(encoding="utf-8") as file:
        evidence = json.load(file)

    result = critique_designs(designs, evidence)
    atomic_write(OUTPUT, result)

    print("\nCUSELECT-AI — SCIENTIFIC CRITIC v1")
    print("=" * 55)

    for critique in result["critiques"]:
        print("\nCandidate:", critique["candidate_id"])
        print("Primary risk:", critique["primary_risk"])
        print(
            "Alternative explanation:",
            critique["alternative_explanation"]
        )
        print(
            "Proposed validation:",
            critique["discriminating_experiment"]
        )
        print(
            "Operating conditions complete:",
            not critique["conditions_incomplete"]
        )

    print("\nTotal critiques:", result["critique_count"])
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
