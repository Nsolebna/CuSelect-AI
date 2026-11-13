"""CuSelect-AI — Interactive Multi-Agent Design Explorer."""

# PSEUDOCODE
# 1. Load the coordinated catalyst-design results.
# 2. Validate their structure.
# 3. Display research readiness for each candidate.
# 4. Allow selection of an individual catalyst.
# 5. Display the evidence, original hypothesis, critique,
#    revised research plan, and experimental recommendations.
# 6. Never interpret readiness scores as predicted FE.

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "data" / "agent_runs" / "coordinated_designs_v1.json"

st.set_page_config(
    page_title="CuSelect-AI | Multi-Agent Design",
    page_icon="🧬",
    layout="wide",
)

st.title("🧬 CuSelect-AI")
st.subheader("Multi-Agent Catalyst Design Explorer")

st.caption(
    "Evidence-grounded research hypotheses for "
    "electrochemical CO₂-to-ethylene conversion"
)


@st.cache_data
def load_results(path, modified_time):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


if not RESULTS.exists():
    st.error(
        "Coordinated design results not found. Run the "
        "complete agent pipeline first."
    )
    st.code(
        "PYTHONPATH=src python scripts/run_agent_demo.py",
        language="bash",
    )
    st.stop()

try:
    result = load_results(
        str(RESULTS),
        RESULTS.stat().st_mtime_ns,
    )
except (OSError, json.JSONDecodeError) as error:
    st.error(f"Cannot load agent results: {error}")
    st.stop()

if result.get("agent") != "optimization_coordinator":
    st.error("Unexpected agent output type.")
    st.stop()

candidates = result.get("candidates", [])

if not isinstance(candidates, list) or not candidates:
    st.warning("No candidate proposals available.")
    st.stop()

if any(
    not isinstance(c, dict)
    or c.get("predicted_fe_percent") is not None
    or not isinstance(c.get("evolution"), list)
    or len(c["evolution"]) != 3
    for c in candidates
):
    st.error("Invalid or unsupported candidate data.")
    st.stop()

st.info(
    "These candidates are untested research hypotheses. "
    "Readiness scores are heuristic; they do not predict "
    "Faradaic efficiency or intrinsic catalytic activity."
)

m1, m2, m3 = st.columns(3)

m1.metric("Research hypotheses", len(candidates))
m2.metric(
    "Recorded agent stages",
    sum(len(c["evolution"]) for c in candidates),
)
m3.metric(
    "Performance predictions",
    "None",
)

st.divider()

# Candidate overview
st.header("Candidate overview")

rows = []

for candidate in candidates:
    rows.append({
        "Candidate": candidate["candidate_id"],
        "Design": candidate["candidate_name"],
        "Readiness / 100": candidate[
            "research_readiness"
        ]["total"],
        "Evidence DOI": candidate["supporting_doi"],
        "Development stages": len(candidate["evolution"]),
    })

overview = pd.DataFrame(rows)

st.dataframe(
    overview,
    hide_index=True,
    width="stretch",
)

st.caption(
    "Research readiness measures evidence documentation "
    "and testability, not expected catalytic performance."
)

st.divider()

# Candidate selection
st.header("Explore a catalyst design")

options = {
    f'{c["candidate_id"]} — {c["candidate_name"]}': c
    for c in candidates
}

selected_label = st.selectbox(
    "Select a proposed catalyst",
    options=list(options),
)

candidate = options[selected_label]
st.subheader(candidate["candidate_name"])

left, right = st.columns([2, 1])

with left:
    st.write(
        "**Candidate ID:**",
        candidate["candidate_id"],
    )
    st.write(
        "**Supporting publication:**",
        candidate["supporting_doi"],
    )
    st.link_button(
        "Open supporting publication",
        "https://doi.org/" + candidate["supporting_doi"],
    )

with right:
    st.metric(
        "Research readiness",
        f'{candidate["research_readiness"]["total"]}/100',
    )

st.divider()

# Explain how the research hypothesis evolved
st.header("Candidate development history")

stage_labels = {
    "initial_design": "1. Initial Design Hypothesis",
    "scientific_critique": "2. Scientific Critique",
    "revised_research_plan": "3. Revised Research Plan",
}

for stage in candidate["evolution"]:
    stage_name = stage.get("stage", "unknown")
    label = stage_labels.get(stage_name, stage_name)

    with st.expander(label, expanded=True):
        st.caption(
            "Component: " + stage.get("agent", "unknown")
        )

        if stage_name == "initial_design":
            st.markdown("**Scientific hypothesis**")
            st.write(stage.get("hypothesis", ""))

            st.markdown("**Original experimental plan**")
            st.write(stage.get("experimental_plan", ""))

        elif stage_name == "scientific_critique":
            st.markdown("**Primary scientific risk**")
            st.warning(stage.get("primary_risk", ""))

            st.markdown("**Alternative explanation**")
            st.write(
                stage.get("alternative_explanation", "")
            )

        elif stage_name == "revised_research_plan":
            st.markdown("**Original experiment**")
            st.write(stage.get("original_experiment", ""))

            st.markdown("**Additional control experiment**")
            st.success(
                stage.get("added_control_experiment", "")
            )

            st.markdown("**Alternative to investigate**")
            st.write(
                stage.get("alternative_explanation_to_test", "")
            )

            st.markdown("**Primary risk to monitor**")
            st.write(stage.get("main_risk_to_monitor", ""))

st.divider()

# Research-readiness breakdown
st.header("Research-readiness assessment")

scores = candidate["research_readiness"]

score_rows = [
    {
        "Criterion": key.replace("_", " ").title(),
        "Score / 25": value,
    }
    for key, value in scores.items()
    if key != "total"
]

st.dataframe(
    pd.DataFrame(score_rows),
    hide_index=True,
    width="stretch",
)

st.progress(
    min(max(float(scores["total"]) / 100, 0), 1)
)

st.caption(
    "Weights are predefined. Scores have not been "
    "calibrated against experimental catalyst outcomes."
)

st.divider()

st.header("Recommended next experiment")
st.info(
    candidate.get(
        "recommended_next_experiment",
        "No experiment specified.",
    )
)

st.warning(
    "This workflow is currently deterministic and template-based. "
    "No autonomous LLM reasoning, DFT validation, or "
    "experimental catalyst optimization has been performed."
)

st.caption(
    "CuSelect-AI | Multi-Agent Design Explorer v1 | "
    "Read-only research prototype"
)
