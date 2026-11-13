"""CuSelect-AI: preliminary Cu-Ag EMT benchmark."""

# PSEUDOCODE
# 1. Load adjacent and separated Ag-pair structures.
# 2. Verify matching composition and simulation cells.
# 3. Attach independent ASE EMT calculators.
# 4. Calculate single-point energies and forces.
# 5. Report the energy difference and force magnitudes.
# 6. Do not modify or overwrite source structures.

from pathlib import Path

import numpy as np
from ase.io import read
from ase.calculators.emt import EMT

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "data/processed/04_structures"

FILES = {
    "Adjacent": "CU-001-100-AG2-NN.extxyz",
    "Separated": "CU-001-100-AG2-SEP.extxyz",
}


def calculate(label, filename):
    atoms = read(FOLDER / filename)

    if atoms.get_chemical_formula() != "Ag2Cu34":
        raise ValueError("Unexpected composition.")

    if atoms.info.get("geometry_status") != "unrelaxed":
        raise ValueError("Unexpected geometry status.")

    # Attach a calculator to the in-memory structure only.
    atoms.calc = EMT()

    energy = float(atoms.get_potential_energy())
    forces = atoms.get_forces()
    force_norms = np.linalg.norm(forces, axis=1)

    return {
        "label": label,
        "atoms": atoms,
        "energy": energy,
        "max_force": float(force_norms.max()),
        "mean_force": float(force_norms.mean()),
    }


def main():
    results = [
        calculate(label, filename)
        for label, filename in FILES.items()
    ]

    adjacent, separated = results

    if not np.allclose(
        adjacent["atoms"].cell,
        separated["atoms"].cell,
    ):
        raise ValueError("Simulation cells do not match.")

    if not np.array_equal(
        adjacent["atoms"].pbc,
        separated["atoms"].pbc,
    ):
        raise ValueError("Periodic boundaries do not match.")

    print("\nCUSELECT-AI — FIRST EMT ENERGY BENCHMARK")
    print("=" * 65)

    for result in results:
        print("\n", result["label"])
        print("Energy (eV):", round(result["energy"], 6))
        print(
            "Maximum force (eV/Å):",
            round(result["max_force"], 6),
        )
        print(
            "Mean force (eV/Å):",
            round(result["mean_force"], 6),
        )

    delta = (
        separated["energy"] - adjacent["energy"]
    )

    print("\n" + "=" * 65)
    print("ENERGY DIFFERENCE")
    print("ΔE = E(separated) - E(adjacent)")
    print(f"ΔE = {delta:+.6f} eV")

    if delta > 0:
        print(
            "At these fixed coordinates, EMT gives "
            "a lower energy for the adjacent arrangement."
        )
    elif delta < 0:
        print(
            "At these fixed coordinates, EMT gives "
            "a lower energy for the separated arrangement."
        )
    else:
        print("Both arrangements have equal EMT energies.")

    print("\nIMPORTANT LIMITATIONS")
    print("- Structures are unrelaxed.")
    print("- This is an approximate empirical potential.")
    print("- No solvent, applied potential, or reaction pathway.")
    print("- No catalytic selectivity prediction.")
    print("- No source structure files modified.")


if __name__ == "__main__":
    main()
