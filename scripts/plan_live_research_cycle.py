"""CuSelect-AI — controlled research execution planner."""

# PSEUDOCODE
# 1. Load the existing design, literature and computational context.
# 2. Verify the source records and their provenance.
# 3. Check that both LLM agents support the required interfaces.
# 4. Plan the critic-to-revision execution order.
# 5. Refuse to overwrite an existing research-run directory.
# 6. Print the execution plan without calling an API.

import hashlib
import inspect
import json
from pathlib import Path

from cuselect.agents.llm_critic_agent import generate_critique
from cuselect.agents.llm_revision_agent import generate_revision

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/agent_runs"

DESIGN = RUNS / "llm_design_proposals_v2.json"
LITERATURE = RUNS / "literature_evidence_v1.json"
CONTEXT = (
    ROOT / "data/processed/18_agent_evidence_context"
    / "agent_evidence_context_v1.json"
)

RUN_ID = "research_cycle_001"
OUTPUT_DIR = RUNS / "orchestrated_runs" / RUN_ID


def load(path):
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    design = load(DESIGN)
    literature = load(LITERATURE)
    context = load(CONTEXT)

    if design.get("agent") != "llm_design_agent":
        raise ValueError("Invalid design source.")

    if literature.get("agent") != "literature_agent":
        raise ValueError("Invalid literature source.")

    if context.get("system") != "Ag2Cu34 / Cu(100)":
        raise ValueError("Unexpected computational system.")

    if context.get("reference", {}).get("status") != "preliminary_dft":
        raise ValueError("Unexpected DFT status.")

    if context.get("evidence_assessment", {}).get(
        "ethylene_selectivity"
    ) != "not_predicted":
        raise ValueError("Unsupported selectivity prediction.")

    from cuselect.agents.llm_critic_agent import (
        EXPECTED_COMPUTATIONAL_CONTEXT_SHA256,
    )

    if fingerprint(CONTEXT) != EXPECTED_COMPUTATIONAL_CONTEXT_SHA256:
        raise ValueError("Computational context fingerprint mismatch.")

    critic_params = inspect.signature(
        generate_critique
    ).parameters

    revision_params = inspect.signature(
        generate_revision
    ).parameters

    if "computational_context" not in critic_params:
        raise ValueError("Critic interface incompatible.")

    if not {
        "computational_context",
        "critique_source_path",
    }.issubset(revision_params):
        raise ValueError("Revision interface incompatible.")

    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Research run directory already exists: {OUTPUT_DIR}"
        )

    plan = {
        "run_id": RUN_ID,
        "mode": "dry_run",
        "candidate": design["proposal"]["candidate_name"],
        "source_sha256": {
            "design": fingerprint(DESIGN),
            "literature": fingerprint(LITERATURE),
            "computational_context": fingerprint(CONTEXT),
        },
        "planned_stages": [
            {
                "stage": 1,
                "name": "validate_scientific_inputs",
                "api_requests": 0,
            },
            {
                "stage": 2,
                "name": "run_evidence_aware_scientific_critic",
                "maximum_api_requests": 1,
            },
            {
                "stage": 3,
                "name": "validate_and_save_critique",
                "api_requests": 0,
            },
            {
                "stage": 4,
                "name": "run_evidence_aware_revision",
                "maximum_api_requests": 1,
            },
            {
                "stage": 5,
                "name": "validate_and_save_research_record",
                "api_requests": 0,
            },
        ],
        "execution_policy": {
            "live_llm_execution_enabled": False,
            "maximum_planned_llm_requests": 2,
            "automatic_dft_execution": False,
            "existing_outputs_may_be_overwritten": False,
            "human_scientific_review_required": True,
        },
        "output_directory": str(OUTPUT_DIR.relative_to(ROOT)),
    }

    print("\nCUSELECT-AI — LIVE ORCHESTRATION DRY RUN")
    print("=" * 65)
    print("Research run:", plan["run_id"])
    print("Candidate:", plan["candidate"])

    for step in plan["planned_stages"]:
        print(
            f"  {step['stage']}. {step['name']}"
        )

    print("\nMaximum planned LLM requests: 2")
    print("Actual LLM requests: 0")
    print("DFT calculations: 0")
    print("Files written: 0")
    print("Output destination:", OUTPUT_DIR)
    print("Preflight validation: PASSED")

    return plan


if __name__ == "__main__":
    main()
