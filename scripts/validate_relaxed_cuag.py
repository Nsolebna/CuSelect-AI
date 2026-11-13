"""CuSelect-AI: structural integrity after EMT/MACE relaxation."""

# PSEUDOCODE
# 1. Read original, EMT-relaxed and MACE-relaxed structures.
# 2. Confirm that the atoms and simulation cells match.
# 3. Verify that the original bottom 18 atoms remained fixed.
# 4. Measure atomic displacements and Ag–Ag distances.
# 5. Reject unexpected structural modifications.
# 6. Do not modify source files.

from pathlib import Path
import numpy as np
from ase.io import read

ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "Original": ROOT / "data/processed/04_structures",
    "EMT": ROOT / "data/processed/05_emt_relaxations",
    "MACE": ROOT / "data/processed/07_mace_relaxations",
}

NAMES = [
    "CU-001-100-AG2-NN",
    "CU-001-100-AG2-SEP",
]


def inspect(name):
    original = read(
        SOURCES["Original"] / f"{name}.extxyz"
    )

    z = original.positions[:, 2]
    order = np.argsort(z, kind="stable")
    fixed = order[:18]
    free = order[18:]

    if np.sort(z)[18] - np.sort(z)[17] < 0.5:
        raise ValueError("Original layer separation unclear")

    print("\n" + "=" * 65)
    print("Candidate:", name)

    reference_symbols = original.get_chemical_symbols()

    for label in ["EMT", "MACE"]:
        atoms = read(
            SOURCES[label] / f"{name}.extxyz"
        )

        if atoms.get_chemical_symbols() != reference_symbols:
            raise ValueError(
                f"{label}: atomic identities changed"
            )

        if not np.allclose(atoms.cell, original.cell):
            raise ValueError(
                f"{label}: simulation cell changed"
            )

        if not np.array_equal(atoms.pbc, original.pbc):
            raise ValueError(
                f"{label}: periodicity changed"
            )

        # Minimum-image displacements handle xy periodicity.
        differences = atoms.positions - original.positions
        differences, _ = original.cell.minimum_image_displacement(
            differences
        ) if hasattr(
            original.cell, "minimum_image_displacement"
        ) else (differences, None)

        # Compare raw Cartesian coordinates for frozen atoms.
        frozen_error = float(
            np.linalg.norm(
                atoms.positions[fixed]
                - original.positions[fixed],
                axis=1,
            ).max()
        )

        # The mobile atoms are compared using MIC.
        from ase.geometry import find_mic
        _, distances = find_mic(
            atoms.positions[free]
            - original.positions[free],
            original.cell,
            original.pbc,
        )

        max_mobile_displacement = float(
            np.max(distances)
        )

        ag = [
            i for i, element in enumerate(
                atoms.get_chemical_symbols()
            )
            if element == "Ag"
        ]

        ag_distance = float(
            atoms.get_distance(
                ag[0], ag[1], mic=True
            )
        )

        print(f"\n{label}")
        print(
            "Max fixed-atom displacement:",
            f"{frozen_error:.8f} Å",
        )
        print(
            "Max mobile-atom displacement:",
            f"{max_mobile_displacement:.4f} Å",
        )
        print(
            "Final Ag–Ag separation:",
            f"{ag_distance:.4f} Å",
        )

        if frozen_error > 1e-5:
            raise ValueError(
                f"{label}: bottom layers moved unexpectedly"
            )

    print("\nIntegrity: PASSED")


for name in NAMES:
    inspect(name)

print("\nSTRUCTURAL INTEGRITY AUDIT COMPLETE")
print("All source files unchanged.")
