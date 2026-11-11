"""Conservative dynamic retrieval from the verified scientific corpus.

PSEUDOCODE
1. Accept a source question only.
2. Reject unsupported scientific question categories.
3. Load the authoritative trusted corpus.
4. Run the existing citation-audited RAG service.
5. Require one unambiguous supporting record.
6. Check catalyst, product and any explicitly requested FE.
7. Return the trusted result or abstain.

This module does not modify the existing Literature Agent.
"""

import re
from pathlib import Path

from .evidence_store import load_verified_corpus
from .agents import ResearchTask
from .legacy_agents import EvidenceResult, UNSUPPORTED_TERMS
from .rag import lexical_tokens, run_rag_question


def abstain(reason="insufficient_retrieval_support"):
    return EvidenceResult(
        ids=(),
        independent_publications=0,
        status=reason,
        answer="Insufficient human-verified evidence for this request.",
        citation_audit_passed=False,
    )


def normalized(text):
    return " ".join(
        re.findall(r"[a-z0-9]+", str(text).casefold())
    )



def scientific_match(question, record):
    """Conservatively match trusted FE records to catalyst questions."""

    q = normalized(question)

    # PSEUDOCODE
    # 1. Identify the catalyst explicitly named in the question.
    # 2. Confirm that identity in the trusted record.
    # 3. Require the correct product.
    # 4. Reject conflicting FE values or explicit potentials.
    # 5. Never authorize evidence outside the trusted RAG result.

    aliases = ("ag1cu nw", "agcu nw")

    query_aliases = [
        alias for alias in aliases
        if re.search(r"(?<![a-z0-9])" + re.escape(alias)
                     + r"(?![a-z0-9])", q)
    ]

    if len(query_aliases) != 1:
        return False

    record_text = normalized(" ".join([
        str(record.get("catalyst_system", "")),
        str(record.get("claim_paraphrase", "")),
    ]))

    record_aliases = [
        alias for alias in aliases
        if re.search(r"(?<![a-z0-9])" + re.escape(alias)
                     + r"(?![a-z0-9])", record_text)
    ]

    if set(record_aliases) != set(query_aliases):
        return False

    # PSEUDOCODE
    # 1. Normalize the product formula or chemical name.
    # 2. Match it to a controlled chemical identity.
    # 3. Require the correct product in the question.
    # 4. Reject ambiguous or conflicting product identities.

    product_aliases = {
        "ethylene": {"ethylene", "ethene", "c2h4"},
        "ethanol": {"ethanol", "ethyl alcohol", "c2h5oh"},
    }

    product = normalized(record.get("fe_product", ""))

    identified = [
        chemical
        for chemical, aliases in product_aliases.items()
        if product in {normalized(a) for a in aliases}
    ]

    if len(identified) != 1:
        return False

    chemical = identified[0]

    query_products = {
        name
        for name, aliases in product_aliases.items()
        if any(
            re.search(
                r"(?<![a-z0-9])" + re.escape(normalized(alias))
                + r"(?![a-z0-9])",
                q,
            )
            for alias in aliases
        )
    }

    if query_products != {chemical}:
        return False

    fe = str(
        record.get("faradaic_efficiency_percent", "")
    ).strip()

    if not fe:
        return False

    requested_fe = re.findall(
        r"(?<![\w.])(\d+(?:\.\d+)?)\s*%",
        question,
    )

    if requested_fe:
        if len(requested_fe) != 1:
            return False

        try:
            if abs(float(requested_fe[0]) - float(fe)) > 1e-6:
                return False
        except ValueError:
            return False

    if re.search(
        r"[+-]?\d+(?:\.\d+)?\s*v\s*(?:vs\.?\s*rhe)?",
        question,
        flags=re.IGNORECASE,
    ):
        return False

    return True


def dynamic_literature_agent(
    task: ResearchTask,
    *,
    project_root: str | Path = ".",
) -> EvidenceResult:
    """Experimental adapter; uses only existing trusted evidence."""

    if not isinstance(task, ResearchTask):
        raise TypeError("Expected ResearchTask")

    if task.task_type != "source_question":
        return abstain("not_applicable")

    if not task.question.strip() or task.candidate_ids:
        return abstain("unsupported_question")

    terms = set(lexical_tokens(task.question))

    if terms & UNSUPPORTED_TERMS:
        return abstain("unsupported_question")

    # These request types are not established by simple FE retrieval.
    if terms & {
        "why", "explain", "cause", "causes",
        "prove", "proof", "maximum", "minimum",
        "highest", "lowest",
    }:
        return abstain("unsupported_question")

    # Trusted loader detects corpus integrity failures.
    records = load_verified_corpus(project_root)

    response = run_rag_question(
        task.question,
        records,
        top_k=3,
    )

    if (
        response.get("decision") != "evidence_found"
        or response.get("citation_audit_passed") is not True
    ):
        return abstain()

    ids = tuple(response.get("cited_ids", ()))

    # Never select between conflicting or multiple measurements
    # using this provisional matching policy.
    if len(ids) != 1:
        return abstain("ambiguous_evidence")

    record_by_id = {
        record["evidence_id"]: record
        for record in records
    }

    record = record_by_id.get(ids[0])

    if record is None or not scientific_match(task.question, record):
        return abstain()

    return EvidenceResult(
        ids=ids,
        independent_publications=1,
        status="matched_reviewed_observation",
        answer=response["answer"],
        citation_audit_passed=True,
    )
