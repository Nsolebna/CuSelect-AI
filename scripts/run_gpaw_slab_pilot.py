"""CuSelect-AI: preliminary DFT on the 36-atom NN slab."""

# PSEUDOCODE
# 1. Read the MACE-relaxed Cu-Ag slab.
# 2. Validate composition, cell and periodicity.
# 3. Configure a consistent preliminary PAW-PBE model.
# 4. Run one self-consistent calculation.
# 5. Record energy, forces, provenance and memory usage.
# 6. Preserve all original structures and previous results.

import hashlib
import json
import resource
from pathlib import Path

import numpy as np
import gpaw
from ase.io import read
from gpaw import GPAW, PW, FermiDirac

ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT
    / "data/processed/07_mace_relaxations"
    / "CU-001-100-AG2-NN.extxyz"
)

OUTPUT = ROOT / "data/processed/10_dft_slab_pilot"

RESULT = OUTPUT / "nn_pbe_250ev_gamma.json"
LOG = OUTPUT / "nn_pbe_250ev_gamma.log"

if RESULT.exists():
    raise SystemExit(
        "Result already exists. Refusing to overwrite."
    )

atoms = read(SOURCE)

if atoms.get_chemical_formula() != "Ag2Cu34":
    raise ValueError("Unexpected slab composition")

if len(atoms) != 36:
    raise ValueError("Unexpected atom count")

if not np.array_equal(
    atoms.pbc,
    [True, True, False]
):
    raise ValueError("Unexpected periodic boundaries")

OUTPUT.mkdir(parents=True, exist_ok=True)

print("\nCUSELECT-AI — FIRST CU-AG SLAB DFT PILOT")
print("=" * 55)
print("Structure: Cu(100), adjacent Ag pair")
print("Atoms:", len(atoms))
print("Method: GPAW PAW-PBE")
print("Cutoff: 250 eV — unconverged pilot")
print("K-points: Gamma only — unconverged pilot")
print("Coordinates: MACE-relaxed, unchanged")
print("Detailed SCF log:", LOG, flush=True)

calc = GPAW(
    mode=PW(250),
    xc="PBE",
    setups="paw",
    kpts=(1, 1, 1),
    occupations=FermiDirac(0.1),
    spinpol=False,
    symmetry="off",
    convergence={"energy": 0.001},
    maxiter=100,
    txt=str(LOG),
)

atoms.calc = calc

# Any failure stops execution before results are saved.
energy = float(atoms.get_potential_energy())
forces = atoms.get_forces(
    apply_constraint=False
)

force_norms = np.linalg.norm(forces, axis=1)

# On macOS, ru_maxrss is reported in bytes.
peak_rss = resource.getrusage(
    resource.RUSAGE_SELF
).ru_maxrss

result = {
    "candidate_id": "CU-001-100-AG2-NN",
    "calculation": "DFT_single_point_pilot",
    "functional": "PBE",
    "paw_setups": "standard",
    "gpaw_version": gpaw.__version__,
    "cutoff_ev": 250,
    "kpoints": [1, 1, 1],
    "smearing_ev": 0.1,
    "spin_polarized": False,
    "geometry_source": SOURCE.name,
    "geometry_sha256": hashlib.sha256(
        SOURCE.read_bytes()
    ).hexdigest(),
    "energy_ev": energy,
    "max_force_ev_per_angstrom": float(
        force_norms.max()
    ),
    "peak_process_rss_mib": round(
        peak_rss / (1024 ** 2), 2
    ),
    "scf_completed_without_exception": True,
    "numerically_converged_settings": False,
    "selectivity_prediction": None,
}

RESULT.write_text(
    json.dumps(result, indent=2),
    encoding="utf-8",
)

print("\nDFT SLAB PILOT COMPLETED")
print(f"Total energy: {energy:.6f} eV")
print(
    "Maximum atomic force:",
    f"{force_norms.max():.6f} eV/Å"
)
print(
    "Peak process memory:",
    f"{result['peak_process_rss_mib']:.1f} MiB"
)
print("Result:", RESULT)
print("Detailed log:", LOG)
print("Original geometry unchanged.")
