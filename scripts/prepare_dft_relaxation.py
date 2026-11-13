"""Validate proposed NN/SEP slab relaxation inputs. No GPAW execution."""

from pathlib import Path
import hashlib
import json

import numpy as np
from ase.io import read
from ase.constraints import FixAtoms

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
PLAN = DATA / "21_dft_relaxation/relaxation_plan_v1.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if not PLAN.is_file():
        raise SystemExit(
            "Relaxation plan missing. "
            "Generate relaxation_plan_v1.json first."
        )

    plan = json.loads(PLAN.read_text(encoding="utf-8"))

    if plan.get("status") != "planning_only":
        raise SystemExit("Unexpected plan status.")

    if plan.get("approved_for_execution") is not False:
        raise SystemExit("Unexpected approval state.")

    records = plan.get("candidates", [])
    if {r["candidate"] for r in records} != {"NN", "SEP"}:
        raise SystemExit("Expected exactly NN and SEP.")
    if len(records) != 2:
        raise SystemExit("Duplicate candidate detected.")

    prepared = {}

    print("\nCUSELECT-AI — GPAW RELAXATION PREPARATION")
    print("=" * 55)

    for record in records:
        candidate = record["candidate"]
        source = DATA / "07_mace_relaxations" / (
            f"CU-001-100-AG2-{candidate}.extxyz"
        )

        if sha256(source) != record["geometry_sha256"]:
            raise SystemExit(
                f"{candidate}: geometry fingerprint mismatch"
            )

        atoms = read(source)
        fixed = record["proposed_fixed_indices"]

        if (
            not fixed
            or len(fixed) != len(set(fixed))
            or any(type(i) is not int or i < 0 or i >= len(atoms)
                   for i in fixed)
        ):
            raise SystemExit(
                f"{candidate}: invalid frozen-atom proposal"
            )

        # Check that the frozen atoms belong to the bottom region.
        z = atoms.positions[:, 2]
        lowest = min(
            record["layers_bottom_to_top"],
            key=lambda layer: layer["mean_z_angstrom"],
        )

        if set(fixed) != set(lowest["indices"]):
            raise SystemExit(
                f"{candidate}: frozen indices differ from "
                "the proposed bottom layer"
            )

        # In-memory only; the original structure is not modified.
        atoms.set_constraint(FixAtoms(indices=fixed))

        prepared[candidate] = atoms

        print(f"\n{candidate}")
        print("Formula:", atoms.get_chemical_formula())
        print("Atoms:", len(atoms))
        print("Frozen atoms:", fixed)
        print("Movable atoms:", len(atoms) - len(fixed))
        print("Frozen elements:", [atoms[i].symbol for i in fixed])
        print("Constraint review:", record["constraint_review_status"])

    nn, sep = prepared["NN"], prepared["SEP"]

    print("\nCOMPARABILITY CHECKS")
    print("-" * 55)

    checks = {
        "Same atom count": len(nn) == len(sep),
        "Same chemical formula":
            nn.get_chemical_formula() == sep.get_chemical_formula(),
        "Same simulation cell":
            np.allclose(nn.cell.array, sep.cell.array, atol=1e-6),
        "Same periodic boundaries":
            np.array_equal(nn.pbc, sep.pbc),
    }

    for name, passed in checks.items():
        print(("PASS" if passed else "FAIL"), name)

    if not all(checks.values()):
        raise SystemExit("Structural comparability check failed.")

    print("\nPREPARATION CHECKS PASSED")
    print("Constraint approval: PENDING SCIENTIFIC REVIEW")
    print("GPAW calculations started: NO")
    print("Original geometry files modified: NO")


if __name__ == "__main__":
    main()
