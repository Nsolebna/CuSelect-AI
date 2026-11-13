"""CuSelect-AI: first MACE-MP-0 Cu-Ag benchmark."""

# PSEUDOCODE
# 1. Read the existing EMT-relaxed geometries.
# 2. Verify matching composition and periodic cells.
# 3. Load one pretrained MACE model on CPU.
# 4. Calculate energies and forces without relaxation.
# 5. Compare the NN and SEP energies.
# 6. Record reproducibility metadata.
# 7. Never modify original scientific data.

import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from ase.io import read
from mace.calculators import mace_mp

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/05_emt_relaxations"
OUTPUT = ROOT / "data/processed/06_mace_benchmark"

FILES = {
    "NN": "CU-001-100-AG2-NN.extxyz",
    "SEP": "CU-001-100-AG2-SEP.extxyz",
}

MODEL = "small"
DEVICE = "cpu"
DTYPE = "float64"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_structures():
    structures = {}

    for label, filename in FILES.items():
        path = SOURCE / filename

        if not path.exists():
            raise FileNotFoundError(path)

        atoms = read(path)

        if atoms.get_chemical_formula() != "Ag2Cu34":
            raise ValueError(f"{label}: composition mismatch")

        if atoms.info.get("geometry_status") != "relaxed_emt":
            raise ValueError(
                f"{label}: expected EMT-relaxed geometry"
            )

        structures[label] = (atoms, path)

    nn = structures["NN"][0]
    sep = structures["SEP"][0]

    if not np.allclose(nn.cell, sep.cell):
        raise ValueError("Different simulation cells")

    if not np.array_equal(nn.pbc, sep.pbc):
        raise ValueError("Different PBC settings")

    return structures


def main():
    structures = load_structures()

    output_file = OUTPUT / "mace_mp0_small_results.json"

    if output_file.exists():
        raise SystemExit(
            "Benchmark output already exists. "
            "No file overwritten."
        )

    print("\nCUSELECT-AI — FIRST MACE BENCHMARK")
    print("=" * 60)
    print("Model: MACE-MP-0 small")
    print("Device:", DEVICE)
    print("Precision:", DTYPE)
    print("PyTorch:", torch.__version__)

    # The checkpoint is obtained from the official
    # MACE-MP release and cached locally.
    calculator = mace_mp(
        model=MODEL,
        device=DEVICE,
        default_dtype=DTYPE,
    )

    results = {}

    for label, (atoms, path) in structures.items():
        # Work only on an in-memory copy.
        structure = atoms.copy()
        structure.calc = calculator

        energy = float(structure.get_potential_energy())
        forces = structure.get_forces()

        force_norms = np.linalg.norm(forces, axis=1)

        ag_indices = [
            i for i, s in enumerate(
                structure.get_chemical_symbols()
            )
            if s == "Ag"
        ]

        distance = float(
            structure.get_distance(
                ag_indices[0],
                ag_indices[1],
                mic=True,
            )
        )

        results[label] = {
            "energy_ev": energy,
            "max_force_ev_per_angstrom": float(
                force_norms.max()
            ),
            "ag_ag_distance_angstrom": distance,
            "structure_sha256": sha256(path),
            "source_filename": path.name,
        }

        print("\nCandidate:", label)
        print(f"Energy: {energy:.6f} eV")
        print(
            "Maximum force:",
            f"{force_norms.max():.6f} eV/Å",
        )
        print(f"Ag–Ag distance: {distance:.4f} Å")

    delta = (
        results["SEP"]["energy_ev"]
        - results["NN"]["energy_ev"]
    )

    print("\n" + "=" * 60)
    print("MACE ENERGY COMPARISON")
    print("ΔE = E(SEP) - E(NN)")
    print(f"ΔE = {delta:+.6f} eV")

    if delta < 0:
        print("MACE gives SEP the lower energy.")
    elif delta > 0:
        print("MACE gives NN the lower energy.")
    else:
        print("MACE energies are equal.")

    record = {
        "calculation": "single_point",
        "model_family": "MACE-MP-0",
        "model_identifier": MODEL,
        "device": DEVICE,
        "dtype": DTYPE,
        "pytorch_version": torch.__version__,
        "input_geometry": "EMT-relaxed",
        "energy_difference_sep_minus_nn_ev": delta,
        "results": results,
        "geometry_optimization_performed": False,
        "dft_validation_performed": False,
        "predicted_fe_percent": None,
        "scientific_status": "preliminary_model_comparison",
    }

    OUTPUT.mkdir(parents=True, exist_ok=True)

    output_file.write_text(
        json.dumps(record, indent=2),
        encoding="utf-8",
    )

    print("\nBenchmark saved:", output_file)
    print("Original structures: unchanged")
    print("Catalytic selectivity: not predicted")


if __name__ == "__main__":
    main()
