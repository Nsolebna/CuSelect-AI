"""CuSelect-AI: paired GPAW cutoff convergence test."""

# PSEUDOCODE
# 1. Read an existing MACE-relaxed slab.
# 2. Confirm its fingerprint matches the DFT pilot.
# 3. Calculate DFT energy with a higher plane-wave cutoff.
# 4. Save energy, forces, settings and provenance.
# 5. Preserve all existing calculations.

import argparse
import hashlib
import json
import resource
from pathlib import Path

import numpy as np
import gpaw
from ase.io import read
from gpaw import GPAW, PW, FermiDirac

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data/processed/07_mace_relaxations"
PILOT_DIR = ROOT / "data/processed/10_dft_slab_pilot"
OUTPUT_DIR = ROOT / "data/processed/11_dft_cutoff_tests"

parser = argparse.ArgumentParser()
parser.add_argument("candidate", choices=["NN", "SEP"])
parser.add_argument("--cutoff", type=int, default=350)
args = parser.parse_args()

candidate = args.candidate
prefix = candidate.lower()

if args.cutoff < 250:
    raise ValueError("Cutoff must be at least 250 eV.")

source = SOURCE_DIR / f"CU-001-100-AG2-{candidate}.extxyz"
pilot_file = PILOT_DIR / f"{prefix}_pbe_250ev_gamma.json"

result_file = OUTPUT_DIR / f"{prefix}_pbe_{args.cutoff}ev_gamma.json"
log_file = OUTPUT_DIR / f"{prefix}_pbe_{args.cutoff}ev_gamma.log"

if result_file.exists() or log_file.exists():
    raise SystemExit(
        "Existing output detected. Refusing to overwrite."
    )

pilot = json.loads(pilot_file.read_text())

sha = hashlib.sha256(source.read_bytes()).hexdigest()

if pilot["geometry_sha256"] != sha:
    raise ValueError("Structure fingerprint mismatch.")

for key, expected in {
    "functional": "PBE",
    "cutoff_ev": 250,
    "kpoints": [1, 1, 1],
    "smearing_ev": 0.1,
    "spin_polarized": False,
}.items():
    if pilot.get(key) != expected:
        raise ValueError(f"Unexpected pilot setting: {key}")

atoms = read(source)

if atoms.get_chemical_formula() != "Ag2Cu34":
    raise ValueError("Incorrect composition.")

if len(atoms) != 36:
    raise ValueError("Incorrect atom count.")

if not np.array_equal(atoms.pbc, [True, True, False]):
    raise ValueError("Incorrect periodicity.")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("\nCUSELECT-AI — GPAW CUTOFF TEST")
print("=" * 55)
print("Candidate:", candidate)
print("Cutoff:", args.cutoff, "eV")
print("Functional: PBE")
print("K-points: Gamma only")
print("Smearing: 0.1 eV")
print("Input geometry: MACE-relaxed")
print("SCF convergence: 0.001 eV")
print("Log:", log_file, flush=True)

calculator = GPAW(
    mode=PW(args.cutoff),
    xc="PBE",
    setups="paw",
    kpts=(1, 1, 1),
    occupations=FermiDirac(0.1),
    spinpol=False,
    symmetry="off",
    convergence={"energy": 0.001},
    maxiter=100,
    txt=str(log_file),
)

atoms.calc = calculator

energy = float(atoms.get_potential_energy())
forces = atoms.get_forces(apply_constraint=False)

max_force = float(
    np.linalg.norm(forces, axis=1).max()
)

rss_mib = (
    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    / (1024 ** 2)
)

result = {
    "candidate": candidate,
    "calculation": "DFT_single_point",
    "functional": "PBE",
    "cutoff_ev": args.cutoff,
    "kpoints": [1, 1, 1],
    "smearing_ev": 0.1,
    "spin_polarized": False,
    "geometry_sha256": sha,
    "gpaw_version": gpaw.__version__,
    "energy_ev": energy,
    "max_force_ev_per_angstrom": max_force,
    "peak_process_rss_mib": round(rss_mib, 2),
    "scf_completed_without_exception": True,
    "numerically_converged_settings": False,
}

result_file.write_text(
    json.dumps(result, indent=2),
    encoding="utf-8",
)

print("\nCALCULATION COMPLETE")
print(f"Total energy: {energy:+.6f} eV")
print(f"Maximum force: {max_force:.6f} eV/Å")
print(f"Peak process RSS: {rss_mib:.1f} MiB")
print("Saved:", result_file)
print("Original structures unchanged.")
