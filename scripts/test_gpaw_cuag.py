"""CuSelect-AI: minimal Cu-Ag GPAW feasibility test."""

# PSEUDOCODE
# 1. Construct a simple two-atom Cu-Ag system.
# 2. Use GPAW with the PBE exchange-correlation functional.
# 3. Run a self-consistent plane-wave calculation.
# 4. Calculate energy and atomic forces.
# 5. Record the result without changing existing data.

import json
from pathlib import Path

import numpy as np
import gpaw
from ase import Atoms
from gpaw import GPAW, PW, FermiDirac

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/processed/09_dft_pilot"

RESULT_FILE = OUTPUT / "cuag_pilot.json"
LOG_FILE = OUTPUT / "cuag_pilot.log"

if RESULT_FILE.exists() or LOG_FILE.exists():
    raise SystemExit(
        "Existing pilot output detected. No overwrite."
    )

OUTPUT.mkdir(parents=True, exist_ok=True)

atoms = Atoms(
    symbols="CuAg",
    positions=[
        [6.0, 6.0, 5.0],
        [6.0, 6.0, 7.6],
    ],
    cell=[12.0, 12.0, 12.0],
    pbc=[False, False, False],
)

print("\nCUSELECT-AI — FIRST GPAW PILOT")
print("=" * 55)
print("System: CuAg two-atom model")
print("Method: PAW-PBE")
print("Plane-wave cutoff: 250 eV")
print("K-points: Gamma only")
print("Spin treatment: non-spin-polarized")
print("Status: preliminary feasibility test")

calculator = GPAW(
    mode=PW(250),
    xc="PBE",
    setups="paw",
    kpts=(1, 1, 1),
    occupations=FermiDirac(0.1),
    spinpol=False,
    symmetry="off",
    convergence={"energy": 0.001},
    maxiter=100,
    txt=str(LOG_FILE),
)

atoms.calc = calculator

energy = float(atoms.get_potential_energy())
forces = atoms.get_forces()

force_norms = np.linalg.norm(forces, axis=1)

result = {
    "system": "CuAg",
    "purpose": "software_feasibility_only",
    "gpaw_version": gpaw.__version__,
    "xc": "PBE",
    "cutoff_ev": 250,
    "kpts": [1, 1, 1],
    "spinpol": False,
    "energy_ev": energy,
    "max_force_ev_per_angstrom": float(
        force_norms.max()
    ),
    "dft_convergence_study_completed": False,
    "catalytic_selectivity_predicted": False,
}

RESULT_FILE.write_text(
    json.dumps(result, indent=2),
    encoding="utf-8",
)

print("\nDFT calculation completed.")
print(f"Total energy: {energy:.6f} eV")
print(
    "Maximum atomic force:",
    f"{force_norms.max():.6f} eV/Å",
)
print("Result saved:", RESULT_FILE)
print("Detailed SCF log:", LOG_FILE)
