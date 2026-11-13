"""Read-only CuSelect-AI multi-agent research cycle interface."""

# PSEUDOCODE
# 1. Load existing saved scientific records.
# 2. Validate evidence, finding coverage, and source fingerprints.
# 3. Display structured research information instead of raw JSON.
# 4. Connect each Critic finding to its revision response.
# 5. Display experiments and remaining uncertainties.
# 6. Keep complete original records available for auditing.
# 7. Never modify research records or invoke AI models.

import json
from pathlib import Path

import streamlit as st

from cuselect.agents.llm_cycle_validation import validate_cycle


def load_research_cycle(root, version="v2"):
    directory = Path(root) / "data/agent_runs"

    if version not in ("v2", "v3"):
        raise ValueError("Unsupported research cycle version.")

    paths = {
        "evidence": directory / "literature_evidence_v1.json",
        "design": directory / "llm_design_proposals_v2.json",
        "critic": directory / (
            "llm_scientific_critique_with_dft_v3.json"
            if version == "v3" else "llm_scientific_critique_v2.json"
        ),
        "revision": directory / (
            "llm_revised_candidate_with_dft_v3.json"
            if version == "v3" else "llm_revised_candidate_v2.json"
        ),
    }

    records = {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, path in paths.items()
    }

    report = validate_cycle(
        records["evidence"],
        records["design"],
        records["critic"],
        records["revision"],
        file_paths={
            "design": paths["design"],
            "critic": paths["critic"],
        },
    )

    return records, report


def show_items(items):
    """Render scientific lists without exposing raw JSON."""
    if not items:
        st.caption("No information recorded.")
        return

    for item in items:
        if isinstance(item, str):
            st.markdown(f"- {item}")
        elif isinstance(item, dict):
            show_fields(item)
        else:
            st.write(item)


def show_fields(data, exclude=()):
    """Display a record as labeled scientific fields."""
    for key, value in data.items():
        if key in exclude or value in (None, "", [], {}):
            continue

        label = key.replace("_", " ").capitalize()
        st.markdown(f"**{label}**")

        if isinstance(value, list):
            show_items(value)
        elif isinstance(value, dict):
            show_fields(value)
        else:
            st.write(value)


def show_decision(disposition):
    names = {
        "advance_to_experimental_planning":
            "Advance to experimental planning",
        "revise_before_advancing":
            "Revise before advancing",
        "reject_current_hypothesis":
            "Reject current hypothesis",
    }

    label = names.get(disposition, disposition)

    if disposition == "revise_before_advancing":
        st.warning(label)
    elif disposition == "reject_current_hypothesis":
        st.error(label)
    elif disposition == "advance_to_experimental_planning":
        st.success(label)
    else:
        st.info(label)


def render_research_cycle(root):
    st.title("AI Research Cycle")
    st.caption(
        "Evidence → Design → Scientific Critic → Revision"
    )

    version = st.radio(
        "Research cycle",
        options=["v3", "v2"],
        format_func=lambda value: (
            "Evidence-aware v3" if value == "v3"
            else "Historical v2"
        ),
        horizontal=True,
    )

    try:
        records, report = load_research_cycle(root, version=version)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        st.error(
            "Research cycle verification failed: "
            f"{type(exc).__name__}"
        )
        return

    proposal = records["design"]["proposal"]
    critic_record = records["critic"]
    critique = critic_record["critique"]
    revision_record = records["revision"]
    revision = revision_record["revision"]

    provenance = critic_record.get(
        "instruction_provenance"
    )

    st.caption(
        "EVIDENCE-AWARE RESEARCH CASE — PRELIMINARY COMPUTATIONAL EVIDENCE"
        if version == "v3" else "HISTORICAL RESEARCH CASE"
    )
    st.header(proposal["candidate_name"])

    st.caption(
        "Ag/Cu catalyst | CO₂-to-ethylene conversion | "
        "Human scientific review pending"
    )

    if provenance is None:
        st.warning(
            "Historical Critic report: evaluated-v2 instruction "
            "provenance was not recorded."
        )
    else:
        st.caption(
            "Critic instruction version: "
            + str(provenance.get("version", "unknown"))
        )

    decision, summary = st.columns([2, 1])
    with decision:
        show_decision(critique.get("recommended_disposition", "not_recorded"))
        with st.expander("Decision rationale"):
            st.write(critique.get("disposition_reason", "No decision reasoning recorded."))
    with summary:
        st.write(
            f"**{report['scientific_findings']}** findings · "
            f"**{report['findings_responded_to']}** responses · "
            f"**{report['revised_experiments']}** proposed experiments"
        )
        st.caption("A recorded response does not establish that a finding was resolved.")

    tabs = st.tabs([
        "Catalyst Design",
        "Scientific Critic",
        "Candidate Revision",
        "Research Audit",
    ])

    # TAB 1 — CATALYST DESIGN
    with tabs[0]:
        st.subheader("Original catalyst proposal")

        left, right = st.columns(2, gap="large")

        with left:
            with st.container(border=True):
                st.markdown("**Catalyst architecture**")
                st.write(
                    proposal.get(
                        "catalyst_architecture",
                        "Not recorded.",
                    )
                )
                st.markdown("**Design modification**")
                st.write(
                    proposal.get(
                        "design_modification",
                        "Not recorded.",
                    )
                )

            with st.container(border=True):
                st.markdown("**Major uncertainties**")
                show_items(
                    proposal.get("major_uncertainties", [])
                )

        with right:
            with st.container(border=True):
                st.markdown("**Scientific hypothesis**")
                st.write(
                    proposal.get(
                        "scientific_hypothesis",
                        "Not recorded.",
                    )
                )

                st.markdown("**Mechanistic rationale**")
                st.write(
                    proposal.get(
                        "mechanistic_rationale",
                        "Not recorded.",
                    )
                )

            with st.container(border=True):
                st.markdown("**Supporting literature**")

                for item in proposal.get(
                    "supporting_evidence", []
                ):
                    doi = item.get("doi", "")
                    st.write("**DOI:**", doi)
                    st.write(
                        item.get(
                            "relevance",
                            "No relevance recorded.",
                        )
                    )

                    if doi.startswith("10."):
                        st.link_button(
                            "Open publication",
                            "https://doi.org/" + doi,
                        )

        with st.expander("Original proposed experiment"):
            st.write(
                proposal.get(
                    "proposed_experiment",
                    "Not recorded.",
                )
            )
            st.markdown("**Discriminating control**")
            st.write(
                proposal.get(
                    "discriminating_control",
                    "Not recorded.",
                )
            )


    # EVIDENCE-AWARE V3 — COMPUTATIONAL EVIDENCE
    if version == "v3":
        st.divider()
        st.subheader("Computational evidence — preliminary")

        registry_path = (
            Path(root)
            / "data/processed/16_computational_registry"
            / "computational_evidence_v1.json"
        )

        if not registry_path.is_file():
            st.warning("Computational evidence registry unavailable.")
        else:
            registry = json.loads(
                registry_path.read_text(encoding="utf-8")
            )

            st.caption(
                "Ag₂Cu₃₄/Cu(100), adjacent versus separated Ag. "
                "Negative SEP − NN energies favor separated Ag "
                "within the tested clean-slab model."
            )

            comparisons = registry.get("comparisons", [])
            rows = [
                {
                    "Method": item.get("method"),
                    "Geometry": item.get("geometry"),
                    "SEP − NN (eV)": item.get(
                        "delta_sep_minus_nn_ev"
                    ),
                    "Evidence status": item.get("evidence_status"),
                }
                for item in comparisons
            ]

            st.dataframe(
                rows,
                width="stretch",
                hide_index=True,
            )

            with st.expander("Scientific limitations"):
                for limitation in registry.get(
                    "scientific_limitations", []
                ):
                    st.write("•", limitation)

            st.warning(
                "These clean-slab calculations do not predict "
                "ethylene selectivity or Faradaic efficiency. "
                "DFT convergence and human scientific review "
                "remain incomplete."
            )

    # TAB 2 — SCIENTIFIC CRITIC
    with tabs[1]:
        st.subheader("Scientific Critic assessment")

        with st.container(border=True):
            st.markdown(
                "**Most serious scientific risk**"
            )
            st.write(
                critique.get(
                    "most_serious_scientific_risk",
                    "Not recorded.",
                )
            )

        st.markdown("#### Scientific findings")

        findings = critique.get(
            "scientific_findings", []
        )

        responses = {
            item.get("finding_number"): item
            for item in revision.get(
                "finding_responses", []
            )
        }

        for number, finding in enumerate(
            findings, start=1
        ):
            title = finding.get(
                "finding", f"Finding {number}"
            )

            with st.expander(
                f"{number}. {title}"
            ):
                st.markdown("**Scientific reasoning**")
                st.write(
                    finding.get(
                        "reasoning", "Not recorded."
                    )
                )

                st.markdown("**Recommended action**")
                st.write(
                    finding.get(
                        "recommended_action",
                        "Not recorded.",
                    )
                )

                response = responses.get(number)

                if response:
                    st.divider()
                    st.markdown(
                        "**Revision Agent response**"
                    )
                    st.write(
                        response.get(
                            "revision_action",
                            "Not recorded.",
                        )
                    )
                    st.caption(
                        "Resolution: "
                        + str(
                            response.get(
                                "resolution_status",
                                "unknown",
                            )
                        )
                    )

                    uncertainty = response.get(
                        "remaining_uncertainty"
                    )
                    if uncertainty:
                        st.markdown(
                            "**Remaining uncertainty**"
                        )
                        st.write(uncertainty)
                else:
                    st.warning(
                        "No matching revision response."
                    )

        st.markdown("#### Critical experiments")

        for index, experiment in enumerate(
            critique.get(
                "critical_experiments", []
            ),
            start=1,
        ):
            name = (
                experiment.get("experiment_name")
                or experiment.get("name")
                or f"Experiment {index}"
            )

            with st.expander(str(name)):
                show_fields(experiment, exclude=(
                    "experiment_name", "name"
                ))

    # TAB 3 — CANDIDATE REVISION
    with tabs[2]:
        st.subheader("Revised research proposal")

        st.write(
            "**Revised candidate:**",
            revision.get(
                "candidate_name", "Not recorded."
            )
        )

        st.markdown("#### Responses to Critic findings")

        for item in revision.get(
            "finding_responses", []
        ):
            number = item.get(
                "finding_number", "?"
            )

            with st.expander(
                f"Finding {number} — "
                + str(
                    item.get(
                        "resolution_status",
                        "Resolution pending",
                    )
                )
            ):
                show_fields(
                    item,
                    exclude=(
                        "finding_number",
                        "resolution_status",
                    ),
                )

        st.markdown("#### Revised experimental plan")

        for index, experiment in enumerate(
            revision.get(
                "controlled_experiments", []
            ),
            start=1,
        ):
            name = (
                experiment.get("name")
                or experiment.get("experiment_name")
                or f"Experiment {index}"
            )

            with st.expander(str(name)):
                show_fields(
                    experiment,
                    exclude=("name", "experiment_name"),
                )

        with st.container(border=True):
            st.markdown("**Next research decision gate**")
            st.write(
                revision.get(
                    "next_decision_gate",
                    "Not recorded.",
                )
            )

    # TAB 4 — SCIENTIFIC AUDIT
    with tabs[3]:
        st.subheader("Scientific integrity and audit")

        st.warning(
            "This is an AI-assisted historical research cycle. "
            "Human review is required. Catalyst performance "
            "has not been independently validated."
        )

        st.write(
            "**Evidence identity:**",
            report["evidence_identity_checks"],
        )
        st.write(
            "**Critic coverage:**",
            report["critic_coverage"],
        )
        st.write(
            "**File provenance:**",
            report["provenance_checks"],
        )
        st.write(
            "**FE prediction safeguard:**",
            report["fe_prediction_checks"],
        )

        st.write(
            "**Scientific truth verified:**",
            report["scientific_truth_verified"],
        )

        st.markdown("#### Download scientific audit records")

        st.download_button(
            "Download validation report",
            data=json.dumps(report, indent=2),
            file_name="cuselect_validation_report.json",
            mime="application/json",
        )

        st.download_button(
            "Download complete research records",
            data=json.dumps(records, indent=2),
            file_name="cuselect_research_records.json",
            mime="application/json",
        )

        provenance_data = {
            "critic_instructions": provenance,
            "revision_source_sha256":
                revision_record.get("source_sha256"),
        }

        st.download_button(
            "Download provenance report",
            data=json.dumps(provenance_data, indent=2),
            file_name="cuselect_provenance.json",
            mime="application/json",
        )

    st.divider()
    st.caption(
        "Read-only scientific research replay. "
        "No API requests or new predictions are "
        "generated by this interface."
    )
