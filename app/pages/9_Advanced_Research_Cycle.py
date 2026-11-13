"""CuSelect-AI — integrated, read-only research dashboard."""

# PSEUDOCODE
# 1. Load the saved research records.
# 2. Display the original proposal and revised hypothesis.
# 3. Show literature and computational evidence separately.
# 4. Link every critic finding to the corresponding revision.
# 5. Present experiments, falsification criteria and decision gate.
# 6. Display provenance and scientific limitations.
# 7. Never trigger an LLM or DFT calculation.

import hashlib
import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "data" / "agent_runs"
PROCESSED = ROOT / "data" / "processed"

FILES = {
    "Original proposal": RUNS / "llm_design_proposals_v2.json",
    "Literature": RUNS / "literature_evidence_v1.json",
    "Original critique": RUNS / "llm_scientific_critique_v2.json",
    "Evidence-aware critique": (
        RUNS / "llm_scientific_critique_with_dft_v3.json"
    ),
    "Original revision": RUNS / "llm_revised_candidate_v2.json",
    "Evidence-aware revision": (
        RUNS / "llm_revised_candidate_with_dft_v3.json"
    ),
    "Computational context": (
        PROCESSED / "18_agent_evidence_context"
        / "agent_evidence_context_v1.json"
    ),
    "Computational registry": (
        PROCESSED / "16_computational_registry"
        / "computational_evidence_v1.json"
    ),
    "Computational critique": (
        PROCESSED / "17_computational_critique"
        / "scientific_critique_v1.json"
    ),
}


@st.cache_data(show_spinner=False)
def read_json(path_string, modification_time):
    """Reload a record when its modification time changes."""
    del modification_time
    with Path(path_string).open(encoding="utf-8") as file:
        return json.load(file)


def load_records():
    missing = [name for name, path in FILES.items()
               if not path.is_file()]

    if missing:
        st.error(
            "Missing required research files: " + ", ".join(missing)
        )
        st.stop()

    return {
        name: read_json(str(path), path.stat().st_mtime_ns)
        for name, path in FILES.items()
    }


def display_value(value):
    """Display text, lists or dictionaries without assuming a schema."""
    if isinstance(value, str):
        st.write(value)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (str, int, float)):
                st.markdown(f"- {item}")
            else:
                st.json(item)
    elif isinstance(value, dict):
        st.json(value)
    else:
        st.write(value)


st.set_page_config(
    page_title="CuSelect-AI | Research Cycle",
    page_icon="🧪",
    layout="wide",
)

st.title("CuSelect-AI")
st.subheader("Evidence-Aware Research Cycle")

st.caption(
    "Research prototype | Saved scientific records | "
    "No live LLM or DFT execution"
)

data = load_records()

design_record = data["Original proposal"]
literature_record = data["Literature"]
critic_record = data["Evidence-aware critique"]
revision_record = data["Evidence-aware revision"]
context = data["Computational context"]

proposal = design_record["proposal"]
critique = critic_record["critique"]
revision = revision_record["revision"]

findings = critique.get("scientific_findings", [])
responses = revision.get("finding_responses", [])
experiments = revision.get("controlled_experiments", [])

if critic_record.get("candidate_name") != proposal.get(
    "candidate_name"
):
    st.error("Candidate mismatch between design and critique.")
    st.stop()

if revision.get("original_candidate_name") != proposal.get(
    "candidate_name"
):
    st.error("Candidate mismatch between design and revision.")
    st.stop()

if revision_record.get("scientific_validation") != (
    "pending_human_review"
):
    st.warning("Unexpected scientific validation status.")

st.warning(
    "Scientific status: untested revised hypothesis. "
    "The DFT results are preliminary clean-slab calculations. "
    "No ethylene Faradaic efficiency is predicted."
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Scientific findings", len(findings))
c2.metric("Revision responses", len(responses))
c3.metric("Controlled experiments", len(experiments))
c4.metric(
    "Research status",
    "Pending review",
)

st.markdown("### Research workflow")

stages = [
    "1. Design",
    "2. Evidence",
    "3. Critique",
    "4. Revision",
    "5. Decision",
]

for column, stage in zip(st.columns(5), stages):
    with column:
        st.container(border=True).markdown(
            f"**{stage}**"
        )

st.divider()

tabs = st.tabs([
    "Research Overview",
    "Scientific Evidence",
    "Critic → Revision",
    "Experiments",
    "Provenance",
])

with tabs[0]:
    st.header("From Catalyst Hypothesis to Revised Design")

    left, right = st.columns(2)

    with left:
        st.markdown("### Original proposal")
        st.write(
            "**Candidate:**",
            proposal.get("candidate_name", "Unknown"),
        )
        st.markdown("**Catalyst architecture**")
        display_value(
            proposal.get("catalyst_architecture", "Not specified")
        )

        st.markdown("**Design modification**")
        display_value(
            proposal.get("design_modification", "Not specified")
        )

        st.markdown("**Scientific hypothesis**")
        display_value(
            proposal.get("scientific_hypothesis", "Not specified")
        )

        with st.expander("Mechanistic rationale"):
            display_value(
                proposal.get("mechanistic_rationale")
            )

        with st.expander("Supporting literature"):
            display_value(
                proposal.get("supporting_evidence", [])
            )

        with st.expander("Alternative explanations"):
            display_value(
                proposal.get("alternative_explanations", [])
            )

        with st.expander("Proposed experiment and controls"):
            st.markdown("**Proposed experiment**")
            display_value(
                proposal.get("proposed_experiment")
            )
            st.markdown("**Discriminating control**")
            display_value(
                proposal.get("discriminating_control")
            )

        with st.expander("Full original proposal — JSON"):
            st.json(proposal)

    with right:
        st.markdown("### Evidence-aware revision")
        st.write(
            "**Revised candidate:**",
            revision.get("candidate_name", "Unknown"),
        )
        st.write("**Architecture**")
        display_value(revision.get("revised_architecture"))
        st.write("**Hypothesis**")
        display_value(revision.get("revised_hypothesis"))
        st.write("**Mechanistic claim status**")
        display_value(
            revision.get("mechanistic_claim_status")
        )

    st.markdown("### Revision summary")
    display_value(
        revision.get("concise_revision_summary")
    )

    st.markdown("### Research decision")
    st.write(
        "**Critic recommendation:**",
        critique.get("recommended_disposition"),
    )
    display_value(critique.get("disposition_reason"))

with tabs[1]:
    st.header("Scientific Evidence")

    st.markdown("### Experimental literature")
    st.caption(
        "Source excerpts and measurements; "
        "not independently reverified by this dashboard."
    )

    evidence = literature_record.get("evidence", [])

    st.write("Saved literature measurements:", len(evidence))

    for index, item in enumerate(evidence, start=1):
        with st.expander(
            f"Literature record {index}: "
            f"{item.get('measurement_id', 'Unspecified')}"
        ):
            st.json(item)

    st.divider()

    st.markdown("### Computational evidence")

    reference = context.get("reference", {})

    st.write(
        "**System:**",
        context.get("system", "Not specified"),
    )
    st.write(
        "**Reference method:**",
        reference.get("method", "Not specified"),
    )
    st.write(
        "**DFT status:**",
        reference.get("status", "Not specified"),
    )

    energy = reference.get("delta_sep_minus_nn_mev")

    if isinstance(energy, (int, float)):
        st.metric(
            "DFT ΔE (SEP − NN)",
            f"{energy:.3f} meV",
        )
    else:
        st.write("DFT energy difference:", energy)

    st.caption(
        "Negative ΔE indicates lower calculated energy "
        "for separated Ag in this specific model. "
        "It does not establish CO₂RR activity, CO transfer, "
        "or ethylene selectivity."
    )


    # PSEUDOCODE
    # 1. Select matched-geometry model comparisons.
    # 2. Visualize SEP-NN energy differences in meV.
    # 3. Plot DFT k-point sensitivity at fixed 350 eV.
    # 4. Report the separate gamma-point cutoff comparison.
    # 5. Label all results preliminary and non-predictive.

    import pandas as pd

    comparisons = data["Computational registry"].get(
        "comparisons", []
    )

    st.markdown("### Method comparison — matched geometry")
    st.caption(
        "All three calculations below evaluate MACE-relaxed "
        "Ag2Cu34/Cu(100) geometries. Negative ΔE (SEP − NN) "
        "means the separated Ag configuration has lower energy."
    )

    model_rows = []

    for method in ("EMT", "MACE-MP-0-small"):
        matches = [
            item for item in comparisons
            if item.get("method") == method
            and item.get("geometry") == "MACE-relaxed"
            and item.get("evidence_status") == "model_comparison"
        ]

        if len(matches) == 1:
            model_rows.append({
                "Method": method,
                "ΔE (meV)": (
                    1000 * matches[0][
                        "delta_sep_minus_nn_ev"
                    ]
                ),
            })

    dft_matches = [
        item for item in comparisons
        if item.get("method") == "GPAW-PBE"
        and item.get("geometry") == "MACE-relaxed"
        and item.get("run_id") == "350ev_6x6x1"
    ]

    if len(dft_matches) == 1:
        model_rows.append({
            "Method": "GPAW-PBE (350 eV, 6×6×1)",
            "ΔE (meV)": (
                1000 * dft_matches[0][
                    "delta_sep_minus_nn_ev"
                ]
            ),
        })

    if len(model_rows) == 3:
        model_df = pd.DataFrame(model_rows)

        st.bar_chart(
            model_df.set_index("Method"),
            y="ΔE (meV)",
        )

        st.dataframe(
            model_df.style.format({"ΔE (meV)": "{:.3f}"}),
            hide_index=True,
            width="stretch",
        )
    else:
        st.warning(
            "Some matched-geometry comparisons are missing "
            "or ambiguous. Chart not displayed."
        )

    st.info(
        "Method agreement on energy ordering is not proof "
        "of catalytic activity. EMT and MACE are approximate "
        "potentials, while the GPAW-PBE result is preliminary "
        "and uses geometries not optimized with DFT."
    )

    st.divider()

    st.markdown("### DFT k-point sampling sensitivity")
    st.caption(
        "GPAW-PBE | 350 eV cutoff | MACE-relaxed geometries. "
        "Only k-point sampling changes in this comparison."
    )

    kpoint_runs = [
        ("350ev_gamma", "Γ"),
        ("350ev_2x2x1", "2×2×1"),
        ("350ev_4x4x1", "4×4×1"),
        ("350ev_6x6x1", "6×6×1"),
    ]

    kpoint_rows = []

    for run_id, label in kpoint_runs:
        matches = [
            item for item in comparisons
            if item.get("method") == "GPAW-PBE"
            and item.get("run_id") == run_id
            and item.get("cutoff_ev") == 350
        ]

        if len(matches) == 1:
            kpoint_rows.append({
                "k-point grid": label,
                "ΔE (meV)": (
                    1000 * matches[0][
                        "delta_sep_minus_nn_ev"
                    ]
                ),
            })

    if len(kpoint_rows) == 4:
        kpoint_df = pd.DataFrame(kpoint_rows)

        # PSEUDOCODE
        # Preserve the physical k-point sampling sequence.
        # Do not let alphabetical sorting reorder Gamma.
        import altair as alt

        chart = (
            alt.Chart(kpoint_df)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "k-point grid:N",
                    sort=[
                        "Γ",
                        "2×2×1",
                        "4×4×1",
                        "6×6×1",
                    ],
                    title="k-point sampling",
                ),
                y=alt.Y(
                    "ΔE (meV):Q",
                    title="ΔE (SEP − NN), meV",
                    scale=alt.Scale(zero=False),
                ),
                tooltip=[
                    alt.Tooltip("k-point grid:N"),
                    alt.Tooltip(
                        "ΔE (meV):Q",
                        format=".3f",
                    ),
                ],
            )
        )

        st.altair_chart(
            chart,
            width="stretch",
        )

        st.dataframe(
            kpoint_df.style.format(
                {"ΔE (meV)": "{:.3f}"}
            ),
            hide_index=True,
            width="stretch",
        )

        latest_change = abs(
            kpoint_rows[-1]["ΔE (meV)"]
            - kpoint_rows[-2]["ΔE (meV)"]
        )

        st.metric(
            "Difference: 4×4×1 versus 6×6×1",
            f"{latest_change:.3f} meV",
        )
    else:
        st.warning(
            "Complete 350 eV k-point series unavailable."
        )

    st.markdown("### Separate cutoff sensitivity check")

    cutoff_rows = []

    for run_id in ("250ev_gamma", "350ev_gamma"):
        matches = [
            item for item in comparisons
            if item.get("method") == "GPAW-PBE"
            and item.get("run_id") == run_id
        ]

        if len(matches) == 1:
            item = matches[0]
            cutoff_rows.append({
                "Cutoff (eV)": item["cutoff_ev"],
                "Grid": "Γ",
                "ΔE (meV)": (
                    1000 * item["delta_sep_minus_nn_ev"]
                ),
            })

    if len(cutoff_rows) == 2:
        cutoff_df = pd.DataFrame(cutoff_rows)
        st.dataframe(
            cutoff_df.style.format(
                {"ΔE (meV)": "{:.3f}"}
            ),
            hide_index=True,
            width="stretch",
        )

        cutoff_change = abs(
            cutoff_rows[1]["ΔE (meV)"]
            - cutoff_rows[0]["ΔE (meV)"]
        )

        st.caption(
            "Gamma-point 250 → 350 eV cutoff change: "
            f"{cutoff_change:.3f} meV."
        )

    st.warning(
        "Convergence is not established. These results "
        "exclude explicit electrolyte, electrode potential, "
        "adsorbates and reaction pathways. No ethylene "
        "Faradaic efficiency or CO-transfer rate is predicted."
    )

    with st.expander("Complete computational context"):
        st.json(context)

    with st.expander("Computational model comparisons"):
        st.json(data["Computational registry"])

    with st.expander("Computational scientific critique"):
        st.json(data["Computational critique"])

with tabs[2]:
    st.header("Scientific Findings and Revision Actions")

    st.caption(
        "Each numbered response should address the matching "
        "finding from the evidence-aware Scientific Critic."
    )

    response_map = {
        item.get("finding_number"): item
        for item in responses
    }

    for number, finding in enumerate(findings, start=1):
        response = response_map.get(number)

        with st.expander(
            f"Finding {number}: "
            f"{finding.get('category', 'Unclassified')}",
            expanded=(number == 1),
        ):
            st.write(
                "**Critic assessment:**",
                finding.get("assessment"),
            )
            display_value(finding.get("finding"))

            st.write("**Scientific reasoning:**")
            display_value(finding.get("reasoning"))

            if response:
                st.divider()
                st.write("**Revision action:**")
                display_value(
                    response.get("revision_action")
                )
                st.write("**Resolution status:**")
                display_value(
                    response.get("resolution_status")
                )
                st.write("**Remaining uncertainty:**")
                display_value(
                    response.get("remaining_uncertainty")
                )
            else:
                st.error(
                    f"No revision response for finding {number}."
                )

    st.markdown("### Unresolved questions")
    display_value(revision.get("unresolved_questions", []))

with tabs[3]:
    st.header("Controlled Experiments")

    for index, experiment in enumerate(experiments, start=1):
        with st.expander(
            f"Experiment {index}: "
            f"{experiment.get('name', 'Unnamed')}",
            expanded=(index == 1),
        ):
            fields = [
                ("Research question", "question"),
                ("Experimental groups", "experimental_groups"),
                ("Variables to control", "variables_to_control"),
                ("Measurements", "measurements"),
                (
                    "Outcome challenging the hypothesis",
                    "outcome_challenging_hypothesis",
                ),
                (
                    "Interpretation limitations",
                    "interpretation_limitations",
                ),
            ]

            for label, field in fields:
                st.markdown(f"**{label}**")
                display_value(experiment.get(field))

    st.divider()
    st.markdown("### Next Research Decision Gate")
    st.info(
        "The criteria below are LLM-proposed and require "
        "human scientific review before adoption."
    )

    display_value(revision.get("next_decision_gate"))

    st.markdown("### Design variables")
    for variable in revision.get("design_variables", []):
        with st.expander(
            variable.get("variable", "Design variable")
        ):
            st.json(variable)

with tabs[4]:
    st.header("Research Provenance")

    st.write(
        "**Scientific validation:**",
        revision_record.get("scientific_validation"),
    )
    st.write(
        "**Performance prediction available:**",
        revision_record.get(
            "performance_prediction_available"
        ),
    )

    st.markdown("### Input and output files")

    for name, path in FILES.items():
        digest = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

        st.markdown(f"**{name}**")
        st.code(str(path.relative_to(ROOT)))
        st.caption(f"SHA-256: {digest}")

    st.markdown("### Recorded agent provenance")
    st.json({
        "critique": critic_record.get(
            "computational_evidence_provenance"
        ),
        "revision": revision_record.get(
            "computational_evidence_provenance"
        ),
        "revision_sources": revision_record.get(
            "source_sha256"
        ),
    })

    st.caption(
        "File hashes are displayed for inspection. "
        "This page does not independently authenticate "
        "the scientific sources or validate every claim."
    )

st.divider()
st.caption(
    "CuSelect-AI | Evidence-aware catalyst research prototype | "
    "Human scientific review required"
)
