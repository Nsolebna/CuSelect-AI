"""Conservative synthesis of hybrid scientific research results."""


import re


# SOURCE-GROUNDED SCIENTIFIC CONTEXT
def _relevant_source_passages(question, source_abstracts, limit=3):
    """Select short source excerpts, not generated experimental claims."""
    terms = {
        word.lower()
        for word in re.findall(r"[A-Za-z]{3,}", question)
        if word.lower() not in {
            "why", "how", "does", "what", "need", "adding",
            "with", "from", "into", "the", "and", "for",
            "electroreduction", "carbon", "dioxide",
        }
    }

    mechanism_terms = {
        "mechanism", "intermediate", "tandem", "synergy",
        "synergistic", "coupling", "adsorption", "selectivity",
        "formation", "pathway", "transfer", "interface",
    }

    candidates = []

    for doi, abstract in source_abstracts.items():
        doi = str(doi).strip()
        abstract = str(abstract).strip()

        if not doi.startswith("10.") or not abstract:
            continue

        sentences = re.split(r"(?<=[.!?])\\s+", abstract)

        for sentence in sentences:
            words = set(re.findall(r"[A-Za-z]{3,}", sentence.lower()))
            score = (
                2 * len(terms & words)
                + len(mechanism_terms & words)
            )

            if score > 0:
                candidates.append((score, doi, sentence.strip()))

    candidates.sort(key=lambda item: item[0], reverse=True)

    selected = []
    used_dois = set()

    for _, doi, sentence in candidates:
        if doi in used_dois:
            continue

        words = sentence.split()
        excerpt = " ".join(words[:25])

        if len(words) > 25:
            excerpt += " ..."

        selected.append(
            '- "' + excerpt + '" (DOI: ' + doi + ')'
        )
        used_dois.add(doi)

        if len(selected) >= limit:
            break

    return selected


def synthesize_research_answer(result):
    """Create an answer without promoting provisional claims."""

    question = str(result.get("question") or "").strip()
    verified = result.get("verified_evidence") or {}
    publications = result.get("global_publications") or []

    if not question:
        raise ValueError("Research question is missing.")

    if verified.get("citation_audit_passed") is not True:
        raise RuntimeError("Internal evidence citation audit failed.")

    if verified.get("draft_filter_passed") is not True:
        raise RuntimeError(
            "Draft-evidence safeguard has not been confirmed."
        )

    decision = verified.get("decision")
    cited_ids = verified.get("cited_ids") or []

    if decision not in {"evidence_found", "answer", "abstain"}:
        raise RuntimeError("Unsupported RAG decision.")

    if decision in {"evidence_found", "answer"} and not cited_ids:
        raise RuntimeError("Evidence answer lacks citations.")

    if decision == "abstain" and cited_ids:
        raise RuntimeError("Abstention cannot cite evidence.")

    if any("draft" in str(cid).lower() for cid in cited_ids):
        raise RuntimeError("Draft evidence appeared in citations.")

    if result.get("global_claims_verified") is not False:
        raise RuntimeError(
            "Global claims must remain unverified at this stage."
        )

    for paper in publications:
        if paper.get("experimental_claims_verified") is not False:
            raise RuntimeError(
                "Provisional publication incorrectly marked verified."
            )

    sections = []

    if decision in {"evidence_found", "answer"}:
        sections.append(
            "**Findings from the reviewed local corpus**\n\n"
            + str(verified.get("answer") or "").strip()
        )
    else:
        sections.append(
            "**Local evidence**\n\n"
            "The current reviewed corpus does not provide "
            "a sufficient supported answer to this question."
        )

    if publications:
        entries = []

        for paper in publications[:5]:
            title = str(paper.get("title") or "Untitled paper")
            doi = str(paper.get("doi") or "").strip()
            assessment = paper.get("assessment") or {}
            relevance = assessment.get(
                "relevance", "not_assessed"
            )

            entry = "- " + title

            if doi:
                entry += " (DOI: " + doi + ")"

            entry += " — " + relevance.replace("_", " ")

            entries.append(entry)

        sections.append(
            "**Additional publications identified by live search**"
            "\n\n" + "\n".join(entries)
            + "\n\nThese are provisionally screened publications, "
            "not independently verified experimental claims."
        )
    else:
        sections.append(
            "**Global literature search**\n\n"
            "No directly relevant publications were retained "
            "by the current screening process. This does not "
            "establish that none exist."
        )

    source_passages = _relevant_source_passages(
        question,
        result.get("source_abstracts") or {},
    )

    if source_passages:
        sections.append(
            "**Relevant scientific source passages**\n\n"
            + "\n".join(source_passages)
            + "\n\nThese are excerpts from publication "
            "abstracts, not independently verified "
            "experimental findings. They should not "
            "be treated as proof of a mechanism."
        )

    if result.get("screening_complete") is False:
        sections.append(
            "**Screening limitation**\n\n"
            "Some literature-screening operations were incomplete."
        )

    performance_question = any(
        term in question.lower()
        for term in (
            "world record",
            "worldwide record",
            "highest reported",
            "best performing",
            "state of the art",
        )
    )

    if performance_question:
        conclusion = (
            "The available evidence does not establish a "
            "worldwide performance record. Quantitative "
            "comparisons require verification of primary "
            "measurements and operating conditions."
        )
    else:
        conclusion = (
            "The retrieved literature provides preliminary "
            "scientific context, but this extractive summary "
            "does not yet establish a complete mechanistic "
            "explanation. Specific proposed pathways require "
            "source-level evaluation and critical synthesis."
        )

    sections.append(
        "**Scientific conclusion**\n\n" + conclusion
    )

    return {
        "question": question,
        "answer": "\n\n".join(sections),
        "status": "evidence_limited_synthesis",
        "verified_citation_ids": cited_ids,
        "provisional_publication_count": len(publications),
        "global_claims_verified": False,
        "citation_audit_passed": True,
        "files_modified": False,
        "computation_executed": False,
    }
