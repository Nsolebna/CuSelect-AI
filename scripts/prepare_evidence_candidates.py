"""Prepare unverified evidence candidates from shortlisted papers."""

import hashlib
import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data/rag_discovery_queue.json"
OUTPUT = ROOT / "data/evidence_extraction_candidates.json"

KEYWORDS = re.compile(
    r"faradaic|efficien|ethylene|ethanol|acetate|formate|"
    r"catalyst|copper|silver|tandem|electrolyte|"
    r"current density|flow cell|potential|selectivit|"
    r"CO2|CO₂|C2|C₂",
    re.IGNORECASE,
)


def clean(text):
    text = html.unescape(str(text or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_abstract(doi):
    try:
        response = requests.get(
            "https://api.openalex.org/works",
            params={
                "filter": f"doi:https://doi.org/{doi}",
                "per_page": 1,
            },
            timeout=20,
        )
        response.raise_for_status()
        records = response.json().get("results", [])

        if records:
            index = records[0].get("abstract_inverted_index") or {}
            positions = {}

            for word, locations in index.items():
                for position in locations:
                    if isinstance(position, int):
                        positions[position] = word

            abstract = clean(
                " ".join(positions[p] for p in sorted(positions))
            )
            if abstract:
                return abstract, "OpenAlex reconstructed abstract"

    except (requests.RequestException, ValueError, TypeError):
        pass

    try:
        response = requests.get(
            f"https://api.crossref.org/works/{doi}",
            timeout=20,
        )
        response.raise_for_status()

        abstract = clean(
            response.json().get("message", {}).get("abstract")
        )
        if abstract:
            return abstract, "Crossref deposited abstract"

    except (requests.RequestException, ValueError, TypeError):
        pass

    return "", "Abstract unavailable"


def extract_passages(abstract):
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", abstract)

    return [
        {
            "source_location": "abstract",
            "source_excerpt": sentence[:500],
            "verified": False,
        }
        for sentence in sentences
        if KEYWORDS.search(sentence)
    ][:6]


def main():
    papers = json.loads(QUEUE.read_text(encoding="utf-8"))

    existing = (
        json.loads(OUTPUT.read_text(encoding="utf-8"))
        if OUTPUT.exists() else []
    )

    if not isinstance(papers, list) or not isinstance(existing, list):
        raise ValueError("Expected JSON lists; no changes made.")

    seen = {str(p.get("doi", "")).lower() for p in existing}
    shortlisted = [
        paper for paper in papers
        if isinstance(paper, dict)
        and paper.get("review_status")
        == "shortlisted_for_full_text_review"
    ]

    if not shortlisted:
        print("No shortlisted papers.")
        print("Shortlist a paper in Evidence > Literature Queue.")
        return

    new = []

    for paper in shortlisted:
        doi = str(paper.get("doi", "")).lower().strip()

        if not doi or doi in seen:
            continue

        abstract, source = fetch_abstract(doi)

        if not abstract:
            print(f"Abstract unavailable: {doi}")
            continue

        passages = extract_passages(abstract)

        new.append({
            "candidate_id": hashlib.sha256(
                doi.encode()
            ).hexdigest()[:16],
            "doi": doi,
            "title": paper.get("title", ""),
            "abstract_source": source,
            "source_extent": "abstract_only",
            "retrieved_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "scientific_status": "unverified_candidate",
            "review_status": "awaiting_human_full_text_verification",
            "candidate_passages": passages,
            "experimental_conditions": {
                "catalyst": None,
                "cell_type": None,
                "electrolyte": None,
                "potential": None,
                "current_density": None,
                "FE_ethylene": None,
            },
        })

        seen.add(doi)
        print(f"Prepared {doi}: {len(passages)} passages")

    if new:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        temp = OUTPUT.with_suffix(".json.tmp")

        temp.write_text(
            json.dumps(existing + new, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(temp, OUTPUT)

    print("\nCUSELECT-AI SCIENTIFIC EVIDENCE EXTRACTION")
    print("=" * 45)
    print("Shortlisted papers:", len(shortlisted))
    print("New extraction records:", len(new))
    print("Total extraction records:", len(existing) + len(new))
    print("Approved evidence modified: NO")
    print("RAG index modified: NO")


if __name__ == "__main__":
    main()
