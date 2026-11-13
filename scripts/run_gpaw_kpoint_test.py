"""CuSelect-AI: GPAW k-point convergence study."""

# PSEUDOCODE
# 1. Read the already validated MACE-relaxed geometry.
# 2. Confirm the structure matches the 350 eV reference.
# 3. Keep the DFT method and numerical settings unchanged.
# 4. Change only the k-point sampling to 2x2x1.
# 5. Calculate total energy and forces without relaxation.
# 6. Save settings, provenance and results separately.

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
REFERENCE_DIR = ROOT / "data/processed/11_dft_cutoff_retry"
OUTPUT_DIR = ROOT / "data/processed/12_dft_kpoint_tests"

CUTOFF = 350
KPOINTS = (2, 2, 1)
SMEARING = 0.1

parser = argparse.ArgumentParser()
parser.add_argument("candidate", choices=["NN", "SEP"])
args = parser.parse_args()

candidate = args.candidate
label = candidate.lower()

source = SOURCE_DIR / f"CU-001-100-AG2-{candidate}.extxyz"
reference_file = (
    REFERENCE_DIR / f"{label}_pbe_350ev_gamma.json"
)

stem = f"{label}_pbe_350ev_2x2x1"
result_file = OUTPUT_DIR / f"{stem}.json"
log_file = OUTPUT_DIR / f"{stem}.log"

if result_file.exists() or log_file.exists():
    raise SystemExit(
        "Existing output detected; refusing to overwrite."
    )

reference = json.loads(reference_file.read_text())
fingerprint = hashlib.sha256(source.read_bytes()).hexdigest()

# Ensure the same physical structure is being evaluated.
if fingerprint != reference["geometry_sha256"]:
    raise ValueError("Source structure has changed.")

if reference.get("cutoff_ev") != CUTOFF:
    raise ValueError("Reference cutoff mismatch.")

if reference.get("kpoints") != [1, 1, 1]:
    raise ValueError("Reference k-point grid mismatch.")

if reference.get("functional") != "PBE":
    raise ValueError("Reference functional mismatch.")

if reference.get("smearing_ev") != SMEARING:
    raise ValueError("Reference smearing mismatch.")

if reference.get("spin_polarized", reference.get("spinpol")) is not False:
    raise ValueError("Reference spin treatment mismatch.")

atoms = read(source)

if len(atoms) != 36:
    raise ValueError("Expected 36 atoms.")

if atoms.get_chemical_formula() != "Ag2Cu34":
    raise ValueError("Composition mismatch.")

if not np.array_equal(atoms.pbc, [True, True, False]):
    raise ValueError("Unexpected periodic boundaries.")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("\nCUSELECT-AI — GPAW K-POINT TEST")
print("=" * 60)
print("Candidate:", candidate)
print("Functional: PBE")
print("Cutoff:", CUTOFF, "eV")
print("K-points:", KPOINTS)
print("Smearing:", SMEARING, "eV")
print("Geometry: MACE-relaxed, unchanged")
print("Numerical convergence: not established")
print("Detailed log:", log_file, flush=True)

calculator = GPAW(
    mode=PW(CUTOFF),
    xc="PBE",
    setups="paw",
    kpts=KPOINTS,
    occupations=FermiDirac(SMEARING),
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

peak_rss_mib = (
    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    / 1024**2
)

result = {
    "candidate": candidate,
    "calculation": "DFT_single_point_kpoint_test",
    "functional": "PBE",
    "gpaw_version": gpaw.__version__,
    "cutoff_ev": CUTOFF,
    "kpoints": list(KPOINTS),
    "smearing_ev": SMEARING,
    "spin_polarized": False,
    "symmetry": "off",
    "scf_energy_criterion": 0.001,
    "geometry_source": source.name,
    "geometry_sha256": fingerprint,
    "energy_ev": energy,
    "max_force_ev_per_angstrom": max_force,
    "peak_process_rss_mib": round(peak_rss_mib, 2),
    "scf_completed_without_exception": True,
    "numerical_convergence_established": False,
    "predicted_ethlyene_fe_percent": None,
}

result_file.write_text(
    json.dumps(result, indent=2),
    encoding="utf-8",
)

print("\nK-POINT CALCULATION COMPLETED")
print(f"Total energy: {energy:+.6f} eV")
print(f"Maximum force: {max_force:.6f} eV/Å")
print(f"Peak process RSS: {peak_rss_mib:.1f} MiB")
print("Saved:", result_file)
print("Original structures unchanged.")
