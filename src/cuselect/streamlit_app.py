
# CuSelect-AI — Interactive research application
#
# PSEUDOCODE
# 1. Load the tested scientific orchestrator.
# 2. Let the researcher choose and edit a research question.
# 3. Execute the three agents with real event callbacks.
# 4. Show the genuine agent execution sequence.
# 5. Display the critic-approved response and citations.
# 6. Clearly distinguish observations from hypotheses.

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from cuselect.agents import ResearchTask
from cuselect.orchestrator import run_research_workflow


st.set_page_config(
    page_title="CuSelect-AI",
    page_icon="🔬",
    layout="wide",
)

st.title("🔬 CuSelect-AI")
st.caption(
    "Evidence-grounded multi-agent research for "
    "electrochemical CO₂ reduction"
)

st.info(
    "Research prototype: three human-reviewed observations "
    "from one publication and eight unrelaxed Cu–Ag structures. "
    "No validated selectivity predictions are available."
)

EXAMPLES = {
    "Reported ethylene FE": {
        "task_type": "source_question",
        "question": "What ethylene FE was reported for AgCu NW?",
        "candidate_ids": (),
    },
    "Reported ethanol FE": {
        "task_type": "source_question",
        "question": "What ethanol FE was reported for Ag1Cu NW?",
        "candidate_ids": (),
    },
    "Reported product ratios": {
        "task_type": "source_question",
        "question": (
            "What ethanol-to-ethylene product ratios "
            "were reported?"
        ),
        "candidate_ids": (),
    },
    "Compare Cu–Ag structures": {
        "task_type": "structure_hypothesis",
        "question": (
            "Investigate adjacent versus separated "
            "Ag pairs on Cu(100)"
        ),
        "candidate_ids": (
            "CU-001-100-AG2-NN",
            "CU-001-100-AG2-SEP",
        ),
    },
    "Unsupported prediction demonstration": {
        "task_type": "predict_selectivity",
        "question": (
            "Predict which catalyst has higher ethylene FE"
        ),
        "candidate_ids": (),
    },
}

st.subheader("Research request")

with st.form("research_form"):
    selected = st.selectbox(
        "Choose a research example",
        list(EXAMPLES),
    )

    example = EXAMPLES[selected]

    question = st.text_area(
        "Research question",
        value=example["question"],
        key=f"question_{selected}",
        height=100,
    )

    submitted = st.form_submit_button(
        "Run scientific workflow",
        type="primary",
    )

if submitted:
    task = ResearchTask(
        task_id="APP-001",
        task_type=example["task_type"],
        question=question.strip(),
        candidate_ids=example["candidate_ids"],
    )

    st.subheader("Live agent execution")

    events = []

    with st.status(
        "Executing scientific workflow...",
        expanded=True,
    ) as status:

        def on_event(event):
            # Display each event as it is emitted.
            events.append(event.copy())

            symbol = {
                "started": "▶️",
                "completed": "✅",
                "failed": "❌",
            }.get(event["status"], "•")

            st.write(
                f"{symbol} {event['agent']} — "
                f"{event['status']}"
            )

        try:
            result = run_research_workflow(
                task,
                project_root=ROOT,
                on_event=on_event,
            )
        except Exception as error:
            status.update(
                label="Workflow failed",
                state="error",
            )
            st.error(
                "The workflow could not complete. "
                f"Error type: {type(error).__name__}"
            )
            st.stop()

        status.update(
            label="Workflow completed",
            state="complete",
        )

    st.subheader("Scientific decision")

    decision = result["decision"]

    if decision == "evidence_only":
        st.success("Evidence-only scientific observation")
    elif decision == "hypothesis_only":
        st.info("Registered structural hypothesis only")
    else:
        st.warning(
            "Abstention: insufficient verified support "
            "for the requested conclusion"
        )

    st.write(result["response"])

    if result["citations"]:
        st.subheader("Verified evidence citations")

        for citation in result["citations"]:
            st.markdown(
                f"**Evidence:** {citation['evidence_id']}"
            )
            st.write(f"DOI: {citation['doi']}")
            st.write(
                f"Source location: "
                f"{citation['source_location']}"
            )
            st.write(
                f"Source extent: "
                f"{citation['source_extent']}"
            )

    if result["candidate_ids"]:
        st.subheader("Registered catalyst hypotheses")
        for candidate_id in result["candidate_ids"]:
            st.write(f"• {candidate_id}")

        st.caption(
            "Structures are unrelaxed and pending "
            "human visual review."
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
