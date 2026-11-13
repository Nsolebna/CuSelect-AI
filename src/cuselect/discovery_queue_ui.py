"""CuSelect-AI literature metadata review. Does not approve scientific evidence."""

from __future__ import annotations
import fcntl
import hashlib
import html
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from math import ceil
from pathlib import Path
from urllib.parse import quote

import streamlit as st

QUEUE_NAME = "data/rag_discovery_queue.json"
REVIEW_STATES = {
    "pending_metadata_review": "Pending",
    "shortlisted_for_full_text_review": "Shortlisted",
    "rejected_metadata": "Rejected",
}


def clean(value):
    return re.sub(r"<[^>]*>", "", html.unescape(str(value or ""))).strip()


def load_discovered_papers(root: Path):
    path = root / QUEUE_NAME
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Literature queue must contain a JSON list")
    seen, unique = set(), []
    for paper in data:
        if not isinstance(paper, dict):
            continue
        doi = str(paper.get("doi", "")).strip().lower()
        if doi and doi not in seen:
            unique.append(paper)
            seen.add(doi)
    return unique


def date_category(value):
    raw = str(value or "").strip()
    if not re.fullmatch(r"\d{4}(-\d{2}){0,2}", raw):
        return "Incomplete/unknown date"
    try:
        fmt = {4: "%Y", 7: "%Y-%m", 10: "%Y-%m-%d"}[len(raw)]
        published = datetime.strptime(raw, fmt).date()
    except (ValueError, KeyError):
        return "Incomplete/unknown date"
    today = date.today()
    if published > today:
        return "Future-dated metadata"
    if len(raw) < 10:
        return "Incomplete/unknown date"
    if published >= today - timedelta(days=30):
        return "Published in last 30 days"
    return "Earlier publication"


def score_relevance(paper):
    """Discovery priority only; NEVER a scientific quality score."""
    title = clean(paper.get("title")).lower()
    abstract = clean(paper.get("abstract")).lower()
    text = f"{title} {abstract}"
    def match(pattern):
        return bool(re.search(pattern, text, flags=re.I))
    score = 0
    score += 3 if match(r"\b(co\s*2|co₂|carbon[ -]dioxide)\b") else 0
    score += 2 if match(r"\b(copper|cu|cu-based|cuprous)\b") else 0
    score += 2 if match(r"\b(silver|ag|ag/cu|cu/ag)\b") else 0
    score += 2 if match(r"\b(tandem|bimetallic|interface|dual.site)\b") else 0
    score += 2 if match(r"\b(ethylene|c2h4|c₂h₄|c2\+|c₂\+)\b") else 0
    score += 1 if match(r"\b(electroreduction|electrocatal|electrochemical|co2rr)\w*") else 0
    return score


def ag_cu_title(paper):
    title = clean(paper.get("title")).lower()
    return (bool(re.search(r"\b(silver|ag)\b", title)) and
            bool(re.search(r"\b(copper|cu|cuprous)\b", title)))


def can_review():
    """Fail closed: OIDC login by itself is not review authorization."""
    try:
        allowed = st.secrets.get("reviewer_emails", [])
    except Exception:
        allowed = []
    if isinstance(allowed, str):
        allowed = [allowed]
    email = str(st.user.get("email", "") or "").strip().lower()
    return bool(st.user.is_logged_in and email and
                email in {str(x).strip().lower() for x in allowed})


def update_status(root, doi, status):
    if status not in REVIEW_STATES:
        raise ValueError("Unknown metadata review status")
    path = root / QUEUE_NAME
    lock_path = root / "data/rag_discovery_queue.lock"
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        records = json.loads(path.read_text(encoding="utf-8"))
        found = False
        for p in records:
            if isinstance(p, dict) and str(p.get("doi", "")).lower() == doi.lower():
                p["review_status"] = status
                p["metadata_reviewed_at"] = datetime.now(timezone.utc).isoformat()
                found = True
                break
        if not found:
            raise ValueError("DOI missing from current queue. Refresh.")
        tmp = path.with_suffix(".json.tmp")
        try:
            tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def render_discovery_queue(root: Path):
    st.title("Literature Review Queue")
    st.caption("Crossref metadata candidates · no scientific claims approved by this screen")
    try:
        papers = load_discovered_papers(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        st.error(f"Could not read literature queue: {exc}")
        return
    if not papers:
        st.info("No papers found. Run `python scripts/discover_papers.py`.")
        return
    allowed = can_review()
    pending = sum(p.get("review_status", "pending_metadata_review") == "pending_metadata_review" for p in papers)
    shortlisted = sum(p.get("review_status") == "shortlisted_for_full_text_review" for p in papers)
    rejected = sum(p.get("review_status") == "rejected_metadata" for p in papers)
    cols = st.columns(4)
    for col, title, value in zip(cols,
        ["Discovered", "Pending", "Shortlisted", "Rejected"],
        [len(papers), pending, shortlisted, rejected]):
        col.metric(title, value)
    if not allowed:
        st.caption("Read-only mode. To enable review buttons, add your authenticated Google email "
                   "to `reviewer_emails` in `.streamlit/secrets.toml` and restart Streamlit.")
    st.divider()
    search = st.text_input("Search title, journal, DOI or abstract", key="literature_search_v02").strip().lower()
    dates = ["All dates", "Published in last 30 days", "Earlier publication",
             "Incomplete/unknown date", "Future-dated metadata"]
    years = sorted({str(p.get("publication_date", ""))[:4] for p in papers
                    if re.match(r"^\d{4}", str(p.get("publication_date", "")))}, reverse=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        topic = st.selectbox("Topic", ["All topics", "Ag/Cu title matches", "High-priority titles/abstracts"], key="literature_topic_v02")
        status_filter = st.selectbox("Review status", ["All statuses", "Pending", "Shortlisted", "Rejected"], key="literature_status_v02")
    with c2:
        year = st.selectbox("Publication year", ["All years"] + years, key="literature_year_v02")
        date_filter = st.selectbox("Publication date", dates, key="literature_date_v02")
    with c3:
        order = st.selectbox("Sort by", ["Highest discovery priority", "Newest publication", "Recently discovered", "Title A–Z"], key="literature_sort_v02")
    filtered = []
    for p in papers:
        title = clean(p.get("title"))
        journal = clean(p.get("journal"))
        doi = str(p.get("doi", ""))
        searchable = " ".join([title, journal, doi, clean(p.get("abstract"))]).lower()
        score = score_relevance(p)
        status = REVIEW_STATES.get(p.get("review_status", "pending_metadata_review"), "Pending")
        publication = str(p.get("publication_date", ""))
        if search and search not in searchable: continue
        if topic == "Ag/Cu title matches" and not ag_cu_title(p): continue
        if topic == "High-priority titles/abstracts" and score < 9: continue
        if year != "All years" and not publication.startswith(year): continue
        if date_filter != "All dates" and date_category(publication) != date_filter: continue
        if status_filter != "All statuses" and status != status_filter: continue
        filtered.append(p)
    if order == "Highest discovery priority":
        filtered.sort(key=lambda p: (score_relevance(p), str(p.get("publication_date", ""))), reverse=True)
    elif order == "Newest publication":
        filtered.sort(key=lambda p: str(p.get("publication_date", "")), reverse=True)
    elif order == "Recently discovered":
        filtered.sort(key=lambda p: str(p.get("discovered_at", "")), reverse=True)
    else:
        filtered.sort(key=lambda p: clean(p.get("title")).lower())
    st.write(f"**{len(filtered)} papers match your filters**")
    if not filtered:
        return
    per_page = 10
    pages = ceil(len(filtered) / per_page)
    page = st.selectbox("Results page", range(1, pages + 1),
                        format_func=lambda i: f"Page {i} of {pages}", key="literature_page_v02")
    for p in filtered[(page - 1) * per_page:page * per_page]:
        doi = str(p.get("doi", ""))
        ident = hashlib.sha256(doi.encode()).hexdigest()[:16]
        score = score_relevance(p)
        category = date_category(p.get("publication_date"))
        status = REVIEW_STATES.get(p.get("review_status", "pending_metadata_review"), "Pending")
        with st.container(border=True):
            st.write(f"**{clean(p.get('title'))}**")
            st.caption(f"{clean(p.get('journal'))} · Published: {p.get('publication_date', 'Unknown')} · {category}")
            st.caption(f"Discovery priority: {score}/12 (keyword heuristic, not scientific quality) · Metadata review: {status}")
            st.write(f"DOI: `{doi}`")
            if re.fullmatch(r"10\.\d{4,9}/[^\s<>]+", doi):
                st.link_button("Open publication", "https://doi.org/" + quote(doi, safe="/"))
            if allowed:
                a, b, c = st.columns(3)
                actions = [(a, "Shortlist", "shortlisted_for_full_text_review"),
                           (b, "Reject", "rejected_metadata"),
                           (c, "Reset to pending", "pending_metadata_review")]
                for col, label, state in actions:
                    with col:
                        if st.button(label, key=f"lit_{state}_{ident}",
                                     disabled=p.get("review_status", "pending_metadata_review") == state):
                            update_status(root, doi, state)
                            st.rerun()
    st.info("Shortlisting marks bibliographic interest only. Approved evidence and the RAG index remain unchanged.")
