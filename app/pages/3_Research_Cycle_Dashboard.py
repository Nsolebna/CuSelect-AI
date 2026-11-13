
"""Simple, evidence-aware CuSelect-AI decision workspace."""

import sys
from pathlib import Path

import streamlit as st

st.set_page_config(layout="wide")

ROOT = Path(__file__).resolve().parents[2]
SRC = str(ROOT / "src")

if SRC not in sys.path:
    sys.path.insert(0, SRC)

from components.header import render_header
from cuselect.benchmark_registry import load_benchmarks

render_header()

st.markdown("## Make your next research decision")
st.caption(
    "Use scientific evidence to identify a practical next step."
)

registry = load_benchmarks(ROOT)
records = registry["records"]

if not records:
    st.info(
        "No benchmark candidates are available yet. "
        "Use Discover and Validate to build an evidence base."
    )
else:
    options = {
        (
            f"{r['catalyst']} · {r['product']} · "
            f"{r['benchmark_id']}"
        ): r
        for r in records
    }

    with st.form("decide_form"):
        selection = st.selectbox(
            "Select a research candidate",
            list(options),
        )

        submitted = st.form_submit_button(
            "Assess next step →",
            type="primary",
        )

    if submitted:
        st.session_state["decide_selected_id"] = (
            options[selection]["benchmark_id"]
        )

    chosen_id = st.session_state.get("decide_selected_id")
    selected = options[selection]

    if chosen_id == selected["benchmark_id"]:
        st.divider()
        st.subheader("Research recommendation")

        missing = []

        if not selected.get("electrolyte"):
            missing.append("electrolyte")

        density_type = str(
            selected.get("current_density_type") or ""
        ).lower()

        if density_type in {"", "unknown", "unresolved"}:
            missing.append("current-density definition")

        st.markdown("#### What should you prioritize?")

        if missing:
            st.write(
                "**Confirm the unresolved experimental conditions.**"
            )

            st.markdown("#### Why?")
            st.write(
                f"The benchmark reports "
                f"**{selected['faradaic_efficiency_percent']:g}% "
                f"{selected['product']} FE** for "
                f"**{selected['catalyst']}**, but the "
                f"following information is unresolved: "
                + ", ".join(missing)
                + ". These gaps limit quantitative comparison."
            )

            st.markdown("#### Recommended next action")
            st.write(
                "Inspect the primary publication's experimental "
                "methods and supplementary information. "
                "Confirm the missing fields before comparing "
                "this candidate with other catalysts."
            )

        else:
            st.write(
                "**Review measurement comparability and "
                "independent evidence.**"
            )

            st.markdown("#### Why?")
            st.write(
                "The benchmark has no missing conditions flagged "
                "by this basic check, but that alone does not "
                "establish reproducibility, reliability, "
                "or superior catalyst performance."
            )

            st.markdown("#### Recommended next action")
            st.write(
                "Review experimental controls and uncertainty, "
                "then identify suitable comparison measurements "
                "under matched operating conditions."
            )

        st.caption(
            f"Source: DOI {selected['doi']} · "
            "Provisional, rule-based recommendation"
        )

        with st.expander("Supporting scientific details"):
            st.write(
                "Reported FE:",
                selected["faradaic_efficiency_percent"],
            )
            st.write(
                "Cell configuration:",
                selected.get("cell_configuration")
                or "Not confirmed",
            )
            st.write(
                "Current-density definition:",
                selected.get("current_density_type")
                or "Unresolved",
            )
            st.write(
                "Scientific approval:",
                selected.get("scientifically_verified") is True,
            )
            st.caption(
                "This recommendation does not validate the "
                "experiment, predict catalyst performance, "
                "or launch computations."
            )

if registry["errors"]:
    with st.expander("Registry warnings"):
        st.json(registry["errors"])

st.divider()

if st.button(
    "Open Advanced Research Cycle →",
    key="open_advanced_decide",
):
    st.switch_page("pages/9_Advanced_Research_Cycle.py")
