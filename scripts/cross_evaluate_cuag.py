"""CuSelect-AI: EMT and MACE geometry cross-evaluation."""

# PSEUDOCODE
# 1. Load both sets of relaxed Cu-Ag structures.
# 2. Verify composition, simulation cell and periodicity.
# 3. Evaluate each geometry using EMT and MACE.
# 4. Measure energy differences and residual forces.
# 5. Compare model preferences and geometry sensitivity.
# 6. Save an independent reproducible JSON report.
# 7. Never modify original structures.

import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
from ase.io import read
from ase.calculators.emt import EMT
from mace.calculators import mace_mp

ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "EMT-relaxed": ROOT / "data/processed/05_emt_relaxations",
    "MACE-relaxed": ROOT / "data/processed/07_mace_relaxations",
}

CANDIDATES = {
    "NN": "CU-001-100-AG2-NN.extxyz",
    "SEP": "CU-001-100-AG2-SEP.extxyz",
}

OUTPUT = (
    ROOT / "data/processed/08_cross_evaluation"
    / "cross_evaluation.json"
)


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_structures():
    structures = {}
    reference = None

    for geometry, folder in SOURCES.items():
        for candidate, filename in CANDIDATES.items():
            path = folder / filename
            atoms = read(path)

            if atoms.get_chemical_formula() != "Ag2Cu34":
                raise ValueError(f"Invalid composition: {path}")

            if not np.array_equal(
                atoms.pbc, [True, True, False]
            ):
                raise ValueError(f"Invalid periodicity: {path}")

            if len(atoms) != 36:
                raise ValueError(f"Invalid atom count: {path}")

            if reference is None:
                reference = atoms
            elif not np.allclose(
                atoms.cell, reference.cell, atol=1e-5
            ):
                raise ValueError("Simulation cells differ.")

            # Identify the bottom 18 atoms geometrically.
            z = atoms.positions[:, 2]
            ordering = np.argsort(z)
            sorted_z = z[ordering]

            if sorted_z[18] - sorted_z[17] < 0.5:
                raise ValueError(
                    f"Cannot identify fixed bottom layers: {path}"
                )

            fixed = ordering[:18].tolist()
            free = ordering[18:].tolist()

            structures[(geometry, candidate)] = {
                "atoms": atoms,
                "path": path,
                "fixed": fixed,
                "free": free,
            }

    return structures


def evaluate(atoms, free_indices, calculator):
    # Fresh in-memory structure; source file unchanged.
    sample = atoms.copy()
    sample.set_constraint()
    sample.calc = calculator

    energy = float(sample.get_potential_energy())

    # Unconstrained forces, then explicitly select
    # the atoms that were allowed to relax.
    forces = sample.get_forces(
        apply_constraint=False
    )

    magnitudes = np.linalg.norm(forces, axis=1)

    return {
        "energy_ev": energy,
        "max_force_all_ev_ang": float(
            magnitudes.max()
        ),
        "max_force_free_ev_ang": float(
            magnitudes[free_indices].max()
        ),
    }


def main():
    if OUTPUT.exists():
        raise SystemExit(
            "Cross-evaluation output already exists. "
            "No files overwritten."
        )

    structures = load_structures()

    print("\nCUSELECT-AI — MODEL CROSS-EVALUATION")
    print("=" * 65)
    print("Loading MACE-MP-0 small on CPU...")

    calculators = {
        "EMT": EMT(),
        "MACE-MP-0-small": mace_mp(
            model="small",
            device="cpu",
            default_dtype="float64",
        ),
    }

    results = {}
    deltas = {}

    for model_name, calculator in calculators.items():
        results[model_name] = {}
        deltas[model_name] = {}

        for geometry in SOURCES:
            results[model_name][geometry] = {}

            for candidate in CANDIDATES:
                data = structures[(geometry, candidate)]

                result = evaluate(
                    data["atoms"],
                    data["free"],
                    calculator,
                )

                result["structure_sha256"] = fingerprint(
                    data["path"]
                )

                results[model_name][geometry][
                    candidate
                ] = result

                print(
                    f"{model_name:18} | "
                    f"{geometry:12} | "
                    f"{candidate:3} | "
                    f"E={result['energy_ev']:+.6f} eV | "
                    f"Ffree={result['max_force_free_ev_ang']:.4f}"
                )

            pair = results[model_name][geometry]

            delta = (
                pair["SEP"]["energy_ev"]
                - pair["NN"]["energy_ev"]
            )

            deltas[model_name][geometry] = delta

    print("\nENERGY DIFFERENCE: SEP - NN")
    print("-" * 65)

    for model_name, values in deltas.items():
        for geometry, delta in values.items():
            favored = (
                "SEP" if delta < 0
                else "NN" if delta > 0
                else "TIE"
            )

            print(
                f"{model_name:18} | "
                f"{geometry:12} | "
                f"{delta:+.6f} eV | "
                f"Lower energy: {favored}"
            )

    summary = {
        "task": "cuag_potential_cross_evaluation",
        "mace_model": "MACE-MP-0 small",
        "device": "cpu",
        "dtype": "float64",
        "ase_version": version("ase"),
        "mace_torch_version": version("mace-torch"),
        "torch_version": version("torch"),
        "source_geometries": list(SOURCES),
        "results": results,
        "deltas_sep_minus_nn_ev": deltas,
        "geometry_relaxation_performed": False,
        "dft_reference_validation": False,
        "predicted_fe_percent": None,
    }

    OUTPUT.parent.mkdir(
        parents=True, exist_ok=True
    )

    OUTPUT.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\nCROSS-EVALUATION COMPLETE")
    print("Saved:", OUTPUT)
    print("Original structures unchanged.")
    print("No catalyst selectivity prediction.")


if __name__ == "__main__":
    main()
