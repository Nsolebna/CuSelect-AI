
# CuSelect-AI — Abstract-Aware Scientific Screening
#
# PSEUDOCODE
# 1. Receive a publication with title and abstract.
# 2. Check whether an abstract is available.
# 3. Normalize the text for scientific keyword matching.
# 4. Identify catalyst architecture indicators.
# 5. Identify reported reaction-product terminology.
# 6. Identify experimental and computational methods.
# 7. Identify potential mechanistic concepts.
# 8. Store transparent classifications and matched terms.
# 9. Preserve publication metadata and source provenance.
# 10. Never interpret keyword matches as verified evidence.

import re

from cuselect.discovery import normalize_title


ARCHITECTURE_PATTERNS = {
    "alloy": r"\b(?:alloy|alloys|alloyed)\b",
    "tandem": r"\b(?:tandem|cascade|relay)\b",
    "core_shell": r"\bcore[\s-]*shell\b",
    "interface": (
        r"\b(?:interface|interfaces|interfacial"
        r"|heterointerface)\b"
    ),
    "nanoporous": r"\b(?:nanoporous|porous)\b",
}


PRODUCT_PATTERNS = {
    "ethylene": (
        r"\b(?:ethylene|ethene|c\s*2\s*h\s*4)\b"
    ),
    "ethanol": (
        r"\b(?:ethanol|c\s*2\s*h\s*5\s*oh)\b"
    ),
    "carbon_monoxide": (
        r"\bcarbon[\s-]+monoxide\b"
        r"|\bco[\s-]+intermediate"
        r"|\bco[\s-]+production\b"
    ),
    "acetate": (
        r"\b(?:acetate|acetic[\s-]+acid)\b"
    ),
    "methane": (
        r"\b(?:methane|ch\s*4)\b"
    ),
    "c2_plus": (
        r"\bc\s*2\s*\+(?!\w)"
        r"|\bc\s*2[\s-]+products?\b"
        r"|\bmulticarbon\b"
    ),
}


EXPERIMENTAL_PATTERNS = {
    "electrodeposition": r"\belectrodeposit\w*\b",
    "electrolysis": r"\belectrolys\w*\b",
    "faradaic_efficiency": (
        r"\bfaradaic[\s-]+efficien\w*\b"
    ),
    "raman": r"\braman\b",
    "exafs": r"\bexafs\b",
    "gas_chromatography": (
        r"\bgas[\s-]+chromatograph\w*\b"
    ),
}

COMPUTATIONAL_PATTERNS = {
    "dft": r"\bdft\b",
    "density_functional_theory": (
        r"\bdensity[\s-]+functional[\s-]+theory\b"
    ),
    "molecular_dynamics": (
        r"\bmolecular[\s-]+dynamics\b"
    ),
    "first_principles": (
        r"\bfirst[\s-]+principles\b"
    ),
}

MECHANISM_PATTERNS = {
    "co_intermediate": (
        r"\bco[\s-]+intermediate\w*\b"
    ),
    "spillover": r"\bspillover\b",
    "oxide_stabilization": (
        r"\b(?:oxide|cu2o)[\s-]+(?:overlayer|stabiliz\w*)\b"
        r"|\bstabiliz\w*[\s-]+(?:oxide|cu2o)\b"
    ),
    "c_c_coupling": (
        r"\bc[\s-]*c[\s-]+coupling\b"
    ),
    "adsorption": r"\badsorp\w*\b",
}


def detect_terms(text, patterns):
    """Return labels for explicitly matched keywords."""

    return [
        label
        for label, pattern in patterns.items()
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]


def classify_study_type(experimental, computational):
    """Infer study-type indicators from abstract terminology."""

    if experimental and computational:
        return "mixed_indicators"

    if experimental:
        return "experimental_indicators"

    if computational:
        return "computational_indicators"

    return "unknown"


def screen_abstract(paper):
    """
    Analyze publication abstract terminology.

    This is automated screening, not evidence verification.
    """

    if not isinstance(paper, dict):
        raise ValueError("paper must be a dictionary")

    result = dict(paper)

    abstract = result.get("abstract") or ""

    if not isinstance(abstract, str):
        raise ValueError("abstract must be a string")

    # Missing abstracts cannot receive reliable
    # abstract-level scientific classifications.
    if not abstract.strip():
        result.update({
            "abstract_screening_status": "abstract_unavailable",
            "architecture_indicators": [],
            "product_indicators": [],
            "experimental_indicators": [],
            "computational_indicators": [],
            "mechanism_indicators": [],
            "study_type_indicator": "unknown",
            "abstract_screening_version": "1.0",
            "requires_human_review": True,
        })

        return result

    text = normalize_title(abstract)

    architecture = detect_terms(
        text, ARCHITECTURE_PATTERNS
    )

    products = detect_terms(
        text, PRODUCT_PATTERNS
    )

    experimental = detect_terms(
        text, EXPERIMENTAL_PATTERNS
    )

    computational = detect_terms(
        text, COMPUTATIONAL_PATTERNS
    )

    mechanisms = detect_terms(
        text, MECHANISM_PATTERNS
    )

    study_type = classify_study_type(
        experimental, computational
    )

    result.update({
        "abstract_screening_status": "screened",
        "architecture_indicators": architecture,
        "product_indicators": products,
        "experimental_indicators": experimental,
        "computational_indicators": computational,
        "mechanism_indicators": mechanisms,
        "study_type_indicator": study_type,
        "abstract_screening_version": "1.0",
        "requires_human_review": True,
    })

    # An abstract mentioning a product or technique
    # does not establish a verified experimental claim.
    result["scientific_status"] = "unverified_discovery"

    return result


def screen_publications(papers):
    """Screen all publication records and retain their order."""

    if not isinstance(papers, list):
        raise ValueError("papers must be a list")

    return [
        screen_abstract(paper)
        for paper in papers
    ]
