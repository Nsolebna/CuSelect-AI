
# CuSelect-AI — Scientific Relevance Classification
#
# PSEUDOCODE
# 1. Receive discovered publication metadata.
# 2. Normalize the publication title.
# 3. Detect Cu, Ag, CO2 and electrochemical terminology.
# 4. Detect target products and mechanistic concepts.
# 5. Assign one conservative relevance category.
# 6. Record the reasons for the classification.
# 7. Preserve DOI and scientific verification status.
# 8. Never invent experimental evidence.

import re

from cuselect.discovery import normalize_title


def has_pattern(text, pattern):
    """Check whether a scientific term occurs in text."""
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def classify_relevance(paper):
    """
    Classify a publication using title metadata only.

    This is a relevance assessment, not scientific
    verification or experimental evidence extraction.
    """

    # PSEUDOCODE
    # 1. Validate the publication record.
    # 2. Normalize its title.
    # 3. Identify catalyst and reaction terminology.
    # 4. Identify ethylene, other C2+ products and CO.
    # 5. Classify using explicit title-level evidence.
    # 6. Return the result with a traceable explanation.

    if not isinstance(paper, dict):
        raise ValueError("paper must be a dictionary")

    title = paper.get("title", "")
    doi = paper.get("doi", "")

    if not isinstance(title, str):
        title = ""

    if not isinstance(doi, str):
        doi = ""

    text = normalize_title(title)

    copper = has_pattern(
        text,
        r"\b(?:copper|cu|cuo[x0-9]*|cu[0-9]+o[x0-9]*"
        r"|cu[0-9]*ag|ag[0-9]*cu)\b",
    )

    silver = has_pattern(
        text,
        r"\b(?:silver|ag|ag[0-9]*cu|cu[0-9]*ag)\b",
    )

    carbon_dioxide = has_pattern(
        text,
        r"\b(?:co2|co2rr)\b|carbon[\s-]+dioxide",
    )

    electrochemical = has_pattern(
        text,
        r"electroreduc|electrocatal|electrochem"
        r"|electrolys|co2rr",
    )

    ethylene = has_pattern(
        text,
        r"\b(?:ethylene|ethene|c2h4)\b",
    )

    other_c2 = has_pattern(
        text,
        r"\b(?:ethanol|acetate|acetic[\s-]+acid"
        r"|ethylene[\s-]+glycol|propanol"
        r"|c2[\s-]+products?|multicarbon)\b"
        r"|\bc2\+(?!\w)",
    )

    carbon_monoxide = has_pattern(
        text,
        r"\b(?:carbon[\s-]+monoxide|co[\s-]+intermediate"
        r"|co[\s-]+production|to[\s-]+co)\b",
    )

    tandem = has_pattern(
        text,
        r"\b(?:tandem|relay|cascade)\b",
    )

    interface = has_pattern(
        text,
        r"\b(?:interface|interfacial|core[\s-]+shell"
        r"|heterointerface)\b",
    )

    detected_terms = []

    for term, detected in [
        ("copper", copper),
        ("silver", silver),
        ("carbon_dioxide", carbon_dioxide),
        ("electrochemical", electrochemical),
        ("ethylene", ethylene),
        ("other_c2", other_c2),
        ("carbon_monoxide", carbon_monoxide),
        ("tandem", tandem),
        ("interface", interface),
    ]:
        if detected:
            detected_terms.append(term)

    # Require an explicitly identifiable Cu/Ag system
    # and CO2 electrochemistry for the specialized labels.
    target_system = (
        copper
        and silver
        and carbon_dioxide
        and electrochemical
    )

    if not text:
        category = "insufficient_information"
        reason = "Publication title is missing."

    elif target_system and ethylene:
        category = "direct_ethylene"
        reason = (
            "Title identifies a Cu/Ag CO2 electrochemical "
            "system and explicitly mentions ethylene."
        )

    elif target_system and other_c2:
        category = "other_c2_products"
        reason = (
            "Title identifies a Cu/Ag CO2 electrochemical "
            "system and a C2+ product or product class."
        )

    elif target_system and (
        tandem or interface or carbon_monoxide
    ):
        category = "mechanistic_support"
        reason = (
            "Title identifies a Cu/Ag CO2 electrochemical "
            "system with a potential mechanistic topic."
        )

    elif carbon_dioxide and (
        electrochemical or copper or silver
    ):
        category = "background"
        reason = (
            "Title suggests related CO2 research, but "
            "the specialized relevance criteria are unmet."
        )

    else:
        category = "insufficient_information"
        reason = (
            "Title alone does not establish relevance "
            "to the target Cu/Ag CO2RR system."
        )

    return {
        "doi": doi.strip().lower(),
        "title": title,
        "relevance_category": category,
        "relevance_reason": reason,
        "detected_terms": detected_terms,
        "classification_source": "title_only",
        "scientific_status": "unverified_discovery",
        "requires_human_review": True,
    }


def classify_publications(papers):
    """
    Classify a collection of publications and
    deduplicate records using normalized DOIs.
    """

    results = []
    seen_dois = set()

    for paper in papers:
        doi = str(paper.get("doi") or "").strip().lower()

        if not doi or doi in seen_dois:
            continue

        seen_dois.add(doi)

        # Preserve the original metadata.
        result = dict(paper)

        # Add conservative relevance classification.
        result.update(classify_relevance(paper))

        results.append(result)

    return results
