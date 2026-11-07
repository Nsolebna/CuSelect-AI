# CuSelect-AI — Literature Review Queue interface
#
# PSEUDOCODE
# 1. Search Crossref for new scientific publications.
# 2. Display preliminary title-screening results.
# 3. Let the researcher select papers to save.
# 4. Load the existing human-review queue.
# 5. Allow review decisions and notes to be edited.
# 6. Save changes using the tested queue backend.
# 7. Never modify verified scientific evidence.

from pathlib import Path
from urllib.parse import quote

import streamlit as st

from .discovery import discover_crossref
from .review_queue import (
    ReviewQueueError,
    load_queue,
    merge_discoveries,
    save_queue,
    update_review,
)


def render_review_queue(project_root):
    """Render the literature discovery and human-review interface."""

    root = Path(project_root)

    queue_path = (
        root
        / "data"
        / "interim"
        / "literature_review_queue.json"
    )

    st.divider()
    st.header("Literature Discovery & Review Queue")

    st.caption(
        "Discovered publications are unverified. "
        "Review decisions do not authorize scientific claims."
    )

    with st.form("literature_discovery_form"):
        query = st.text_input(
            "Research query",
            value=(
                "copper silver CO2 electroreduction "
                "ethylene ethanol"
            ),
        )

        rows = st.number_input(
            "Maximum publications",
            min_value=1,
            max_value=30,
            value=10,
            step=1,
        )

        search = st.form_submit_button(
            "Discover publications",
            type="primary",
        )

    if search:
        try:
            with st.spinner("Searching Crossref..."):
                papers = discover_crossref(
                    query,
                    rows=int(rows),
                )

            st.session_state["discovered_papers"] = papers
            st.session_state["selected_discovery_dois"] = []

            st.success(
                f"Discovered {len(papers)} candidate publications."
            )

        except Exception as error:
            st.error(
                "Crossref discovery failed: "
                f"{type(error).__name__}. "
                "Your saved review queue is unchanged."
            )

    papers = st.session_state.get(
        "discovered_papers",
        [],
    )

    if papers:
        st.subheader("Discovered publications")

        st.dataframe(
            [
                {
                    "Year": paper["year"],
                    "Title": paper["title"],
                    "DOI": paper["doi"],
                    "Screening": paper["screening_status"],
                }
                for paper in papers
            ],
            hide_index=True,
        )

        by_doi = {
            paper["doi"]: paper
            for paper in papers
        }

        selected = st.multiselect(
            "Choose publications to save for review",
            options=list(by_doi),
            format_func=lambda doi: (
                by_doi[doi]["title"][:100]
            ),
            key="selected_discovery_dois",
        )

        if st.button(
            "Add selected publications to review queue",
            disabled=not selected,
        ):
            try:
                existing = load_queue(queue_path)

                updated = merge_discoveries(
                    [by_doi[doi] for doi in selected],
                    existing,
                )

                save_queue(queue_path, updated)

                st.success(
                    f"Review queue now contains {len(updated)} "
                    "unique publications."
                )

            except (ReviewQueueError, OSError, ValueError) as error:
                st.error(
                    "Could not save selected publications: "
                    f"{error}"
                )

    st.subheader("Saved literature review queue")

    try:
        queue = load_queue(queue_path)

    except (ReviewQueueError, OSError, ValueError) as error:
        st.error(
            "Unable to read the existing review queue: "
            f"{error}"
        )
        return

    if not queue:
        st.info(
            "Your review queue is empty. "
            "Discover publications and select the ones "
            "you want to investigate."
        )
        return

    st.metric("Saved publications", len(queue))

    st.dataframe(
        [
            {
                "Title": paper["title"],
                "Year": paper["year"],
                "Screening": paper["screening_status"],
                "Review decision": paper["review_status"],
                "DOI": paper["doi"],
            }
            for paper in queue
        ],
        hide_index=True,
    )

    by_saved_doi = {
        paper["doi"]: paper
        for paper in queue
    }

    selected_doi = st.selectbox(
        "Select a publication to review",
        options=list(by_saved_doi),
        format_func=lambda doi: (
            by_saved_doi[doi]["title"][:100]
        ),
    )

    paper = by_saved_doi[selected_doi]

    st.write("**Publication:**", paper["title"])
    st.write("**DOI:**", paper["doi"])
    st.write(
        "**Scientific status:**",
        paper["scientific_status"],
    )

    publication_url = (
        "https://doi.org/"
        + quote(paper["doi"], safe="/-._;():+")
    )

    st.link_button(
        "Open publication",
        publication_url,
    )

    statuses = [
        "new",
        "review_further",
        "set_aside",
    ]

    with st.form(f"review_form_{selected_doi}"):
        status = st.selectbox(
            "Review decision",
            statuses,
            index=statuses.index(
                paper["review_status"]
            ),
        )

        notes = st.text_area(
            "Scientific review notes",
            value=paper["notes"],
            height=130,
            help=(
                "Record questions, experimental details "
                "to inspect, or supporting-figure references."
            ),
        )

        save = st.form_submit_button(
            "Save review decision",
            type="primary",
        )

    if save:
        try:
            updated = update_review(
                queue,
                selected_doi,
                status,
                notes,
            )

            save_queue(queue_path, updated)

            st.success("Review decision and notes saved.")

        except (ReviewQueueError, OSError, ValueError) as error:
            st.error(f"Could not save review: {error}")

    st.caption(
        "This queue is local to your project. "
        "It does not update the verified RAG corpus."
    )
