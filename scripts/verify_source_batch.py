"""Source-grounded batch verification for CuSelect-AI.

PSEUDOCODE
1. Load extracted evidence and original XML publication.
2. Verify that the DOI matches.
3. Normalize scientific text for retrieval.
4. Retrieve supporting paragraph windows.
5. Check numerical-token consistency.
6. Generate a report without approving claims.
"""

import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path

from cuselect.evidence import normalize_doi
from cuselect.evidence_promotion import identify_candidate_passages

import argparse

def get_paths():
    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", required=True, type=Path)
    parser.add_argument(
        "--candidates",
        default="data/evidence_extraction_candidates.json",
        type=Path,
    )
    parser.add_argument(
        "--output",
        default="data/reports/source_verification_v2.json",
        type=Path,
    )
    return parser.parse_args()


def tokenize(text):
    text = unicodedata.normalize("NFKC", text.lower())
    return re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text)


def best_source_match(excerpt, paragraphs):
    query = tokenize(excerpt)
    if query[:1] == ["abstract"]:
        query = query[1:]

    if not query:
        return 0.0, "", ""

    best = (0.0, "", "")

    for paragraph in paragraphs:
        words = tokenize(paragraph)
        width = len(query)
        step = max(1, width // 5)

        for start in range(0, len(words), step):
            window = words[start:start + width]
            if not window:
                continue

            score = SequenceMatcher(
                None, query, window, autojunk=False
            ).ratio()

            if score > best[0]:
                best = (score, paragraph, " ".join(window))

    return best


def main():
    args = get_paths()
    root = ET.parse(args.xml).getroot()

    dois = {
        normalize_doi(element.text)
        for element in root.findall(".//article-meta/article-id")
        if element.get("pub-id-type") == "doi" and element.text
    }

    paragraphs = [
        " ".join("".join(p.itertext()).split())
        for p in root.iter("p")
    ]

    papers = json.loads(args.candidates.read_text(encoding="utf-8"))
    results = []

    for paper in papers:
        doi = normalize_doi(paper["doi"])

        if doi not in dois:
            raise ValueError(f"Publication DOI mismatch: {doi}")

        for passage in identify_candidate_passages(paper):
            score, paragraph, matched = best_source_match(
                passage["source_excerpt"], paragraphs
            )

            query_numbers = set(re.findall(
                r"\d+(?:\.\d+)?",
                passage["source_excerpt"]
            ))
            source_numbers = set(re.findall(
                r"\d+(?:\.\d+)?",
                paragraph
            ))

            results.append({
                "evidence_id": passage["evidence_id"],
                "doi": doi,
                "similarity": round(score, 3),
                "matched_window": matched,
                "source_paragraph": paragraph,
                "query_numbers": sorted(query_numbers),
                "missing_numbers": sorted(
                    query_numbers - source_numbers
                ),
                "verification_status": "requires_scientific_review",
                "scientifically_verified": False,
                "rag_ingestion_status": "not_ingested",
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("CUSELECT-AI — SOURCE VERIFICATION V2")
    print("Passages processed:", len(results))
    print("DOI identity: matched")
    print("Scientific approvals: 0")
    print("Report:", args.output)

    for i, result in enumerate(results, 1):
        print(
            f"Passage {i}: similarity={result['similarity']}, "
            f"missing numbers={result['missing_numbers']}"
        )


if __name__ == "__main__":
    main()
