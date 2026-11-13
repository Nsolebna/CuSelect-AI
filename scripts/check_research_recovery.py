"""CuSelect-AI — verify whether an interrupted run is resumable."""

# PSEUDOCODE
# 1. Read the failed research-run record.
# 2. Require a successfully saved Scientific Critic output.
# 3. Verify the saved critique has not changed.
# 4. Verify the original evidence has not changed.
# 5. Ensure the Revision Agent has not already made an API request.
# 6. Ensure no revision or completed record already exists.
# 7. Report whether resuming is permitted.
# 8. Never execute an LLM or modify any file.

import argparse
import hashlib
import json
from pathlib import Path

from cuselect.agents.llm_critic_agent import (
    EXPECTED_COMPUTATIONAL_CONTEXT_SHA256,
)

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/agent_runs"

SOURCES = {
    "design": RUNS / "llm_design_proposals_v2.json",
    "literature": RUNS / "literature_evidence_v1.json",
    "computational_context": (
        ROOT / "data/processed/18_agent_evidence_context"
        / "agent_evidence_context_v1.json"
    ),
}

DEFAULT_RUN = (
    RUNS / "orchestrated_runs/research_cycle_001"
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_recovery(run_directory):
    """Return a validated recovery plan; perform no writes."""

    run_directory = Path(run_directory).resolve()

    failure = read_json(run_directory / "failure.json")

    critique_path = run_directory / "scientific_critique.json"

    require(
        failure.get("status") == "failed",
        "Run is not marked as failed.",
    )

    require(
        failure.get("failed_stage") == "revision_agent",
        "Only Revision Agent failures can be resumed.",
    )

    require(
        failure.get("saved_critique_available") is True,
        "No completed Scientific Critic result recorded.",
    )

    require(
        failure.get("llm_requests_attempted") == 1,
        "Revision request may already have been attempted. "
        "Refusing to exceed the original request budget.",
    )

    require(
        critique_path.is_file(),
        "Saved scientific critique is missing.",
    )

    expected_critique_hash = failure.get(
        "saved_critique_sha256"
    )

    require(
        isinstance(expected_critique_hash, str)
        and len(expected_critique_hash) == 64,
        "Failure record lacks a usable critique fingerprint.",
    )

    require(
        sha256(critique_path) == expected_critique_hash,
        "Saved scientific critique was modified.",
    )

    for filename in (
        "revised_candidate.json",
        "research_run.json",
    ):
        require(
            not (run_directory / filename).exists(),
            f"Existing output prevents recovery: {filename}",
        )

    critique = read_json(critique_path)
    design = read_json(SOURCES["design"])
    context = read_json(SOURCES["computational_context"])

    require(
        critique.get("agent") == "llm_scientific_critic",
        "Unexpected critique agent.",
    )

    require(
        critique.get("candidate_name")
        == design["proposal"]["candidate_name"],
        "Critique and original design differ.",
    )

    recorded_hashes = critique.get("source_sha256", {})

    for name, path in SOURCES.items():
        require(
            path.is_file(),
            f"Missing source: {name}",
        )
        require(
            recorded_hashes.get(name) == sha256(path),
            f"Source fingerprint mismatch: {name}",
        )

    require(
        sha256(SOURCES["computational_context"])
        == EXPECTED_COMPUTATIONAL_CONTEXT_SHA256,
        "Computational context integrity check failed.",
    )

    provenance = critique.get(
        "computational_evidence_provenance", {}
    )

    require(
        provenance.get("context_sha256")
        == sha256(SOURCES["computational_context"]),
        "Critique computational provenance mismatch.",
    )

    require(
        context.get("system") == "Ag2Cu34 / Cu(100)",
        "Unexpected computational system.",
    )

    require(
        context.get("reference", {}).get("status")
        == "preliminary_dft",
        "Unexpected DFT evidence status.",
    )

    require(
        context.get("evidence_assessment", {})
        .get("ethylene_selectivity") == "not_predicted",
        "Unsupported ethylene-selectivity status.",
    )

    findings = critique.get(
        "critique", {}
    ).get("scientific_findings", [])

    require(
        len(findings) >= 5,
        "Saved critique lacks required scientific findings.",
    )

    return {
        "status": "eligible_for_controlled_revision_resume",
        "run_directory": str(run_directory),
        "critique_sha256": sha256(critique_path),
        "candidate": critique["candidate_name"],
        "existing_requests_attempted": 1,
        "remaining_request_allowance": 1,
        "automated_dft_allowed": False,
        "human_approval_required": True,
        "files_modified": 0,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--run-dir",
        type=Path,
        default=DEFAULT_RUN,
    )

    args = parser.parse_args()
    result = check_recovery(args.run_dir)

    print("\nCUSELECT-AI — RECOVERY PREFLIGHT")
    print("=" * 60)
    print("Status:", result["status"])
    print("Candidate:", result["candidate"])
    print(
        "Previous requests:",
        result["existing_requests_attempted"],
    )
    print(
        "Remaining allowance:",
        result["remaining_request_allowance"],
    )
    print("Human approval: Required")
    print("API requests made: 0")
    print("Files modified: 0")


if __name__ == "__main__":
    main()
