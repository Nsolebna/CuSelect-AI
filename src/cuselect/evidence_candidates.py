
# CuSelect-AI — Scientific Evidence Candidate Extraction
#
# PSEUDOCODE
# 1. Receive publications with retrieved abstracts.
# 2. Preserve the original DOI and metadata.
# 3. Split each abstract into source sentences.
# 4. Identify sentences containing measurement terminology.
# 5. Detect possible performance and composition claims.
# 6. Preserve exact source sentences.
# 7. Generate reproducible evidence identifiers.
# 8. Flag every candidate for human verification.
# 9. Never infer missing values or product assignments.
# 10. Never insert candidates into verified evidence.

import hashlib
import re


EVIDENCE_PATTERNS = {
    "faradaic_efficiency": (
        r"\bfaradaic[\s-]+efficien\w*\b"
        r"|\bFE\s*\("
    ),
    "current_density": (
        r"\bcurrent[\s-]+densit\w*\b"
        r"|\bmA\s*/\s*cm\s*2\b"
        r"|\bmA\s*cm\s*[-−]?\s*2\b"
        r"|\bmA\s*cm\s*\^\s*[-−]?\s*2\b"
    ),

    "electrode_potential": (
        r"\b(?:applied|cathode|electrode|cell|operating)"
        r"[\s-]+potential\b"
        r"|\bpotentials?\s+(?:of|at|between|from)\s*"
        r"[−\-+]?\s*\d"
        r"|\bvs\.?\s*(?:RHE|Ag/AgCl|SHE|NHE)\b"
        r"|\b[−\-+]?\s*\d+(?:\.\d+)?\s*V"
        r"\s*(?:vs\.?\s*(?:RHE|Ag/AgCl|SHE|NHE))"
    ),


    "catalyst_composition": (
        r"\b(?:alloy|composition|atomic[\s-]+percent"
        r"|molar[\s-]+ratio)\b"
        r"|\b(?:Ag|Cu)\s*(?:content|loading)\b"
        r"|\b\d+(?:\.\d+)?\s*%\s*(?:Ag|Cu)\b"
    ),
    "stability": (
        r"\b(?:stability|durability|degradation"
        r"|operational[\s-]+lifetime)\b"
    ),
}

NUMBER_PATTERN = re.compile(
    r"(?<![\w.])"
    r"[+\-−~≈]?\s*\d+(?:\.\d+)?"
    r"(?:\s*%)?"
    r"(?![\w])"
)

PRODUCT_PATTERNS = {
    "ethylene": (
        r"\bethylene\b|\bethene\b"
        r"|\bc\s*2\s*h\s*4\b"
    ),
    "ethanol": (
        r"\bethanol\b|\bc\s*2\s*h\s*5\s*oh\b"
    ),
    "carbon_monoxide": (
        r"\bcarbon[\s-]+monoxide\b"
        r"|\bco[\s-]+intermediate\b"
    ),
    "hydrogen": r"\bhydrogen\b|\bh2\b",
    "acetate": r"\bacetate\b",
}


def split_sentences(text):
    """
    Split scientific abstract text into candidate sentences.

    This is a conservative heuristic, not a full
    scientific sentence parser.
    """

    if not isinstance(text, str):
        return []

    text = text.strip()

    if not text:
        return []

    # Avoid splitting at decimal points such as 0.7.
    # Retain original text within each sentence.
    return [
        sentence.strip()
        for sentence in re.split(
            r"(?<=[.!?])\s+(?=[A-Z])|\n+",
            text,
        )
        if sentence.strip()
    ]


def detect_labels(sentence, patterns):
    """Return labels with explicit pattern matches."""

    return [
        label
        for label, pattern in patterns.items()
        if re.search(
            pattern,
            sentence,
            flags=re.IGNORECASE,
        )
    ]


def extract_evidence_candidates(paper):
    """
    Extract candidate evidence sentences from an abstract.

    No reported number is automatically assigned to
    a product or converted into a verified measurement.
    """

    if not isinstance(paper, dict):
        raise ValueError("paper must be a dictionary")

    doi = str(paper.get("doi") or "").strip().lower()
    abstract = paper.get("abstract") or ""

    if not doi:
        raise ValueError("Publication DOI is required")

    if not isinstance(abstract, str):
        raise ValueError("abstract must be a string")

    if not abstract.strip():
        return []

    candidates = []

    for sentence_index, sentence in enumerate(
        split_sentences(abstract)
    ):
        evidence_types = detect_labels(
            sentence, EVIDENCE_PATTERNS
        )

        if not evidence_types:
            continue

        # Require numeric content for a first-pass
        # performance or composition candidate.
        numeric_matches = [
            match.group(0).strip()
            for match in NUMBER_PATTERN.finditer(sentence)
        ]

        if not numeric_matches:
            continue

        products = detect_labels(
            sentence, PRODUCT_PATTERNS
        )

        identifier_text = (
            doi + "|" + str(sentence_index) + "|" + sentence
        )

        evidence_id = hashlib.sha256(
            identifier_text.encode("utf-8")
        ).hexdigest()[:20]

        candidates.append({
            "evidence_id": evidence_id,
            "doi": doi,
            "title": paper.get("title", ""),
            "source_type": "abstract",
            "source_provider": paper.get(
                "abstract_source", "unknown"
            ),
            "source_sentence_index": sentence_index,
            "exact_source_text": sentence,
            "evidence_type_indicators": evidence_types,
            "product_mentions": products,
            "numeric_tokens": numeric_matches,
            "measurement_value": None,
            "measurement_unit": None,
            "assigned_product": None,
            "conditions_verified": False,
            "review_status": "pending_human_review",
            "scientific_status": "unverified_candidate",
            "extraction_method": "rule_based_v1",
        })

    return candidates


def extract_corpus_candidates(papers):
    """Extract candidates and retain DOI provenance."""

    if not isinstance(papers, list):
        raise ValueError("papers must be a list")

    results = []
    seen_ids = set()

    for paper in papers:
        for candidate in extract_evidence_candidates(paper):
            identifier = candidate["evidence_id"]

            if identifier in seen_ids:
                continue

            seen_ids.add(identifier)
            results.append(candidate)

    return results
