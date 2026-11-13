
"""Transparent product-intent interpretation for CO2RR research."""

import re

PRODUCTS = {
    "Ethylene (C₂H₄)": "ethylene",
    "Ethanol (C₂H₅OH)": "ethanol",
    "Carbon monoxide (CO)": "co",
    "Formate (HCOO⁻)": "formate",
}

PATTERNS = {
    "ethylene": [
        r"\bethylene\b",
        r"\bethene\b",
        r"\bC2H4\b",
        r"C₂H₄",
    ],
    "ethanol": [
        r"\bethanol\b",
        r"\bethyl alcohol\b",
        r"\bC2H5OH\b",
        r"C₂H₅OH",
    ],
    "co": [
        r"\bcarbon monoxide\b",
        r"(?<![A-Za-z0-9])CO(?![A-Za-z0-9₂])",
    ],
    "formate": [
        r"\bformate\b",
        r"\bformic acid\b",
        r"HCOO[⁻-]?",
    ],
    "propanol": [
        r"\b(?:1-)?propanol\b",
        r"\b(?:n-)?propyl alcohol\b",
        r"\bC3H7OH\b",
        r"C₃H₇OH",
    ],
    "methanol": [
        r"\bmethanol\b",
        r"\bCH3OH\b",
        r"CH₃OH",
    ],
    "methane": [
        r"\bmethane\b",
        r"\bCH4\b",
        r"CH₄",
    ],
    "acetate": [
        r"\bacetate\b",
        r"\bacetic acid\b",
    ],
}

def interpret_request(objective, selected_product):
    objective = str(objective).strip()

    if not objective:
        return {
            "status": "invalid",
            "message": "Enter a research objective.",
        }

    found = sorted(
        product
        for product, expressions in PATTERNS.items()
        if any(
            re.search(pattern, objective, re.IGNORECASE)
            for pattern in expressions
        )
    )

    supported = set(PRODUCTS.values())
    unsupported = sorted(set(found) - supported)

    if unsupported:
        return {
            "status": "unsupported_product",
            "message": (
                "The research question mentions an unsupported "
                "product: " + ", ".join(unsupported) + ". "
                "Add verified evidence and supported design "
                "templates before running this request."
            ),
            "detected_products": found,
        }

    if len(found) > 1:
        return {
            "status": "ambiguous",
            "message": (
                "Multiple products were recognized: "
                + ", ".join(found)
                + ". Specify one target product for this run."
            ),
            "detected_products": found,
        }

    chosen = PRODUCTS.get(selected_product)

    if chosen is None:
        return {
            "status": "invalid",
            "message": "Select a supported target product.",
            "detected_products": found,
        }

    if found and found[0] != chosen:
        return {
            "status": "conflict",
            "message": (
                f"Your question mentions {found[0]}, "
                f"but the dropdown selects {chosen}. "
                "Please correct the selection or your question."
            ),
            "detected_products": found,
            "selected_product": chosen,
        }

    return {
        "status": "ready",
        "target_product": chosen,
        "detected_products": found,
        "message": (
            f"Target product confirmed: {chosen}."
            if found else
            "No explicit target product recognized in the "
            "question. Using the dropdown selection: "
            f"{chosen}."
        ),
        "interpretation_method": "rule_based_product_matching",
    }
