"""CuSelect-AI: constrained MACE relaxation of Cu-Ag pairs."""

# PSEUDOCODE
# 1. Load the two EMT-relaxed structures.
# 2. Validate matching composition and simulation cells.
# 3. Freeze the bottom two layers.
# 4. Load the pretrained MACE-MP-0 small calculator.
# 5. Relax both structures independently.
# 6. Check convergence and compare energies.
# 7. Save new files without overwriting original structures.

import json
import hashlib
from pathlib import Path

import numpy as np
import torch
import mace
import ase

from ase.io import read, write
from ase.constraints import FixAtoms
from ase.optimize import BFGS
from mace.calculators import mace_mp

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/05_emt_relaxations"
OUTPUT = ROOT / "data/processed/07_mace_relaxations"

FILES = {
    "NN": "CU-001-100-AG2-NN.extxyz",
    "SEP": "CU-001-100-AG2-SEP.extxyz",
}

FMAX = 0.05
MAX_STEPS = 300


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(filename):
    path = SOURCE / filename
    atoms = read(path)

    if atoms.get_chemical_formula() != "Ag2Cu34":
        raise ValueError("Incorrect composition.")

    if not np.array_equal(atoms.pbc, [True, True, False]):
        raise ValueError("Incorrect periodic boundaries.")

    # Identify the two lower layers from the original slab.
    z = atoms.positions[:, 2]
    ordered = np.argsort(z, kind="stable")
    fixed = sorted(ordered[:18].tolist())

    # Confirm a clear gap between lower and upper halves.
    z_sorted = np.sort(z)
    if z_sorted[18] - z_sorted[17] < 0.5:
        raise ValueError("Cannot identify bottom two layers.")

    # Reset any previously serialized constraints.
    atoms.set_constraint(FixAtoms(indices=fixed))

    return atoms, fixed, path


def main():
    prepared = {
        label: prepare(filename)
        for label, filename in FILES.items()
    }

    nn = prepared["NN"][0]
    sep = prepared["SEP"][0]

    if not np.allclose(nn.cell, sep.cell):
        raise ValueError("Simulation cells differ.")

    if not np.array_equal(nn.pbc, sep.pbc):
        raise ValueError("Periodic boundaries differ.")

    if prepared["NN"][1] != prepared["SEP"][1]:
        print(
            "Note: fixed atom indices differ; "
            "the bottom two layers were selected independently."
        )

    output_files = [
        OUTPUT / filename for filename in FILES.values()
    ] + [OUTPUT / "mace_relaxation_summary.json"]

    if any(path.exists() for path in output_files):
        raise SystemExit(
            "Existing MACE outputs detected. No overwrite."
        )

    print("\nCUSELECT-AI — MACE STRUCTURAL RELAXATION")
    print("=" * 60)
    print("Model: MACE-MP-0 small")
    print("Device: CPU")
    print("Precision: float64")
    print("Force threshold:", FMAX, "eV/Å")

    calculator = mace_mp(
        model="small",
        device="cpu",
        default_dtype="float64",
    )

    results = {}

    for label, (atoms, fixed, source_path) in prepared.items():
        atoms.calc = calculator

        initial_energy = float(atoms.get_potential_energy())

        print(f"\nRelaxing {label}...")

        optimizer = BFGS(atoms, logfile=None)
        converged = bool(
            optimizer.run(fmax=FMAX, steps=MAX_STEPS)
        )

        final_energy = float(atoms.get_potential_energy())
        forces = atoms.get_forces()

        free = [
            index for index in range(len(atoms))
            if index not in fixed
        ]

        max_force = float(
            np.linalg.norm(forces[free], axis=1).max()
        )

        ag = [
            i for i, symbol in enumerate(
                atoms.get_chemical_symbols()
            )
            if symbol == "Ag"
        ]

        distance = float(
            atoms.get_distance(ag[0], ag[1], mic=True)
        )

        results[label] = {
            "initial_energy_ev": initial_energy,
            "final_energy_ev": final_energy,
            "max_free_force_ev_per_angstrom": max_force,
            "ag_ag_distance_angstrom": distance,
            "optimization_steps": optimizer.nsteps,
            "converged": converged,
            "source_sha256": fingerprint(source_path),
        }

        print(f"Initial energy: {initial_energy:.6f} eV")
        print(f"Final energy: {final_energy:.6f} eV")
        print(f"Max free force: {max_force:.6f} eV/Å")
        print(f"Ag–Ag distance: {distance:.4f} Å")
        print("Converged:", converged)

    if not all(r["converged"] for r in results.values()):
        raise RuntimeError(
            "MACE relaxation did not converge for both "
            "structures. No result files saved."
        )

    delta = (
        results["SEP"]["final_energy_ev"]
        - results["NN"]["final_energy_ev"]
    )

    print("\nRELAXED MACE ENERGY DIFFERENCE")
    print(f"SEP - NN = {delta:+.6f} eV")

    OUTPUT.mkdir(parents=True, exist_ok=True)

    for label, filename in FILES.items():
        atoms = prepared[label][0]
        atoms.info["geometry_status"] = "relaxed_mace_mp0"
        atoms.info["energy_status"] = "computed_mace_mp0"

        write(
            OUTPUT / filename,
            atoms,
            format="extxyz",
        )

    summary = {
        "calculator": "MACE-MP-0 small",
        "device": "cpu",
        "precision": "float64",
        "torch_version": torch.__version__,
        "mace_version": getattr(mace, "__version__", "unknown"),
        "ase_version": ase.__version__,
        "optimizer": "BFGS",
        "fmax_ev_per_angstrom": FMAX,
        "fixed_bottom_atoms": 18,
        "delta_sep_minus_nn_ev": delta,
        "dft_validation": False,
        "predicted_fe_percent": None,
        "results": results,
    }

    (OUTPUT / "mace_relaxation_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\nMACE RELAXATION COMPLETE")
    print("Output:", OUTPUT)
    print("Original structures unchanged.")
    print("Catalytic selectivity not predicted.")


if __name__ == "__main__":
    main()
