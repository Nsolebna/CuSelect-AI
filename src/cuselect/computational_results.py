
"""Read-only access to existing CuSelect-AI calculations."""

import json
from pathlib import Path


def load_computational_results(project_root):
    root = Path(project_root).resolve()
    base = root / "data/processed"

    def read(relative):
        path = base / relative
        if not path.is_file():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object: {relative}")
        return data

    kpoint_files = {
        "2x2x1": "12_dft_kpoint_tests/nn_pbe_350ev_2x2x1.json",
        "4x4x1": "13_dft_kpoint_4x4/nn_pbe_350ev_4x4x1.json",
        "6x6x1": "14_dft_kpoint_6x6/nn_pbe_350ev_6x6x1.json",
    }

    cutoff_files = {
        350: "14_dft_kpoint_6x6/nn_pbe_350ev_6x6x1.json",
        450: "19_dft_cutoff_450_6x6/nn_pbe_450ev_6x6x1.json",
    }

    kpoint = []
    cutoff = []

    for label, filename in kpoint_files.items():
        data = read(filename)
        if data and isinstance(data.get("energy_ev"), (int, float)):
            kpoint.append({
                "kpoint_grid": label,
                "energy_ev": data["energy_ev"],
                "geometry_sha256": data.get("geometry_sha256"),
                "numerically_converged": data.get(
                    "numerical_convergence_established"
                ),
                "source_file": filename,
            })

    for value, filename in cutoff_files.items():
        data = read(filename)
        if data and isinstance(data.get("energy_ev"), (int, float)):
            cutoff.append({
                "cutoff_ev": value,
                "energy_ev": data["energy_ev"],
                "geometry_sha256": data.get("geometry_sha256"),
                "numerically_converged": data.get(
                    "numerical_convergence_established"
                ),
                "source_file": filename,
            })

    relative = read(
        "20_dft_cutoff_assessment/cutoff_assessment_v1.json"
    )
    relaxation = read(
        "21_dft_relaxation/runs/nn/result.json"
    )
    relaxed_comparison = read(
        "22_dft_relaxation_analysis/nn_sep_comparison.json"
    )
    emt = read(
        "05_emt_relaxations/emt_relaxation_summary.json"
    )
    mace = read(
        "07_mace_relaxations/mace_relaxation_summary.json"
    )

    return {
        "kpoint": kpoint,
        "cutoff": cutoff,
        "relative_assessment": relative,
        "nn_relaxation": relaxation,
        "relaxed_comparison": relaxed_comparison,
        "emt": emt,
        "mace": mace,
        "computations_executed": False,
    }
