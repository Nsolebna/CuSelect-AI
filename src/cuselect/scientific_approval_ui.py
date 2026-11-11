"""Human scientific approval of source-grounded evidence."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st


QUESTIONS = {
    "correct_catalyst": "The reported catalyst is HOH Cu/Ag.",
    "correct_product": "The reported product is ethylene.",
    "fe_and_potential_attributed_correctly":
        "60.37% FE and -1.3 V vs RHE refer to the same measurement.",
    "experimental_conditions_applicable":
        "The cited flow-cell methods apply to this result.",
    "figure_supports_claim":
        "I inspected Figure 4d in the original publication and confirmed its relevance.",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=".approval_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def render_scientific_approval(root, doi, reviewer_email):
    """Only the authenticated Streamlit reviewer may submit."""

    if not reviewer_email:
        return

    dossier_path = (
        root / "data/reports/hoh_cuag_evidence_dossier.json"
    )
    claim_path = (
        root / "data/reports/pending_scientific_claim.json"
    )
    xml_path = (
        root / "data/raw/publications/PMC13692753.xml"
    )
    approval_path = (
        root / "data/scientific_claim_approvals.json"
    )

    if not all(
        p.is_file()
        for p in (dossier_path, claim_path, xml_path)
    ):
        return

    dossier = json.loads(dossier_path.read_text())
    claim = json.loads(claim_path.read_text())

    if str(doi).lower().strip() != dossier["doi"].lower():
        return

    if (
        dossier["claim_id"] != claim["evidence_id"]
        or dossier["paper_id"] != claim["paper_id"]
        or dossier["doi"] != claim["doi"]
        or claim["paper_id"] != "P009"
        or claim.get("source_checked_by_human") is not False
    ):
        st.error("Staged claim and source dossier disagree.")
        return

    st.subheader("Scientific Claim Approval")
    st.write("**Claim:**", dossier["claim"])
    st.write("**Publication:**", dossier["paper_id"])
    st.write("**Reviewer:**", reviewer_email)

    with st.expander("Original performance evidence"):
        for i, passage in enumerate(
            dossier["performance_sources"], 1
        ):
            st.markdown(f"**Passage {i}**")
            st.write(passage)

    with st.expander("Experimental methods"):
        for passage in dossier["methodology_sources"]:
            st.write(passage)

    with st.expander("Supporting figure"):
        st.write("Figure 4d — HOH Cu/Ag")
        st.write(dossier["figure"]["caption"])
        st.warning(
            "The caption alone cannot verify plotted values. "
            "Inspect the original figure before approval."
        )

    existing = {}
    if approval_path.exists():
        existing = json.loads(approval_path.read_text())

    if claim["evidence_id"] in existing:
        record = existing[claim["evidence_id"]]
        st.info(
            "Recorded decision: "
            + str(record.get("decision", "unknown"))
        )
        st.write("Reviewer:", record.get("reviewer"))
        st.write("Timestamp:", record.get("timestamp"))
        st.caption(
            "This record is locked in this interface. "
            "The trusted registry has not been modified."
        )
        return

    with st.form("scientific_claim_approval_p009"):
        st.markdown("**Scientific verification checklist**")

        answers = {}
        for key, label in QUESTIONS.items():
            answers[key] = st.checkbox(label, key=f"approve_{key}")

        decision = st.radio(
            "Scientific decision",
            ["Not ready", "Approve", "Reject"],
        )

        note = st.text_area(
            "Scientific justification / reviewer notes"
        )

        submitted = st.form_submit_button("Record decision")

    if not submitted:
        return

    if decision == "Not ready":
        st.warning("No decision recorded.")
        return

    if decision == "Approve" and not all(answers.values()):
        st.error("All five checks must be confirmed for approval.")
        return

    if not note.strip():
        st.error("Provide a scientific justification.")
        return

    # Recheck the source state before recording the decision.
    if (
        dossier != json.loads(dossier_path.read_text())
        or claim != json.loads(claim_path.read_text())
    ):
        st.error("Source evidence changed. Reload and review again.")
        return

    record = {
        "claim_id": claim["evidence_id"],
        "paper_id": claim["paper_id"],
        "doi": claim["doi"],
        "decision": decision.lower(),
        "reviewer": reviewer_email,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": answers,
        "reviewer_note": note.strip(),
        "dossier_sha256": digest(dossier_path),
        "claim_sha256": digest(claim_path),
        "source_xml_sha256": digest(xml_path),
        "promotion_status": "pending_controlled_promotion",
        "rag_ingestion_status": "not_ingested",
    }

    # Prevent silently overwriting an earlier decision.
    if approval_path.exists():
        existing = json.loads(approval_path.read_text())
    if claim["evidence_id"] in existing:
        st.error("A decision already exists. Reload the page.")
        return

    existing[claim["evidence_id"]] = record
    atomic_json_write(approval_path, existing)

    st.success("Scientific review decision recorded.")
    st.info(
        "Trusted evidence registry and RAG corpus remain unchanged."
    )
