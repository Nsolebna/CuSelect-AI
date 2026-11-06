"""CuSelect-AI Stage-1 Streamlit app: evidence registry and 3D slab structures.

Nothing here is an agent, DFT model, MLIP prediction or catalyst activity forecast.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cuselect.structures import (
    geometry_summary,
    make_cu100,
    make_substitutional_cuag,
)

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="CuSelect-AI | Stage 1", page_icon="🔬", layout="wide")
st.title("CuSelect-AI")
st.caption("Stage 1 — Evidence-first catalyst structure exploration")
st.warning(
    "Scientific status: structures are UNRELAXED geometry models. No MLIP, "
    "DFT, energy, kinetic barrier, ethylene selectivity or Faradaic efficiency "
    "has been calculated."
)

@st.cache_data

def load_papers() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "papers.csv")


def plot_slab(atoms):
    pos = np.asarray(atoms.get_positions())
    colors = ["#e2a06f" if atom.symbol == "Cu" else "#93a2b1" for atom in atoms]
    labels = [f"{atom.symbol} #{atom.index} | layer tag {atom.tag}" for atom in atoms]
    fig = go.Figure(go.Scatter3d(
        x=pos[:, 0], y=pos[:, 1], z=pos[:, 2], mode="markers",
        marker={"size": 9, "color": colors, "line": {"width": 0.3, "color": "#39444d"}},
        text=labels, hovertemplate="%{text}<extra></extra>",
    ))
    fig.update_layout(
        height=540, margin=dict(l=0, r=0, t=0, b=0),
        scene=dict(xaxis_title="x (Å)", yaxis_title="y (Å)", zaxis_title="z (Å)", aspectmode="data"),
        showlegend=False,
    )
    return fig

with st.sidebar:
    st.header("Initial research case")
    selected = st.selectbox("Surface model", ["Pure Cu(100)", "Substitutional Ag on Cu(100)"])
    st.caption("3 × 3 × 4 slab, a = 3.615 Å, 12 Å vacuum (each side).")

atoms = make_cu100() if selected == "Pure Cu(100)" else make_substitutional_cuag()
summary = geometry_summary(atoms)

tab1, tab2, tab3 = st.tabs(["3D structures", "Evidence library", "Project protocol"])
with tab1:
    left, right = st.columns([2, 1])
    with left:
        st.plotly_chart(plot_slab(atoms), use_container_width=True)
    with right:
        st.subheader("Geometry record")
        st.json(summary)
        st.caption("The colored Ag atom is substitutional, not an adsorbed Ag adatom.")
        st.caption("This periodic 3×3 model has one Ag among nine surface atoms; "
                   "its concentration and periodic image effects need validation.")
        # File generated in memory: safe for download without side effects.
        from io import StringIO
        from ase.io import write
        buffer = StringIO()
        write(buffer, atoms, format="extxyz")
        st.download_button("Download atomic structure (.extxyz)",
                           data=buffer.getvalue(),
                           file_name=f"{summary['candidate_id']}.extxyz",
                           mime="text/plain")
with tab2:
    st.subheader("Verified reference register")
    df = load_papers()
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption("Bibliographic records only. They are not numerical catalyst performance measurements.")
with tab3:
    st.subheader("What comes next")
    st.markdown("""1. Verify and normalize literature-derived evidence with complete provenance.
2. Add deterministic geometry checks and a scientific calculation adapter.
3. Benchmark numerical descriptors against independent reference calculations.
4. Build RAG, catalyst-design and mechanism-aware critic agents.
5. Compare the full system against controlled baselines using held-out studies.
""")
    st.info("A scientific hypothesis is not a validated result. Missing evidence must remain unknown.")
