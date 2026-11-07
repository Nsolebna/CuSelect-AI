
# CuSelect-AI — Phase II
# Module: src/cuselect/agents.py
#
# PSEUDOCODE
# 1. Define immutable research-task and literature-result objects.
# 2. Reject unknown task types and unsupported scientific requests.
# 3. Recognize the three question categories approved in Notebook 07.
# 4. Load scientific evidence through the trusted registry gate.
# 5. Call the reusable RAG service and verify its result.
# 6. Require the cited evidence ID to match the admitted question.
# 7. Return an auditable result or abstain.
# 8. Never grant model approval, call an LLM, or change evidence.

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .evidence_store import load_verified_corpus
from .rag import lexical_tokens, run_rag_question


TaskType = Literal[
    "source_question",
    "structure_hypothesis",
    "predict_selectivity",
]


@dataclass(frozen=True)
class ResearchTask:
    task_id: str
    task_type: TaskType
    question: str
    candidate_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceResult:
    ids: tuple[str, ...]
    independent_publications: int
    status: str
    answer: str = ""
    citation_audit_passed: bool = False


MAX_EVIDENCE = 3

UNSUPPORTED_TERMS = {
    "durability", "lifetime", "stability", "stable",
    "degradation", "kinetics", "activation", "barrier",
    "adsorption", "desorption", "dft", "energy",
    "mechanism", "mechanistic", "predict", "prediction",
    "forecast", "ranking", "rank", "best", "optimal",
    "superior", "outperform", "better", "compare",
    "comparison", "hour", "hours",
}


def _abstain_literature(status: str) -> EvidenceResult:
    return EvidenceResult(
        ids=(),
        independent_publications=0,
        status=status,
        answer="Insufficient human-verified evidence for this request.",
        citation_audit_passed=False,
    )


def _admitted_evidence_id(question: str) -> str | None:
    """Recognize the narrow measurement cases from Notebook 07."""

    normalized = (
        question.casefold()
        .replace("₁", "1")
        .replace("–", "-")
    )

    terms = set(lexical_tokens(normalized))

    if terms & UNSUPPORTED_TERMS:
        return None

    if (
        terms & {"ratio", "ratios"}
        and "ethanol" in terms
        and "ethylene" in terms
    ):
        return "E-DRAFT-001"

    asks_fe = bool(
        terms & {
            "fe", "faradaic", "efficiency", "efficiencies"
        }
    )

    if (
        asks_fe
        and "ethylene" in terms
        and "ethanol" not in terms
        and "agcu nw" in normalized
        and "ag1cu nw" not in normalized
    ):
        return "E-P005-FE-C2H4-001"

    if (
        asks_fe
        and "ethanol" in terms
        and "ethylene" not in terms
        and "ag1cu nw" in normalized
    ):
        return "E-P005-FE-ETOH-001"

    return None


def literature_agent(
    task: ResearchTask,
    *,
    project_root: str | Path = ".",
) -> EvidenceResult:
    """Run the conservative literature role with trusted RAG."""

    if not isinstance(task, ResearchTask):
        raise TypeError("Expected a ResearchTask")

    if task.task_type not in {
        "source_question",
        "structure_hypothesis",
        "predict_selectivity",
    }:
        raise ValueError("Unknown research task type")

    if task.task_type != "source_question":
        return EvidenceResult(
            ids=(),
            independent_publications=0,
            status="not_applicable",
        )

    if not isinstance(task.question, str) or not task.question.strip():
        return _abstain_literature("unsupported_question")

    if task.candidate_ids:
        return _abstain_literature("unsupported_question")

    terms = set(lexical_tokens(task.question))

    if terms & UNSUPPORTED_TERMS:
        return _abstain_literature("unsupported_question")

    expected_id = _admitted_evidence_id(task.question)

    if expected_id is None:
        return _abstain_literature(
            "insufficient_retrieval_support"
        )

    # Integrity failures are deliberately not suppressed.
    records = load_verified_corpus(project_root)

    response = run_rag_question(
        task.question,
        records,
        top_k=MAX_EVIDENCE,
    )

    cited_ids = tuple(response["cited_ids"])

    # Fail closed if retrieval returns a different evidence set.
    if (
        response["decision"] != "evidence_found"
        or not response["citation_audit_passed"]
        or cited_ids != (expected_id,)
    ):
        return _abstain_literature(
            "insufficient_retrieval_support"
        )

    record_by_id = {
        record["evidence_id"]: record
        for record in records
    }

    independent_publications = len({
        record_by_id[evidence_id]["paper_id"]
        for evidence_id in cited_ids
    })

    return EvidenceResult(
        ids=cited_ids,
        independent_publications=independent_publications,
        status="matched_reviewed_observation",
        answer=response["answer"],
        citation_audit_passed=True,
    )


# PSEUDOCODE
# 1. Accept only structure-hypothesis requests.
# 2. Validate candidate counts and identifiers.
# 3. Confirm candidates belong to the supplied geometry registry.
# 4. Require unrelaxed, pending-review structures.
# 5. Refuse structures marked approved for modeling.
# 6. Check composition and facet for the registered Cu(100) pair.
# 7. Return hypotheses only, without energies or selectivity claims.

@dataclass(frozen=True)
class DesignResult:
    ids: tuple[str, ...]
    status: str


MAX_CANDIDATES = 2

PAIRED_CU100 = (
    "CU-001-100-AG2-NN",
    "CU-001-100-AG2-SEP",
)


def design_agent(
    task: ResearchTask,
    registry_records: list[dict],
) -> DesignResult:
    """Select existing structural hypotheses without modeling approval."""

    if not isinstance(task, ResearchTask):
        raise TypeError("Expected a ResearchTask")

    if task.task_type not in {
        "source_question",
        "structure_hypothesis",
        "predict_selectivity",
    }:
        raise ValueError("Unknown research task type")

    if task.task_type != "structure_hypothesis":
        return DesignResult((), "not_applicable")

    ids = task.candidate_ids

    if (
        not isinstance(ids, tuple)
        or not ids
        or len(ids) > MAX_CANDIDATES
        or any(not isinstance(cid, str) or not cid for cid in ids)
        or len(set(ids)) != len(ids)
    ):
        return DesignResult((), "invalid_candidate_request")

    registry_by_id = {}

    for record in registry_records:
        if not isinstance(record, dict):
            raise ValueError("Invalid geometry registry record")

        cid = record.get("candidate_id")

        if not isinstance(cid, str) or not cid:
            raise ValueError("Missing geometry registry ID")

        if cid in registry_by_id:
            raise ValueError("Duplicate geometry registry ID")

        registry_by_id[cid] = record

    if any(cid not in registry_by_id for cid in ids):
        return DesignResult((), "unknown_candidate_id")

    for cid in ids:
        record = registry_by_id[cid]

        if (
            record.get("geometry_status") != "unrelaxed"
            or record.get("structure_review_status")
            != "pending_visual_review"
            or str(record.get("approved_for_modeling", ""))
            .strip().lower() != "false"
        ):
            return DesignResult((), "ineligible_structure_state")

    if len(ids) == 2 and set(ids) == set(PAIRED_CU100):
        for cid in ids:
            record = registry_by_id[cid]

            if (
                record.get("chemical_formula") != "Ag2Cu34"
                or str(record.get("facet")) != "100"
            ):
                return DesignResult(
                    (), "inconsistent_paired_geometry"
                )

    return DesignResult(
        ids=ids,
        status="existing_unrelaxed_hypotheses_only",
    )
