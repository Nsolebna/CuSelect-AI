
# CuSelect-AI — Phase II
# Module: src/cuselect/rag.py
#
# PSEUDOCODE
# 1. Accept evidence records already approved by the evidence pipeline.
# 2. Normalize scientific text and tokenize it.
# 3. Calculate document frequency and average document length.
# 4. Score matching evidence using the Notebook 06 BM25-style formula.
# 5. Sort results deterministically and preserve citation metadata.
# 6. Return no matches when the corpus or query cannot support retrieval.
# 7. Never interpret retrieval scores as scientific validation.

from collections import Counter
import math
import re
import statistics


STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "for",
    "in", "of", "from", "to", "on", "at", "and", "or",
    "with", "which", "what", "who", "does", "do", "did",
    "this", "that", "reported", "report", "by", "as",
    "it", "their", "its", "about", "show", "give",
    "value", "values", "there", "has", "have", "had",
    "under", "how", "much", "many",
}


def lexical_tokens(text: str) -> list[str]:
    """Normalize and tokenize scientific text."""
    plain = str(text).lower()

    for old, new in [
        ("₁", "1"),
        ("₂", "2"),
        ("₄", "4"),
        ("₅", "5"),
        ("₆", "6"),
    ]:
        plain = plain.replace(old, new)

    plain = plain.replace("co₂", "co2")
    plain = plain.replace("co−", "co-")
    plain = plain.replace(
        "faradaic efficiencies",
        "faradaic efficiency",
    )

    tokens = re.findall(r"[a-z0-9]+", plain)

    return [
        token
        for token in tokens
        if token not in STOPWORDS
    ]


def lexical_retrieve(
    question: str,
    approved_records: list[dict],
    *,
    top_k: int = 3,
) -> list[dict]:
    """
    Retrieve ranked evidence using the Notebook 06 scoring formula.

    Important:
        approved_records must already have passed the
        authoritative human-review and evidence-validation
        gates. This function does not grant approval.
    """

    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise ValueError("top_k must be a positive integer")

    if top_k < 1:
        raise ValueError("top_k must be a positive integer")

    if not approved_records:
        return []

    term_lists = [
        lexical_tokens(record["text"])
        for record in approved_records
    ]

    doc_freq = Counter(
        token
        for tokens in term_lists
        for token in set(tokens)
    )

    lengths = [len(tokens) for tokens in term_lists]

    if not any(lengths):
        return []

    mean_length = statistics.mean(lengths)

    query_terms = set(lexical_tokens(question))
    n_docs = len(approved_records)

    ranked = []

    for record, doc_tokens in zip(
        approved_records,
        term_lists,
    ):
        counts = Counter(doc_tokens)
        score = 0.0

        for word in query_terms:
            tf = counts.get(word, 0)

            if not tf:
                continue

            df = doc_freq[word]

            idf = math.log(
                1 + (n_docs - df + 0.5) / (df + 0.5)
            )

            denominator = (
                tf
                + 1.2 * (
                    1 - 0.75
                    + 0.75 * len(doc_tokens) / mean_length
                )
            )

            score += idf * (tf * 2.2) / denominator

        if score > 0:
            ranked.append({
                "evidence_id": record["evidence_id"],
                "score": round(score, 6),
                "record": record,
            })

    return sorted(
        ranked,
        key=lambda item: (
            -item["score"],
            item["evidence_id"],
        ),
    )[:top_k]


# PSEUDOCODE
# 1. Identify requests beyond currently verified scientific scope.
# 2. Select records with the correct review status and provenance fields.
# 3. Filter measurement type and requested product before retrieval.
# 4. Retrieve matching evidence using our existing lexical ranker.
# 5. Construct a source-linked extractive scientific answer.
# 6. Abstain when no eligible evidence supports the question.
# 7. Never infer catalyst rankings or unmeasured performance.

UNSUPPORTED_TERMS = {
    "durability", "lifetime", "stability", "stable",
    "degradation", "degrade", "kinetics", "activation",
    "barrier", "adsorption", "desorption", "dft",
    "energy", "energies", "bandgap", "conductivity",
    "hours", "hour", "overpotential", "turnover",
    "mechanism", "mechanistic", "intermediate",
    "toxicity", "commercialization", "cost", "price",
    "synthesis",
}

RANKING_TERMS = {
    "best", "optimal", "optimum", "superior",
    "outperform", "guaranteed", "proven",
    "definitively", "rank",
}

SUPPORTED_QUERY_TERMS = {
    "ethylene", "ethanol", "c2h4", "c2h5oh",
    "faradaic", "fe", "efficiency", "efficiencies",
    "ratio", "ratios", "selectivity",
    "observation", "observations",
    "experimental", "evidence",
}


def _field(record: dict, name: str) -> str:
    """Read a text field without converting missing values to 'None'."""
    value = record.get(name)
    return "" if value is None else str(value).strip()


def _abstain(reason: str) -> dict:
    return {
        "decision": "abstain",
        "reason": reason,
        "answer": "Insufficient human-verified evidence for this request.",
        "cited_ids": [],
        "hits": [],
    }


def answer_from_verified(
    question: str,
    records: list[dict],
    *,
    top_k: int = 3,
) -> dict:
    """Construct a constrained, extractive evidence response."""

    terms = set(lexical_tokens(question))

    blocked = terms & (UNSUPPORTED_TERMS | RANKING_TERMS)

    if blocked:
        return _abstain(
            "Unsupported claim scope: " + ", ".join(sorted(blocked))
        )

    if not terms & SUPPORTED_QUERY_TERMS:
        return _abstain(
            "Question outside the reviewed FE/product-ratio scope"
        )

    required_fields = (
        "evidence_id",
        "doi",
        "source_extent",
        "source_location",
        "text",
    )

    eligible = [
        record
        for record in records
        if record.get("review_status") == "human_verified"
        and all(_field(record, key) for key in required_fields)
    ]

    # Filter by measurement type before ranking.
    if terms & {"ratio", "ratios"}:
        eligible = [
            record
            for record in eligible
            if "ratio" in _field(
                record, "target_or_observation"
            ).lower()
        ]

    elif terms & {
        "fe", "faradaic", "efficiency", "efficiencies"
    }:
        eligible = [
            record
            for record in eligible
            if _field(record, "faradaic_efficiency_percent")
        ]

        wants_ethylene = bool(terms & {"ethylene", "c2h4"})
        wants_ethanol = bool(terms & {"ethanol", "c2h5oh"})

        if wants_ethylene and not wants_ethanol:
            eligible = [
                record
                for record in eligible
                if _field(record, "fe_product").lower() == "c2h4"
            ]

        elif wants_ethanol and not wants_ethylene:
            eligible = [
                record
                for record in eligible
                if _field(record, "fe_product").lower() == "c2h5oh"
            ]

    hits = lexical_retrieve(
        question,
        eligible,
        top_k=top_k,
    )

    if not hits:
        return _abstain(
            "No approved record supports the requested measurement"
        )

    lines = [
        "Retrieved, human-verified experimental observations "
        "(not model predictions):"
    ]

    cited_ids = []

    for hit in hits:
        record = hit["record"]

        evidence_id = _field(record, "evidence_id")
        cited_ids.append(evidence_id)

        observation = (
            _field(record, "claim_paraphrase")
            or _field(record, "target_or_observation")
        )

        fe = _field(record, "faradaic_efficiency_percent")

        detail = (
            f"FE: {fe}%"
            if fe
            else "No structured FE (different measurement type)"
        )

        conditions = _field(record, "conditions")
        context = (
            f"Reported conditions: {conditions}."
            if conditions
            else "Conditions are not structured in the approved record."
        )

        lines.append(
            f"- {_field(record, 'catalyst_system')}: "
            f"{observation} ({detail}). "
            f"[{evidence_id}] "
            f"DOI: {_field(record, 'doi')}; "
            f"source: {_field(record, 'source_extent')}, "
            f"{_field(record, 'source_location')}. "
            f"{context}"
        )

    lines.append(
        "Scope: records currently originate from one publication; "
        "reported results may differ in product and operating potential."
    )

    lines.append(
        "No intrinsic catalyst ranking, mechanism, DFT result, "
        "or general CO2RR selectivity predicted."
    )

    return {
        "decision": "evidence_found",
        "reason": "Eligible reviewed records retrieved",
        "answer": "\n".join(lines),
        "cited_ids": cited_ids,
        "hits": hits,
    }


# PSEUDOCODE
# 1. Accept a constructed answer and a trusted evidence snapshot.
# 2. Validate the answer decision and citation structure.
# 3. Resolve each cited ID to its original reviewed record.
# 4. Reject missing, duplicated, modified, or unreviewed records.
# 5. Reconstruct the exact expected extractive answer.
# 6. Reject any unexplained numerical or textual modification.
# 7. Never grant scientific approval to arbitrary LLM output.

CITATION_RE = re.compile(r"\[(E-[A-Z0-9-]+)\]")


def verify_extractive_answer(
    result: dict,
    reference_records: list[dict],
) -> bool:
    """Verify a deterministic extractive answer against reference records."""

    if not isinstance(result, dict):
        return False

    answer = result.get("answer")

    if not isinstance(answer, str):
        return False

    if result.get("decision") == "abstain":
        return (
            result.get("cited_ids") == []
            and result.get("hits") == []
            and answer
            == "Insufficient human-verified evidence for this request."
            and not CITATION_RE.search(answer)
        )

    if result.get("decision") != "evidence_found":
        return False

    if result.get("reason") != "Eligible reviewed records retrieved":
        return False

    hits = result.get("hits")
    cited_ids = result.get("cited_ids")

    if not isinstance(hits, list) or not hits:
        return False

    if not isinstance(cited_ids, list):
        return False

    if len(hits) != len(cited_ids):
        return False

    if len(cited_ids) != len(set(cited_ids)):
        return False

    ids_in_text = CITATION_RE.findall(answer)

    if ids_in_text != cited_ids:
        return False

    reference_by_id = {}

    for record in reference_records:
        if not isinstance(record, dict):
            return False

        evidence_id = _field(record, "evidence_id")

        if not evidence_id or evidence_id in reference_by_id:
            return False

        reference_by_id[evidence_id] = record

    expected_lines = [
        "Retrieved, human-verified experimental observations "
        "(not model predictions):"
    ]

    for hit, evidence_id in zip(hits, cited_ids):
        if not isinstance(hit, dict):
            return False

        if hit.get("evidence_id") != evidence_id:
            return False

        original = reference_by_id.get(evidence_id)

        if original is None:
            return False

        if original.get("review_status") != "human_verified":
            return False

        for field in ("doi", "source_extent", "source_location", "text"):
            if not _field(original, field):
                return False

        if hit.get("record") != original:
            return False

        observation = (
            _field(original, "claim_paraphrase")
            or _field(original, "target_or_observation")
        )

        fe = _field(
            original,
            "faradaic_efficiency_percent",
        )

        detail = (
            f"FE: {fe}%"
            if fe
            else "No structured FE (different measurement type)"
        )

        conditions = _field(original, "conditions")

        context = (
            f"Reported conditions: {conditions}."
            if conditions
            else "Conditions are not structured in the approved record."
        )

        expected_lines.append(
            f"- {_field(original, 'catalyst_system')}: "
            f"{observation} ({detail}). "
            f"[{evidence_id}] "
            f"DOI: {_field(original, 'doi')}; "
            f"source: {_field(original, 'source_extent')}, "
            f"{_field(original, 'source_location')}. "
            f"{context}"
        )

    expected_lines.append(
        "Scope: records currently originate from one publication; "
        "reported results may differ in product and operating potential."
    )

    expected_lines.append(
        "No intrinsic catalyst ranking, mechanism, DFT result, "
        "or general CO2RR selectivity predicted."
    )

    return answer == "\n".join(expected_lines)


# PSEUDOCODE
# 1. Receive a research question and trusted evidence records.
# 2. Retrieve evidence and construct an extractive response.
# 3. Run the citation-consistency verifier.
# 4. Fail closed if verification fails.
# 5. Return a structured response for the agent orchestrator.

def run_rag_question(
    question: str,
    verified_records: list[dict],
    *,
    top_k: int = 3,
) -> dict:
    """Run the deterministic scientific RAG pipeline."""

    result = answer_from_verified(
        question,
        verified_records,
        top_k=top_k,
    )

    audit_passed = verify_extractive_answer(
        result,
        verified_records,
    )

    if not audit_passed:
        raise RuntimeError(
            "RAG citation-consistency verification failed"
        )

    return {
        "question": question,
        "decision": result["decision"],
        "reason": result["reason"],
        "answer": result["answer"],
        "cited_ids": result["cited_ids"],
        "retrieved_count": len(result["hits"]),
        "citation_audit_passed": True,
        "generation_mode": "deterministic_extractive",
    }
