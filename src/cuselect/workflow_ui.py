"""Interactive deterministic research workflow."""

import json

import streamlit as st

from .agents import ResearchTask
from .catalyst_ui import render_structures
from .evidence_library_ui import render_evidence_card
from .evidence_navigator import build_evidence_cards
from .orchestrator import run_research_workflow


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


def render_local_workflow(root):
    st.subheader("Local research workflow")
    st.caption("Runs three deterministic agents on saved evidence and geometries. No model requests.")

    example, request = st.columns([1, 2])
    with example:
        selected = st.selectbox("Research example", list(EXAMPLES))
    task_type, default_question, candidate_ids = EXAMPLES[selected]

    with request, st.form("research_form"):
        literature_mode = st.selectbox(
            "Literature retrieval",
            ("legacy", "dynamic"),
            format_func=lambda mode: (
                "Legacy — trusted default"
                if mode == "legacy"
                else "Dynamic — experimental"
            ),
        )
        question = st.text_area(
            "Research question", value=default_question, key=f"question_{selected}"
        )
        submitted = st.form_submit_button("Run scientific workflow", type="primary")

    if submitted:
        st.session_state.pop("local_workflow_result", None)
        if not question.strip():
            st.error("Please enter a research question.")
            return

        task = ResearchTask(
            task_id="APP-001",
            task_type=task_type,
            question=question.strip(),
            candidate_ids=candidate_ids,
        )

        st.subheader("Agent execution")

        with st.status(
            "Running the scientific workflow...",
            expanded=False,
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
                    project_root=root,
                    on_event=on_event,
                    literature_mode=literature_mode,
                )
            except Exception as exc:
                status.update(
                    label="Workflow failed",
                    state="error",
                )
                st.error(
                    f"Workflow error: {type(exc).__name__}"
                )
                return

            status.update(
                label="Workflow completed",
                state="complete",
            )
        st.session_state["local_workflow_result"] = (
            selected, literature_mode, result
        )

    saved = st.session_state.get("local_workflow_result")
    if (
        saved is None
        or len(saved) != 3
        or saved[0] != selected
        or saved[1] != literature_mode
    ):
        return
    result = saved[2]

    st.subheader("Scientific result")
    st.caption(result["task"]["question"])
    if result["decision"] == "evidence_only":
        st.success("Evidence-only observation")
    elif result["decision"] == "hypothesis_only":
        st.info("Structural hypothesis only")
    else:
        st.warning("Abstain · insufficient verified evidence")
    st.write(result["response"])

    if result["citations"]:
        try:
            cards = build_evidence_cards(result["citations"], root)
        except (OSError, ValueError) as error:
            st.error(f"Citation verification failed: {error}")
        else:
            for card in cards:
                with st.expander(f"Evidence {card['evidence_id']}"):
                    render_evidence_card(card)

    if result["candidate_ids"]:
        st.subheader("Registered catalyst structures")
        render_structures(root, result["candidate_ids"])

    with st.expander("Scientific audit and execution trace"):
        st.dataframe(result["trace"], hide_index=True)
        st.write("**Critic decision**", result["critic"]["decision"])
        st.write("**Reason codes**", ", ".join(result["critic"]["reason_codes"]))
        st.write("**Run SHA-256**")
        st.code(result["run_sha256"])
        st.write("**Source corpus SHA-256**")
        st.code(result["source_corpus_sha256"])
        st.download_button(
            "Download workflow audit", json.dumps(result, indent=2),
            "cuselect_workflow_audit.json", "application/json",
        )
