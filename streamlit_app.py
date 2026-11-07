# CuSelect-AI — Streamlit research interface
#
# PSEUDOCODE
# 1. Present predefined research examples.
# 2. Accept a researcher's question.
# 3. Run the trusted three-agent orchestrator.
# 4. Display genuine live execution events.
# 5. Show the scientific decision and source citations.
# 6. Expose the audit trace without modifying data.

import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from cuselect.agents import ResearchTask
from cuselect.orchestrator import run_research_workflow
from cuselect.molecular_viewer import build_structure_html


st.set_page_config(
    page_title="CuSelect-AI",
    page_icon="🔬",
    layout="wide",
)

st.title("🔬 CuSelect-AI")
st.caption(
    "Evidence-grounded multi-agent research "
    "for electrochemical CO₂ reduction"
)

st.info(
    "Research prototype: 3 human-reviewed observations "
    "from one publication and 8 unrelaxed Cu–Ag structures. "
    "No validated catalyst-selectivity prediction model."
)

EXAMPLES = {
    "Ethylene Faradaic efficiency": (
        "source_question",
        "What ethylene FE was reported for AgCu NW?",
        (),
    ),
    "Ethanol Faradaic efficiency": (
        "source_question",
        "What ethanol FE was reported for Ag1Cu NW?",
        (),
    ),
    "Ethanol/ethylene product ratios": (
        "source_question",
        "What ethanol-to-ethylene product ratios were reported?",
        (),
    ),
    "Compare Cu–Ag geometries": (
        "structure_hypothesis",
        "Investigate adjacent versus separated Ag pairs on Cu(100)",
        (
            "CU-001-100-AG2-NN",
            "CU-001-100-AG2-SEP",
        ),
    ),
    "Unsupported prediction example": (
        "predict_selectivity",
        "Predict which catalyst has higher ethylene FE",
        (),
    ),
}

st.subheader("Research request")

with st.form("research_form"):
    selected = st.selectbox(
        "Choose a research example",
        list(EXAMPLES),
    )

    task_type, default_question, candidate_ids = EXAMPLES[selected]

    question = st.text_area(
        "Research question",
        value=default_question,
        key=f"question_{selected}",
    )

    submitted = st.form_submit_button(
        "Run scientific workflow",
        type="primary",
    )


if submitted:
    if not question.strip():
        st.error("Please enter a research question.")
        st.stop()

    task = ResearchTask(
        task_id="APP-001",
        task_type=task_type,
        question=question.strip(),
        candidate_ids=candidate_ids,
    )

    st.subheader("Agent execution")

    with st.status(
        "Running the scientific workflow...",
        expanded=True,
    ) as status:

        def on_event(event):
            symbols = {
                "started": "▶️",
                "completed": "✅",
                "failed": "❌",
            }

            symbol = symbols.get(event["status"], "•")

            st.write(
                f"{symbol} {event['agent']}: "
                f"{event['status']}"
            )

        try:
            result = run_research_workflow(
                task,
                project_root=ROOT,
                on_event=on_event,
            )
        except Exception as exc:
            status.update(
                label="Workflow failed",
                state="error",
            )
            st.error(
                f"Workflow error: {type(exc).__name__}"
            )
            st.stop()

        status.update(
            label="Workflow completed",
            state="complete",
        )

    st.subheader("Scientific result")

    decision = result["decision"]

    if decision == "evidence_only":
        st.success("Evidence-only observation")
    elif decision == "hypothesis_only":
        st.info("Structural hypothesis only")
    else:
        st.warning("Abstain — unsupported scientific conclusion")

    st.write(result["response"])

    if result["citations"]:
        st.subheader("Source evidence")

        for citation in result["citations"]:
            st.write(
                "**Evidence ID:**",
                citation["evidence_id"],
            )
            st.write("**DOI:**", citation["doi"])
            st.write(
                "**Source location:**",
                citation["source_location"],
            )
            st.write(
                "**Source extent:**",
                citation["source_extent"],
            )

    if result["candidate_ids"]:
        st.subheader("Interactive 3D catalyst structures")

        # PSEUDOCODE
        # 1. Create a column for each registered candidate.
        # 2. Load actual validated atomic coordinates.
        # 3. Display interactive Cu and Ag atom positions.
        # 4. Show structural metadata, not performance claims.

        candidates = result["candidate_ids"]
        columns = st.columns(len(candidates))

        for column, candidate_id in zip(columns, candidates):
            with column:
                st.markdown(f"**{candidate_id}**")

                html, record = build_structure_html(
                    ROOT,
                    candidate_id,
                )

                components.html(
                    html,
                    height=480,
                    scrolling=False,
                )

                st.caption(
                    f"{record['chemical_formula']} | "
                    f"{record['atom_count']} atoms | "
                    f"{record['geometry_status']}"
                )

                separation = record.get(
                    "ag_ag_minimum_image_distance_A", ""
                ).strip()

                if separation:
                    st.write(
                        "Ag–Ag minimum-image distance: "
                        f"**{float(separation):.3f} Å**"
                    )

        st.caption(
            "Structures are unrelaxed and pending human "
            "visual review. Marker sizes are illustrative. "
            "No stability, energy or selectivity prediction."
        )

    with st.expander("Scientific audit and execution trace"):
        st.json({
            "critic": result["critic"],
            "trace": result["trace"],
            "run_sha256": result["run_sha256"],
            "source_corpus_sha256": (
                result["source_corpus_sha256"]
            ),
        })
