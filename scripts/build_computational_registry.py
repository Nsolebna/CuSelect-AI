"""CuSelect-AI: provenance-tracked computational evidence registry."""

# PSEUDOCODE
# 1. Read existing EMT/MACE cross-evaluation results.
# 2. Read available GPAW DFT result files.
# 3. Validate structure hashes, methods and paired settings.
# 4. Compute within-method NN-versus-SEP energy differences.
# 5. Attach scientific limitations and validation status.
# 6. Save a machine-readable registry without altering inputs.

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
OUTPUT = DATA / "16_computational_registry"
DESTINATION = OUTPUT / "computational_evidence_v1.json"

STRUCTURES = DATA / "07_mace_relaxations"

CONFIGURATIONS = {
    "NN": "CU-001-100-AG2-NN.extxyz",
    "SEP": "CU-001-100-AG2-SEP.extxyz",
}

DFT_RUNS = [
    ("250ev_gamma", "10_dft_slab_pilot", 250, [1, 1, 1]),
    ("350ev_gamma", "11_dft_cutoff_retry", 350, [1, 1, 1]),
    ("350ev_2x2x1", "12_dft_kpoint_tests", 350, [2, 2, 1]),
    ("350ev_4x4x1", "13_dft_kpoint_4x4", 350, [4, 4, 1]),
    ("350ev_6x6x1", "14_dft_kpoint_6x6", 350, [6, 6, 1]),
]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    if DESTINATION.exists():
        raise SystemExit(
            "Registry already exists. Refusing to overwrite."
        )

    hashes = {}

    for candidate, filename in CONFIGURATIONS.items():
        path = STRUCTURES / filename

        if not path.exists():
            raise FileNotFoundError(path)

        hashes[candidate] = sha256(path)

    registry = {
        "schema_version": "1.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "project": "CuSelect-AI",
        "system": "Ag2Cu34 on periodic Cu(100)",
        "comparisons": [],
        "missing_results": [],
        "scientific_limitations": [
            "Only NN and SEP configurations are compared.",
            "Clean-slab energies do not predict ethylene selectivity.",
            "Models have not been validated for electrochemical potential.",
            "DFT cutoff convergence at dense k-points is incomplete.",
            "DFT structures have not been geometry-optimized.",
            "Finite-size and periodic-image effects remain untested.",
            "Agreement across models is not a statistical uncertainty.",
        ],
    }

    # Load the existing model cross-evaluation.
    cross_path = (
        DATA / "08_cross_evaluation"
        / "cross_evaluation.json"
    )
    cross = load_json(cross_path)

    for model, geometries in cross[
        "deltas_sep_minus_nn_ev"
    ].items():
        for geometry, delta in geometries.items():
            registry["comparisons"].append({
                "method": model,
                "geometry": geometry,
                "delta_sep_minus_nn_ev": float(delta),
                "source_path": str(
                    cross_path.relative_to(ROOT)
                ),
                "source_sha256": sha256(cross_path),
                "evidence_status": "model_comparison",
                "dft_reference": False,
            })

    # Load and validate matched DFT calculations.
    for run_id, folder, cutoff, kpoints in DFT_RUNS:
        records = {}
        paths = {}

        for candidate in ("NN", "SEP"):
            path = (
                DATA / folder
                / f"{candidate.lower()}_pbe_{run_id}.json"
            )

            if not path.exists():
                registry["missing_results"].append(
                    str(path.relative_to(ROOT))
                )
                continue

            record = load_json(path)

            if record.get("geometry_sha256") != hashes[candidate]:
                raise ValueError(
                    f"Structure fingerprint mismatch: {path}"
                )

            if record.get("cutoff_ev") != cutoff:
                raise ValueError(f"Cutoff mismatch: {path}")

            actual_kpoints = record.get(
                "kpoints", record.get("kpts")
            )

            if actual_kpoints != kpoints:
                raise ValueError(f"K-point mismatch: {path}")

            if record.get("functional") != "PBE":
                raise ValueError(f"Functional mismatch: {path}")

            if record.get("smearing_ev") != 0.1:
                raise ValueError(f"Smearing mismatch: {path}")

            spin = record.get(
                "spin_polarized", record.get("spinpol")
            )
            if spin is not False:
                raise ValueError(f"Spin setting mismatch: {path}")

            if record.get("scf_completed_without_exception") is not True:
                raise ValueError(f"SCF not confirmed: {path}")

            records[candidate] = record
            paths[candidate] = path

        if set(records) != {"NN", "SEP"}:
            continue

        nn_energy = float(records["NN"]["energy_ev"])
        sep_energy = float(records["SEP"]["energy_ev"])

        registry["comparisons"].append({
            "method": "GPAW-PBE",
            "geometry": "MACE-relaxed",
            "run_id": run_id,
            "cutoff_ev": cutoff,
            "kpoints": kpoints,
            "smearing_ev": 0.1,
            "nn_energy_ev": nn_energy,
            "sep_energy_ev": sep_energy,
            "delta_sep_minus_nn_ev": sep_energy - nn_energy,
            "source_files": {
                candidate: {
                    "path": str(paths[candidate].relative_to(ROOT)),
                    "sha256": sha256(paths[candidate]),
                    "structure_sha256": hashes[candidate],
                }
                for candidate in ("NN", "SEP")
            },
            "evidence_status": "preliminary_dft",
            "numerically_converged": False,
            "dft_geometry_optimized": False,
            "ethylene_selectivity_predicted": False,
        })

    dft = [
        record for record in registry["comparisons"]
        if record["method"] == "GPAW-PBE"
    ]

    registry["summary"] = {
        "total_comparisons": len(registry["comparisons"]),
        "matched_dft_comparisons": len(dft),
        "all_dft_orderings_favor_sep": (
            bool(dft) and all(
                r["delta_sep_minus_nn_ev"] < 0
                for r in dft
            )
        ),
        "scientific_conclusion": (
            "Preliminary energetic preference for SEP "
            "within the tested periodic slab configurations."
        ),
        "ethylene_fe_prediction_available": False,
        "publication_quality_validation_complete": False,
    }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_text(
        json.dumps(registry, indent=2),
        encoding="utf-8",
    )

    print("\nCUSELECT-AI — COMPUTATIONAL EVIDENCE REGISTRY")
    print("=" * 65)

    for item in dft:
        print(
            f"{item['run_id']:17} "
            f"SEP-NN = "
            f"{item['delta_sep_minus_nn_ev']*1000:+.3f} meV"
        )

    print("\nTotal comparisons:",
          registry["summary"]["total_comparisons"])
    print("Matched DFT comparisons:", len(dft))
    print("Missing results:", len(registry["missing_results"]))
    print("Saved:", DESTINATION)
    print("Original scientific results unchanged.")


if __name__ == "__main__":
    main()
