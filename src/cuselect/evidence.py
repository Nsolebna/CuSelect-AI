"""Evidence-ledger primitives for CU-001.

No literature claim is automatically verified by an LLM, DOI lookup, or seed CSV.
Network access is optional and reserved for publisher-deposited metadata lookup.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen
import json
import re

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
SEED_COLUMNS = ("paper_id", "year", "title", "doi", "kind", "why_relevant")


def normalize_doi(value: str) -> str:
    """Normalize bare/DOI-URL identifiers; raise if the DOI is not syntactically valid."""
    if not isinstance(value, str):
        raise ValueError("DOI must be a string")
    doi = unquote(value.strip()).lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi).strip()
    if not DOI_PATTERN.fullmatch(doi):
        raise ValueError(f"Malformed DOI: {value!r}")
    return doi


def title_similarity(first: str, second: str) -> float:
    """String similarity is a review aid, not proof of publication authenticity."""
    def tidy(s: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", s.lower().replace("co₂", "co2")))
    return SequenceMatcher(None, tidy(first), tidy(second)).ratio()


def audit_seed_bibliography(papers: pd.DataFrame) -> pd.DataFrame:
    """Syntax and duplication checks; never calls a DOI 'verified' on this basis."""
    missing = sorted(set(SEED_COLUMNS) - set(papers.columns))
    if missing:
        raise ValueError(f"Bibliography missing columns: {missing}")
    rows = []
    seen_paper_ids: set[str] = set()
    seen_dois: set[str] = set()
    for _, p in papers.iterrows():
        pid = str(p["paper_id"]).strip()
        raw_doi = str(p["doi"])
        try:
            doi = normalize_doi(raw_doi)
            doi_error = ""
        except ValueError as exc:
            doi, doi_error = "", str(exc)
        pid_dup = pid in seen_paper_ids
        doi_dup = bool(doi and doi in seen_dois)
        seen_paper_ids.add(pid)
        if doi:
            seen_dois.add(doi)
        try:
            year = int(p["year"])
            year_valid = 1900 <= year <= 2100
        except (ValueError, TypeError):
            year_valid = False
        rows.append({
            "paper_id": pid,
            "doi": doi,
            "doi_syntax_valid": bool(doi),
            "duplicate_paper_id": pid_dup,
            "duplicate_doi": doi_dup,
            "publication_year_valid": year_valid,
            "seed_title": str(p["title"]),
            "seed_year": p["year"],
            "bibliographic_status": "seed_not_verified",
            "validation_note": doi_error,
        })
    return pd.DataFrame(rows)


def crossref_lookup(doi: str, timeout: float = 9.0) -> dict:
    """Retrieve *metadata only* from Crossref with bounded timeout.

    Raises for transport failures, which must not be converted to verification.
    """
    normalized = normalize_doi(doi)
    url = "https://api.crossref.org/works/" + quote(normalized, safe="/")
    request = Request(url, headers={"User-Agent": "CuSelect-AI/0.3 (academic metadata audit; no scraping)", "Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    message = payload.get("message", {})
    if not message.get("DOI"):
        raise ValueError("Crossref response lacks DOI")
    def years(field: str) -> set[int]:
        parts = (message.get(field) or {}).get("date-parts", [])
        return {int(row[0]) for row in parts if row}
    return {
        "doi": normalize_doi(message["DOI"]),
        "title": (message.get("title") or [""])[0],
        "publisher": message.get("publisher", ""),
        "journal": (message.get("container-title") or [""])[0],
        "published_years": sorted(years("published") | years("published-online") | years("published-print") | years("issued")),
        "license_metadata_present": bool(message.get("license")),
        "metadata_source": "crossref_rest_api",
    }


def verify_metadata(papers: pd.DataFrame, *, online: bool = False) -> pd.DataFrame:
    """Compare publisher-deposited metadata with seeds; claims remain unverified.

    Online failures are retained as explicit failure states, not silent fallbacks.
    """
    audited = audit_seed_bibliography(papers)
    records = []
    for row in audited.to_dict("records"):
        record = dict(row)
        record.update({
            "metadata_status": "not_queried" if not online else "not_checked",
            "crossref_title": "",
            "crossref_journal": "",
            "crossref_publisher": "",
            "crossref_years": "",
            "title_similarity": None,
            "year_consistent": None,
            "metadata_error": "",
            "license_review_status": "not_reviewed",
            "claim_review_status": "not_started",
        })
        if online and row["doi_syntax_valid"] and not row["duplicate_doi"]:
            try:
                returned = crossref_lookup(row["doi"])
                similarity = title_similarity(row["seed_title"], returned["title"])
                year_consistent = int(row["seed_year"]) in returned["published_years"]
                doi_matches = returned["doi"] == row["doi"]
                record.update({
                    "crossref_title": returned["title"],
                    "crossref_journal": returned["journal"],
                    "crossref_publisher": returned["publisher"],
                    "crossref_years": ";".join(map(str, returned["published_years"])),
                    "title_similarity": round(similarity, 3),
                    "year_consistent": year_consistent,
                    "metadata_status": "matching_metadata_needs_manual_review" if doi_matches and similarity >= 0.80 and year_consistent else "metadata_discrepancy_review",
                })
            except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
                record["metadata_status"] = "lookup_failed_not_verified"
                record["metadata_error"] = type(exc).__name__
        records.append(record)
    return pd.DataFrame(records)


ClaimType = Literal["experimental_observation", "computed_result", "author_interpretation", "hypothesis", "methodology", "review_context"]
ClaimStatus = Literal["pending_source_review", "human_verified", "rejected"]
SourceExtent = Literal["abstract", "full_text", "supplementary", "unknown"]

class EvidenceClaim(BaseModel):
    """Single attributable claim. Promotion requires explicit human verification."""
    model_config = ConfigDict(extra="forbid")
    evidence_id: str = Field(min_length=3)
    paper_id: str
    doi: str
    claim_paraphrase: str = Field(min_length=15)
    claim_type: ClaimType
    source_extent: SourceExtent = "unknown"
    exact_source_location: str = ""
    catalyst_system: str = ""
    target_or_observation: str = ""
    conditions: str = ""
    faradaic_efficiency_percent: float | None = Field(default=None, ge=0, le=100)
    fe_product: str = ""
    attribution_note: str = ""
    source_checked_by_human: bool = False
    review_status: ClaimStatus = "pending_source_review"
    reviewer_note: str = ""
    split_group: str = ""

    @model_validator(mode="after")
    def integrity(self) -> "EvidenceClaim":
        self.doi = normalize_doi(self.doi)
        if self.faradaic_efficiency_percent is not None and not self.fe_product.strip():
            raise ValueError("FE value requires identifying the specific product or product class")
        if self.review_status == "human_verified":
            if (not self.source_checked_by_human or not self.exact_source_location.strip()
                or not self.reviewer_note.strip() or "confirm independently" in self.exact_source_location.lower()):
                raise ValueError("Human verification requires source checked, exact location, and reviewer note")
        if self.split_group and self.split_group != self.doi:
            raise ValueError("split_group must be the normalized publication DOI")
        if not self.split_group:
            self.split_group = self.doi
        return self


def check_claim_links(claims: list[EvidenceClaim], papers: pd.DataFrame) -> None:
    """Raise if a claim is detached from the seed register or duplicates an ID."""
    paper_map = {str(row.paper_id): normalize_doi(row.doi) for row in papers.itertuples(index=False)}
    seen = set()
    for claim in claims:
        if claim.evidence_id in seen:
            raise ValueError(f"Duplicate evidence ID: {claim.evidence_id}")
        seen.add(claim.evidence_id)
        if claim.paper_id not in paper_map or claim.doi != paper_map[claim.paper_id]:
            raise ValueError(f"Claim not linked to the correct paper/DOI: {claim.evidence_id}")


def claims_frame(claims: list[EvidenceClaim]) -> pd.DataFrame:
    """Preserve an explicit schema even if zero claims have been verified."""
    columns = list(EvidenceClaim.model_fields)
    return pd.DataFrame([c.model_dump() for c in claims], columns=columns)


def save_csv(frame: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")
    return path
