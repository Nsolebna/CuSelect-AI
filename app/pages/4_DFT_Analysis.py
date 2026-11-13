
"""Compact, evidence-aware CuSelect-AI validation workspace."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")

ROOT = Path(__file__).resolve().parents[2]
SRC = str(ROOT / "src")

if SRC not in sys.path:
    sys.path.insert(0, SRC)

from components.header import render_header
from cuselect.benchmark_registry import load_benchmarks
from cuselect.catalyst_comparison import compare_existing_candidates
from cuselect.research_cases import (
    get_case,
    save_validation_assessment,
)

render_header()

st.title("Validate research")
st.caption(
    "Assess scientific evidence, identify uncertainties, "
    "and prepare your next research decision."
)

kind = st.radio(
    "Validation type",
    ["Experimental evidence", "Computational results"],
    horizontal=True,
)


if st.button("Open Evidence Library", key="open_evidence_library"):
    st.switch_page("pages/5_Evidence_Explorer.py")



if kind == "Computational results":
    from cuselect.computational_summary_ui import render_computational_summary
    render_computational_summary(ROOT)

else:
    registry = load_benchmarks(ROOT)
    records = registry["records"]

    if not records:
        st.info("No provisional benchmarks are available.")
    else:
        options = {
            (
                f"{r['catalyst']} · {r['product']} · "
                f"{r['benchmark_id']}"
            ): r
            for r in records
        }

        selection = st.selectbox(
            "Research candidate",
            list(options),
        )

        record = options[selection]
        benchmark_id = record["benchmark_id"]

        try:
            case = get_case(ROOT, benchmark_id)
            case_error = None
        except (OSError, ValueError) as exc:
            case = None
            case_error = str(exc)

        if case_error:
            st.error("Research-case registry could not be read.")
            with st.expander("Technical details"):
                st.code(case_error)
        elif case:
            st.caption(
                f"Research case: {case['case_id']} "
                f"· Evidence: {case.get('review_status', 'provisional')} "
                f"· Validation: "
                f"{case.get('validation_status', 'not_assessed')}"
            )
        else:
            st.warning(
                "This benchmark has no research case yet. "
                "Create one in Evidence before saving."
            )

        fe = record.get("faradaic_efficiency_percent")
        potential = record.get("potential_V_vs_RHE")
        cell = record.get("cell_configuration")
        electrolyte = record.get("electrolyte")
        density_type = str(
            record.get("current_density_type") or ""
        ).strip().lower()

        fe_display = (
            f"{fe:g}%" if isinstance(fe, (int, float))
            else "Not reported"
        )
        potential_display = (
            f"{potential:g} V" if isinstance(
                potential, (int, float)
            ) else "Not reported"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Reported ethylene FE", fe_display)

        with col2:
            st.metric("Potential vs RHE", potential_display)

        with col3:
            st.metric("Cell configuration", cell or "Unknown")

        missing = []

        if not electrolyte:
            missing.append("Electrolyte composition")

        if density_type in {"", "unknown", "unresolved"}:
            missing.append("Current-density definition")

        missing.append(
            "Human verification of the reported measurement "
            "and experimental conditions"
        )

        recommendation = (
            "Check the primary publication and supplementary "
            "information, resolve the missing experimental "
            "conditions, and assess comparability before "
            "ranking this catalyst."
        )

        assessment_tab, compare_tab, source_tab = st.tabs([
            "Assessment", "Compare", "Source details"
        ])

        with assessment_tab:
            st.subheader("Scientific assessment")

            st.write(
                f"**Reported observation:** {record['catalyst']} "
                f"has a source-traceable report of "
                f"{fe_display} {record['product']} FE."
            )

            st.markdown("**What needs verification**")
            for item in missing:
                st.write("• " + item)

            st.markdown("**Recommended next action**")
            st.write(recommendation)

            st.warning(
                "This remains provisional evidence. "
                "The current records do not justify "
                "a catalyst-performance ranking."
            )

            st.divider()

            if case_error:
                st.error("Saving is unavailable until the registry is fixed.")
            elif case is None:
                st.info(
                    "Create a research case in Evidence "
                    "to enable saving."
                )
            else:
                existing = case.get("validation_assessment")
                if existing:
                    st.caption(
                        "Previously saved: "
                        + str(existing.get("saved_at", "Unknown"))
                    )

                if st.button(
                    "Save assessment to research case",
                    type="primary",
                    key=f"save_{benchmark_id}",
                ):
                    assessment = {
                        "assessment_type": "automated_evidence_check",
                        "benchmark_id": benchmark_id,
                        "catalyst": record.get("catalyst"),
                        "product": record.get("product"),
                        "source_doi": record.get("doi"),
                        "reported_fe_percent": fe,
                        "source_verification_status": record.get(
                            "verification_status", "provisional"
                        ),
                        "missing_fields": missing,
                        "ranking_allowed": False,
                        "recommendation": recommendation,
                    }

                    try:
                        saved = save_validation_assessment(
                            ROOT, benchmark_id, assessment
                        )
                    except (OSError, ValueError, TypeError) as exc:
                        st.error("The assessment could not be saved.")
                        with st.expander("Technical details"):
                            st.code(str(exc))
                    else:
                        st.success(
                            "Assessment saved to "
                            + saved["case_id"]
                        )
                        st.caption(
                            "Status: automated_assessed. "
                            "Human scientific approval was not granted."
                        )

        with compare_tab:
            st.subheader("Published ethylene evidence")

            try:
                comparison = compare_existing_candidates(ROOT)
            except (OSError, ValueError, KeyError) as exc:
                st.error("Comparison data could not be loaded.")
                with st.expander("Technical details"):
                    st.code(str(exc))
            else:
                rows = []

                for candidate in comparison["records"]:
                    value = candidate.get("fe_percent")
                    qualifier = candidate.get("fe_qualifier")

                    if value is None:
                        fe_label = "Not reported"
                    elif qualifier == "nearly":
                        fe_label = f"Nearly {value:g}%"
                    else:
                        fe_label = f"{value:g}%"

                    status = candidate.get("evidence_status")
                    if status == "approved":
                        status = "FE reviewed"
                    elif status == "provisional":
                        status = "Provisional"

                    rows.append({
                        "Catalyst / publication": str(
                            candidate.get("catalyst") or ""
                        ).replace(
                            "<sub>", ""
                        ).replace("</sub>", ""),
                        "Ethylene FE": fe_label,
                        "Evidence": status,
                        "Conditions verified": candidate.get(
                            "conditions_verified", False
                        ),
                        "DOI": candidate.get("doi"),
                    })

                st.dataframe(
                    pd.DataFrame(rows),
                    width="stretch",
                    hide_index=True,
                )

                st.warning(comparison["conclusion"])

                with st.expander("Comparison limitations"):
                    for candidate in comparison["records"]:
                        st.markdown(
                            "**" + str(candidate.get("doi")) + "**"
                        )
                        for issue in candidate.get("issues", []):
                            st.write("• " + issue)

        with source_tab:
            st.subheader("Source and experimental conditions")

            st.write("**DOI:**", record.get("doi"))
            st.write(
                "**Cell:**",
                cell or "Not confirmed",
            )
            st.write(
                "**Electrolyte:**",
                electrolyte or "Not confirmed",
            )
            st.write(
                "**Current-density definition:**",
                density_type or "Unresolved",
            )

            current = record.get(
                "reported_current_density_mA_cm2"
            )
            st.write(
                "**Reported current density:**",
                (
                    f"{current:g} mA cm⁻²"
                    if isinstance(current, (int, float))
                    else "Not reported"
                ),
            )

            st.markdown("**Publication excerpt**")
            st.write(
                record.get("source_excerpt")
                or "No excerpt available."
            )

            st.caption(
                "The source excerpt is not a substitute "
                "for independent experimental verification."
            )

            with st.expander("Original benchmark JSON"):
                st.json(record)

    if registry["errors"]:
        with st.expander("Benchmark registry warnings"):
            st.json(registry["errors"])
