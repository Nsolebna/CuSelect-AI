"""CuSelect-AI: matched DFT single-point calculation for SEP."""

# PSEUDOCODE
# 1. Read and validate the completed NN DFT record.
# 2. Load the MACE-relaxed SEP slab.
# 3. Apply identical preliminary GPAW numerical settings.
# 4. Compute its energy and forces without relaxation.
# 5. Calculate SEP minus NN within the same DFT method.
# 6. Preserve original structures and earlier results.

import hashlib
import json
import resource
from pathlib import Path

import numpy as np
from ase.io import read
from gpaw import GPAW, PW, FermiDirac

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/processed/10_dft_slab_pilot"

NN_RESULT = OUTPUT / "nn_pbe_250ev_gamma.json"
SEP_RESULT = OUTPUT / "sep_pbe_250ev_gamma.json"
SEP_LOG = OUTPUT / "sep_pbe_250ev_gamma.log"
COMPARISON = OUTPUT / "nn_sep_pbe_pilot_comparison.json"

SOURCE = (
    ROOT / "data/processed/07_mace_relaxations"
    / "CU-001-100-AG2-SEP.extxyz"
)

if any(p.exists() for p in [SEP_RESULT, SEP_LOG, COMPARISON]):
    raise SystemExit("Output exists. Nothing overwritten.")

nn = json.loads(NN_RESULT.read_text())

expected = {
    "functional": "PBE",
    "cutoff_ev": 250,
    "kpoints": [1, 1, 1],
    "smearing_ev": 0.1,
    "spin_polarized": False,
}

for key, value in expected.items():
    if nn.get(key) != value:
        raise ValueError(
            f"NN setting mismatch: {key}={nn.get(key)}"
        )

if nn.get("scf_completed_without_exception") is not True:
    raise ValueError("NN calculation not confirmed completed")

atoms = read(SOURCE)

if atoms.get_chemical_formula() != "Ag2Cu34":
    raise ValueError("Unexpected composition")

if len(atoms) != 36:
    raise ValueError("Unexpected atom count")

if not np.array_equal(atoms.pbc, [True, True, False]):
    raise ValueError("Unexpected periodicity")

print("\nCUSELECT-AI — MATCHED SEP DFT PILOT")
print("=" * 55)
print("Structure: Cu(100), separated Ag pair")
print("Method: GPAW PAW-PBE")
print("Cutoff: 250 eV")
print("K-points: Gamma only")
print("Smearing: 0.1 eV")
print("All settings: preliminary, unconverged")
print("Log:", SEP_LOG, flush=True)

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
    txt=str(SEP_LOG),
)

atoms.calc = calc

energy = float(atoms.get_potential_energy())
forces = atoms.get_forces(apply_constraint=False)
max_force = float(np.linalg.norm(forces, axis=1).max())

peak_rss = resource.getrusage(
    resource.RUSAGE_SELF
).ru_maxrss

sep = {
    **expected,
    "candidate_id": "CU-001-100-AG2-SEP",
    "calculation": "DFT_single_point_pilot",
    "geometry_source": SOURCE.name,
    "geometry_sha256": hashlib.sha256(
        SOURCE.read_bytes()
    ).hexdigest(),
    "energy_ev": energy,
    "max_force_ev_per_angstrom": max_force,
    "peak_process_rss_mib": round(
        peak_rss / 1024**2, 2
    ),
    "scf_completed_without_exception": True,
    "numerically_converged_settings": False,
    "selectivity_prediction": None,
}

delta = energy - float(nn["energy_ev"])

comparison = {
    "method": "GPAW PAW-PBE",
    "geometry": "MACE-relaxed",
    "cutoff_ev": 250,
    "kpoints": [1, 1, 1],
    "smearing_ev": 0.1,
    "nn_energy_ev": float(nn["energy_ev"]),
    "sep_energy_ev": energy,
    "sep_minus_nn_ev": delta,
    "numerically_converged_settings": False,
    "dft_geometry_optimization_performed": False,
    "selectivity_prediction": None,
}

SEP_RESULT.write_text(json.dumps(sep, indent=2))
COMPARISON.write_text(json.dumps(comparison, indent=2))

print("\nMATCHED DFT COMPARISON")
print(f"NN energy:  {nn['energy_ev']:+.6f} eV")
print(f"SEP energy: {energy:+.6f} eV")
print(f"SEP - NN:   {delta:+.6f} eV")
print(f"SEP maximum force: {max_force:.6f} eV/Å")
print(f"Peak process RSS: {sep['peak_process_rss_mib']} MiB")

if delta < 0:
    print("Preliminary DFT ordering: SEP lower")
elif delta > 0:
    print("Preliminary DFT ordering: NN lower")
else:
    print("Preliminary DFT ordering: equal")

print("\nNumerical convergence: NOT established")
print("Source structures: unchanged")
print("Comparison saved:", COMPARISON)
