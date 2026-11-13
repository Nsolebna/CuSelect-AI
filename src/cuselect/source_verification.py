"""Conservative checks for source-grounded experimental claims."""

import re
from decimal import Decimal, InvalidOperation


def verify_source_claim(claim, source_text, *, source_type="abstract"):
    """Check quotation and numeric traceability, not scientific validity."""

    if source_type not in {"abstract", "full_text", "supplement"}:
        raise ValueError("Unsupported source type.")

    quote = str(claim.get("source_quote") or "").strip()
    source_text = str(source_text or "")
    issues = []

    if not quote or quote not in source_text:
        issues.append("Source quotation not found verbatim.")

    value = claim.get("faradaic_efficiency_percent")

    if value is not None:
        try:
            fe = Decimal(str(value))
            if not fe.is_finite():
                issues.append("FE must be finite.")
            elif not 0 <= fe <= 100:
                issues.append(
                    "FE outside 0–100%; requires measurement review."
                )
        except (InvalidOperation, ValueError):
            issues.append("Invalid numerical FE.")
            fe = None

        # Check the quoted passage, not merely the article.
        numbers = re.findall(
            r"(?<![\w.])\d+(?:\.\d+)?\s*%",
            quote,
        )
        numeric_matches = []

        for number in numbers:
            try:
                numeric_matches.append(
                    Decimal(number.replace("%", "").strip())
                )
            except InvalidOperation:
                pass

        if (
            fe is not None
            and fe.is_finite()
            and fe not in numeric_matches
        ):
            issues.append(
                "Extracted FE has no matching percentage in quote."
            )

    measurement = claim.get("measurement_type")

    if measurement not in {
        "single_electrode",
        "system_level",
        "not_specified",
    }:
        issues.append("Invalid measurement type.")

    if measurement != "single_electrode":
        issues.append(
            "Single-electrode measurement not established."
        )

    if not str(claim.get("product") or "").strip():
        issues.append("Product identity missing.")

    if not str(claim.get("doi") or "").strip():
        issues.append("DOI missing.")

    if not str(claim.get("catalyst_system") or "").strip():
        issues.append("Catalyst identity missing.")

    passed = not issues

    return {
        "doi": claim.get("doi"),
        "source_type": source_type,
        "source_quote": quote,
        "traceability_checks_passed": passed,
        "issues": issues,
        "verification_status": (
            "automated_traceability_passed"
            if passed else "review_required"
        ),
        "scientifically_verified": False,
        "approved_for_rag": False,
    }
