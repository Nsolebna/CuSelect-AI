"""Validate the saved CuSelect-AI LLM reasoning cycle.

No API requests. No modifications to scientific source data.
"""

# PSEUDOCODE
# 1. Read the approved evidence and three LLM outputs.
# 2. Validate evidence references against approved IDs.
# 3. Check that all three outputs refer to the same candidate.
# 4. Check that the Critic covers all required scientific areas.
# 5. Check that the Revision responds to every critic finding.
# 6. Verify recorded source-file SHA256 fingerprints.
# 7. Reject performance predictions and report the results.

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "data" / "agent_runs"

FILES = {
    "evidence": RUNS / "literature_evidence_v1.json",
    "design": RUNS / "llm_design_proposals_v2.json",
    "critic": RUNS / "llm_scientific_critique_v2.json",
    "revision": RUNS / "llm_revised_candidate_v2.json",
}

REQUIRED_CATEGORIES = {
    "evidence",
    "mechanism",
    "experimental_feasibility",
    "alternative_explanation",
    "falsifiability",
}


def load_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_cycle(evidence, design, critic, revision,
                   file_paths=None):
    """Return validation summary or raise ValueError."""

    if evidence.get("agent") != "literature_agent":
        raise ValueError("Incorrect literature package.")

    if design.get("agent") != "llm_design_agent":
        raise ValueError("Incorrect Design Agent output.")

    if critic.get("agent") != "llm_scientific_critic":
        raise ValueError("Incorrect Critic Agent output.")

    if revision.get("agent") != "llm_revision_agent":
        raise ValueError("Incorrect Revision Agent output.")

    approved_records = evidence["evidence"]
    approved_pairs = {
        (item["measurement_id"], item["doi"])
        for item in approved_records
    }
    approved_ids = {
        item["measurement_id"]
        for item in approved_records
    }

    if not approved_pairs:
        raise ValueError("Evidence package is empty.")

    if len(approved_ids) != len(approved_records):
        raise ValueError("Duplicate approved measurement IDs.")

    proposal = design["proposal"]
    critique = critic["critique"]
    revised = revision["revision"]

    original_name = proposal["candidate_name"]

    if critic["candidate_name"] != original_name:
        raise ValueError("Critic candidate mismatch.")

    if critique["candidate_name"] != original_name:
        raise ValueError("Critique name mismatch.")

    if revised["original_candidate_name"] != original_name:
        raise ValueError("Revision candidate mismatch.")

    # Verify source identities for the original proposal.
    references = proposal["supporting_evidence"]

    if not references:
        raise ValueError("Design has no evidence references.")

    design_pairs = [
        (ref["measurement_id"], ref["doi"])
        for ref in references
    ]

    if len(design_pairs) != len(set(design_pairs)):
        raise ValueError("Duplicate design evidence references.")

    if not set(design_pairs).issubset(approved_pairs):
        raise ValueError("Design has an unapproved evidence reference.")

    # Verify source identities in the Critic's report.
    findings = critique["scientific_findings"]
    categories = {item["category"] for item in findings}

    if not REQUIRED_CATEGORIES.issubset(categories):
        raise ValueError("Missing scientific critique category.")

    for finding in findings:
        linked_ids = finding["linked_measurement_ids"]

        if not set(linked_ids).issubset(approved_ids):
            raise ValueError("Critic cites unknown measurement ID.")

    # Verify Revision evidence IDs.
    revised_ids = revised["inherited_evidence_measurement_ids"]

    if not revised_ids:
        raise ValueError("Revision has no evidence references.")

    if len(revised_ids) != len(set(revised_ids)):
        raise ValueError("Duplicate revision evidence references.")

    if not set(revised_ids).issubset(approved_ids):
        raise ValueError("Revision cites unknown measurement ID.")

    # Verify every numbered critic finding has a response.
    responses = revised["finding_responses"]
    response_numbers = [
        item["finding_number"] for item in responses
    ]

    expected = set(range(1, len(findings) + 1))

    if (
        len(response_numbers) != len(set(response_numbers))
        or set(response_numbers) != expected
    ):
        raise ValueError("Incomplete critic finding coverage.")

    for response in responses:
        if response["resolution_status"] not in {
            "addressed_in_research_plan",
            "partially_addressed",
            "unresolved",
        }:
            raise ValueError("Unknown resolution status.")

    experiments = revised["controlled_experiments"]

    if len(experiments) < 2:
        raise ValueError("Insufficient controlled experiments.")

    for experiment in experiments:
        if (
            not experiment["outcome_challenging_hypothesis"].strip()
            or not experiment["interpretation_limitations"].strip()
        ):
            raise ValueError(
                "Experiment lacks falsification or limitations."
            )

    # Reject numerical FE predictions at the output level.
    if design.get("predicted_fe_percent") is not None:
        raise ValueError("Design contains an FE prediction.")

    if critic.get("performance_prediction_available") is not False:
        raise ValueError("Critic performance flag is invalid.")

    if revision.get("predicted_fe_percent") is not None:
        raise ValueError("Revision contains an FE prediction.")

    if revision.get("performance_prediction_available") is not False:
        raise ValueError("Revision performance flag is invalid.")

    # Verify that the revision was generated from the same
    # saved design and critique files now being inspected.
    if file_paths is not None:
        expected_hashes = revision["source_sha256"]

        if sha256(file_paths["design"]) != expected_hashes["design"]:
            raise ValueError("Design changed after revision.")

        if sha256(file_paths["critic"]) != expected_hashes["critique"]:
            raise ValueError("Critique changed after revision.")

    statuses = {
        item["resolution_status"]
        for item in responses
    }

    return {
        "candidate": original_name,
        "approved_measurements": len(approved_records),
        "design_references": len(references),
        "scientific_findings": len(findings),
        "findings_responded_to": len(responses),
        "critical_experiments": len(
            critique["critical_experiments"]
        ),
        "revised_experiments": len(experiments),
        "resolution_statuses": sorted(statuses),
        "evidence_identity_checks": "PASSED",
        "critic_coverage": "PASSED",
        "provenance_checks": (
            "PASSED" if file_paths is not None else "NOT RUN"
        ),
        "fe_prediction_checks": "PASSED",
        "scientific_truth_verified": False,
        "human_review_required": True,
    }


def main():
    data = {
        name: load_json(path)
        for name, path in FILES.items()
    }

    result = validate_cycle(
        data["evidence"],
        data["design"],
        data["critic"],
        data["revision"],
        file_paths=FILES,
    )

    print()
    print("CUSELECT-AI — LLM CYCLE VALIDATION")
    print("=" * 60)

    for key, value in result.items():
        print(f"{key}: {value}")

    print()
    print("INTEGRITY CHECKS: PASSED")
    print("Scientific correctness: NOT YET VERIFIED")
    print("Independent human review: REQUIRED")


if __name__ == "__main__":
    main()
