
"""Simple CuSelect-AI research settings overview."""

import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

st.set_page_config(layout="wide")

ROOT = Path(__file__).resolve().parents[2]
SRC = str(ROOT / "src")

if SRC not in sys.path:
    sys.path.insert(0, SRC)

from components.header import render_header

load_dotenv(dotenv_path=ROOT / ".env")
render_header()

st.title("Settings")
st.caption("Research configuration and scientific safeguards.")

st.subheader("AI research")

model = os.getenv("OPENAI_MODEL", "gpt-5-mini")

st.write("**Configured AI model:**", model)

st.write(
    "**Research sources:** Local scientific evidence, "
    "Crossref and OpenAlex"
)

st.write(
    "**Research routing:** CuSelect-AI selects local "
    "or global research based on the question."
)

st.divider()

st.subheader("Scientific safeguards")

st.write(
    "• Evidence-backed measurements require traceable sources."
)

st.write(
    "• Provisional claims remain separate from reviewed evidence."
)

st.write(
    "• Catalyst rankings are not validated without "
    "sufficient comparable experimental data."
)

st.write(
    "• DFT calculations are not launched automatically "
    "from the current Discover or Validate workflows."
)

st.divider()

st.subheader("System information")

evidence = ROOT / "data/approved_evidence.json"
benchmarks = ROOT / "data/processed/benchmark_candidates"

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "Local evidence file",
        "Available" if evidence.is_file() else "Missing",
    )

with col2:
    st.metric(
        "Benchmark candidate files",
        len(list(benchmarks.glob("*.json")))
        if benchmarks.is_dir() else 0,
    )

with st.expander("Advanced information"):
    st.write("**Project:** CuSelect-AI")
    st.write("**Interface:** Streamlit")
    st.write("**Configured model:**", model)
    st.caption(
        "This page displays configuration information. "
        "It does not change API keys, research settings, "
        "approval policies, or computational jobs."
    )
