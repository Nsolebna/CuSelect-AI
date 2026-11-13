
"""Concise, read-only computational validation summary."""

from pathlib import Path

import pandas as pd
import streamlit as st

from cuselect.computational_results import (
    load_computational_results,
)


def render_computational_summary(project_root):
    root = Path(project_root)

    st.subheader("Computational validation")
    st.caption(
        "Cu–Ag NN and SEP model structures · "
        "Existing EMT, MACE and GPAW/PBE calculations"
    )

    try:
        data = load_computational_results(root)
    except (OSError, ValueError, KeyError) as exc:
        st.error("Computational records could not be loaded.")
        with st.expander("Technical details"):
            st.code(str(exc))
        return

    emt = data.get("emt") or {}
    mace = data.get("mace") or {}
    dft = data.get("relative_assessment") or {}
    relax = data.get("nn_relaxation") or {}

    # 1. Calculation
    st.markdown("#### 1. What was calculated?")
    st.write(
        "Relative energies of two Cu–Ag surface configurations "
        "(NN and SEP), plus DFT numerical-sensitivity tests "
        "and an NN geometry-relaxation attempt."
    )

    # 2. Finding
    st.markdown("#### 2. Main scientific finding")

    values = []

    e = emt.get("energy_difference_sep_minus_nn_ev")
    if isinstance(e, (int, float)):
        values.append({
            "Method": "ASE EMT",
            "SEP minus NN (eV)": float(e),
        })

    e = mace.get("delta_sep_minus_nn_ev")
    if isinstance(e, (int, float)):
        values.append({
            "Method": "MACE-MP-0",
            "SEP minus NN (eV)": float(e),
        })

    relative = (
        dft.get("relative_energy_sep_minus_nn_ev") or {}
    )

    for cutoff, energy in sorted(
        relative.items(),
        key=lambda item: float(item[0]),
    ):
        if isinstance(energy, (int, float)):
            values.append({
                "Method": f"DFT {cutoff} eV",
                "SEP minus NN (eV)": float(energy),
            })

    if values:
        import plotly.graph_objects as go

        frame = pd.DataFrame(values)

        # Use magnitudes for readable right-facing bars.
        # Preserve the signed scientific values in labels and hover.
        methods = frame["Method"].tolist()
        energies = frame["SEP minus NN (eV)"].tolist()
        magnitudes = [abs(v) for v in energies]

        colors = [
            "#55CFC0" if method.startswith("DFT")
            else "#7BA6CE"
            for method in methods
        ]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=magnitudes,
            y=methods,
            orientation="h",
            width=0.44,
            marker=dict(
                color=colors,
                line=dict(width=0),
            ),
            customdata=energies,
            text=[f"{v:+.4f} eV" for v in energies],
            textposition="outside",
            textfont=dict(
                size=13,
                color="#E7F2EF",
            ),
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b>"
                "<br>SEP − NN: %{customdata:.6f} eV"
                "<extra></extra>"
            ),
        ))

        fig.update_layout(
            height=280,
            margin=dict(l=15, r=35, t=10, b=45),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                family="Arial, sans-serif",
                size=13,
                color="#DAE8E4",
            ),
            showlegend=False,
            bargap=0.48,
            xaxis=dict(
                title="Magnitude of SEP − NN energy difference (eV)",
                range=[0, max(magnitudes) * 1.35],
                showgrid=True,
                gridcolor="rgba(180,210,205,0.10)",
                zeroline=False,
                tickformat=".2f",
                title_font=dict(size=12),
            ),
            yaxis=dict(
                title=None,
                autorange="reversed",
                showgrid=False,
                automargin=True,
                tickfont=dict(size=13),
            ),
        )

        st.plotly_chart(
            fig,
            width="stretch",
            config={"displayModeBar": False},
        )

        st.caption(
            "Bar lengths represent absolute magnitudes; "
            "the signed SEP − NN values appear beside the bars. "
            "Negative values indicate lower reported SEP energy. "
            "EMT, MACE and fixed-geometry DFT are not a fully "
            "harmonized benchmark."
        )

        if all(v < 0 for v in energies):
            st.write(
                "**Finding:** All reported comparisons favor "
                "SEP energetically under their respective "
                "calculation conditions. Further scientific "
                "validation is required."
            )
        else:
            st.write(
                "The reported relative-energy comparisons "
                "do not all have the same sign."
            )
    else:
        st.info("No relative-energy results available.")

    # 3. Reliability
    st.markdown("#### 3. Can we trust the conclusion?")

    numerical = (
        dft.get("numerical_convergence_established") is True
    )
    geometry = (
        relax.get("optimizer_converged") is True
    )

    if not numerical or not geometry:
        st.warning(
            "Further scientific validation required. "
            "Full DFT numerical convergence is not established "
            "and/or the NN geometry relaxation is incomplete."
        )
    else:
        st.info(
            "Recorded numerical checks passed; independent "
            "scientific review is still required."
        )

    force = relax.get(
        "max_movable_force_ev_per_angstrom"
    )
    target = relax.get(
        "target_fmax_ev_per_angstrom"
    )

    if isinstance(force, (int, float)) and isinstance(
        target, (int, float)
    ):
        st.caption(
            f"NN maximum movable force: {force:.3f} eV/Å "
            f"· target: {target:.3f} eV/Å"
        )

    st.caption(
        "Human review: "
        + str(dft.get("human_review_status", "pending"))
        + ". These model calculations do not validate "
        "ethylene Faradaic efficiency or catalytic activity."
    )

    # 4. Next action
    st.markdown("#### 4. What should happen next?")
    st.write(
        "**Priority:** Resolve the incomplete geometry "
        "optimization and establish a scientifically "
        "comparable relaxed-structure assessment."
    )

    st.write(
        "Review the numerical convergence criteria and "
        "method consistency before investigating reaction "
        "intermediates or drawing mechanistic conclusions."
    )

    # Preserve all current detailed analyses.
    with st.expander(
        "Explore detailed calculations and structures",
        expanded=False,
    ):
        from cuselect.computational_dashboard_ui import (
            render_computational_dashboard,
        )
        render_computational_dashboard(root)

    if st.button(
        "Open Advanced DFT Analysis",
        key="open_advanced_dft_from_summary",
    ):
        st.switch_page(
            "pages/8_Advanced_DFT_Analysis.py"
        )

    st.caption(
        "Results read from existing files only. "
        "No calculations or scientific approvals performed."
    )
