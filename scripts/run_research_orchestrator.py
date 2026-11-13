"""CuSelect-AI — auditable research orchestration, replay v1."""

# PSEUDOCODE
# 1. Read existing research outputs.
# 2. Check agent identities and candidate consistency.
# 3. Verify cryptographic fingerprints between stages.
# 4. Check computational evidence applicability safeguards.
# 5. Verify every critic finding has a revision response.
# 6. Record the completed research sequence.
# 7. Never call an LLM or run DFT in replay mode.

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "agent_runs"

FILES = {
    "literature": RUNS / "literature_evidence_v1.json",
    "design": RUNS / "llm_design_proposals_v2.json",
    "computational_context": (
        ROOT / "data/processed/18_agent_evidence_context"
        / "agent_evidence_context_v1.json"
    ),
    "critique": (
        RUNS / "llm_scientific_critique_with_dft_v3.json"
    ),
    "revision": (
        RUNS / "llm_revised_candidate_with_dft_v3.json"
    ),
}

OUTPUT = RUNS / "research_cycle_replay_v1.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def build_replay():
    """Validate inputs and construct a read-only replay record."""

    for name, path in FILES.items():
        require(path.is_file(), f"Missing {name}: {path}")

    records = {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, path in FILES.items()
    }

    hashes = {
        name: digest(path)
        for name, path in FILES.items()
    }

    literature = records["literature"]
    design = records["design"]
    context = records["computational_context"]
    critique = records["critique"]
    revision = records["revision"]

    require(
        literature.get("agent") == "literature_agent",
        "Unexpected literature agent.",
    )
    require(
        design.get("agent") == "llm_design_agent",
        "Unexpected design agent.",
    )
    require(
        critique.get("agent") == "llm_scientific_critic",
        "Unexpected critic agent.",
    )
    require(
        revision.get("agent") == "llm_revision_agent",
        "Unexpected revision agent.",
    )

    candidate = design["proposal"]["candidate_name"]

    require(
        critique.get("candidate_name") == candidate,
        "Design and critique candidate mismatch.",
    )
    require(
        revision["revision"]["original_candidate_name"]
        == candidate,
        "Design and revision candidate mismatch.",
    )

    # Verify the recorded origin of the critique.
    critic_sources = critique.get("source_sha256", {})

    for name in ("design", "literature", "computational_context"):
        require(
            critic_sources.get(name) == hashes[name],
            f"Critic source mismatch: {name}.",
        )

    # Verify the recorded origin of the revision.
    revision_sources = revision.get("source_sha256", {})

    require(
        revision_sources.get("design") == hashes["design"],
        "Revision design fingerprint mismatch.",
    )
    require(
        revision_sources.get("critique") == hashes["critique"],
        "Revision critique fingerprint mismatch.",
    )

    # Verify computational context used by both LLM agents.
    for name, record in (
        ("critique", critique),
        ("revision", revision),
    ):
        provenance = record.get(
            "computational_evidence_provenance", {}
        )

        require(
            provenance.get("context_sha256")
            == hashes["computational_context"],
            f"{name} computational context mismatch.",
        )

    require(
        context.get("system") == "Ag2Cu34 / Cu(100)",
        "Unexpected computational model.",
    )
    require(
        context.get("reference", {}).get("status")
        == "preliminary_dft",
        "Unexpected DFT status.",
    )
    require(
        context.get("evidence_assessment", {})
        .get("ethylene_selectivity") == "not_predicted",
        "Invalid ethylene selectivity claim.",
    )

    require(
        critique.get("performance_prediction_available") is False,
        "Critic unexpectedly claims performance prediction.",
    )
    require(
        revision.get("performance_prediction_available") is False,
        "Revision unexpectedly claims performance prediction.",
    )
    require(
        revision.get("predicted_fe_percent") is None,
        "Revision contains a numerical FE prediction.",
    )

    findings = critique["critique"]["scientific_findings"]
    responses = revision["revision"]["finding_responses"]
    experiments = revision["revision"]["controlled_experiments"]

    expected = set(range(1, len(findings) + 1))
    observed = [
        item["finding_number"]
        for item in responses
    ]

    require(
        len(observed) == len(set(observed))
        and set(observed) == expected,
        "Critic findings not fully or uniquely addressed.",
    )

    require(
        bool(experiments),
        "Revision has no proposed controlled experiments.",
    )

    gate = revision["revision"]["next_decision_gate"]
    require(
        isinstance(gate, str) and bool(gate.strip()),
        "Research decision gate missing.",
    )

    steps = [
        ("literature", "verified_saved_input"),
        ("design", "verified_saved_input"),
        ("computational_context", "verified_saved_input"),
        ("critique", "verified_saved_output"),
        ("revision", "verified_saved_output"),
    ]

    return {
        "schema_version": "1.0",
        "project": "CuSelect-AI",
        "run_mode": "replay",
        "execution_policy": {
            "llm_calls_allowed": False,
            "new_dft_calculations_allowed": False,
            "external_requests_allowed": False,
        },
        "created_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "research_objective": (
            "Investigate testable Cu-Ag catalyst hypotheses "
            "for electrochemical CO2-to-ethylene conversion."
        ),
        "original_candidate": candidate,
        "revised_candidate": revision["revision"]["candidate_name"],
        "scientific_status": "pending_human_review",
        "computational_status": "preliminary_clean_slab",
        "workflow": [
            {
                "stage": name,
                "status": status,
                "source_file": str(FILES[name].relative_to(ROOT)),
                "sha256": hashes[name],
            }
            for name, status in steps
        ],
        "outcomes": {
            "scientific_findings": len(findings),
            "findings_addressed": len(responses),
            "proposed_controlled_experiments": len(experiments),
            "critic_disposition": (
                critique["critique"]["recommended_disposition"]
            ),
            "next_decision_gate": gate,
            "ethylene_fe_predicted": False,
        },
        "limitations": [
            "Replay verifies saved records; it does not run agents.",
            "Saved fingerprints verify file consistency, not scientific truth.",
            "DFT findings apply only to the tested clean-slab model.",
            "Research decisions require human scientific review.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate inputs without saving an output.",
    )
    args = parser.parse_args()

    record = build_replay()

    if not args.check_only:
        # Exclusive creation prevents accidental overwriting.
        with OUTPUT.open("x", encoding="utf-8") as file:
            json.dump(record, file, indent=2, ensure_ascii=False)
            file.write("\n")

    outcomes = record["outcomes"]

    print("\nCUSELECT-AI — RESEARCH ORCHESTRATOR")
    print("=" * 60)
    print("Mode:", record["run_mode"])
    print("Candidate:", record["original_candidate"])
    print("Recorded stages:", len(record["workflow"]))
    print("Scientific findings:", outcomes["scientific_findings"])
    print("Findings addressed:", outcomes["findings_addressed"])
    print(
        "Proposed experiments:",
        outcomes["proposed_controlled_experiments"],
    )
    print("Decision:", outcomes["critic_disposition"])
    print("Human review: Required")
    print("LLM requests: 0")
    print("New DFT calculations: 0")
    print(
        "Result:",
        "Validated only" if args.check_only else str(OUTPUT),
    )


if __name__ == "__main__":
    main()
