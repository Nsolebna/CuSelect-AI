"""Read-only scientific records alongside the existing literature review queue."""

import json

import pandas as pd
import streamlit as st

from .evidence_navigator import build_evidence_cards
from .evidence_store import load_verified_corpus
from .review_queue_ui import render_review_queue


def render_evidence_card(card):
    st.write(card["claim"])
    st.caption(f"{card['catalyst']} · {card['conditions']}")
    st.write("**Source location**", card["source_location"])
    st.write("**Source extent**", card["source_extent"])
    st.caption(f"{card['review_status']} · DOI {card['doi']}")
    st.link_button("Open original publication", card["publication_url"])


def render_claims(root):
    try:
        records = load_verified_corpus(root)
        cards = build_evidence_cards(records, root)
    except (OSError, ValueError) as error:
        st.error(f"Reviewed claim verification failed: {error}")
        return

    if not cards:
        st.info("No reviewed observations are available.")
        return
    st.caption(
        f"{len(cards)} human-reviewed observations from one publication. "
        "Each observation applies to its reported catalyst and conditions."
    )
    for column, card in zip(st.columns(len(cards)), cards):
        with column, st.container(border=True):
            st.markdown(f"**{card['evidence_id']}**")
            render_evidence_card(card)


def load_approved_measurements(root):
    records = json.loads((root / "data/approved_evidence.json").read_bytes())
    if not isinstance(records, list):
        raise ValueError("Expected a list of approved FE measurements")
    ids = set()
    for record in records:
        if not isinstance(record, dict) or not {
            "measurement_id", "product", "value", "unit", "review", "doi",
        }.issubset(record):
            raise ValueError("Incomplete measurement record")
        measurement_id = record["measurement_id"]
        review = record["review"]
        value = record["value"]
        if (
            measurement_id in ids
            or record.get("review_status") != "approved"
            or not isinstance(review, dict)
            or review.get("human_confirmed") is not True
            or type(value) not in (int, float)
            or not 0 <= value <= 100
            or record["unit"] != "%"
        ):
            raise ValueError("Invalid or unapproved FE measurement")
        ids.add(measurement_id)
    return records


def render_measurements(root):
    try:
        records = load_approved_measurements(root)
    except (OSError, ValueError, TypeError) as error:
        st.error(f"Approved measurement export unavailable: {error}")
        return

    st.caption(
        "Saved human-approved Faradaic-efficiency measurements. "
        "Experimental conditions have a separate field-level review."
    )
    if not records:
        st.info("The approved measurement export is empty.")
        return

    filter_column, selection = st.columns([1, 2])
    products = sorted({row["product"] for row in records})
    selected_products = filter_column.multiselect("Products", products, default=products)
    filtered = {row["measurement_id"]: row for row in records if row["product"] in selected_products}
    if not filtered:
        st.info("Select a product to display its measurements.")
        return

    def label(measurement_id):
        row = filtered[measurement_id]
        qualifier = row.get("qualifier") or ""
        return f"{row['product']} · {qualifier} {row['value']:g}% · {row['doi']}"

    selected = selection.selectbox("Measurement", filtered, format_func=label)
    record = filtered[selected]
    review = record["review"]

    left, right = st.columns(2)
    with left:
        st.markdown("**Publication and source**")
        st.write(record.get("title") or record["doi"])
        st.write("**DOI**", record["doi"])
        st.write("**Source location**", review.get("source_location", "Unavailable"))
        if review.get("supporting_excerpt"):
            st.write(review["supporting_excerpt"])
    with right:
        st.markdown("**Human FE review**")
        st.write(review.get("justification", "Unavailable"))
        st.caption(f"{review.get('reviewer', 'Reviewer unavailable')} · {review.get('review_date', '')}")

    with st.expander("Experimental-condition review"):
        try:
            reviews = json.loads((root / "data/conditions_review.json").read_bytes())
            entry = reviews.get(selected, {})
            fields = entry.get("field_reviews", {})
            if entry and (entry["doi"] != record["doi"] or entry["product"] != record["product"]):
                raise ValueError("Condition review identity differs from the measurement")
            rows = [
                {
                    "Condition": name,
                    "Value": str(field["value"]) if field.get("value") is not None else "",
                    "Status": field.get("status", "not_reviewed"),
                    "Source": field.get("source", ""),
                    "Reviewer": field.get("reviewer", ""),
                    "Date": field.get("review_date", ""),
                }
                for name, field in fields.items()
            ]
        except FileNotFoundError:
            rows = []
        except (OSError, ValueError, TypeError, AttributeError, KeyError) as error:
            st.error(f"Condition review unavailable: {error}")
            return
        if rows:
            st.dataframe(rows, hide_index=True)
            st.caption("Field-level verification applies only to the conditions listed.")
        else:
            st.info("No field-level condition review is saved for this measurement.")


def render_evidence_library(root):
    st.title("Evidence Library")
    view = st.radio(
        "Evidence view", ["Reviewed claims", "FE measurements", "Publications", "Literature review"],
        horizontal=True, label_visibility="collapsed",
    )
    if view == "Reviewed claims":
        render_claims(root)
    elif view == "FE measurements":
        render_measurements(root)
    elif view == "Publications":
        st.caption("Seed bibliographic register. Review source papers before extracting evidence.")
        try:
            st.dataframe(pd.read_csv(root / "data/papers.csv"), hide_index=True)
        except (OSError, ValueError) as error:
            st.error(f"Publication register unavailable: {error}")
    else:
        render_review_queue(root)
