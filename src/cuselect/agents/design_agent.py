"""CuSelect-AI — Evidence-grounded catalyst Design Agent v1."""

# PSEUDOCODE
# 1. Load the Literature Agent's reviewed evidence package.
# 2. Match each candidate design to relevant publications.
# 3. Generate three testable catalyst-design hypotheses.
# 4. Preserve the difference between literature evidence and
#    proposed, experimentally unverified design modifications.
# 5. Save proposals for the Scientific Critic.

import json
from pathlib import Path

from cuselect.agents.literature_package_agent import atomic_write

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data" / "agent_runs" / "literature_evidence_v1.json"
OUTPUT = ROOT / "data" / "agent_runs" / "design_proposals_v1.json"

DESIGN_TEMPLATES = [
    {
        "id": "CUAG-001",
        "name": "Ag/Cu interface-density engineering",
        "source_doi": "10.1021/acsami.8b20545",
        "hypothesis": (
            "Controlling the spatial distribution of Ag/Cu "
            "interfaces may influence ethylene selectivity."
        ),
        "proposed_experiment": (
            "Prepare catalysts with systematically varied "
            "Ag/Cu interface density while controlling "
            "composition, loading, and testing conditions."
        ),
        "key_uncertainty": (
            "Whether interface density can be varied "
            "independently of morphology and composition."
        ),
    },
    {
        "id": "CUAG-002",
        "name": "Porosity-controlled Cu-Ag catalyst",
        "source_doi": "10.1021/jacs.8b01868",
        "hypothesis": (
            "Modifying pore morphology in Cu-Ag catalysts "
            "may influence local transport and C2 selectivity."
        ),
        "proposed_experiment": (
            "Prepare comparable Cu-Ag catalysts with different "
            "pore structures and measure ethylene and ethanol "
            "selectivity under matched operating conditions."
        ),
        "key_uncertainty": (
            "Whether changes in selectivity arise from "
            "porosity, surface composition, or restructuring."
        ),
    },
    {
        "id": "CUAG-003",
        "name": "Ag nanoparticle distribution on Cu frameworks",
        "source_doi": "10.1002/aenm.202300088",
        "hypothesis": (
            "Controlling Ag nanoparticle distribution on "
            "Cu-containing framework nanosheets may change "
            "ethylene selectivity."
        ),
        "proposed_experiment": (
            "Vary Ag nanoparticle dispersion while monitoring "
            "framework stability, catalyst composition, "
            "and product selectivity."
        ),
        "key_uncertainty": (
            "Whether the original framework structure "
            "persists under CO2 reduction conditions."
        ),
    },
]


def generate_proposals(package):
    if package.get("agent") != "literature_agent":
        raise ValueError("Expected Literature Agent output.")

    evidence = package.get("evidence", [])
    proposals = []

    for template in DESIGN_TEMPLATES:
        relevant = [
            record for record in evidence
            if record["doi"] == template["source_doi"]
        ]

        if not relevant:
            raise ValueError(
                f"No approved evidence for {template['source_doi']}"
            )

        proposals.append({
            **template,
            "status": "untested_design_hypothesis",
            "evidence_measurement_ids": [
                record["measurement_id"] for record in relevant
            ],
            "supporting_observations": [
                {
                    "product": record["product"],
                    "fe_percent": record["fe_percent"],
                    "qualifier": record["fe_qualifier"],
                    "source_location": record["fe_review"][
                        "source_location"
                    ],
                }
                for record in relevant
            ],
            "predicted_fe_percent": None,
            "scientific_warning": (
                "Reported literature performance is not "
                "a prediction for this proposed design."
            ),
        })

    return {
        "schema_version": "1.0",
        "agent": "design_agent",
        "objective": "Explore Cu-based CO2-to-ethylene catalysts",
        "generation_method": "deterministic_evidence_grounded_templates",
        "candidate_count": len(proposals),
        "candidates": proposals,
    }


def main():
    with SOURCE.open(encoding="utf-8") as file:
        package = json.load(file)

    output = generate_proposals(package)
    atomic_write(OUTPUT, output)

    print("\nCUSELECT-AI — DESIGN AGENT v1")
    print("=" * 55)

    for candidate in output["candidates"]:
        print(candidate["id"], "|", candidate["name"])
        print("Evidence DOI:", candidate["source_doi"])
        print("Status:", candidate["status"])
        print()

    print("Total candidates:", output["candidate_count"])
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
