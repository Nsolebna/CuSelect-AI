"""CuSelect-AI — controlled critic-to-revision execution."""

# PSEUDOCODE
# 1. Validate the existing research execution plan.
# 2. Default to dry-run mode with zero API requests.
# 3. Require an explicit flag for live execution.
# 4. Disable automatic API retries and enforce two calls maximum.
# 5. Run and save the Scientific Critic first.
# 6. Pass that exact saved critique to the Revision Agent.
# 7. Save the revision and final run summary.
# 8. Preserve partial results if a stage fails.
# 9. Never execute DFT automatically.

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv
from openai import OpenAI

from cuselect.agents.llm_critic_agent import generate_critique
from cuselect.agents.llm_revision_agent import generate_revision

from plan_live_research_cycle import (
    main as validate_plan,
    DESIGN,
    LITERATURE,
    CONTEXT,
    OUTPUT_DIR,
)

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def save_new(path, record):
    """Create a JSON file without overwriting anything."""
    with path.open("x", encoding="utf-8") as file:
        json.dump(record, file, indent=2, ensure_ascii=False)
        file.write("\n")


class RequestBudget:
    """Limit the number of structured LLM requests."""

    def __init__(self, client, maximum=2):
        self.client = client
        self.maximum = maximum
        self.attempts = 0
        self.responses = SimpleNamespace(parse=self.parse)

    def parse(self, **kwargs):
        if self.attempts >= self.maximum:
            raise RuntimeError(
                "LLM request budget exhausted."
            )

        self.attempts += 1
        return self.client.responses.parse(**kwargs)


def execute_live():
    load_dotenv(ROOT / ".env")

    # Preflight validation must pass before any API activity.
    plan = validate_plan()

    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Run directory already exists: {OUTPUT_DIR}"
        )

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY missing. No API request made."
        )

    design = load_json(DESIGN)
    literature = load_json(LITERATURE)

    sources = {
        "design": digest(DESIGN),
        "literature": digest(LITERATURE),
        "computational_context": digest(CONTEXT),
    }

    if sources != plan["source_sha256"]:
        raise ValueError(
            "Source files changed after validation."
        )

    critic_model = (
        os.getenv("CRITIC_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-5-mini"
    )

    revision_model = (
        os.getenv("REVISION_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-5-mini"
    )

    # max_retries=0 avoids implicit SDK retry requests.
    client = OpenAI(
        timeout=120.0,
        max_retries=0,
    )

    budget = RequestBudget(client, maximum=2)

    # Exclusive directory creation protects earlier runs.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

    critic_path = OUTPUT_DIR / "scientific_critique.json"
    revision_path = OUTPUT_DIR / "revised_candidate.json"
    summary_path = OUTPUT_DIR / "research_run.json"

    stage = "scientific_critic"

    try:
        print("\nCUSELECT-AI — CONTROLLED LIVE EXECUTION")
        print("=" * 65)
        print("Run:", plan["run_id"])
        print("Critic model:", critic_model)
        print("Revision model:", revision_model)
        print("Maximum LLM requests:", budget.maximum)
        print("Automatic API retries: Disabled")
        print("Automatic DFT: Disabled")
        print(flush=True)

        # STAGE 1: Evidence-aware Scientific Critic.
        critique = generate_critique(
            design,
            literature,
            client=budget,
            model=critic_model,
            computational_context=CONTEXT,
        )

        if critique.get("agent") != "llm_scientific_critic":
            raise ValueError("Invalid critic output.")

        if "computational_evidence_provenance" not in critique:
            raise ValueError(
                "Missing critic computational provenance."
            )

        # Record the exact inputs used by the critic.
        critique["source_sha256"] = dict(sources)

        save_new(critic_path, critique)

        print("Scientific Critic: Completed and saved")
        print(
            "Findings:",
            len(critique["critique"]["scientific_findings"]),
        )

        # STAGE 2: Revise using this exact saved critique.
        stage = "revision_agent"

        saved_critique = load_json(critic_path)

        revision = generate_revision(
            design,
            saved_critique,
            client=budget,
            model=revision_model,
            computational_context=CONTEXT,
            critique_source_path=critic_path,
        )

        if revision.get("agent") != "llm_revision_agent":
            raise ValueError("Invalid revision output.")

        if revision.get("predicted_fe_percent") is not None:
            raise ValueError(
                "Unsupported numerical FE prediction."
            )

        if (
            revision.get("critic_findings_expected")
            != revision.get("critic_findings_addressed")
        ):
            raise ValueError(
                "Not all scientific findings were addressed."
            )

        save_new(revision_path, revision)

        print("Revision Agent: Completed and saved")

        # STAGE 3: Record final provenance.
        stage = "research_run_record"

        summary = {
            "schema_version": "1.0",
            "project": "CuSelect-AI",
            "run_id": plan["run_id"],
            "mode": "controlled_live",
            "status": "completed_pending_human_review",
            "completed_utc": timestamp(),
            "original_candidate": (
                design["proposal"]["candidate_name"]
            ),
            "revised_candidate": (
                revision["revision"]["candidate_name"]
            ),
            "models": {
                "critic": critic_model,
                "revision": revision_model,
            },
            "llm_requests_attempted": budget.attempts,
            "automatic_sdk_retries": 0,
            "new_dft_calculations": 0,
            "source_sha256": sources,
            "output_files": {
                "critique": critic_path.name,
                "revision": revision_path.name,
            },
            "output_sha256": {
                "critique": digest(critic_path),
                "revision": digest(revision_path),
            },
            "scientific_findings": (
                revision["critic_findings_expected"]
            ),
            "findings_addressed": (
                revision["critic_findings_addressed"]
            ),
            "proposed_experiments": len(
                revision["revision"]["controlled_experiments"]
            ),
            "decision_gate": (
                revision["revision"]["next_decision_gate"]
            ),
            "scientific_validation": "pending_human_review",
        }

        save_new(summary_path, summary)

        print("\nRESEARCH CYCLE COMPLETED")
        print("=" * 65)
        print("LLM requests attempted:", budget.attempts)
        print(
            "Scientific findings addressed:",
            summary["findings_addressed"],
        )
        print(
            "Proposed experiments:",
            summary["proposed_experiments"],
        )
        print("Result directory:", OUTPUT_DIR)
        print("Scientific review: Required")

    except Exception as error:
        # Never delete successful partial stages.
        # Record failure without storing secrets or API messages.
        failure = {
            "status": "failed",
            "failed_stage": stage,
            "timestamp_utc": timestamp(),
            "exception_type": type(error).__name__,
            "llm_requests_attempted": budget.attempts,
            "saved_critique_available": critic_path.is_file(),
            "saved_critique_sha256": (
                digest(critic_path)
                if critic_path.is_file()
                else None
            ),
            "saved_revision_available": revision_path.is_file(),
            "automatic_dft_execution": False,
        }

        save_new(OUTPUT_DIR / "failure.json", failure)
        raise


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--execute-live",
        action="store_true",
        help="Explicitly authorize live LLM execution.",
    )

    args = parser.parse_args()

    if args.execute_live:
        execute_live()
    else:
        validate_plan()
        print("\nCONTROLLED RUNNER — DRY RUN")
        print("Live execution: Not authorized")
        print("API requests: 0")
        print("Files written: 0")


if __name__ == "__main__":
    main()
