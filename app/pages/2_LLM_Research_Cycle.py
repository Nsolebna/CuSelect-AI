"""CuSelect-AI — LLM Research Cycle Explorer."""

# PSEUDOCODE
# 1. Load Design, Critic, Revision and evidence JSON.
# 2. Run the existing offline validation checks.
# 3. Display the three stages of the LLM cycle.
# 4. Show evidence links and scientific uncertainties.
# 5. Never treat an untested proposal as a proven catalyst.

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.agents.llm_cycle_validation import (
    FILES,
    validate_cycle,
)

st.set_page_config(
    page_title="CuSelect-AI | LLM Research Cycle",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 CuSelect-AI")
st.subheader("LLM Scientific Research Cycle")

st.caption(
    "Evidence-grounded Design → Critique → Revision "
    "for electrochemical CO₂-to-ethylene catalyst research"
)


@st.cache_data
def read_json(path, modification_time):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


missing = [
    name for name, path in FILES.items()
    if not path.exists()
]

if missing:
    st.error("Missing input files: " + ", ".join(missing))
    st.stop()

try:
    data = {
        name: read_json(
            str(path),
            path.stat().st_mtime_ns,
        )
        for name, path in FILES.items()
    }

    validation = validate_cycle(
        data["evidence"],
        data["design"],
        data["critic"],
        data["revision"],
        file_paths=FILES,
    )
except (ValueError, KeyError, TypeError, OSError,
        json.JSONDecodeError) as error:
    st.error(f"LLM cycle validation failed: {error}")
    st.stop()

design = data["design"]
critic = data["critic"]
revision = data["revision"]

proposal = design["proposal"]
critique = critic["critique"]
revised = revision["revision"]

st.success(
    "LLM-cycle integrity and provenance checks passed."
)

st.warning(
    "Scientific correctness and mechanistic claims are "
    "not independently verified. Human review required. "
    "No catalyst performance prediction has been made."
)

m1, m2, m3, m4 = st.columns(4)

m1.metric("AI stages", 3)
m2.metric(
    "Scientific findings",
    validation["scientific_findings"],
)
m3.metric(
    "Findings addressed",
    validation["findings_responded_to"],
)
m4.metric(
    "Revised experiments",
    validation["revised_experiments"],
)

st.divider()

st.header("Candidate evolution")

st.markdown(
    "**Original:** " + proposal["candidate_name"]
)
st.markdown(
    "**Revised:** " + revised["candidate_name"]
)

tab_design, tab_critic, tab_revision, tab_checks = st.tabs(
    [
        "1. Design Agent",
        "2. Scientific Critic",
        "3. Revision Agent",
        "4. Validation",
    ]
)

with tab_design:
    st.header("Original catalyst hypothesis")
    st.write("**Model:**", design["model"])

    st.markdown("#### Catalyst architecture")
    st.write(proposal["catalyst_architecture"])

    st.markdown("#### Proposed modification")
    st.write(proposal["design_modification"])

    st.markdown("#### Scientific hypothesis")
    st.write(proposal["scientific_hypothesis"])

    st.markdown("#### Mechanistic rationale")
    st.write(proposal["mechanistic_rationale"])

    st.markdown("#### Proposed experiment")
    st.write(proposal["proposed_experiment"])

    st.markdown("#### Discriminating control")
    st.write(proposal["discriminating_control"])

    st.markdown("#### Supporting evidence")

    for ref in proposal["supporting_evidence"]:
        with st.expander(ref["measurement_id"]):
            st.write("DOI:", ref["doi"])
            st.link_button(
                "Open publication",
                "https://doi.org/" + ref["doi"],
            )
            st.write("Claimed relevance:", ref["relevance"])

    st.markdown("#### Major uncertainties")
    for uncertainty in proposal["major_uncertainties"]:
        st.write("•", uncertainty)

with tab_critic:
    st.header("Scientific criticism")
    st.write("**Model:**", critic["model"])

    st.markdown("#### Main scientific risk")
    st.error(critique["most_serious_scientific_risk"])

    st.markdown("#### Scientific findings")

    for number, finding in enumerate(
        critique["scientific_findings"], start=1
    ):
        with st.expander(
            f'{number}. {finding["category"]}',
            expanded=False,
        ):
            st.write(
                "**Assessment:**", finding["assessment"]
            )
            st.write("**Finding:**", finding["finding"])
            st.write("**Reasoning:**", finding["reasoning"])
            st.write(
                "**Evidence IDs:**",
                finding["linked_measurement_ids"],
            )
            st.write(
                "**Recommended action:**",
                finding["recommended_action"],
            )

    st.markdown("#### Critical experiments")

    for experiment in critique["critical_experiments"]:
        with st.expander(experiment["experiment_name"]):
            st.write(
                "**Question:**",
                experiment["hypothesis_tested"],
            )
            st.write(
                "**Controls:**",
                experiment["controlled_variables"],
            )
            st.write(
                "**Measurements:**",
                experiment["measurement_strategy"],
            )
            st.write(
                "**Result challenging the hypothesis:**",
                experiment[
                    "result_that_would_challenge_hypothesis"
                ],
            )

    st.markdown("#### Critic recommendation")
    st.info(critique["recommended_disposition"])
    st.write(critique["disposition_reason"])

with tab_revision:
    st.header("Revised research hypothesis")
    st.write("**Model:**", revision["model"])

    st.markdown("#### Revised architecture")
    st.write(revised["revised_architecture"])

    st.markdown("#### Revised hypothesis")
    st.write(revised["revised_hypothesis"])

    st.markdown("#### Responses to the Critic")

    for item in revised["finding_responses"]:
        with st.expander(
            f'Finding {item["finding_number"]}: '
            f'{item["resolution_status"]}'
        ):
            st.write("**Issue:**", item["issue_addressed"])
            st.write(
                "**Revision:**", item["revision_action"]
            )
            st.write(
                "**Remaining uncertainty:**",
                item["remaining_uncertainty"],
            )

    st.markdown("#### Design variables")

    for variable in revised["design_variables"]:
        with st.expander(variable["variable"]):
            st.write(
                "**Levels/range:**",
                variable["proposed_levels_or_range"],
            )
            st.write(
                "**Scientific rationale:**",
                variable["scientific_reason"],
            )
            st.write(
                "**Control or measurement:**",
                variable["control_or_measurement"],
            )

    st.markdown("#### Controlled experiments")

    for experiment in revised["controlled_experiments"]:
        with st.expander(experiment["name"]):
            st.write("**Question:**", experiment["question"])
            st.write(
                "**Experimental groups:**",
                experiment["experimental_groups"],
            )
            st.write(
                "**Variables to control:**",
                experiment["variables_to_control"],
            )
            st.write(
                "**Measurements:**",
                experiment["measurements"],
            )
            st.write(
                "**Outcome challenging the hypothesis:**",
                experiment[
                    "outcome_challenging_hypothesis"
                ],
            )
            st.write(
                "**Interpretation limitations:**",
                experiment["interpretation_limitations"],
            )

    st.markdown("#### Next decision gate")
    st.info(revised["next_decision_gate"])

    st.markdown("#### Unresolved questions")
    for question in revised["unresolved_questions"]:
        st.write("•", question)

with tab_checks:
    st.header("Integrity and provenance checks")

    for name, value in validation.items():
        st.write(
            "**" + name.replace("_", " ").title() + ":**",
            value,
        )

    st.divider()
    st.write(
        "**Design source fingerprint:**",
        revision["source_sha256"]["design"],
    )
    st.write(
        "**Critic source fingerprint:**",
        revision["source_sha256"]["critique"],
    )

    st.caption(
        "Fingerprints detect changes to the recorded input files. "
        "They do not independently verify the scientific content."
    )

st.divider()
st.caption(
    "CuSelect-AI | LLM Research Cycle v1 | "
    "Read-only, untested scientific hypotheses"
)
