
"""Conservative source-context checks for experimental FE claims."""

import re
from decimal import Decimal, InvalidOperation


PRODUCT_ALIASES = {
    "ethylene": ("ethylene", "c2h4", "ethene"),
    "ethanol": ("ethanol", "c2h5oh"),
    "formate": ("formate", "hcoo"),
    "carbon monoxide": ("carbon monoxide", "co"),
}


def _normalise(text):
    return " ".join(str(text or "").split()).lower()


def _fe_values(text):
    values = []
    for match in re.finditer(r"\d+(?:\.\d+)?\s*%", text):
        try:
            value = Decimal(match.group().replace("%", "").strip())
        except InvalidOperation:
            continue
        values.append((value, match.start(), match.end()))
    return values


def validate_measurement(claim, source_text):
    """Check explicit association without approving scientific evidence."""

    issues = []
    quote = str(claim.get("source_quote") or "").strip()
    source_text = str(source_text or "")

    if not quote or quote not in source_text:
        issues.append("Supporting quotation is absent from source.")
        return {
            "passed": False,
            "issues": issues,
            "scientifically_verified": False,
            "approved_for_rag": False,
        }

    product = _normalise(claim.get("product"))
    aliases = PRODUCT_ALIASES.get(product)

    if not aliases:
        issues.append("Product identity cannot be checked.")

    try:
        target_fe = Decimal(
            str(claim.get("faradaic_efficiency_percent"))
        )
        if not target_fe.is_finite():
            raise InvalidOperation()
    except (InvalidOperation, TypeError, ValueError):
        target_fe = None
        issues.append("Valid FE value is missing.")

    values = _fe_values(quote)

    matching = [
        (start, end)
        for value, start, end in values
        if value == target_fe
    ]

    if not matching:
        issues.append("FE value not present in quotation.")

    if aliases and matching:
        product_positions = []

        for alias in aliases:
            pattern = (
                r"(?<![a-z0-9])"
                + re.escape(alias)
                + r"(?![a-z0-9])"
            )
            product_positions.extend(
                match.start()
                for match in re.finditer(pattern, quote.lower())
            )

        if not product_positions:
            issues.append("Target product absent from quotation.")
        else:
            # Require the product to appear close to its
            # numerical FE. This is a heuristic, not proof.
            nearby = any(
                abs(position - start) <= 120
                for position in product_positions
                for start, _ in matching
            )

            if not nearby:
                issues.append(
                    "Product and FE are not sufficiently close."
                )

    catalyst = _normalise(claim.get("catalyst_system"))

    if not catalyst:
        issues.append("Catalyst identity missing.")
    elif catalyst not in _normalise(quote):
        issues.append(
            "Catalyst identity not explicitly present in quotation."
        )

    measurement_type = claim.get("measurement_type")

    if measurement_type != "single_electrode":
        issues.append(
            "Single-electrode FE identity not established."
        )

    return {
        "passed": not issues,
        "issues": issues,
        "scientifically_verified": False,
        "approved_for_rag": False,
        "check_scope": (
            "Automated quotation and proximity screening; "
            "product-catalyst attribution and measurement "
            "validity still require scientific review."
        ),
    }
