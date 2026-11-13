"""CuSelect-AI research homepage."""

from pathlib import Path

import streamlit as st

from .research_cycle_ui import load_research_cycle, show_decision


def navigate_to(page):
    """Select a destination in the main navigation."""
    st.session_state["primary_navigation"] = page


def render_workspace(root: Path):
    st.title("Research Workspace")
    st.caption(
        "Investigate Cu-based CO₂ reduction with literature evidence, "
        "saved agent records and registered atomic models."
    )

    with st.container(border=True):
        st.subheader("Current research project")
        project, status = st.columns([2, 1])
        try:
            records, _ = load_research_cycle(root)
        except (OSError, ValueError, KeyError, TypeError):
            project.error("Historical project verification failed. Check the saved records.")
        else:
            proposal = records["design"]["proposal"]
            critique = records["critic"]["critique"]
            project.markdown("**" + proposal["candidate_name"] + "**")
            project.write(
                "Could the spatial arrangement of Ag islands change the local "
                "CO environment and ethylene formation?"
            )
            with status:
                st.caption("Historical research decision")
                show_decision(critique.get("recommended_disposition"))

    destinations = (
        ("AI Research Cycle", "Review the current project or run a local evidence workflow.",
         "Open research project"),
        ("Evidence Library", "Browse reviewed claims, measurements and the literature queue.",
         "Explore evidence"),
        ("Catalyst Explorer", "Compare registered 3D structures and inspect saved calculations.",
         "Explore catalysts"),
    )
    for column, (page, description, action) in zip(st.columns(3), destinations):
        with column, st.container(border=True):
            st.markdown(f"**{page}**")
            st.write(description)
            st.button(action, on_click=navigate_to, args=(page,), width="stretch")

    st.caption("Research prototype. Catalyst selectivity and Faradaic efficiency require experimental validation.")
