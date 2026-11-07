
# CuSelect-AI — Phase II
# Module: src/cuselect/orchestrator.py
#
# PSEUDOCODE
# 1. Validate the research request and execution limits.
# 2. Load approved evidence and registered geometries.
# 3. Run the Literature Agent using the trusted RAG service.
# 4. Run the Design Agent using the trusted geometry registry.
# 5. Construct a scientific assertion from authorized results.
# 6. Submit the assertion to the stronger Scientific Critic.
# 7. Enforce consistency between agent outputs and critic decision.
# 8. Record three actual tool operations with SHA-256 digests.
# 9. Return a cited response, hypothesis, or abstention.
# 10. Never write files, change approvals, or predict selectivity.

from dataclasses import asdict
from pathlib import Path
import hashlib
import json

from .agents import (
    ResearchTask,
    literature_agent,
    design_agent,
)
from .evidence_store import load_verified_corpus
from .geometry_store import load_geometry_registry
from .scientific_critic import (
    ScientificAssertion,
    extract_potential,
    review_scientific_assertion,
)


MAX_AGENT_STEPS = 3
MAX_CANDIDATES = 2

AGENT_TOOLS = {
    "literature_agent": frozenset({"approved_claim_lookup"}),
    "design_agent": frozenset({"registered_geometry_lookup"}),
    "scientific_critic": frozenset({"policy_check"}),
}


def canonical(value) -> str:
    """Serialize a workflow record deterministically."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def digest(value) -> str:
    """Calculate a deterministic SHA-256 digest."""
    return hashlib.sha256(
        canonical(value).encode("utf-8")
    ).hexdigest()


def _assertion_from_results(task, literature, design, evidence_by_id):
    """Build only source-grounded or explicitly unsupported assertions."""

    assertion_id = f"{task.task_id}-CRITIC"

    if task.task_type == "source_question":
        if len(literature.ids) == 1 and literature.citation_audit_passed:
            evidence_id = literature.ids[0]
            source = evidence_by_id.get(evidence_id)

            if source is None:
                raise RuntimeError("Literature cited unknown evidence")

            fe = source["faradaic_efficiency_percent"].strip()

            if fe:
                return ScientificAssertion(
                    assertion_id=assertion_id,
                    kind="reported_fe",
                    evidence_ids=(evidence_id,),
                    catalyst=source["catalyst_system"],
                    product=source["fe_product"],
                    fe_percent=float(fe),
                    potential_v_rhe=extract_potential(
                        source["conditions"]
                    ),
                    statement=source["claim_paraphrase"],
                )

            if "ratio" in source["target_or_observation"].lower():
                return ScientificAssertion(
                    assertion_id=assertion_id,
                    kind="reported_ratio",
                    evidence_ids=(evidence_id,),
                    statement=source["claim_paraphrase"],
                )

        return ScientificAssertion(
            assertion_id=assertion_id,
            kind="evaluation_claim",
        )

    if task.task_type == "structure_hypothesis":
        if design.ids:
            return ScientificAssertion(
                assertion_id=assertion_id,
                kind="structure_hypothesis",
                candidate_ids=design.ids,
                statement=task.question,
            )

        return ScientificAssertion(
            assertion_id=assertion_id,
            kind="evaluation_claim",
        )

    return ScientificAssertion(
        assertion_id=assertion_id,
        kind="catalyst_superiority",
    )


def run_research_workflow(
    task: ResearchTask,
    *,
    project_root: str | Path = ".",
) -> dict:
    """Execute a bounded, deterministic three-agent workflow."""

    if not isinstance(task, ResearchTask):
        raise TypeError("Expected a ResearchTask")

    if task.task_type not in {
        "source_question",
        "structure_hypothesis",
        "predict_selectivity",
    }:
        raise ValueError("Unknown research task type")

    if (
        not isinstance(task.task_id, str)
        or not task.task_id.strip()
        or not isinstance(task.question, str)
        or not task.question.strip()
    ):
        raise ValueError("Task ID and question must not be empty")

    ids = task.candidate_ids

    if (
        not isinstance(ids, tuple)
        or len(ids) > MAX_CANDIDATES
        or len(set(ids)) != len(ids)
        or any(
            not isinstance(cid, str) or not cid.strip()
            for cid in ids
        )
    ):
        raise ValueError("Invalid or excessive candidate IDs")

    root = Path(project_root)

    # Fail closed if either scientific data source is inconsistent.
    evidence = load_verified_corpus(root)
    geometries = load_geometry_registry(root)

    evidence_by_id = {
        record["evidence_id"]: record
        for record in evidence
    }

    trace = []

    def log(agent, tool, inputs, output, message):
        if tool not in AGENT_TOOLS[agent]:
            raise RuntimeError("Unauthorized agent tool")

        if len(trace) >= MAX_AGENT_STEPS:
            raise RuntimeError("Agent step budget exhausted")

        trace.append({
            "step": len(trace) + 1,
            "agent": agent,
            "tool": tool,
            "status": "completed",
            "input_sha256": digest(inputs),
            "output_sha256": digest(asdict(output)),
            "message": message,
        })

    # Step 1: Literature Agent.
    literature = literature_agent(
        task,
        project_root=root,
    )

    log(
        "literature_agent",
        "approved_claim_lookup",
        asdict(task),
        literature,
        f"Status: {literature.status}; evidence IDs: "
        f"{list(literature.ids)}",
    )

    # Step 2: Design Agent.
    design = design_agent(task, geometries)

    log(
        "design_agent",
        "registered_geometry_lookup",
        asdict(task),
        design,
        f"Status: {design.status}; candidate IDs: "
        f"{list(design.ids)}",
    )

    # Step 3: Scientific Critic.
    assertion = _assertion_from_results(
        task,
        literature,
        design,
        evidence_by_id,
    )

    critic = review_scientific_assertion(
        assertion,
        project_root=root,
    )

    log(
        "scientific_critic",
        "policy_check",
        {
            "assertion": asdict(assertion),
            "literature": asdict(literature),
            "design": asdict(design),
        },
        critic,
        f"Decision: {critic.decision}; "
        f"reason codes: {list(critic.reason_codes)}",
    )

    # Final decision must agree with the authorized agent result.
    if critic.decision == "evidence_only":
        if (
            critic.cited_ids != literature.ids
            or not literature.citation_audit_passed
        ):
            raise RuntimeError("Evidence/critic decision mismatch")

    elif critic.decision == "hypothesis_only":
        if critic.candidate_ids != design.ids:
            raise RuntimeError("Design/critic decision mismatch")

    elif critic.decision != "abstain":
        raise RuntimeError("Unknown scientific critic decision")

    citations = [
        {
            "evidence_id": evidence_id,
            "doi": evidence_by_id[evidence_id]["doi"],
            "source_extent": evidence_by_id[evidence_id]["source_extent"],
            "source_location": evidence_by_id[evidence_id]["source_location"],
        }
        for evidence_id in critic.cited_ids
    ]

    response_text = (
        critic.canonical_response
        if critic.decision != "abstain"
        else "Insufficient verified evidence to authorize "
             "the requested scientific conclusion."
    )

    corpus_path = (
        root
        / "data/processed/06_rag_prototype/"
        "06_retrieval_corpus.jsonl"
    )

    result = {
        "task": asdict(task),
        "literature": asdict(literature),
        "design": asdict(design),
        "critic": asdict(critic),
        "decision": critic.decision,
        "response": response_text,
        "citations": citations,
        "candidate_ids": list(critic.candidate_ids),
        "trace": trace,
        "source_corpus_sha256": hashlib.sha256(
            corpus_path.read_bytes()
        ).hexdigest(),
        "workflow_type": "deterministic_local_no_llm",
        "external_api_called": False,
        "predicted_selectivity": False,
        "human_approval_modified": False,
        "scientific_modeling_approved": False,
    }

    result["run_sha256"] = digest(result)

    return result
