"""Discover scientific papers for manual evidence review."""

import html
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data/rag_discovery_queue.json"

QUERIES = [
    "copper silver tandem carbon dioxide electroreduction",
    "CO2 electroreduction ethylene catalysts",
    "electrochemical carbon dioxide reduction",
]


def normalize_doi(value):
    return str(value or "").lower().strip().removeprefix(
        "https://doi.org/"
    )


def collect_dois(obj):
    """Find DOI values, including nested review-queue records."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.lower() == "doi":
                yield normalize_doi(value)
            else:
                yield from collect_dois(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from collect_dois(value)


def relevant(title):
    """Conservative title-based screening."""
    text = title.lower()
    co2 = bool(re.search(r"co\s*[₂2]|carbon dioxide", text))
    chemistry = any(word in text for word in (
        "reduct", "electrocatal", "electrochem",
        "ethylene", "catalyst", "electroly",
    ))
    return co2 and chemistry


def publication_date(item):
    for field in ("published", "issued"):
        parts = item.get(field, {}).get("date-parts", [[]])[0]
        if parts:
            return "-".join(
                str(x).zfill(2) if i else str(x)
                for i, x in enumerate(parts)
            )
    return "Unknown"


def main():
    known = set()

    for filename in (
        "data/approved_evidence.json",
        "data/evidence_review_queue.json",
        "data/rag_discovery_queue.json",
    ):
        path = ROOT / filename
        if path.exists():
            known.update(collect_dois(
                json.loads(path.read_text(encoding="utf-8"))
            ))

    existing = (
        json.loads(QUEUE.read_text(encoding="utf-8"))
        if QUEUE.exists() else []
    )

    since = (
        datetime.now(timezone.utc) - timedelta(days=30)
    ).date().isoformat()

    added = []
    successful_queries = 0

    for query in QUERIES:
        try:
            response = requests.get(
                "https://api.crossref.org/works",
                params={
                    "query.bibliographic": query,
                    "filter": (
                        f"from-index-date:{since},"
                        "type:journal-article"
                    ),
                    "rows": 50,
                },
                headers={
                    "User-Agent": "CuSelect-AI-literature-discovery/0.1"
                },
                timeout=30,
            )
            response.raise_for_status()
            works = response.json()["message"]["items"]
            successful_queries += 1

        except (requests.RequestException, ValueError, KeyError) as exc:
            print(f"Search failed: {query} ({type(exc).__name__})")
            continue

        for item in works:
            doi = normalize_doi(item.get("DOI"))
            titles = item.get("title") or []
            title = html.unescape(
                re.sub(r"<[^>]+>", "", titles[0])
            ) if titles else ""

            if not doi or doi in known or not relevant(title):
                continue

            known.add(doi)
            added.append({
                "doi": doi,
                "title": title,
                "journal": (
                    item.get("container-title") or ["Unknown"]
                )[0],
                "publication_date": publication_date(item),
                "url": f"https://doi.org/{doi}",
                "discovery_source": "Crossref",
                "discovered_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "review_status": "pending_metadata_review",
                "scientific_status": "not_assessed",
            })

    if not successful_queries:
        raise SystemExit(
            "All searches failed. Existing data unchanged."
        )

    QUEUE.parent.mkdir(parents=True, exist_ok=True)

    import fcntl
    lock_path = ROOT / "data/rag_discovery_queue.lock"
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        current = (
            json.loads(QUEUE.read_text(encoding="utf-8"))
            if QUEUE.exists() else []
        )
        current_dois = set(collect_dois(current))
        added = [p for p in added if normalize_doi(p["doi"]) not in current_dois]
        existing = current
        if added or not QUEUE.exists():
            temporary = QUEUE.with_suffix(".json.tmp")
            try:
                temporary.write_text(
                    json.dumps(existing + added, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                os.replace(temporary, QUEUE)
            finally:
                temporary.unlink(missing_ok=True)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    print("\nCUSELECT-AI LITERATURE DISCOVERY")
    print("=" * 40)
    print("Successful searches:", successful_queries)
    print("New candidates:", len(added))
    print("Total pending records:", len(existing) + len(added))
    print("Review queue:", QUEUE)
    print("Approved evidence modified: NO")
    print("Paid model API calls: 0")

    for paper in added[:5]:
        print("\n", paper["title"])
        print(" DOI:", paper["doi"])


if __name__ == "__main__":
    main()
