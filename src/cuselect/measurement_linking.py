
# CuSelect-AI — Context-Aware Measurement Linking
#
# PSEUDOCODE
# 1. Receive an abstract and its DOI.
# 2. Locate Faradaic-efficiency statements.
# 3. Recognize ethylene and ethanol in chemical notation.
# 4. Identify two numerical FE values.
# 5. Require an explicit "respectively" relationship.
# 6. Link products and values in the stated order.
# 7. Preserve qualifiers, source text and DOI.
# 8. Mark all measurements as unverified candidates.
# 9. Reject ambiguous statements.

import hashlib
import re


PRODUCT = (
    r"(?:ethylene|ethene|ethanol"
    r"|C\s*2\s*H\s*4"
    r"|C\s*2\s*H\s*5\s*OH)"
)

QUALIFIER = r"(?:nearly|approximately|about|around|~|≈)"

FE_CONTEXT = re.compile(
    r"\bfaradaic\s+efficien(?:cy|cies)\b",
    re.IGNORECASE,
)

PAIR_PATTERN = re.compile(
    rf"\bfor\s+(?P<product1>{PRODUCT})"
    rf"\s+and\s+(?P<product2>{PRODUCT})"
    rf"(?:\s+production)?"
    rf"\s+(?:reaching|reached|reach|were|are)"
    rf"\s+(?P<qualifier1>{QUALIFIER})?"
    rf"\s*(?P<value1>\d+(?:\.\d+)?)"
    rf"\s*%?\s+and\s+"
    rf"(?P<qualifier2>{QUALIFIER})?"
    rf"\s*(?P<value2>\d+(?:\.\d+)?)"
    rf"\s*%\s*,?\s*respectively\b",
    re.IGNORECASE,
)


def normalize_product(product):
    """Map supported product names and formulas."""

    compact = re.sub(
        r"\s+", "", product
    ).lower()

    if compact in ("ethylene", "ethene", "c2h4"):
        return "ethylene"

    if compact in ("ethanol", "c2h5oh"):
        return "ethanol"

    return None


def link_faradaic_efficiencies(paper):
    """
    Extract explicit two-product FE assignments.

    Every returned measurement remains unverified.
    Ambiguous statements produce no assignments.
    """

    if not isinstance(paper, dict):
        raise ValueError("paper must be a dictionary")

    doi = str(paper.get("doi") or "").strip().lower()
    abstract = paper.get("abstract") or ""

    if not doi:
        raise ValueError("DOI is required")

    if not isinstance(abstract, str):
        raise ValueError("abstract must be a string")

    measurements = []

    if not abstract.strip():
        return measurements

    for match in PAIR_PATTERN.finditer(abstract):

        # Require Faradaic-efficiency context
        # immediately before the product statement.
        prefix = abstract[max(0, match.start() - 100):match.start()]

        if not FE_CONTEXT.search(prefix):
            continue

        source_text = abstract[match.start():match.end()]

        products = [
            normalize_product(match.group("product1")),
            normalize_product(match.group("product2")),
        ]

        values = [
            float(match.group("value1")),
            float(match.group("value2")),
        ]

        qualifiers = [
            match.group("qualifier1"),
            match.group("qualifier2"),
        ]

        # Reject unsupported or duplicate product
        # combinations rather than guessing.
        if (
            None in products
            or products[0] == products[1]
            or any(value < 0 or value > 100 for value in values)
        ):
            continue

        for product, value, qualifier in zip(
            products, values, qualifiers
        ):

            identifier = (
                doi + "|" + str(match.start())
                + "|" + source_text + "|" + product
            )

            measurement_id = hashlib.sha256(
                identifier.encode("utf-8")
            ).hexdigest()[:20]

            measurements.append({
                "measurement_id": measurement_id,
                "doi": doi,
                "title": paper.get("title", ""),
                "product": product,
                "measurement_type": "faradaic_efficiency",
                "value": value,
                "unit": "%",
                "qualifier": (
                    qualifier.lower()
                    if qualifier else None
                ),
                "exact_source_text": source_text,
                "source_start": match.start(),
                "source_end": match.end(),
                "source_type": "abstract",
                "source_provider": paper.get(
                    "abstract_source", "unknown"
                ),
                "linking_rule": "explicit_respectively",
                "review_status": "pending_human_review",
                "scientific_status": "unverified_candidate",
                "conditions_verified": False,
            })

    return measurements


def link_corpus_measurements(papers):
    """Link measurements across publication records."""

    if not isinstance(papers, list):
        raise ValueError("papers must be a list")

    measurements = []
    seen_ids = set()

    for paper in papers:
        for result in link_faradaic_efficiencies(paper):
            identifier = result["measurement_id"]

            if identifier in seen_ids:
                continue

            seen_ids.add(identifier)
            measurements.append(result)

    return measurements
