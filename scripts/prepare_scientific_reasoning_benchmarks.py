"""Prepare offline scientific reasoning evaluation packets."""

# PSEUDOCODE
# 1. Read the six-scenario scientific benchmark.
# 2. Select the four cases requiring scientific reasoning.
# 3. Attach concrete scientific inputs and assessment criteria.
# 4. Record limitations and forbidden conclusions.
# 5. Save a reproducible evaluation dataset.
# 6. Do not call an LLM or assign performance scores.

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/benchmarks/scientific_scenarios_v1.json"
OUTPUT = ROOT / "data/benchmarks/reasoning_evaluation_v1.json"

CASES = {
    "B01": {
        "input": (
            "A published Cu-based CO2 electroreduction catalyst "
            "is reported to achieve 48% ethylene Faradaic "
            "efficiency. The excerpt does not specify the "
            "electrolyte, current density, electrode geometry, "
            "cell configuration, potential scale or duration. "
            "Evaluate whether this result justifies predicting "
            "superior ethylene production in a new gas-fed cell."
        ),
        "required_elements": [
            "Identify missing operating conditions",
            "Distinguish reported FE from transferable performance",
            "Explain why cross-study comparison is unsupported",
            "Recommend obtaining original experimental details",
        ],
        "forbidden_conclusions": [
            "Assume missing experimental parameters",
            "Predict new-cell FE as an established result",
            "Claim superiority over comparable catalysts",
        ],
    },
    "B02": {
        "input": (
            "CuSelect-AI compared adjacent and separated Ag "
            "configurations in an Ag2Cu34/Cu(100) clean slab. "
            "MACE-relaxed structures were evaluated using "
            "GPAW-PBE. At 350 eV and a 6x6x1 k-point grid, "
            "the separated-minus-adjacent energy difference "
            "was -73.421 meV. DFT geometry relaxation, "
            "electrolyte, electrode potential, adsorbates and "
            "reaction intermediates were not included. "
            "Explain what this result establishes and whether "
            "it proves improved CO transfer or ethylene FE."
        ),
        "required_elements": [
            "Interpret negative energy difference correctly",
            "Limit conclusions to modeled structural energetics",
            "Recognize missing electrochemical environment",
            "Recognize outstanding convergence and geometry limitations",
            "Separate energy ordering from reaction selectivity",
        ],
        "forbidden_conclusions": [
            "Claim demonstrated CO spillover",
            "Claim calculated ethylene FE",
            "Treat preliminary clean-slab calculations as catalytic validation",
        ],
    },
    "B03": {
        "input": (
            "Two experimental summaries describe nominally "
            "similar Ag/Cu catalysts. Study A reports 35% "
            "ethylene FE and Study B reports 12% ethylene FE. "
            "Neither summary specifies the full current "
            "density, electrolyte, cell design, catalyst "
            "loading or product-analysis protocols. "
            "Explain whether these observations constitute "
            "a genuine scientific contradiction."
        ),
        "required_elements": [
            "Identify numerical disagreement",
            "Distinguish disagreement from established contradiction",
            "Request comparable operating conditions",
            "Consider measurement and transport differences",
            "Avoid inventing the reason for the discrepancy",
        ],
        "forbidden_conclusions": [
            "Fabricate experimental conditions",
            "Declare either study incorrect without evidence",
            "Assert a specific mechanistic explanation as fact",
        ],
    },
    "B06": {
        "input": (
            "An exploratory Ag-island/Cu foil catalyst produces "
            "more ethylene than an unpatterned Cu control. "
            "However, electrochemically active surface area, "
            "roughness, wetting, local pH, catalyst stability, "
            "mass transport and CO availability are not yet "
            "controlled or characterized. Evaluate a claim "
            "that Ag-derived CO spillover caused the gain. "
            "Propose discriminating experiments."
        ),
        "required_elements": [
            "Reject unique mechanistic attribution",
            "Identify competing surface and transport explanations",
            "Recommend matched-pattern controls",
            "Recommend relevant product and CO measurements",
            "Discuss source-resolved tracing as a possible test",
        ],
        "forbidden_conclusions": [
            "Declare CO spillover experimentally proven",
            "Claim a unique cause for the ethylene increase",
            "Claim source-resolved carbon attribution without tracing",
        ],
    },
}


def build_packets():
    dataset = json.loads(SOURCE.read_text(encoding="utf-8"))

    if dataset.get("schema_version") != "1.0":
        raise ValueError("Unexpected benchmark schema.")

    scenarios = dataset["scenarios"]
    expected_ids = {f"B{i:02d}" for i in range(1, 7)}

    if (
        len(scenarios) != 6
        or {s["id"] for s in scenarios} != expected_ids
    ):
        raise ValueError("Unexpected benchmark scenario set.")

    packets = []

    for scenario in scenarios:
        identifier = scenario["id"]

        if identifier not in CASES:
            continue

        case = CASES[identifier]

        packets.append({
            "id": identifier,
            "category": scenario["category"],
            "scientific_input": case["input"],
            "required_elements": case["required_elements"],
            "forbidden_conclusions": case["forbidden_conclusions"],
            "evaluation_status": "not_evaluated",
            "agent_response": None,
            "human_review": None,
        })

    return {
        "schema_version": "1.0",
        "project": "CuSelect-AI",
        "purpose": "Scientific Critic Agent evaluation",
        "source_benchmark": SOURCE.name,
        "case_count": len(packets),
        "model_calls_executed": 0,
        "evaluation_status": "prepared_only",
        "scoring_policy": {
            "required_element": "assess individually: met, unmet or unclear",
            "forbidden_conclusion": "any supported violation is critical",
            "human_review_required": True,
            "automatic_scientific_accuracy_claim": False,
        },
        "cases": packets,
    }


def main():
    if OUTPUT.exists():
        raise SystemExit(
            f"Output already exists; refusing overwrite: {OUTPUT}"
        )

    report = build_packets()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print("\nCUSELECT-AI — SCIENTIFIC REASONING BENCHMARKS")
    print("=" * 60)
    print("Evaluation packets:", report["case_count"])
    print("Output:", OUTPUT)
    print("Status: Prepared, not evaluated")
    print("Scientific human review: Required")
    print("LLM calls: 0")
    print("DFT calculations: 0")


if __name__ == "__main__":
    main()
