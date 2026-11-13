
"""Source-grounded evidence search interface."""

import html
import json
import re
from urllib.parse import quote

import streamlit as st
from cuselect.rag_retriever import search_evidence


def readable(text):
    """Format chemical subscripts without altering stored evidence."""
    text = html.unescape(str(text or ""))
    subs = str.maketrans("0123456789+-", "₀₁₂₃₄₅₆₇₈₉₊₋")

    text = re.sub(
        r"<sub>(.*?)</sub>",
        lambda m: m.group(1).translate(subs),
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return re.sub(r"<[^>]+>", "", text)


def render_rag_search(root):
    st.subheader("Scientific Evidence Search")
    st.caption(
        "Semantic retrieval from source-linked experimental records."
    )

    with st.form("rag_search_form"):
        question = st.text_input(
            "Research question",
            placeholder="What evidence exists for Ag/Cu catalysts?",
        )
        submitted = st.form_submit_button(
            "Search evidence",
            icon=":material/search:",
        )

    if submitted:
        if not question.strip():
            st.warning("Enter a research question.")
            st.session_state["rag_hits"] = []
        else:
            with st.spinner("Retrieving evidence..."):
                st.session_state["rag_hits"] = search_evidence(
                    root, question, top_k=5
                )

    hits = st.session_state.get("rag_hits")

    if hits is None:
        return

    records = json.loads(
        (root / "data/approved_evidence.json").read_text(
            encoding="utf-8"
        )
    )

    by_id = {
        str(r["measurement_id"]): r
        for r in records
        if r.get("measurement_id")
    }

    unique = []
    seen = set()
    rejected = 0

    for hit in hits:
        record = by_id.get(str(hit.get("measurement_id")))

        # Require an exact match to the authoritative local record.
        if (
            record is None
            or hit.get("doi") != record.get("doi")
            or hit.get("source_excerpt")
            != record.get("exact_source_text")
        ):
            rejected += 1
            continue

        fingerprint = (
            record["doi"],
            " ".join(record["exact_source_text"].split()),
        )

        if fingerprint in seen:
            continue

        seen.add(fingerprint)
        unique.append((hit, record))

    if rejected:
        st.error(
            f"{rejected} result(s) excluded because source "
            "provenance could not be confirmed."
        )

    st.caption(f"{len(unique)} distinct source passages")

    if not unique:
        st.info("No matching source records were available.")
        return

    st.warning(
        "Provisional evidence only. Scientific validity and "
        "experimental conditions have not been independently verified."
    )


    # Grounded extractive answer: no LLM or external API calls.
    st.subheader("Evidence-grounded answer")

    st.write(
        f"The search retrieved {len(unique)} distinct source "
        "passages. The following excerpts describe candidate "
        "experimental observations relevant to the question."
    )

    st.warning(
        "Conclusion: Insufficient independently verified evidence "
        "to establish catalyst superiority, causal mechanisms, "
        "or validated performance. Experimental conditions and "
        "scientific claims require human review."
    )

    st.markdown("**What the retrieved sources report:**")

    for citation, (candidate_hit, record) in enumerate(
        unique[:3], start=1
    ):
        st.write(
            f"[{citation}] "
            f"{readable(record['exact_source_text'])}"
        )
        st.caption(
            f"[{citation}] Measurement: "
            f"{record['measurement_id']} · "
            f"DOI: {record['doi']} · "
            f"Scientific status: "
            f"{record.get('scientific_status', 'unknown')}"
        )

    st.caption(
        "This is an extractive summary of retrieved excerpts, "
        "not an LLM-generated interpretation. Citations identify "
        "source records; they do not certify scientific validity."
    )

    st.divider()


    # Experimental local LLM synthesis.
    # Only the user clicking this button triggers model inference.
    st.subheader("Local AI research draft")

    st.caption(
        "Qwen2.5-0.5B-Instruct · Local inference · "
        "Provisional scientific evidence"
    )

    import hashlib
    from cuselect.rag_generator import generate_local_answer

    signature = hashlib.sha256(
        repr((
            question,
            [
                (
                    r["measurement_id"],
                    r["doi"],
                    r["exact_source_text"],
                )
                for _, r in unique[:3]
            ],
        )).encode("utf-8")
    ).hexdigest()

    if st.button(
        "Generate local AI draft",
        icon=":material/auto_awesome:",
        key="rag_local_generate",
    ):
        # Clear any previous answer before attempting inference.
        st.session_state["rag_local_answer"] = None

        try:
            with st.spinner("Generating and checking local draft..."):
                draft = generate_local_answer(question, unique)

            st.session_state["rag_local_answer"] = {
                "signature": signature,
                "draft": draft,
            }

        except Exception as exc:
            st.error(
                "Local model could not complete generation "
                f"({type(exc).__name__})."
            )

    saved = st.session_state.get("rag_local_answer")

    if saved and saved["signature"] == signature:
        draft = saved["draft"]

        if draft:
            for item in draft:
                st.write(
                    f"- {item['claim']} "
                    f"[{item['source_id']}]"
                )
                st.caption(
                    f"Source {item['source_id']} · "
                    f"DOI: {item['doi']}"
                )
        else:
            st.info(
                "No generated statements passed the basic "
                "citation and numerical checks. "
                "Consult the retrieved source excerpts."
            )

    st.warning(
        "Experimental AI draft only. Citation-ID and "
        "numerical checks do not verify scientific meaning. "
        "All indexed measurements require human review."
    )

    st.divider()

    for index, (hit, record) in enumerate(unique, 1):
        with st.container(border=True):
            st.markdown(
                f"**{index}. {readable(record.get('title'))}**"
            )

            st.write(readable(record["exact_source_text"]))

            st.caption(
                f"Similarity: {hit['similarity']:.3f} · "
                f"Measurement: {record['measurement_id']}"
            )

            with st.expander("Source and verification details"):
                st.write("**DOI:**", record["doi"])

                st.write(
                    "**Scientific status:**",
                    record.get("scientific_status", "Unknown"),
                )

                st.write(
                    "**Conditions review:**",
                    record.get(
                        "conditions_review_status", "Unknown"
                    ),
                )

                st.write(
                    "**Context linking:**",
                    record.get("context_link_status", "Unknown"),
                )

                st.caption(
                    "Original source excerpt (unchanged):"
                )
                st.code(
                    record["exact_source_text"],
                    language=None,
                )

                if record.get("conditions_source_text"):
                    st.caption(
                        "Recorded condition excerpt — "
                        "not yet verified:"
                    )
                    st.code(
                        record["conditions_source_text"],
                        language=None,
                    )

            doi = str(record["doi"])
            if re.fullmatch(r"10\.\d{4,9}/[^\s<>]+", doi):
                st.link_button(
                    "View original publication",
                    "https://doi.org/" + quote(doi, safe="/"),
                )

    st.divider()
