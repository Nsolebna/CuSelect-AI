"""CuSelect-AI: deterministic computational evidence critic."""

# PSEUDOCODE
# 1. Load the computational evidence registry.
# 2. Check its scientific and numerical consistency.
# 3. Quantify k-point sensitivity where supported.
# 4. Distinguish supported claims from unsupported claims.
# 5. Save a provenance-tracked assessment for AI agents.

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT / "data/processed/16_computational_registry"
    / "computational_evidence_v1.json"
)
OUTPUT = (
    ROOT / "data/processed/17_computational_critique"
    / "scientific_critique_v1.json"
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit(
            "Critique already exists; refusing to overwrite."
        )

    registry = read_json(SOURCE)

    if registry.get("schema_version") != "1.0":
        raise ValueError("Unexpected registry schema.")

    records = registry.get("comparisons", [])
    dft = {
        r["run_id"]: r
        for r in records
        if r["method"] == "GPAW-PBE"
    }

    required = [
        "350ev_gamma",
        "350ev_2x2x1",
        "350ev_4x4x1",
        "350ev_6x6x1",
    ]

    for run_id in required:
        if run_id not in dft:
            raise ValueError(f"Missing DFT run: {run_id}")

    for record in records:
        delta = float(record["delta_sep_minus_nn_ev"])

        if not (-100 < delta < 100):
            raise ValueError("Implausible energy difference.")

        if record["method"] == "GPAW-PBE":
            expected = (
                float(record["sep_energy_ev"])
                - float(record["nn_energy_ev"])
            )
            if abs(expected - delta) > 1e-8:
                raise ValueError("DFT energy difference mismatch.")

    all_favor_sep = all(
        float(r["delta_sep_minus_nn_ev"]) < 0
        for r in records
    )

    delta_4 = float(
        dft["350ev_4x4x1"]["delta_sep_minus_nn_ev"]
    )
    delta_6 = float(
        dft["350ev_6x6x1"]["delta_sep_minus_nn_ev"]
    )

    change_mev = abs(delta_6 - delta_4) * 1000

    findings = [
        {
            "finding": "energy_ordering",
            "status": "supported_for_tested_configurations"
                      if all_favor_sep else "model_disagreement",
            "details": (
                "All available comparisons favor separated Ag."
                if all_favor_sep else
                "At least one comparison does not favor separated Ag."
            ),
        },
        {
            "finding": "kpoint_sensitivity",
            "status": "preliminary",
            "difference_4x4_to_6x6_mev": change_mev,
            "details": (
                "Measured at 350 eV using fixed "
                "MACE-relaxed geometries."
            ),
        },
        {
            "finding": "dft_cutoff_convergence",
            "status": "incomplete",
            "details": (
                "Dense-grid plane-wave cutoff convergence "
                "has not been established."
            ),
        },
        {
            "finding": "dft_geometry_relaxation",
            "status": "not_performed",
            "details": (
                "DFT evaluated MACE-relaxed geometries; "
                "atomic positions were not DFT-optimized."
            ),
        },
        {
            "finding": "ethylene_selectivity",
            "status": "unsupported",
            "details": (
                "Clean-slab stability alone cannot establish "
                "CO2-to-ethylene selectivity or Faradaic efficiency."
            ),
        },
    ]

    report = {
        "report_version": "1.0",
        "registry_sha256": sha256(SOURCE),
        "source_registry": str(SOURCE.relative_to(ROOT)),
        "model_comparisons_checked": len(records),
        "matched_dft_comparisons_checked": len(dft),
        "findings": findings,
        "supported_conclusion": (
            "The separated Ag configuration has lower "
            "calculated energy across the tested "
            "clean-slab model comparisons."
        ) if all_favor_sep else (
            "The tested models do not unanimously agree "
            "on the lower-energy configuration."
        ),
        "unsupported_conclusions": [
            "SEP is globally the most stable configuration.",
            "SEP is more active for CO2 reduction.",
            "SEP produces more ethylene.",
            "The DFT reference is fully converged.",
        ],
        "recommended_next_action": (
            "Integrate provisional computational evidence "
            "into candidate review, while prioritizing "
            "reaction-relevant descriptors and uncertainty."
        ),
        "human_scientific_review_required": True,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nCUSELECT-AI — EVIDENCE-AWARE SCIENTIFIC CRITIC")
    print("=" * 60)
    print("Comparisons checked:", len(records))
    print("DFT comparisons checked:", len(dft))
    print("All comparisons favor SEP:", all_favor_sep)
    print(
        "4x4 to 6x6 sensitivity:",
        f"{change_mev:.3f} meV"
    )

    print("\nFINDINGS")
    for finding in findings:
        print(
            f"- {finding['finding']}: "
            f"{finding['status']}"
        )

    print("\nHuman scientific review still required.")
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
