
# CuSelect-AI — Measurement Context Linking
#
# PSEUDOCODE
# 1. Load FE measurement candidates and source abstracts.
# 2. Match each measurement to its original publication.
# 3. Locate its exact source sentence.
# 4. Detect electrode potential and reference scale.
# 5. Detect current density and whether it is total/partial.
# 6. Detect explicitly reported Ag composition.
# 7. Preserve signs, units and approximation indicators.
# 8. Reject ambiguous or conflicting conditions.
# 9. Keep all linked conditions pending human review.
# 10. Never modify the original measurement records.

import re


NUMBER = r"[+−–-]?\s*\d+(?:\.\d+)?"
APPROX = r"(?:approximately|about|around|nearly|~|≈|∼)\s*"

POTENTIAL_PATTERN = re.compile(
    rf"(?P<approx>{APPROX})?"
    rf"(?P<value>{NUMBER})\s*V\s*"
    rf"(?:vs\.?\s*)?"
    rf"(?P<reference>RHE|SHE|NHE|Ag/AgCl)\b",
    re.IGNORECASE,
)

CURRENT_PATTERN = re.compile(
    rf"(?P<approx>{APPROX})?"
    rf"(?P<value>{NUMBER})\s*mA\s*"
    rf"(?:/\s*cm\s*\^?\s*2"
    rf"|[·⋅]\s*cm\s*(?:[−–-]\s*2|⁻²)"
    rf"|\s+cm\s*[−–-]\s*2)\b",
    re.IGNORECASE,
)

AG_COMPOSITION_PATTERN = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*%\s*Ag\b",
    re.IGNORECASE,
)

SENTENCE_BOUNDARY = re.compile(
    r"(?<=[.!?])\s+(?=[A-Z])|\n+"
)


def parse_signed_number(raw):
    """Convert Unicode signs and spacing to a float."""

    cleaned = (
        raw.replace("−", "-")
        .replace("–", "-")
        .replace(" ", "")
    )

    return float(cleaned)


def source_sentences(text):
    """Return sentence text and character offsets."""

    boundaries = [0]

    for match in SENTENCE_BOUNDARY.finditer(text):
        boundaries.append(match.end())

    boundaries.append(len(text))

    results = []

    for start, end in zip(boundaries, boundaries[1:]):
        raw = text[start:end]
        sentence = raw.strip()

        if not sentence:
            continue

        leading = len(raw) - len(raw.lstrip())

        results.append({
            "text": sentence,
            "start": start + leading,
            "end": start + leading + len(sentence),
        })

    return results


def find_measurement_sentence(abstract, measurement):
    """
    Locate the sentence containing the original
    FE measurement span.

    Reject missing or inconsistent offsets.
    """

    start = measurement.get("source_start")
    end = measurement.get("source_end")
    exact = measurement.get("exact_source_text")

    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end <= start
        or end > len(abstract)
        or abstract[start:end] != exact
    ):
        return None

    for sentence in source_sentences(abstract):
        if (
            sentence["start"] <= start
            and end <= sentence["end"]
        ):
            return sentence

    return None


def extract_potential(sentence):
    """Extract one unambiguous electrode potential."""

    matches = list(
        POTENTIAL_PATTERN.finditer(sentence)
    )

    if len(matches) != 1:
        return None, bool(matches)

    match = matches[0]

    return {
        "value_v": parse_signed_number(
            match.group("value")
        ),
        "reference": match.group("reference").upper(),
        "qualifier": (
            match.group("approx").strip()
            if match.group("approx") else None
        ),
        "exact_text": match.group(0).strip(),
    }, False


def extract_current_density(sentence):
    """Extract one unambiguous current-density value."""

    matches = list(
        CURRENT_PATTERN.finditer(sentence)
    )

    if len(matches) != 1:
        return None, bool(matches)

    match = matches[0]

    # Read nearby context before the numeric value.
    prefix = sentence[max(0, match.start() - 75):match.start()]

    total = bool(
        re.search(
            r"\btotal\s+current\s+density\b",
            prefix,
            re.IGNORECASE,
        )
    )

    partial = bool(
        re.search(
            r"\bpartial\s+current\s+density\b",
            prefix,
            re.IGNORECASE,
        )
    )

    if total and partial:
        current_type = "unknown"
    elif total:
        current_type = "total"
    elif partial:
        current_type = "partial"
    else:
        current_type = "unknown"

    return {
        "value_ma_cm2": parse_signed_number(
            match.group("value")
        ),
        "type": current_type,
        "qualifier": (
            match.group("approx").strip()
            if match.group("approx") else None
        ),
        "exact_text": match.group(0).strip(),
    }, False


def extract_ag_composition(sentence):
    """Extract one explicit Ag percentage."""

    matches = list(
        AG_COMPOSITION_PATTERN.finditer(sentence)
    )

    if len(matches) != 1:
        return None, bool(matches)

    match = matches[0]
    value = float(match.group("value"))

    if not 0 <= value <= 100:
        return None, True

    return {
        "element": "Ag",
        "value_percent": value,
        "percentage_basis": "unknown",
        "exact_text": match.group(0),
    }, False


def link_measurement_context(measurement, paper):
    """
    Attach same-sentence operating-condition candidates.

    This is contextual co-occurrence, not confirmation
    that the conditions apply to the FE value.
    """

    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a dictionary")

    if not isinstance(paper, dict):
        raise ValueError("paper must be a dictionary")

    result = dict(measurement)

    doi = str(measurement.get("doi") or "").lower()
    paper_doi = str(paper.get("doi") or "").lower()

    if not doi or doi != paper_doi:
        raise ValueError("Measurement and paper DOI mismatch")

    abstract = paper.get("abstract") or ""

    if not isinstance(abstract, str):
        raise ValueError("abstract must be a string")

    result.update({
        "potential_v": None,
        "reference_electrode": None,
        "potential_qualifier": None,
        "current_density_ma_cm2": None,
        "current_density_type": None,
        "current_density_qualifier": None,
        "ag_content_percent": None,
        "ag_percentage_basis": None,
        "conditions_source_text": None,
        "condition_matches": {},
        "context_link_status": "source_not_located",
        "conditions_review_status": "pending_human_review",
        "conditions_verified": False,
    })

    sentence = find_measurement_sentence(
        abstract, measurement
    )

    if sentence is None:
        return result

    text = sentence["text"]

    potential, potential_ambiguous = (
        extract_potential(text)
    )

    current, current_ambiguous = (
        extract_current_density(text)
    )

    composition, composition_ambiguous = (
        extract_ag_composition(text)
    )

    matches = {}

    if potential:
        result["potential_v"] = potential["value_v"]
        result["reference_electrode"] = (
            potential["reference"]
        )
        result["potential_qualifier"] = (
            potential["qualifier"]
        )
        matches["potential"] = potential["exact_text"]

    if current:
        result["current_density_ma_cm2"] = (
            current["value_ma_cm2"]
        )
        result["current_density_type"] = current["type"]
        result["current_density_qualifier"] = (
            current["qualifier"]
        )
        matches["current_density"] = (
            current["exact_text"]
        )

    if composition:
        result["ag_content_percent"] = (
            composition["value_percent"]
        )
        result["ag_percentage_basis"] = (
            composition["percentage_basis"]
        )
        matches["ag_composition"] = (
            composition["exact_text"]
        )

    result["conditions_source_text"] = text
    result["condition_matches"] = matches

    if any((
        potential_ambiguous,
        current_ambiguous,
        composition_ambiguous,
    )):
        result["context_link_status"] = (
            "ambiguous_context"
        )

    elif matches:
        result["context_link_status"] = (
            "same_sentence_candidates"
        )

    else:
        result["context_link_status"] = (
            "no_explicit_conditions"
        )

    return result


def link_corpus_context(measurements, papers):
    """Enrich measurements using their original abstracts."""

    if not isinstance(measurements, list):
        raise ValueError("measurements must be a list")

    if not isinstance(papers, list):
        raise ValueError("papers must be a list")

    paper_lookup = {
        str(paper["doi"]).strip().lower(): paper
        for paper in papers
    }

    results = []

    for measurement in measurements:
        doi = str(
            measurement.get("doi") or ""
        ).strip().lower()

        paper = paper_lookup.get(doi)

        if paper is None:
            result = dict(measurement)
            result["context_link_status"] = (
                "source_publication_missing"
            )
            result["conditions_verified"] = False
            result["conditions_review_status"] = (
                "pending_human_review"
            )
            results.append(result)
            continue

        results.append(
            link_measurement_context(
                measurement, paper
            )
        )

    return results
