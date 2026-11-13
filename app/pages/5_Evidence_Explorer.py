
# CuSelect-AI — Evidence Explorer v1
#
# PSEUDOCODE
# 1. Load approved evidence without modifying source data.
# 2. Check measurement IDs and review statuses.
# 3. Filter the scientific evidence.
# 4. Display selected records and their provenance.
# 5. Keep FE approval separate from conditions verification.

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "approved_evidence.json"

st.set_page_config(
    page_title="CuSelect-AI Evidence Explorer",
    page_icon="🧪",
    layout="wide",
)

# Use the same navigation as Discover, Validate and Decide.
COMPONENTS = ROOT / "app"
if str(COMPONENTS) not in sys.path:
    sys.path.insert(0, str(COMPONENTS))

from components.header import render_header

render_header()

st.markdown("## Explore scientific evidence")
st.caption(
    "Search reviewed measurements and trace their scientific sources."
)

@st.cache_data
def load_records(path, modified_time):
    with open(path, encoding="utf-8") as file:
        return json.load(file)

if not DATA_PATH.exists():
    st.error(f"Evidence file not found: {DATA_PATH}")
    st.stop()

records = load_records(
    str(DATA_PATH),
    DATA_PATH.stat().st_mtime_ns,
)

if not isinstance(records, list):
    st.error("Expected a JSON list of evidence records.")
    st.stop()

if not records:
    st.warning("No evidence records available.")
    st.stop()

# Validate the basic data structure.
required = {
    "measurement_id",
    "doi",
    "product",
    "value",
    "unit",
    "review_status",
    "review",
    "conditions_verified",
}

for index, record in enumerate(records, start=1):
    if not isinstance(record, dict):
        st.error(f"Record {index} is not a JSON object.")
        st.stop()

    missing = required - record.keys()
    if missing:
        st.error(
            f"Record {index} is missing fields: {sorted(missing)}"
        )
        st.stop()

ids = [record["measurement_id"] for record in records]

if len(ids) != len(set(ids)):
    st.error("Duplicate measurement IDs detected.")
    st.stop()

for record in records:
    review = record["review"]
    if (
        record["review_status"] != "approved"
        or not isinstance(review, dict)
        or review.get("human_confirmed") is not True
    ):
        st.error(
            "The approved export contains an unapproved record."
        )
        st.stop()

    value = record["value"]
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not 0 <= value <= 100
        or record["unit"] != "%"
    ):
        st.error("Invalid Faradaic-efficiency measurement.")
        st.stop()


# SHARED RESEARCH CASES — CUSELECT INTEGRATION
st.subheader("Research cases")
st.caption(
    "Track candidates across the research workflow. "
    "Provisional cases are not approved evidence."
)

try:
    import sys

    src_dir = str(ROOT / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    from cuselect.research_cases import load_cases

    research_cases = load_cases(ROOT)

except Exception as exc:
    st.error("Unable to load research cases.")
    with st.expander("Technical details"):
        st.code(str(exc))
    research_cases = []

if research_cases:
    case_labels = [
        str(case.get("case_id", "Unknown case"))
        for case in research_cases
    ]

    selected_index = st.selectbox(
        "Select research case",
        range(len(research_cases)),
        format_func=lambda i: case_labels[i],
        key="evidence_selected_research_case",
    )

    selected_case = research_cases[selected_index]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Evidence status",
        str(selected_case.get("review_status", "unknown")).title(),
    )

    col2.metric(
        "Validation",
        str(
            selected_case.get(
                "validation_status", "not_assessed"
            )
        ).replace("_", " ").title(),
    )

    col3.metric(
        "Decision",
        str(
            selected_case.get(
                "decision_status", "not_assessed"
            )
        ).replace("_", " ").title(),
    )

    st.write(
        "**Candidate ID:**",
        selected_case.get("candidate_id", "Unknown"),
    )

    st.info(
        "This research case is a reference to an existing "
        "candidate. Its status does not change the approval "
        "of any scientific measurement."
    )

    with st.expander("Research-case provenance"):
        st.json(selected_case)

    st.page_link(
        "pages/4_DFT_Analysis.py",
        label="Open Validate",
    )

    st.page_link(
        "pages/3_Research_Cycle_Dashboard.py",
        label="Open Decide",
    )

    st.caption(
        "Candidate selection is not transferred automatically "
        "to Validate or Decide yet."
    )

else:
    st.info(
        "No research cases registered yet. "
        "Approved evidence remains available below."
    )

st.divider()

# Summary metrics
m1, m2, m3, m4 = st.columns(4)

m1.metric("Approved measurements", len(records))
m2.metric("Publications", len({r["doi"] for r in records}))
m3.metric(
    "Verified conditions",
    sum(r["conditions_verified"] is True for r in records),
)
m4.metric(
    "Products / classes",
    len({r["product"] for r in records}),
)

st.warning(
    "FE measurements have been human-reviewed. "
    "Experimental operating conditions must be independently verified."
)

st.divider()

# Filters
st.header("Explore measurements")

products = sorted({r["product"] for r in records})

selected_products = st.multiselect(
    "Filter by product",
    products,
    default=products,
)

filtered = [
    r for r in records
    if r["product"] in selected_products
]

display_rows = []

for record in filtered:
    display_rows.append({
        "ID": record["measurement_id"],
        "DOI": record["doi"],
        "Product": record["product"],
        "FE (%)": record["value"],
        "Qualifier": record.get("qualifier") or "exact reported",
        "FE review": record["review_status"],
        "Conditions verified": record["conditions_verified"],
    })

st.dataframe(
    pd.DataFrame(display_rows),
    hide_index=True,
    width="stretch",
)

st.divider()

# Record details
st.header("Scientific record details")

if not filtered:
    st.info("No measurements match your filters.")
    st.stop()

options = {
    (
        f'{r["product"]} | {r["value"]}% | '
        f'{r["doi"]} | {r["measurement_id"][:8]}'
    ): r
    for r in filtered
}

selected_label = st.selectbox(
    "Select a measurement",
    options=list(options),
)

record = options[selected_label]
review = record["review"]

st.markdown(f"**Publication DOI:** `{record['doi']}`")
st.markdown(f"**Product:** {record['product']}")
st.markdown(
    f"**FE:** {record['value']} {record['unit']}"
)
st.markdown(
    f"**Qualifier:** {record.get('qualifier') or 'not specified'}"
)

st.link_button(
    "Open publication",
    f"https://doi.org/{record['doi']}",
)

with st.expander("Evidence provenance", expanded=True):
    st.write("Source:", record.get("source_provider"))
    st.write("Source type:", record.get("source_type"))
    st.write(
        "Original extracted text:",
        record.get("exact_source_text"),
    )
    st.write(
        "Reviewed figure / table:",
        review.get("source_location"),
    )
    st.write(
        "Supporting evidence:",
        review.get("supporting_excerpt"),
    )

with st.expander("Human review"):
    st.write("Decision:", review.get("decision"))
    st.write("Reviewer:", review.get("reviewer"))
    st.write("Date:", review.get("review_date"))
    st.write(
        "Human confirmed:",
        review.get("human_confirmed"),
    )
    st.write(
        "Review justification:",
        review.get("justification"),
    )

with st.expander("Experimental conditions"):
    if record["conditions_verified"] is True:
        st.success("Conditions verified")
    else:
        st.warning("Conditions are provisional — not verified")

    st.write(
        "Potential (V):",
        record.get("potential_v"),
    )
    st.write(
        "Reference electrode:",
        record.get("reference_electrode"),
    )
    st.write(
        "Current density (mA/cm²):",
        record.get("current_density_ma_cm2"),
    )
    st.write(
        "Current density type:",
        record.get("current_density_type"),
    )
    st.write(
        "Ag content (%):",
        record.get("ag_content_percent"),
    )
    st.write(
        "Ag percentage basis:",
        record.get("ag_percentage_basis"),
    )
    st.write(
        "Conditions review:",
        record.get("conditions_review_status"),
    )


# ============================================================
# CuSelect-AI v2 — Experimental Condition Review Integration
#
# PSEUDOCODE:
# 1. Read condition reviews from a separate JSON file.
# 2. Match reviews to the selected evidence measurement.
# 3. Display field-level decisions and source references.
# 4. Identify unresolved fields.
# 5. Never modify the scientific evidence files.
# ============================================================

st.divider()
st.header("Experimental Condition Validation")

CONDITIONS_PATH = ROOT / "data" / "conditions_review.json"

if not CONDITIONS_PATH.exists():
    st.info("No experimental-condition reviews have been saved yet.")

else:
    try:
        with CONDITIONS_PATH.open(encoding="utf-8") as file:
            condition_reviews = json.load(file)

    except (OSError, json.JSONDecodeError) as error:
        st.error(f"Cannot read condition reviews: {error}")
        st.stop()

    if not isinstance(condition_reviews, dict):
        st.error("Unexpected condition-review JSON structure.")
        st.stop()

    # Overall summary across all evidence records
    total_verified_fields = 0
    reviewed_measurements = 0

    evidence_ids = {
        item["measurement_id"] for item in records
    }

    for mid, entry in condition_reviews.items():
        if mid not in evidence_ids:
            continue

        if not isinstance(entry, dict):
            continue

        fields = entry.get("field_reviews", {})

        if not isinstance(fields, dict):
            continue

        reviewed_measurements += 1

        total_verified_fields += sum(
            isinstance(info, dict)
            and info.get("status") == "human_verified"
            for info in fields.values()
        )

    col1, col2 = st.columns(2)

    col1.metric(
        "Measurements with condition reviews",
        f"{reviewed_measurements}/{len(records)}",
    )

    col2.metric(
        "Verified condition fields",
        total_verified_fields,
    )

    # Find condition review for selected FE record
    selected_id = record["measurement_id"]
    condition_entry = condition_reviews.get(selected_id)

    st.subheader("Selected measurement")

    if not isinstance(condition_entry, dict):
        st.warning(
            "No condition review available for this measurement."
        )

    else:
        field_reviews = condition_entry.get(
            "field_reviews", {}
        )

        if not isinstance(field_reviews, dict):
            st.error("Invalid field-review structure.")
            st.stop()

        rows = []

        for field_name, info in field_reviews.items():
            if not isinstance(info, dict):
                continue

            rows.append({
                "Condition": field_name,
                "Value": info.get("value"),
                "Status": info.get(
                    "status", "not_reviewed"
                ),
                "Source": info.get("source", ""),
                "Reviewer": info.get("reviewer", ""),
                "Date": info.get("review_date", ""),
            })

        if rows:
            st.dataframe(
                pd.DataFrame(rows),
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("No individual fields have been reviewed.")

        verified = sum(
            row["Status"] == "human_verified"
            for row in rows
        )

        unresolved = [
            row["Condition"]
            for row in rows
            if row["Status"] != "human_verified"
        ]

        st.success(
            f"{verified} condition fields independently verified."
        )

        if unresolved:
            st.warning(
                "Unresolved reviewed fields: "
                + ", ".join(unresolved)
            )

        if "ag_percentage_basis" not in field_reviews:
            st.warning(
                "Ag percentage basis remains unverified."
            )

        st.info(
            "Field-level verification does not automatically "
            "establish complete experimental-condition validation. "
            "The original evidence record is unchanged."
        )

st.divider()
st.caption(
    "CuSelect-AI v2 | FE evidence and field-level "
    "experimental-condition review | Read-only"
)
