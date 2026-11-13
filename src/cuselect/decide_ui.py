"""Minimal, evidence-grounded research decision interface."""

from pathlib import Path
import json

import streamlit as st


def _load_cases(root):
    """Read existing research cases without modifying them."""
    path = Path(root) / "data/research_cases.json"

    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        st.error("Could not read saved research cases.")
        return []

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]

    if isinstance(data, dict):
        for key in ("cases", "research_cases"):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
            if isinstance(value, dict):
                return [
                    dict(item, case_id=item.get("case_id", str(cid)))
                    for cid, item in value.items()
                    if isinstance(item, dict)
                ]

        # Support a dictionary indexed directly by case ID.
        return [
            dict(item, case_id=item.get("case_id", str(cid)))
            for cid, item in data.items()
            if isinstance(item, dict)
        ]

    return []


def _case_id(case):
    return str(
        case.get("case_id")
        or case.get("id")
        or case.get("research_case_id")
        or ""
    )


def _case_name(case):
    for key in (
        "candidate_name",
        "candidate",
        "title",
        "name",
        "catalyst",
    ):
        value = case.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return _case_id(case) or "Unnamed research case"


def _assessment(case):
    """Locate the saved assessment without assuming approval."""
    for key in (
        "validation_assessment",
        "validation",
        "assessment",
        "latest_assessment",
    ):
        value = case.get(key)
        if isinstance(value, dict):
            return value

    return {}


def _explicit_review_status(case, assessment):
    """Only explicit human-verified status can establish review."""
    for record in (assessment, case):
        for key in (
            "review_status",
            "human_review_status",
            "evidence_review_status",
        ):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()

    return "unknown"


def _decision(case):
    """Conservative rules based on stored case status."""
    assessment = _assessment(case)

    review = _explicit_review_status(case, assessment)

    verified = review in {
        "verified",
        "human_verified",
        "approved",
        "human_approved",
    }

    validation_status = str(
        case.get("validation_status")
        or assessment.get("validation_status")
        or ""
    ).lower()

    if not assessment and not validation_status:
        return {
            "next": "Complete the scientific assessment",
            "why": (
                "No saved validation assessment was identified "
                "for this research case."
            ),
            "gate": (
                "A traceable assessment is saved in Validate, "
                "with source provenance and limitations recorded."
            ),
        }

    if not verified:
        return {
            "next": "Verify the scientific evidence",
            "why": (
                "The saved assessment has not established "
                "explicit human-verified evidence. An automated "
                "assessment does not constitute scientific approval."
            ),
            "gate": (
                "The relevant source, experimental or computational "
                "conditions, and scientific limitations have been "
                "reviewed and the review status updated."
            ),
        }

    return {
        "next": "Define the next validation experiment",
        "why": (
            "The saved record indicates human-reviewed evidence, "
            "but this alone does not establish the best experiment "
            "or justify a catalyst-performance ranking."
        ),
        "gate": (
            "A testable hypothesis, appropriate controls, "
            "success criteria, and comparable operating "
            "conditions are documented."
        ),
    }


def render_decide(root):
    st.title("Make your next research decision")
    st.caption(
        "One evidence-grounded action. "
        "No repeated charts or validation reports."
    )

    cases = _load_cases(root)

    if not cases:
        st.info(
            "No saved research cases are available. "
            "Create or assess a candidate in Validate first."
        )
        return

    options = {
        f"{_case_name(case)} · {_case_id(case)}": case
        for case in cases
    }

    selected = st.selectbox(
        "Research candidate",
        options=list(options),
        key="decide_candidate",
    )

    if st.button(
        "Assess next step",
        type="primary",
        key="decide_assess",
    ):
        st.session_state["decide_result_id"] = _case_id(
            options[selected]
        )

    case = options[selected]
    selected_id = _case_id(case)

    if st.session_state.get("decide_result_id") != selected_id:
        return

    decision = _decision(case)

    st.divider()

    st.markdown("#### Recommended next step")
    st.info(f"**{decision['next']}**")

    st.markdown("**Why?**")
    st.write(decision["why"])

    st.markdown("**Proceed when**")
    st.write(decision["gate"])

    st.caption(
        "Decision support derived from saved case status. "
        "No scientific approval or new calculation performed."
    )
