"""CuSelect-AI: read-only Cu–Ag geometry descriptors."""

# PSEUDOCODE
# 1. Load all registered atomic structures.
# 2. Identify the Ag and Cu atoms.
# 3. Calculate Ag–Ag separation where possible.
# 4. Calculate nearest Ag–Cu distances.
# 5. Count nearby Cu atoms around each Ag atom.
# 6. Inspect heights and structure metadata.
# 7. Report results without modifying files.

from pathlib import Path

import numpy as np
from ase.io import read

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "data" / "processed" / "04_structures"

# Illustrative first-shell cutoff, not a validated
# bond definition for these unrelaxed interfaces.
CUTOFF_ANGSTROM = 3.0


def analyze_structure(path):
    atoms = read(path)

    symbols = atoms.get_chemical_symbols()
    ag_indices = [
        i for i, symbol in enumerate(symbols)
        if symbol == "Ag"
    ]
    cu_indices = [
        i for i, symbol in enumerate(symbols)
        if symbol == "Cu"
    ]

    print("\n" + "=" * 65)
    print("Structure:", path.stem)
    print("Formula:", atoms.get_chemical_formula())
    print("Geometry status:",
          atoms.info.get("geometry_status", "unknown"))
    print("Energy status:",
          atoms.info.get("energy_status", "unknown"))
    print("Selectivity status:",
          atoms.info.get("selectivity_status", "unknown"))
    print("Facet:", atoms.info.get("facet", "unknown"))

    if len(ag_indices) == 2:
        ag_distance = atoms.get_distance(
            ag_indices[0],
            ag_indices[1],
            mic=True,
        )
        print(f"Ag–Ag distance: {ag_distance:.3f} Å")

    for ag in ag_indices:
        distances = np.array([
            atoms.get_distance(ag, cu, mic=True)
            for cu in cu_indices
        ])

        ag_z = float(atoms.positions[ag, 2])

        neighbor_count = int(
            np.sum(distances <= CUTOFF_ANGSTROM)
        )

        print(f"\nAg atom index: {ag}")
        print(f"Ag height z: {ag_z:.3f} Å")
        print(
            "Nearest Ag–Cu distance:",
            f"{distances.min():.3f} Å",
        )
        print(
            f"Cu neighbors within {CUTOFF_ANGSTROM:.1f} Å:",
            neighbor_count,
        )

    print(
        "\nInterpretation: geometric descriptors only; "
        "no energy or selectivity predictions."
    )


def main():
    paths = sorted(FOLDER.glob("*.extxyz"))

    if not paths:
        raise SystemExit("No atomic structures found.")

    print("CUSELECT-AI — GEOMETRIC DESCRIPTORS")

    for path in paths:
        analyze_structure(path)

    print("\nSTRUCTURAL ANALYSIS COMPLETE")
    print("Source files unchanged.")


if __name__ == "__main__":
    main()
