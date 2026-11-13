"""Read-only analysis of CuSelect-AI GPAW relaxation results."""

from pathlib import Path
import json
import math
import numpy as np
from ase.io import read

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/processed/21_dft_relaxation/runs"
OUT = ROOT / "data/processed/22_dft_relaxation_analysis"
OUT.mkdir(parents=True, exist_ok=True)


def finite_number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def stored_energy(atoms):
    """Read stored energy; never initiate a new calculation."""
    calc = atoms.calc
    if calc is None:
        return None
    return finite_number(calc.results.get("energy"))


def stored_fmax(atoms, fixed):
    """Maximum force among movable atoms, when stored."""
    calc = atoms.calc
    if calc is None or "forces" not in calc.results:
        return None

    forces = np.asarray(calc.results["forces"], dtype=float)
    movable = [i for i in range(len(atoms)) if i not in fixed]

    if not movable or forces.shape != (len(atoms), 3):
        return None

    return finite_number(
        np.linalg.norm(forces[movable], axis=1).max()
    )


def analyze(name):
    directory = RUNS / name.lower()
    result_path = directory / "result.json"

    report = {
        "candidate": name,
        "analysis_status": "not_available",
        "converged": False,
    }

    # Never inspect an active/incomplete optimization trajectory.
    if not result_path.exists():
        report["reason"] = (
            "result.json is missing; the run may still be active "
            "or may have ended without a final result"
        )
        return report

    try:
        result = json.loads(result_path.read_text())

        if not isinstance(result, dict):
            raise ValueError("result.json must contain a JSON object")

        report["result_keys"] = sorted(result.keys())
        report["converged"] = result.get("converged") is True

        manifest_path = directory / "run_manifest.json"
        if not manifest_path.exists():
            raise ValueError("Run manifest missing")

        manifest = json.loads(manifest_path.read_text())
        report["manifest"] = manifest

        fixed = manifest.get("fixed_indices", [])
        fixed = [int(i) for i in fixed]

        initial_path = directory / "initial_constrained.traj"
        traj_path = directory / "relaxation.traj"

        if not initial_path.exists() or not traj_path.exists():
            raise ValueError("Initial structure or trajectory missing")

        initial = read(initial_path)
        frames = read(traj_path, index=":")
        if not frames:
            raise ValueError("Optimization trajectory is empty")

        final = frames[-1]

        if len(initial) != len(final):
            raise ValueError("Atom count changed during optimization")

        if initial.get_chemical_symbols() != final.get_chemical_symbols():
            raise ValueError("Atomic identities/order changed")

        if any(i < 0 or i >= len(final) for i in fixed):
            raise ValueError("Invalid frozen-atom indices")

        ag_indices = [
            i for i, atom in enumerate(final)
            if atom.symbol == "Ag"
        ]

        # Compare positions using minimum-image displacement
        # under the initial cell and periodic boundary conditions.
        delta = final.positions - initial.positions
        delta, _ = initial.cell.mic(delta, pbc=initial.pbc)
        distances = np.linalg.norm(delta, axis=1)

        movable = [
            i for i in range(len(final)) if i not in fixed
        ]

        energy = stored_energy(final)

        # Allow explicit energy metadata when trajectory energy
        # is unavailable; never treat unrelated numbers as energy.
        if energy is None:
            for key in (
                "final_energy_eV",
                "final_energy_ev",
                "energy_eV",
                "energy_ev",
            ):
                if key in result:
                    energy = finite_number(result[key])
                    if energy is not None:
                        break

        fmax = stored_fmax(final, fixed)

        if fmax is None:
            for key in (
                "final_fmax_eV_per_A",
                "final_fmax",
                "fmax_eV_per_A",
                "fmax",
            ):
                if key in result:
                    fmax = finite_number(result[key])
                    if fmax is not None:
                        break

        report.update({
            "analysis_status": "complete",
            "atom_count": len(final),
            "fixed_indices": fixed,
            "movable_count": len(movable),
            "saved_trajectory_frames": len(frames),
            "final_energy_eV": energy,
            "final_fmax_eV_per_A": fmax,
            "max_displacement_A": finite_number(
                distances.max()
            ),
            "max_movable_displacement_A": finite_number(
                distances[movable].max()
            ) if movable else None,
            "ag_indices": ag_indices,
            "ag_ag_distance_A": (
                finite_number(
                    final.get_distance(
                        ag_indices[0],
                        ag_indices[1],
                        mic=True,
                    )
                )
                if len(ag_indices) == 2 else None
            ),
        })

        # Convergence must be explicitly reported and
        # supported by a saved movable-atom force value.
        target = 0.05
        report["verified_force_convergence"] = (
            report["converged"]
            and fmax is not None
            and fmax <= target
        )

    except Exception as error:
        report["analysis_status"] = "error"
        report["reason"] = str(error)
        report["converged"] = False

    return report


reports = {name: analyze(name) for name in ("NN", "SEP")}

for name, report in reports.items():
    path = OUT / f"{name.lower()}_analysis.json"
    path.write_text(json.dumps(report, indent=2) + "\n")

    print(f"\n{name}: {report['analysis_status']}")
    print("Converged:", report["converged"])

    if report["analysis_status"] == "complete":
        print("Energy (eV):", report["final_energy_eV"])
        print("Movable fmax (eV/Å):",
              report["final_fmax_eV_per_A"])
        print("Max displacement (Å):",
              report["max_displacement_A"])
        print("Ag–Ag distance (Å):",
              report["ag_ag_distance_A"])
        print("Force convergence verified:",
              report["verified_force_convergence"])
    else:
        print("Reason:", report.get("reason"))


nn = reports["NN"]
sep = reports["SEP"]

comparison = {
    "comparison": "SEP minus NN",
    "status": "not_ready",
    "delta_energy_eV": None,
    "delta_energy_meV": None,
}

if (
    nn.get("verified_force_convergence")
    and sep.get("verified_force_convergence")
    and nn.get("final_energy_eV") is not None
    and sep.get("final_energy_eV") is not None
):
    a = nn["manifest"]
    b = sep["manifest"]

    matched = (
        nn["atom_count"] == sep["atom_count"]
        and nn["fixed_indices"] == sep["fixed_indices"]
        and a.get("plan_sha256") == b.get("plan_sha256")
    )

    if matched:
        delta = (
            sep["final_energy_eV"] - nn["final_energy_eV"]
        )
        comparison.update({
            "status": "provisional_matched_relaxed_comparison",
            "delta_energy_eV": delta,
            "delta_energy_meV": delta * 1000,
        })
    else:
        comparison["status"] = "protocol_mismatch"

(OUT / "nn_sep_comparison.json").write_text(
    json.dumps(comparison, indent=2) + "\n"
)

print("\nCOMPARISON:", comparison["status"])
print("Analysis saved to:", OUT)
print("Original GPAW data unchanged.")
