"""CuSelect-AI: verified computational context for AI agents."""

# PSEUDOCODE
# 1. Load the computational registry and scientific critique.
# 2. Verify the critique was generated from this exact registry.
# 3. Extract the highest k-point DFT comparison.
# 4. Preserve the numerical convergence limitations.
# 5. Save a concise, machine-readable context for AI agents.

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"

REGISTRY = (
    DATA / "16_computational_registry"
    / "computational_evidence_v1.json"
)
CRITIQUE = (
    DATA / "17_computational_critique"
    / "scientific_critique_v1.json"
)
OUTPUT = (
    DATA / "18_agent_evidence_context"
    / "agent_evidence_context_v1.json"
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Context already exists; no overwrite.")

    registry = load(REGISTRY)
    critique = load(CRITIQUE)

    if critique["registry_sha256"] != sha256(REGISTRY):
        raise ValueError("Critique and registry do not match.")

    dft = [
        item for item in registry["comparisons"]
        if item["method"] == "GPAW-PBE"
    ]

    if not dft:
        raise ValueError("No matched DFT comparisons.")

    latest = next(
        (
            item for item in dft
            if item.get("run_id") == "350ev_6x6x1"
        ),
        None,
    )

    if latest is None:
        raise ValueError("6x6x1 reference not found.")

    delta = float(latest["delta_sep_minus_nn_ev"])

    if not (
        registry["summary"]["all_dft_orderings_favor_sep"]
    ):
        raise ValueError("DFT energy ordering is inconsistent.")

    findings = {
        finding["finding"]: finding
        for finding in critique["findings"]
    }

    if findings["ethylene_selectivity"]["status"] != "unsupported":
        raise ValueError("Missing selectivity safeguard.")

    context = {
        "schema_version": "1.0",
        "project": "CuSelect-AI",
        "context_type": "computational_evidence",
        "system": "Ag2Cu34 / Cu(100)",
        "scope": (
            "Adjacent versus separated surface Ag atoms "
            "in the tested periodic clean-slab model."
        ),
        "reference": {
            "method": "GPAW-PBE",
            "geometry": "MACE-relaxed",
            "cutoff_ev": latest["cutoff_ev"],
            "kpoints": latest["kpoints"],
            "delta_sep_minus_nn_ev": delta,
            "delta_sep_minus_nn_mev": round(delta * 1000, 3),
            "status": "preliminary_dft",
        },
        "evidence_assessment": {
            "all_tested_comparisons_favor_sep": True,
            "kpoint_change_4x4_to_6x6_mev": findings[
                "kpoint_sensitivity"
            ]["difference_4x4_to_6x6_mev"],
            "cutoff_convergence": "incomplete",
            "dft_geometry_relaxation": "not_performed",
            "ethylene_selectivity": "not_predicted",
        },
        "supported_conclusion": critique[
            "supported_conclusion"
        ],
        "unsupported_conclusions": critique[
            "unsupported_conclusions"
        ],
        "scientific_limitations": registry[
            "scientific_limitations"
        ],
        "agent_instructions": [
            "Use this evidence only for the specified "
            "Cu(100) clean-slab comparison.",
            "Do not infer CO2RR activity or ethylene FE.",
            "Do not describe the DFT results as fully converged.",
            "Do not generalize this comparison to "
            "100 nm Ag-island catalyst designs.",
            "Distinguish computed energies from "
            "experimentally measured results.",
            "Recommend further validation before "
            "making performance claims.",
        ],
        "provenance": {
            "registry_sha256": sha256(REGISTRY),
            "critique_sha256": sha256(CRITIQUE),
        },
        "human_review_required": True,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(context, indent=2),
        encoding="utf-8",
    )

    print("\nCUSELECT-AI — AGENT EVIDENCE CONTEXT")
    print("=" * 55)
    print("System:", context["system"])
    print(
        "DFT SEP-NN:",
        f"{context['reference']['delta_sep_minus_nn_mev']:+.3f} meV"
    )
    print("Energy ordering: SEP favored")
    print("Ethylene FE prediction: Not available")
    print("Human review: Required")
    print("Registry and critique: Verified")
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
