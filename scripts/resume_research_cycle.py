"""CuSelect-AI — explicitly authorized revision-only recovery."""

# PSEUDOCODE
# 1. Validate the failed run and saved critique.
# 2. Default to read-only recovery preflight.
# 3. Require explicit authorization for an API request.
# 4. Reserve the single remaining request before sending it.
# 5. Reuse the saved critique; never regenerate it.
# 6. Save a validated revision and research summary.
# 7. Refuse automatic retries after interruption.

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from cuselect.agents.llm_revision_agent import generate_revision
from check_research_recovery import (
    DEFAULT_RUN,
    SOURCES,
    check_recovery,
)

ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path, data):
    with path.open("x", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def resume(run_directory, execute_live=False):
    directory = Path(run_directory).resolve()

    # Reject any previously reserved recovery attempt.
    marker = directory / "resume_attempt.json"

    if marker.exists():
        raise RuntimeError(
            "A recovery attempt was already reserved. "
            "Automatic retry is prohibited."
        )

    plan = check_recovery(directory)

    print("\nCUSELECT-AI — REVISION RECOVERY")
    print("=" * 60)
    print("Candidate:", plan["candidate"])
    print("Existing LLM attempts:", 1)
    print("Remaining allowance:", 1)
    print("Saved critique: Verified")
    print("New DFT calculations: Disabled")

    if not execute_live:
        print("Mode: Dry run")
        print("API requests: 0")
        print("Files modified: 0")
        return plan

    load_dotenv(ROOT / ".env")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY missing. No request made."
        )

    model = (
        os.getenv("REVISION_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-5-mini"
    )

    critique_path = directory / "scientific_critique.json"
    revision_path = directory / "revised_candidate.json"
    summary_path = directory / "research_run.json"

    design = load(SOURCES["design"])
    critique = load(critique_path)

    source_hashes = {
        name: digest(path)
        for name, path in SOURCES.items()
    }

    # Reserve the request before constructing the API client.
    # Exclusive creation ensures competing processes cannot
    # both claim this recovery attempt.
    save_new(marker, {
        "status": "request_reserved",
        "created_utc": now(),
        "model": model,
        "original_llm_attempts": 1,
        "maximum_additional_requests": 1,
        "saved_critique_sha256": digest(critique_path),
        "source_sha256": source_hashes,
    })

    try:
        # SDK retries are disabled. The marker prevents
        # resubmission after a crash or uncertain failure.
        client = OpenAI(
            timeout=120.0,
            max_retries=0,
        )

        result = generate_revision(
            design,
            critique,
            client=client,
            model=model,
            computational_context=SOURCES[
                "computational_context"
            ],
            critique_source_path=critique_path,
        )

        if result.get("agent") != "llm_revision_agent":
            raise ValueError("Unexpected revision output.")

        if result.get("predicted_fe_percent") is not None:
            raise ValueError(
                "Unsupported performance prediction."
            )

        if (
            result.get("critic_findings_expected")
            != result.get("critic_findings_addressed")
        ):
            raise ValueError(
                "Not all findings were addressed."
            )

        # Sources must not change during execution.
        for name, path in SOURCES.items():
            if digest(path) != source_hashes[name]:
                raise ValueError(
                    f"Source changed during recovery: {name}"
                )

        if digest(critique_path) != plan["critique_sha256"]:
            raise ValueError(
                "Saved critique changed during recovery."
            )

        save_new(revision_path, result)

        summary = {
            "schema_version": "1.0",
            "project": "CuSelect-AI",
            "mode": "revision_only_recovery",
            "status": "completed_pending_human_review",
            "completed_utc": now(),
            "candidate": plan["candidate"],
            "revision_model": model,
            "original_llm_attempts": 1,
            "additional_request_reserved": 1,
            "sdk_retries": 0,
            "new_dft_calculations": 0,
            "saved_critique_sha256": digest(
                critique_path
            ),
            "source_sha256": source_hashes,
            "revision_sha256": digest(revision_path),
            "scientific_findings_addressed": (
                result["critic_findings_addressed"]
            ),
            "decision_gate": result[
                "revision"
            ]["next_decision_gate"],
            "scientific_validation": "pending_human_review",
            "original_failure_record_preserved": True,
        }

        save_new(summary_path, summary)

        print("\nRECOVERY COMPLETED")
        print("Revision:", revision_path)
        print("Research record:", summary_path)
        print("Human review: Required")

    except Exception as error:
        # Preserve the attempt marker and all previous records.
        save_new(
            directory / "resume_failure.json",
            {
                "status": "failed_or_uncertain",
                "timestamp_utc": now(),
                "exception_type": type(error).__name__,
                "request_may_have_been_sent": True,
                "automatic_retry_allowed": False,
            },
        )
        raise


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--run-dir",
        type=Path,
        default=DEFAULT_RUN,
    )

    parser.add_argument(
        "--execute-live",
        action="store_true",
        help="Authorize one revision-only API request.",
    )

    args = parser.parse_args()

    resume(
        args.run_dir,
        execute_live=args.execute_live,
    )


if __name__ == "__main__":
    main()
