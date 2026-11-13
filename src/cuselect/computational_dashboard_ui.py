
"""Read-only computational visualization of existing CuSelect-AI results."""

from pathlib import Path
import math

import pandas as pd
import streamlit as st

from cuselect.computational_results import load_computational_results


def _focused_line(frame, x, y, title, x_title, y_title):
    import plotly.express as px

    fig = px.line(frame, x=x, y=y, markers=True, title=title)
    values = frame[y].dropna()

    if len(values):
        low, high = float(values.min()), float(values.max())
        padding = max((high - low) * 0.18, 0.001)
        fig.update_yaxes(range=[low - padding, high + padding])

    fig.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=55, b=30),
        xaxis_title=x_title,
        yaxis_title=y_title,
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch")


def _trajectory_frames(root):
    """Read serialized trajectory data; never evaluate a calculator."""
    from ase.io import read

    paths = [
        root / "data/processed/21_dft_relaxation/runs/nn/relaxation.traj",
        root / "data/processed/21_dft_relaxation/runs/nn/initial_constrained.traj",
    ]

    for path in paths:
        if path.is_file():
            try:
                frames = read(str(path), index=":")
                if not isinstance(frames, list):
                    frames = [frames]
                if frames:
                    return frames, str(path.relative_to(root))
            except Exception:
                continue

    return [], None


def _recorded_series(frames):
    """Extract only stored calculator results, never run calculations."""
    import numpy as np

    rows = []
    for i, atoms in enumerate(frames):
        calc = atoms.calc
        results = getattr(calc, "results", {}) if calc else {}
        if not isinstance(results, dict):
            results = {}

        energy = results.get("energy")
        forces = results.get("forces")

        if energy is not None:
            try:
                energy = float(energy)
                if not math.isfinite(energy):
                    energy = None
            except (TypeError, ValueError):
                energy = None

        max_force = None
        if forces is not None:
            try:
                arr = np.asarray(forces, dtype=float)
                if arr.shape == (len(atoms), 3):
                    movable = set(range(len(atoms)))
                    for constraint in atoms.constraints:
                        if constraint.__class__.__name__ == "FixAtoms":
                            movable -= set(
                                int(x) for x in constraint.get_indices()
                            )
                    if movable:
                        max_force = float(
                            np.linalg.norm(
                                arr[sorted(movable)], axis=1
                            ).max()
                        )
            except (TypeError, ValueError, AttributeError):
                pass

        rows.append({
            "step": i,
            "energy_ev": energy,
            "max_force_ev_a": max_force,
        })

    return pd.DataFrame(rows)


def _show_structure(atoms, title):
    """Visualize coordinates saved on disk, with no geometry changes."""
    import plotly.graph_objects as go

    fig = go.Figure()

    for element in sorted(set(atoms.get_chemical_symbols())):
        indices = [
            i for i, symbol in enumerate(atoms.get_chemical_symbols())
            if symbol == element
        ]
        xyz = atoms.positions[indices]
        fig.add_trace(go.Scatter3d(
            x=xyz[:, 0], y=xyz[:, 1], z=xyz[:, 2],
            mode="markers",
            name=element,
            marker=dict(size=6),
            text=[f"{element} atom {i}" for i in indices],
            hovertemplate="%{text}<extra></extra>",
        ))

    fig.update_layout(
        title=title,
        height=420,
        margin=dict(l=0, r=0, t=35, b=0),
        scene=dict(
            xaxis_title="x (Å)",
            yaxis_title="y (Å)",
            zaxis_title="z (Å)",
            aspectmode="data",
        ),
    )
    st.plotly_chart(fig, width="stretch")


def render_computational_dashboard(project_root):
    root = Path(project_root).resolve()

    st.subheader("Computational validation")
    st.caption(
        "Saved Cu–Ag model calculations · GPAW/PBE · MACE · ASE EMT"
    )
    st.warning(
        "These are computational model structures, not automatically "
        "the experimental AgCu nanowire catalyst. They do not establish "
        "ethylene selectivity or catalytic performance."
    )

    try:
        data = load_computational_results(root)
    except (OSError, ValueError, KeyError) as exc:
        st.error("Saved computational results could not be loaded.")
        st.code(str(exc))
        return

    relaxation = data.get("nn_relaxation") or {}
    assessment = data.get("relative_assessment") or {}
    emt = data.get("emt") or {}
    mace = data.get("mace") or {}

    c1, c2, c3 = st.columns(3)
    c1.metric("K-point tests", len(data.get("kpoint") or []))
    c2.metric("Cutoff tests", len(data.get("cutoff") or []))
    c3.metric(
        "NN DFT relaxation",
        "Converged" if relaxation.get("optimizer_converged") is True
        else "Not converged",
    )

    results_tab, reliability_tab, methods_tab = st.tabs(
        ["Results", "Reliability", "Methods"]
    )

    with results_tab:
        choice = st.selectbox(
            "Select analysis",
            [
                "DFT — K-point sensitivity",
                "DFT — Cutoff sensitivity",
                "DFT — SEP vs NN",
                "EMT vs MACE",
                "Geometry optimization trajectory",
                "Atomic structure viewer",
            ],
        )

        if choice == "DFT — K-point sensitivity":
            frame = pd.DataFrame(data["kpoint"])
            if not frame.empty:
                labels = ["2x2x1", "4x4x1", "6x6x1"]
                frame["order"] = frame["kpoint_grid"].map(
                    {label: i for i, label in enumerate(labels)}
                )
                frame = frame.sort_values("order")
                _focused_line(
                    frame, "kpoint_grid", "energy_ev",
                    "K-point sensitivity: NN, 350 eV",
                    "K-point grid", "Total energy (eV)",
                )
                frame["change_from_previous_ev"] = (
                    frame["energy_ev"].diff()
                )
                st.dataframe(
                    frame[[
                        "kpoint_grid", "energy_ev",
                        "change_from_previous_ev"
                    ]],
                    hide_index=True, width="stretch",
                )

        elif choice == "DFT — Cutoff sensitivity":
            frame = pd.DataFrame(data["cutoff"]).sort_values(
                "cutoff_ev"
            )
            if not frame.empty:
                _focused_line(
                    frame, "cutoff_ev", "energy_ev",
                    "Cutoff sensitivity: NN, 6×6×1",
                    "Cutoff (eV)", "Total energy (eV)",
                )
                frame["change_from_previous_ev"] = (
                    frame["energy_ev"].diff()
                )
                st.dataframe(
                    frame[[
                        "cutoff_ev", "energy_ev",
                        "change_from_previous_ev"
                    ]],
                    hide_index=True, width="stretch",
                )

        elif choice == "DFT — SEP vs NN":
            relative = (
                assessment.get("relative_energy_sep_minus_nn_ev")
                or {}
            )
            frame = pd.DataFrame([
                {"cutoff_ev": float(k), "delta_ev": float(v)}
                for k, v in relative.items()
            ]).sort_values("cutoff_ev")

            if not frame.empty:
                _focused_line(
                    frame, "cutoff_ev", "delta_ev",
                    "Fixed-geometry energy difference: SEP − NN",
                    "Cutoff (eV)", "SEP − NN (eV)",
                )
                st.dataframe(
                    frame, hide_index=True, width="stretch"
                )
                st.caption(
                    "Negative values indicate lower calculated "
                    "SEP energy for these fixed-geometry models. "
                    "Full numerical convergence is not established."
                )

        elif choice == "EMT vs MACE":
            frame = pd.DataFrame([
                {
                    "method": "ASE EMT",
                    "delta_ev": emt.get(
                        "energy_difference_sep_minus_nn_ev"
                    ),
                },
                {
                    "method": "MACE-MP-0",
                    "delta_ev": mace.get("delta_sep_minus_nn_ev"),
                },
            ])
            st.bar_chart(
                frame.set_index("method")["delta_ev"]
            )
            st.dataframe(
                frame, hide_index=True, width="stretch"
            )
            st.caption(
                "Method-specific relative energies; agreement "
                "in sign does not establish DFT accuracy."
            )

        elif choice == "Geometry optimization trajectory":
            try:
                frames, source_file = _trajectory_frames(root)
                if not frames:
                    st.info("No readable trajectory frames found.")
                else:
                    series = _recorded_series(frames)
                    st.caption(
                        f"Saved trajectory: {source_file} "
                        f"· {len(frames)} frame(s)"
                    )
                    for column, title, unit in [
                        ("energy_ev", "Recorded energy", "Energy (eV)"),
                        (
                            "max_force_ev_a",
                            "Recorded maximum movable force",
                            "Force (eV/Å)",
                        ),
                    ]:
                        usable = series[
                            ["step", column]
                        ].dropna()
                        if not usable.empty:
                            _focused_line(
                                usable, "step", column,
                                title, "Recorded frame index", unit,
                            )
                        else:
                            st.info(
                                f"{title}: no per-frame values stored "
                                "in the readable trajectory."
                            )
                    st.dataframe(
                        series, width="stretch", hide_index=True
                    )
            except ImportError:
                st.error(
                    "ASE or Plotly is unavailable in this environment."
                )

        else:
            try:
                from ase.io import read

                folder = (
                    root / "data/processed/21_dft_relaxation/runs/nn"
                )
                options = [
                    ("Initial constrained geometry",
                     folder / "initial_constrained.traj"),
                    ("Last saved geometry (not converged)",
                     folder / "last_structure.traj"),
                ]
                for label, path in options:
                    if path.is_file():
                        atoms = read(str(path), index=-1)
                        _show_structure(atoms, label)
                st.caption(
                    "Atom coordinates are displayed as saved. "
                    "The last geometry is not an optimized "
                    "or validated structure."
                )
            except ImportError:
                st.error(
                    "ASE or Plotly is unavailable in this environment."
                )
            except (OSError, ValueError) as exc:
                st.error(f"Could not read structure: {exc}")

    with reliability_tab:
        st.subheader("Scientific reliability")
        st.write(
            "**NN relaxation:**",
            "Converged" if relaxation.get("optimizer_converged")
            else "Not converged",
        )
        st.write(
            "**Maximum movable force:**",
            relaxation.get(
                "max_movable_force_ev_per_angstrom"
            ),
            "eV/Å",
        )
        st.write(
            "**Target maximum force:**",
            relaxation.get("target_fmax_ev_per_angstrom"),
            "eV/Å",
        )
        st.write(
            "**Numerical convergence established:**",
            assessment.get(
                "numerical_convergence_established", False
            ),
        )
        st.write(
            "**Human review:**",
            assessment.get("human_review_status", "Pending"),
        )
        st.warning(
            "SCF completion is not equivalent to numerical "
            "convergence or structural convergence. "
            "No catalytic-performance claim is validated."
        )

    with methods_tab:
        st.subheader("Methods and provenance")
        st.write("**DFT:** GPAW / PBE")
        st.write("**EMT:**", emt.get("calculator", "ASE EMT"))
        st.write("**MLIP:**", mace.get(
            "calculator", "MACE-MP-0"
        ))
        st.write(
            "**MACE DFT validation:**",
            mace.get("dft_validation", False),
        )

        with st.expander("Original calculation summaries"):
            st.json({
                "EMT": emt,
                "MACE": mace,
                "NN DFT relaxation": relaxation,
                "DFT cutoff assessment": assessment,
            })

    st.caption(
        "Read-only analysis of stored calculations. "
        "No new simulations or scientific approvals."
    )
