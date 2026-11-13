
import streamlit as st

st.set_page_config(
    page_title="Discover | CuSelect-AI",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

.stApp {
    background: #0C1716;
    color: #F5F8F7;
}

.block-container {
    max-width: 1500px;
    padding-top: 5rem;
}

.cs-brand {
    font-family: 'Outfit', sans-serif;
    font-size: 42px;
    font-weight: 700;
    color: #F5F8F7;
}

.cs-brand span {
    color: #62D5C8;
}

.cs-eyebrow {
    color: #62D5C8;
    font-family: 'Inter', sans-serif;
    font-size: 25px;
    font-weight: 700;
    letter-spacing: 0.12em;
}

.cs-heading {
    font-family: 'Outfit', sans-serif;
    color: #F5F8F7;
    font-size: clamp(30px, 4vw, 40px);
    font-weight: 700;
    letter-spacing: -0.04em;
    line-height: 1.12;
    margin: 18px 0 18px;
}

.cs-description {
    color: #B2C6C1;
    font-family: 'Inter', sans-serif;
    font-size: 22px;
    line-height: 1.6;
    max-width: 850px;
    margin-bottom: 30px;
}

.stFormSubmitButton > button[kind="primary"] {
    background: #62D5C8 !important;
    color: #0C1716 !important;
    border: none !important;
    border-radius: 10px !important;
    min-height: 54px !important;
    font-size: 18px !important;
    font-weight: 700 !important;
}

.cs-note {
    color: #AFC8C2;
    font-size: 20px;
    margin-top: 20px;
}
</style>
""", unsafe_allow_html=True)


# SHARED CUSELECT-AI NAVIGATION

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]

if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from components.header import render_header

import importlib
import components.header as _cuselect_header
importlib.reload(_cuselect_header)
_cuselect_header.render_header()

st.divider()


# SIMPLE DISCOVER EXPERIENCE

st.markdown(
    '<div class="cs-heading">'
    'What would you like to discover?'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="cs-description">'
    'Ask about catalysts, scientific literature, '
    'electrochemistry, or computational research.'
    '</div>',
    unsafe_allow_html=True,
)

with st.form("simple_research_form"):
    question = st.text_area(
        "Your research question",
        placeholder=(
            "Ask CuSelect-AI a scientific question..."
        ),
        height=130,
    )

    submitted = st.form_submit_button(
        "Ask CuSelect-AI →",
        type="primary",
    )

if submitted:
    st.session_state.pop("simple_research_result", None)
    st.session_state.pop("simple_research_error", None)

    if not question.strip():
        st.warning("Please enter a question.")
    else:
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        src = str(root / "src")

        if src not in sys.path:
            sys.path.insert(0, src)

        from cuselect.discover_dispatch import execute_discover_question

        try:
            with st.spinner("Researching your question..."):
                response = execute_discover_question(
                    question,
                    project_root=root,
                )

            st.session_state["simple_research_result"] = response

        except Exception as exc:
            st.session_state["simple_research_error"] = str(exc)


error = st.session_state.get("simple_research_error")

if error:
    st.error("CuSelect-AI could not complete this request.")

    with st.expander("Technical details"):
        st.code(error)


result = st.session_state.get("simple_research_result")

if result:
    st.divider()
    st.subheader("Research answer")

    context_note = result.get("query_context_note")
    if context_note:
        st.info("Research scope: " + str(context_note))


    status = result.get("status")

    if status == "benchmark_summary":
        st.markdown(result.get("answer", ""))
        st.caption(
            "Provisional benchmark records — "
            "not an approved catalyst ranking."
        )

    elif status == "evidence_limited_synthesis":
        st.markdown(result.get("answer", ""))
        st.caption(
            "Global publications are provisionally screened. "
            "Their experimental claims have not yet been verified."
        )

    elif status == "evidence_response":
        import re

        raw_answer = str(result.get("answer") or "")
        observations = [
            line.strip()[2:].strip()
            for line in raw_answer.splitlines()
            if line.strip().startswith("- ")
        ]

        if observations:
            st.markdown("**From your reviewed literature:**")

            for observation in observations:
                # Remove duplicate introductory catalyst labels.
                observation = re.sub(
                    r"^([^:]{2,80}):\\s*\\1\\b",
                    r"\\1",
                    observation,
                )

                st.markdown("- " + observation)
        else:
            st.markdown(raw_answer)

        with st.expander("Original evidence response"):
            st.text(raw_answer)

        st.caption(
            "Literature observations are not "
            "predictions for proposed catalysts."
        )

    elif status == "evidence_abstention":
        st.info(
            "The reviewed evidence does not currently "
            "support a reliable answer to this question."
        )

    elif status == "planning_only":
        st.info(
            "I understand the research request, but "
            "this type of scientific workflow is not "
            "yet available for automatic execution."
        )

    else:
        st.warning("No supported research answer was returned.")

    with st.expander("Scientific details"):
        # DISCOVER RESULT DIAGNOSTIC
        st.write(
            "**Response status:**",
            result.get("status", "Unknown"),
        )
        st.write(
            "**Publication count:**",
            result.get("global_publication_count", "Not reported"),
        )
        st.write(
            "**Screening complete:**",
            result.get("screening_complete", "Not reported"),
        )

        st.write(
            "**Workflow:**",
            (
                result.get("workflow")
                or result.get("execution_mode")
                or "Research workflow"
            ),
        )

        st.write(
            "**Execution mode:**",
            result.get("execution_mode", "Unknown"),
        )

        st.write(
            "**Citation audit:**",
            result.get("citation_audit_passed", False),
        )

        citations = result.get("citations", [])

        if citations:
            st.write("**Supporting sources:**")

            for citation in citations:
                if isinstance(citation, dict):
                    doi = citation.get("doi")
                    evidence_id = citation.get("evidence_id")
                    location = citation.get("source_location")

                    if doi:
                        st.write("DOI:", doi)
                    if evidence_id:
                        st.write("Evidence:", evidence_id)
                    if location:
                        st.caption(location)

                elif isinstance(citation, str):
                    st.write("Evidence ID:", citation)

                else:
                    st.warning("Unsupported citation format.")

        if result.get("missing_information"):
            st.write(
                "**Missing information:**",
                result["missing_information"],
            )

        if result.get("scientific_constraints"):
            st.write(
                "**Scientific constraints:**",
                result["scientific_constraints"],
            )

st.markdown(
    '<div class="cs-note">'
    'Literature-grounded · Computationally assessable · '
    'Human scientific review required'
    '</div>',
    unsafe_allow_html=True,
)


# CUSELECT_DISCOVERY_SAVE_V1
# Save a researcher-selected hypothesis, not an entire
# AI-generated answer or an automatically verified claim.

if isinstance(result, dict) and result.get("answer"):

    with st.expander("Save a hypothesis for Validation"):
        st.caption(
            "Select one specific research idea from the answer. "
            "It will be saved as provisional and unassessed."
        )

        with st.form("save_discovery_case_form"):
            discovery_title = st.text_input(
                "Candidate or hypothesis name",
                placeholder="e.g. Spatially separated Cu–Ag tandem catalyst",
            )

            discovery_hypothesis = st.text_area(
                "Hypothesis to investigate",
                placeholder=(
                    "Describe the proposed catalyst modification, "
                    "expected effect, and scientific reasoning."
                ),
                height=110,
            )

            save_discovery = st.form_submit_button(
                "Save for Validation",
                type="primary",
            )

        if save_discovery:
            if not discovery_title.strip() or not discovery_hypothesis.strip():
                st.warning(
                    "Enter a candidate name and a specific hypothesis."
                )
            else:
                try:
                    from cuselect.discovery_cases import (
                        save_discovery_case,
                    )

                    case = save_discovery_case(
                        ROOT,
                        title=discovery_title,
                        hypothesis=discovery_hypothesis,
                        research_question=str(
                            result.get("question") or question
                        ),
                        sources=[],
                    )

                    st.session_state[
                        "last_saved_discovery_case"
                    ] = case["case_id"]

                except Exception as exc:
                    st.error(
                        "The discovery case could not be saved."
                    )
                    with st.expander("Technical details"):
                        st.code(
                            f"{type(exc).__name__}: {exc}"
                        )

        saved_id = st.session_state.get(
            "last_saved_discovery_case"
        )

        if saved_id:
            st.success("Research case saved.")
            st.code(saved_id)
            st.caption(
                "Status: provisional · Validation: not assessed. "
                "Source-to-hypothesis links have not yet been "
                "verified or attached."
            )
