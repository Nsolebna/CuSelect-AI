
# CuSelect-AI — Single-Product FE Extraction
#
# PSEUDOCODE
# 1. Receive publication metadata and an abstract.
# 2. Search for explicit Faradaic-efficiency statements.
# 3. Recognize ethylene, ethanol, and C2 product classes.
# 4. Link one explicitly stated FE value to its product.
# 5. Preserve the percentage and uncertainty qualifier.
# 6. Reject ambiguous multi-product statements.
# 7. Avoid extracting comparative values as absolute FE.
# 8. Preserve DOI, source text, and character positions.
# 9. Mark all results for human scientific review.

import hashlib
import re


PRODUCT = (
    r"(?:"
    r"ethylene|ethene|ethanol"
    r"|C\s*2\s*H\s*5\s*OH"
    r"|C\s*2\s*H\s*4"
    r"|C\s*2\s*\+\s*products?"
    r"|C\s*2\s*products?"
    r"|C\s*2\s*\+"
    r")"
)

VALUE = r"(?P<value>\d+(?:\.\d+)?)"
QUALIFIER = r"(?P<qualifier>nearly|approximately|about|around|~|≈)?"

# PSEUDOCODE
# Recognize three explicit sentence constructions.
# Every construction requires Faradaic-efficiency context.

PATTERNS = [
    # Example:
    # Faradaic efficiency for ethylene reached 42%.
    re.compile(
        rf"\bfaradaic\s+efficien(?:cy|cies)"
        rf"\s+for\s+(?P<product>{PRODUCT})"
        rf"(?:\s+(?:formation|production))?"
        rf"\s+(?:reached|reaches|was|is|"
        rf"is\s+enhanced\s+to)"
        rf"\s+{QUALIFIER}\s*{VALUE}\s*%",
        re.IGNORECASE,
    ),

    # Example:
    # Faradaic efficiency (FE C2H4) of 21.43%.
    re.compile(
        rf"\bfaradaic\s+efficien(?:cy|cies)"
        rf"\s*\(\s*FE\s+(?P<product>{PRODUCT})\s*\)"
        rf"\s+of\s+{QUALIFIER}\s*{VALUE}\s*%",
        re.IGNORECASE,
    ),

    # Example:
    # Faradaic efficiency (FE) of 72.85% for C2 products.
    re.compile(
        rf"\bfaradaic\s+efficien(?:cy|cies)"
        rf"\s*\(\s*FE\s*\)"
        rf"\s+of\s+{QUALIFIER}\s*{VALUE}\s*%"
        rf"\s+for\s+(?P<product>{PRODUCT})",
        re.IGNORECASE,
    ),
]


def normalize_product(raw):
    """Map product formulas to canonical labels."""

    compact = re.sub(r"\s+", "", raw).lower()

    if compact in ("ethylene", "ethene", "c2h4"):
        return "ethylene"

    if compact in ("ethanol", "c2h5oh"):
        return "ethanol"

    if compact in (
        "c2",
        "c2+",
        "c2products",
        "c2+products",
        "c2product",
        "c2+product",
    ):
        return "c2_product_class"

    return None


def extract_single_fe(paper):
    """Extract explicitly linked single-product FE candidates."""

    if not isinstance(paper, dict):
        raise ValueError("paper must be a dictionary")

    doi = str(paper.get("doi") or "").strip().lower()
    abstract = paper.get("abstract") or ""

    if not doi:
        raise ValueError("DOI is required")

    if not isinstance(abstract, str):
        raise ValueError("abstract must be a string")

    results = []
    seen_spans = set()

    for pattern in PATTERNS:
        for match in pattern.finditer(abstract):

            span = match.span()

            if span in seen_spans:
                continue

            product = normalize_product(
                match.group("product")
            )

            value = float(match.group("value"))

            # Faradaic efficiency is bounded by 0–100%.
            if (
                product is None
                or not 0 <= value <= 100
            ):
                continue

            # Preserve the original text and positions.
            source_text = abstract[span[0]:span[1]]

            qualifier = match.group("qualifier")

            identifier = (
                doi + "|" + str(span[0])
                + "|" + source_text + "|" + product
            )

            measurement_id = hashlib.sha256(
                identifier.encode("utf-8")
            ).hexdigest()[:20]

            results.append({
                "measurement_id": measurement_id,
                "doi": doi,
                "title": paper.get("title", ""),
                "product": product,
                "measurement_type": "faradaic_efficiency",
                "value": value,
                "unit": "%",
                "qualifier": (
                    qualifier.lower() if qualifier else None
                ),
                "exact_source_text": source_text,
                "source_start": span[0],
                "source_end": span[1],
                "source_type": "abstract",
                "source_provider": paper.get(
                    "abstract_source", "unknown"
                ),
                "linking_rule": "explicit_single_product_fe",
                "review_status": "pending_human_review",
                "scientific_status": "unverified_candidate",
                "conditions_verified": False,
            })

            seen_spans.add(span)

    return sorted(
        results,
        key=lambda item: item["source_start"],
    )


def extract_single_fe_corpus(papers):
    """Extract single-product FE candidates across papers."""

    if not isinstance(papers, list):
        raise ValueError("papers must be a list")

    results = []
    seen_ids = set()

    for paper in papers:
        for measurement in extract_single_fe(paper):

            identifier = measurement["measurement_id"]

            if identifier in seen_ids:
                continue

            seen_ids.add(identifier)
            results.append(measurement)

    return results
