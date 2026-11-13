"""Guarded GPAW geometry relaxation with BFGS restart support."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
PLAN = DATA / "21_dft_relaxation/relaxation_plan_v1.json"
RUNS = DATA / "21_dft_relaxation/runs"

CUTOFF = 450
KPOINTS = (6, 6, 1)
SMEARING = 0.1
FMAX = 0.05


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise SystemExit("BLOCKED: " + message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", choices=["NN", "SEP"])
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-steps", type=int, default=5)
    args = parser.parse_args()

    require(args.max_steps > 0, "max-steps must be positive")
    require(not args.resume or args.run,
            "--resume requires --run")
    require(PLAN.is_file(), "relaxation plan missing")

    plan = json.loads(PLAN.read_text())
    records = [
        r for r in plan["candidates"]
        if r["candidate"] == args.candidate
    ]
    require(len(records) == 1, "candidate plan invalid")

    record = records[0]
    source = (
        DATA / "07_mace_relaxations"
        / f"CU-001-100-AG2-{args.candidate}.extxyz"
    )
    require(source.is_file(), "source geometry missing")
    require(
        sha256(source) == record["geometry_sha256"],
        "source geometry fingerprint mismatch"
    )

    fixed = record["proposed_fixed_indices"]
    require(
        bool(fixed)
        and all(type(i) is int for i in fixed)
        and len(fixed) == len(set(fixed)),
        "invalid frozen-atom proposal"
    )

    print("\nCUSELECT-AI — GPAW RELAXATION")
    print("=" * 48)
    print("Candidate:", args.candidate)
    print("Method: GPAW/PBE")
    print("Cutoff:", CUTOFF, "eV")
    print("K-points:", KPOINTS)
    print("Smearing:", SMEARING, "eV")
    print("Target fmax:", FMAX, "eV/Å")
    print("Frozen indices:", fixed)
    print("Review:", record["constraint_review_status"])
    print("Resume requested:", args.resume)

    if not args.run:
        print("\nDRY RUN COMPLETE — GPAW NOT STARTED")
        return

    require(
        plan.get("approved_for_execution") is True,
        "relaxation plan has not been approved"
    )
    require(
        record.get("constraint_review_status") == "approved",
        "frozen-atom constraints not approved"
    )

    from ase.io import read, write
    from ase.io.trajectory import Trajectory
    from ase.constraints import FixAtoms
    from ase.optimize import BFGS
    from gpaw import GPAW, PW, FermiDirac

    directory = RUNS / args.candidate.lower()
    trajectory = directory / "relaxation.traj"
    restart = directory / "bfgs_restart.json"
    manifest_path = directory / "run_manifest.json"

    if args.resume:
        require(directory.is_dir(), "run directory missing")
        require(trajectory.is_file(), "trajectory missing")
        require(restart.is_file(), "BFGS checkpoint missing")
        require(manifest_path.is_file(), "run manifest missing")

        manifest = json.loads(manifest_path.read_text())
        require(
            manifest["source_sha256"] == sha256(source),
            "source changed since initial run"
        )
        require(
            manifest["plan_sha256"] == sha256(PLAN),
            "approved plan changed since initial run"
        )
        require(
            manifest["fixed_indices"] == fixed,
            "frozen indices changed"
        )
        require(
            manifest["cutoff_ev"] == CUTOFF
            and manifest["kpoints"] == list(KPOINTS)
            and manifest["smearing_ev"] == SMEARING
            and manifest["target_fmax_ev_per_angstrom"] == FMAX,
            "calculation settings differ from original run"
        )

        with Trajectory(str(trajectory), "r") as frames:
            require(len(frames) > 0, "empty trajectory")
            atoms = frames[-1].copy()

        require(
            len(atoms) == manifest["atom_count"],
            "recovered atom count mismatch"
        )

        atoms.set_constraint(FixAtoms(indices=fixed))
        print("Recovered last saved geometry.")

    else:
        require(
            not directory.exists(),
            "run directory already exists; use --resume"
        )

        atoms = read(source)
        require(
            all(0 <= i < len(atoms) for i in fixed),
            "frozen atom index out of range"
        )

        atoms.set_constraint(FixAtoms(indices=fixed))

        directory.mkdir(parents=True, exist_ok=False)

        manifest = {
            "candidate": args.candidate,
            "source_sha256": sha256(source),
            "plan_sha256": sha256(PLAN),
            "fixed_indices": fixed,
            "atom_count": len(atoms),
            "cutoff_ev": CUTOFF,
            "kpoints": list(KPOINTS),
            "smearing_ev": SMEARING,
            "target_fmax_ev_per_angstrom": FMAX,
        }

        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n"
        )
        write(directory / "initial_constrained.traj", atoms)

    # Reconstructing the calculator on resume is safe but may
    # repeat electronic SCF work; this is not a GPAW wavefunction restart.
    atoms.calc = GPAW(
        mode=PW(CUTOFF),
        xc="PBE",
        kpts=KPOINTS,
        occupations=FermiDirac(SMEARING),
        spinpol=False,
        symmetry={"point_group": False, "time_reversal": False},
        convergence={"energy": 0.001},
        maxiter=100,
        txt=str(directory / "gpaw.log"),
    )

    optimizer = BFGS(
        atoms,
        restart=str(restart),
        trajectory=str(trajectory),
        append_trajectory=args.resume,
        logfile=str(directory / "optimizer.log"),
    )

    converged = optimizer.run(
        fmax=FMAX,
        steps=args.max_steps,
    )

    write(directory / "last_structure.traj", atoms)

    import numpy as np
    forces = atoms.get_forces()
    max_force = float(
        np.linalg.norm(forces, axis=1).max()
    )

    result = {
        "candidate": args.candidate,
        "energy_ev": float(atoms.get_potential_energy()),
        "max_movable_force_ev_per_angstrom": max_force,
        "optimizer_converged": bool(converged),
        "steps_this_invocation": int(optimizer.nsteps),
        "target_fmax_ev_per_angstrom": FMAX,
        "scientific_review_required": True,
    }

    (directory / "result.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )

    print("\nRELAXATION INVOCATION FINISHED")
    print("Converged:", converged)
    print("Maximum movable force:", max_force, "eV/Å")
    print("Output:", directory)


if __name__ == "__main__":
    main()
