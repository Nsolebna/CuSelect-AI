"""Human evidence verification. Never modifies approved RAG data."""

import fcntl
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from cuselect.evidence_promotion import (
    identify_candidate_passages,
    get_passage_review,
    submit_claim_review,
)

CANDIDATES = "data/evidence_extraction_candidates.json"
REVIEWS = "data/evidence_verification_reviews.json"
CLAIM_REVIEWS = "data/evidence_claim_reviews.json"

STATUSES = {
    "needs_full_text": "Needs full-text review",
    "rejected": "Reject candidate",
    "source_checked": "Full text checked — not RAG-approved",
}


def read_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def authorized_email():
    allowed = st.secrets.get("reviewer_emails", [])
    if isinstance(allowed, str):
        allowed = [allowed]

    email = str(st.user.get("email", "") or "").strip().lower()

    if (
        st.user.is_logged_in
        and email
        and email in {str(x).strip().lower() for x in allowed}
    ):
        return email

    return None


def validate_review(record):
    errors = []

    if record.get("status") not in STATUSES:
        errors.append("Invalid review decision.")

    fe = str(record.get("fe_percent") or "").strip()

    if fe:
        try:
            value = float(fe)
            if not math.isfinite(value) or not 0 <= value <= 100:
                errors.append("FE must be between 0 and 100%.")
        except ValueError:
            errors.append("FE must be numeric.")

        if not record.get("fe_product", "").strip():
            errors.append("Specify the FE product.")

    if record.get("status") == "source_checked":
        location = record.get("source_location", "").strip()
        excerpt = record.get("source_excerpt", "").strip()

        if not record.get("confirmed"):
            errors.append("Confirm original-publication verification.")

        if not location or location.lower() in {
            "abstract", "unknown", "n/a"
        }:
            errors.append(
                "Provide a specific full-text page, figure or table."
            )

        if len(excerpt.split()) < 8:
            errors.append(
                "Enter the exact source passage (at least 8 words)."
            )

    return errors


def save_review(root, doi, record):
    reviewer = authorized_email()

    if not reviewer:
        raise PermissionError("Reviewer authorization required.")

    errors = validate_review(record)
    if errors:
        raise ValueError("; ".join(errors))

    path = root / REVIEWS
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = root / "data/evidence_verification_reviews.lock"

    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

        try:
            reviews = read_json(path, {})

            if not isinstance(reviews, dict):
                raise ValueError("Review ledger must be a JSON object.")

            reviews[doi] = {
                **record,
                "doi": doi,
                "reviewer_email": reviewer,
                "reviewed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "rag_ingestion_status": "not_ingested",
            }

            temporary = path.with_suffix(".json.tmp")

            try:
                temporary.write_text(
                    json.dumps(
                        reviews,
                        indent=2,
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def render_evidence_review(root: Path):
    st.title("Scientific Evidence Verification")

    st.caption(
        "Stage 4/8 · Human source verification · "
        "No automatic RAG approval"
    )

    st.info(
        "Extracted abstract passages are unverified. "
        "Check the original paper before recording "
        "a full-text-checked claim."
    )

    try:
        candidates = read_json(root / CANDIDATES, [])
        reviews = read_json(root / REVIEWS, {})
        claim_reviews = read_json(root / CLAIM_REVIEWS, {})

        if not isinstance(candidates, list):
            raise ValueError("Expected a list of candidates.")

        if not isinstance(reviews, dict):
            raise ValueError("Expected a review ledger.")

    except (OSError, ValueError) as exc:
        st.error(f"Cannot load evidence: {exc}")
        return

    candidates = [
        p for p in candidates
        if isinstance(p, dict) and p.get("doi")
    ]

    if not candidates:
        st.warning(
            "No extracted candidates. Run "
            "`python scripts/prepare_evidence_candidates.py`."
        )
        return

    counts = {
        status: sum(
            r.get("status") == status
            for r in reviews.values()
            if isinstance(r, dict)
        )
        for status in STATUSES
    }

    columns = st.columns(4)

    for col, label, number in zip(
        columns,
        [
            "Extraction records",
            "Needs full text",
            "Rejected",
            "Full text checked",
        ],
        [
            len(candidates),
            counts["needs_full_text"],
            counts["rejected"],
            counts["source_checked"],
        ],
    ):
        col.metric(label, number)

    selected = st.selectbox(
        "Select a scientific paper",
        range(len(candidates)),
        format_func=lambda i: (
            f"{str(candidates[i].get('title', 'Untitled'))[:75]}"
            f" · {candidates[i]['doi']}"
        ),
    )

    paper = candidates[selected]
    doi = str(paper["doi"]).lower().strip()
    ident = hashlib.sha256(doi.encode()).hexdigest()[:14]
    current = reviews.get(doi, {})

    if not isinstance(current, dict):
        current = {}

    st.write(f"**{paper.get('title', 'Untitled')}**")
    st.write(f"DOI: `{doi}`")

    from urllib.parse import quote
    import re

    if re.fullmatch(r"10\.\d{4,9}/[^\s<>]+", doi):
        st.link_button(
            "Open original publication",
            "https://doi.org/" + quote(doi, safe="/"),
        )

    with st.expander(
        "Extracted abstract passages — unverified",
        expanded=True,
    ):
        try:
            passages = identify_candidate_passages(paper)
        except (ValueError, TypeError) as exc:
            st.error(f"Passage identification failed: {exc}")
            return

        if not passages:
            st.write("No matching passages found.")

        for index, passage in enumerate(passages, 1):
            st.caption(f"Passage {index} · Abstract")
            st.code(passage["evidence_id"])
            st.write(passage.get("source_excerpt", ""))

            passage_review = get_passage_review(
                passage, claim_reviews
            )

            if passage_review is None:
                st.caption("Claim review: Not yet reviewed")
            else:
                st.caption(
                    "Claim review: "
                    + str(passage_review.get("status", "unknown"))
                )

    # PSEUDOCODE
    # 1. Display each extracted passage independently.
    # 2. Require an authorized reviewer for claim-level submissions.
    # 3. Require source verification for source_checked decisions.
    # 4. Submit through the validated promotion backend.
    # 5. Never approve or modify trusted RAG evidence.

    # PSEUDOCODE
    # 1. Load the automated scientific review package.
    # 2. Display review readiness for all passages.
    # 3. Keep scientific approval and RAG ingestion disabled.

    package_path = root / "data/reports/evidence_review_package.json"

    if package_path.exists():
        package = read_json(package_path, [])

        if isinstance(package, list):
            st.subheader("Automated Evidence Review Summary")

            for item in package:
                if item.get("doi") != doi:
                    continue

                with st.expander(
                    "Evidence " + str(item.get("evidence_id", "")),
                    expanded=False,
                ):
                    st.write(
                        "Similarity:",
                        item.get("similarity"),
                    )
                    st.write(
                        "Missing numeric tokens:",
                        item.get("missing_numbers", []),
                    )
                    st.write(
                        "Review status:",
                        item.get("review_status"),
                    )
                    st.write(
                        "Matched publication text:",
                        item.get("matched_source_text", ""),
                    )

            st.caption(
                "Automated screening only. "
                "No scientific approval or RAG ingestion."
            )

    reviewer_email = authorized_email()

    # Human scientific approval, separate from RAG promotion.
    from cuselect.scientific_approval_ui import render_scientific_approval
    render_scientific_approval(root, doi, reviewer_email)

    if reviewer_email:
        st.subheader("Individual passage review")

        for passage in identify_candidate_passages(paper):
            evidence_id = passage["evidence_id"]
            prior = get_passage_review(passage, claim_reviews) or {}

            with st.expander(
                f"Review {evidence_id}",
                expanded=False,
            ):
                st.write(passage["source_excerpt"])
                st.caption(
                    "Current status: "
                    + prior.get("status", "not reviewed")
                )

                decisions = [
                    "needs_full_text",
                    "source_checked",
                    "rejected",
                ]

                prior_status = prior.get(
                    "status", "needs_full_text"
                )

                if prior_status not in decisions:
                    prior_status = "needs_full_text"

                with st.form(f"claim_form_{evidence_id}"):
                    decision = st.selectbox(
                        "Review decision",
                        decisions,
                        index=decisions.index(prior_status),
                    )

                    location = st.text_input(
                        "Verified full-text page, figure or table",
                        value=prior.get("source_location", ""),
                    )

                    excerpt = st.text_area(
                        "Exact supporting passage from original publication",
                        value=prior.get("source_excerpt", ""),
                    )

                    confirmed = st.checkbox(
                        "I personally verified this passage "
                        "against the original publication",
                        value=False,
                    )

                    submitted = st.form_submit_button(
                        "Save passage review"
                    )

                if submitted:
                    try:
                        saved = submit_claim_review(
                            root=root,
                            passage=passage,
                            decision=decision,
                            authenticated_reviewer=reviewer_email,
                            source_location=location,
                            source_excerpt=excerpt,
                            confirmed=confirmed,
                        )
                    except (ValueError, TypeError, OSError,
                            PermissionError) as exc:
                        st.error(f"Review not saved: {exc}")
                    else:
                        st.success(
                            "Review saved for "
                            + saved["evidence_id"]
                            + ". RAG evidence unchanged."
                        )

    if st.session_state.pop("evidence_review_saved", False):
        st.success(
            "Review saved. Approved RAG evidence was not modified."
        )

    if not authorized_email():
        st.warning("Read-only: authorized reviewer login required.")
        return

    options = list(STATUSES)
    previous = current.get("status", "needs_full_text")

    if previous not in options:
        previous = "needs_full_text"

    with st.form(f"scientific_review_{ident}"):
        decision = st.selectbox(
            "Review decision",
            options,
            index=options.index(previous),
            format_func=lambda x: STATUSES[x],
        )

        location = st.text_input(
            "Exact source location (page / figure / table)",
            value=current.get("source_location", ""),
        )

        excerpt = st.text_area(
            "Exact passage checked against original full text",
            value=current.get("source_excerpt", ""),
            height=110,
        )

        a, b = st.columns(2)

        with a:
            catalyst = st.text_input(
                "Catalyst / electrode",
                value=current.get("catalyst", ""),
            )

            cell = st.text_input(
                "Cell configuration",
                value=current.get("cell_type", ""),
            )

            electrolyte = st.text_input(
                "Electrolyte",
                value=current.get("electrolyte", ""),
            )

        with b:
            potential = st.text_input(
                "Potential and reference",
                value=current.get("potential", ""),
            )

            current_density = st.text_input(
                "Current density with units",
                value=current.get("current_density", ""),
            )

            fe_product = st.text_input(
                "FE product (e.g. ethylene)",
                value=current.get("fe_product", ""),
            )

            fe = st.text_input(
                "Faradaic efficiency, % (optional)",
                value=str(current.get("fe_percent", "")),
            )

        notes = st.text_area(
            "Reviewer notes",
            value=current.get("notes", ""),
        )

        confirmed = st.checkbox(
            "I personally checked the original full-text "
            "source passage and location"
        )

        submitted = st.form_submit_button(
            "Save scientific review",
            type="primary",
        )

    if submitted:
        record = {
            "status": decision,
            "source_location": location.strip(),
            "source_excerpt": excerpt.strip(),
            "catalyst": catalyst.strip(),
            "cell_type": cell.strip(),
            "electrolyte": electrolyte.strip(),
            "potential": potential.strip(),
            "current_density": current_density.strip(),
            "fe_product": fe_product.strip(),
            "fe_percent": fe.strip(),
            "notes": notes.strip(),
            "confirmed": confirmed,
        }

        errors = validate_review(record)

        if errors:
            for error in errors:
                st.error(error)
        else:
            try:
                save_review(root, doi, record)
            except (OSError, ValueError, PermissionError) as exc:
                st.error(f"Could not save review: {exc}")
            else:
                st.session_state["evidence_review_saved"] = True
                st.rerun()

    st.caption(
        "Next: Controlled preparation of checked claims "
        "for the RAG knowledge base."
    )
