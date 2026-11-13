"""Generate one evidence-aware CuSelect-AI catalyst revision."""

# PSEUDOCODE
# 1. Load the saved design and evidence-aware critique.
# 2. Verify inputs and protect the previous revision.
# 3. Supply the verified computational evidence context.
# 4. Make one structured LLM revision request.
# 5. Save the revised hypothesis with provenance.
# 6. Report the revision without claiming scientific validation.

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from cuselect.agents.llm_revision_agent import (
    generate_revision,
)

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/agent_runs"

DESIGN = RUNS / "llm_design_proposals_v2.json"

CRITIQUE = (
    RUNS / "llm_scientific_critique_with_dft_v3.json"
)

CONTEXT = (
    ROOT / "data/processed/18_agent_evidence_context"
    / "agent_evidence_context_v1.json"
)

OUTPUT = (
    RUNS / "llm_revised_candidate_with_dft_v3.json"
)


def load(path):
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    load_dotenv(ROOT / ".env")

    if OUTPUT.exists():
        raise SystemExit(
            "Output already exists. No overwrite or API request."
        )

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY missing. No API request."
        )

    design = load(DESIGN)
    critique = load(CRITIQUE)
    context = load(CONTEXT)

    if design.get("agent") != "llm_design_agent":
        raise ValueError("Unexpected design input.")

    if critique.get("agent") != "llm_scientific_critic":
        raise ValueError("Unexpected critique input.")

    if (
        critique.get("candidate_name")
        != design["proposal"]["candidate_name"]
    ):
        raise ValueError("Candidate mismatch.")

    if (
        context["evidence_assessment"]["ethylene_selectivity"]
        != "not_predicted"
    ):
        raise ValueError("Invalid selectivity evidence.")

    model = (
        os.getenv("REVISION_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-5-mini"
    )

    print("\nCUSELECT-AI — LIVE EVIDENCE-AWARE REVISION")
    print("=" * 65)
    print("Candidate:", critique["candidate_name"])
    print("Model:", model)
    print(
        "Scientific findings:",
        len(critique["critique"]["scientific_findings"]),
    )
    print("DFT reference:", context["reference"]["status"])
    print("Previous revision: Preserved")
    print("New output:", OUTPUT)

    print("\nMaking one live LLM request...", flush=True)

    result = generate_revision(
        design,
        critique,
        model=model,
        computational_context=CONTEXT,
    )

    if result.get("agent") != "llm_revision_agent":
        raise ValueError("Unexpected revision output.")

    if result.get("performance_prediction_available") is not False:
        raise ValueError("Unexpected performance prediction.")

    if result.get("predicted_fe_percent") is not None:
        raise ValueError("Unsupported FE prediction.")

    if (
        result.get("critic_findings_expected")
        != result.get("critic_findings_addressed")
    ):
        raise ValueError("Not all findings were addressed.")

    if "computational_evidence_provenance" not in result:
        raise ValueError("Missing computational provenance.")

    record = {
        **result,
        "run_type": "evidence_aware_revision",
        "created_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "human_scientific_review_required": True,
    }

    # Exclusive creation protects all existing research outputs.
    with OUTPUT.open("x", encoding="utf-8") as file:
        json.dump(
            record,
            file,
            indent=2,
            ensure_ascii=False,
        )
        file.write("\n")

    print("\nREVISION COMPLETED")
    print("=" * 65)
    print("Model:", record["model"])
    print(
        "Findings addressed:",
        record["critic_findings_addressed"],
        "/",
        record["critic_findings_expected"],
    )
    print(
        "Controlled experiments:",
        len(record["revision"]["controlled_experiments"]),
    )
    print(
        "Next decision gate:",
        record["revision"]["next_decision_gate"],
    )
    print("Saved:", OUTPUT)
    print("Scientific validation: Pending human review")


if __name__ == "__main__":
    main()
