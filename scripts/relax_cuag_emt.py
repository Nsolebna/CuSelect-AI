"""CuSelect-AI: constrained EMT relaxation of Cu(100)-Ag pairs."""

# PSEUDOCODE
# 1. Read the two original Cu-Ag structures.
# 2. Verify composition, cell, periodicity and four layers.
# 3. Freeze the bottom two layers.
# 4. Optimize the remaining atoms using EMT and BFGS.
# 5. Calculate relaxed energies and free-atom forces.
# 6. Save results in a separate directory.
# 7. Preserve the original structures.

import json
from pathlib import Path

import numpy as np
from ase.io import read, write
from ase.calculators.emt import EMT
from ase.constraints import FixAtoms
from ase.optimize import BFGS

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/04_structures"
OUTPUT = ROOT / "data/processed/05_emt_relaxations"

FILES = {
    "NN": "CU-001-100-AG2-NN.extxyz",
    "SEP": "CU-001-100-AG2-SEP.extxyz",
}

FMAX = 0.05  # eV/Angstrom
MAX_STEPS = 300


def prepare(label, filename):
    atoms = read(SOURCE / filename)

    if atoms.get_chemical_formula() != "Ag2Cu34":
        raise ValueError(f"{label}: composition mismatch")

    if not np.array_equal(atoms.pbc, [True, True, False]):
        raise ValueError(f"{label}: unexpected periodicity")

    if atoms.info.get("geometry_status") != "unrelaxed":
        raise ValueError(f"{label}: unexpected source status")

    z = atoms.positions[:, 2]
    levels = np.unique(np.round(z, 3))

    if len(levels) != 4:
        raise ValueError(
            f"{label}: expected 4 atomic layers, "
            f"found {len(levels)}"
        )

    boundary = (levels[1] + levels[2]) / 2
    fixed_indices = np.where(z < boundary)[0]

    if len(fixed_indices) != 18:
        raise ValueError(
            f"{label}: expected 18 fixed atoms, "
            f"found {len(fixed_indices)}"
        )

    atoms.set_constraint(
        FixAtoms(indices=fixed_indices.tolist())
    )
    atoms.calc = EMT()

    return atoms, fixed_indices


def relax(label, atoms, fixed_indices):
    initial_energy = float(atoms.get_potential_energy())

    optimizer = BFGS(atoms, logfile=None)
    converged = bool(
        optimizer.run(fmax=FMAX, steps=MAX_STEPS)
    )

    final_energy = float(atoms.get_potential_energy())
    forces = atoms.get_forces()
    free_indices = np.array([
        index for index in range(len(atoms))
        if index not in set(fixed_indices)
    ])

    max_free_force = float(
        np.linalg.norm(forces[free_indices], axis=1).max()
    )

    ag_indices = [
        index
        for index, symbol in enumerate(
            atoms.get_chemical_symbols()
        )
        if symbol == "Ag"
    ]

    ag_distance = float(
        atoms.get_distance(
            ag_indices[0],
            ag_indices[1],
            mic=True,
        )
    )

    return {
        "candidate": label,
        "initial_energy_ev": initial_energy,
        "final_energy_ev": final_energy,
        "energy_change_ev": final_energy - initial_energy,
        "max_free_force_ev_per_angstrom": max_free_force,
        "ag_ag_distance_angstrom": ag_distance,
        "fixed_atoms": len(fixed_indices),
        "optimizer_steps": optimizer.nsteps,
        "converged": converged,
    }


def main():
    prepared = {
        label: prepare(label, filename)
        for label, filename in FILES.items()
    }

    nn_atoms = prepared["NN"][0]
    sep_atoms = prepared["SEP"][0]

    if not np.allclose(nn_atoms.cell, sep_atoms.cell):
        raise ValueError("Candidate cells differ")

    if not np.array_equal(nn_atoms.pbc, sep_atoms.pbc):
        raise ValueError("Candidate PBC settings differ")

    # Prevent accidental replacement of earlier results.
    targets = [
        OUTPUT / filename
        for filename in FILES.values()
    ] + [OUTPUT / "emt_relaxation_summary.json"]

    if any(target.exists() for target in targets):
        raise SystemExit(
            "Existing EMT relaxation outputs found. "
            "No files overwritten."
        )

    print("\nCUSELECT-AI — CONSTRAINED EMT RELAXATION")
    print("=" * 60)

    results = {}

    for label, (atoms, fixed_indices) in prepared.items():
        print(f"\nOptimizing {label}...")

        result = relax(label, atoms, fixed_indices)
        results[label] = result

        print(
            "Initial energy:",
            round(result["initial_energy_ev"], 6), "eV"
        )
        print(
            "Final energy:",
            round(result["final_energy_ev"], 6), "eV"
        )
        print(
            "Max free force:",
            round(
                result["max_free_force_ev_per_angstrom"], 6
            ),
            "eV/Å",
        )
        print("Converged:", result["converged"])

    if not all(r["converged"] for r in results.values()):
        raise RuntimeError(
            "At least one relaxation did not converge. "
            "No results saved."
        )

    delta = (
        results["SEP"]["final_energy_ev"]
        - results["NN"]["final_energy_ev"]
    )

    print("\nRELAXED ENERGY DIFFERENCE")
    print("ΔE = E(SEP) - E(NN)")
    print(f"ΔE = {delta:+.6f} eV")

    OUTPUT.mkdir(parents=True, exist_ok=True)

    for label, filename in FILES.items():
        atoms = prepared[label][0]
        atoms.info["geometry_status"] = "relaxed_emt"
        atoms.info["energy_status"] = "computed_emt"

        write(OUTPUT / filename, atoms, format="extxyz")

    summary = {
        "calculator": "ASE EMT",
        "optimizer": "BFGS",
        "fmax_ev_per_angstrom": FMAX,
        "fixed_bottom_layers": 2,
        "energy_difference_sep_minus_nn_ev": delta,
        "performance_prediction": None,
        "results": results,
    }

    with (OUTPUT / "emt_relaxation_summary.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(summary, file, indent=2)

    print("\nRELAXATION COMPLETE")
    print("Output:", OUTPUT)
    print("Original structure files: unchanged")
    print("Catalytic selectivity: not predicted")


if __name__ == "__main__":
    main()
