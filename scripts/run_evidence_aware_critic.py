"""CuSelect-AI: one live evidence-aware LLM critique."""

# PSEUDOCODE
# 1. Load the original LLM catalyst proposal.
# 2. Load the approved literature evidence.
# 3. Load the verified computational evidence context.
# 4. Confirm all inputs and the output destination.
# 5. Invoke the scientific critic exactly once.
# 6. Save the structured result with source fingerprints.
# 7. Preserve every previous critique and scientific result.

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from cuselect.agents.llm_critic_agent import (
    generate_critique,
)

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/agent_runs"

DESIGN = RUNS / "llm_design_proposals_v2.json"
LITERATURE = RUNS / "literature_evidence_v1.json"

CONTEXT = (
    ROOT
    / "data/processed/18_agent_evidence_context"
    / "agent_evidence_context_v1.json"
)

BASELINE = RUNS / "llm_scientific_critique_v2.json"

OUTPUT = RUNS / "llm_scientific_critique_with_dft_v3.json"


def load_json(path):
    if not path.is_file():
        raise FileNotFoundError(path)

    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    load_dotenv(ROOT / ".env")

    # Protect the existing research records.
    if OUTPUT.exists():
        raise SystemExit(
            "Evidence-aware critique already exists. "
            "No overwrite and no API request."
        )

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not configured. "
            "No API request made."
        )

    design = load_json(DESIGN)
    literature = load_json(LITERATURE)
    context = load_json(CONTEXT)
    baseline = load_json(BASELINE)

    if design.get("agent") != "llm_design_agent":
        raise ValueError("Unexpected design agent output.")

    if literature.get("agent") != "literature_agent":
        raise ValueError("Unexpected literature evidence.")

    if baseline.get("agent") != "llm_scientific_critic":
        raise ValueError("Unexpected baseline critique.")

    if (
        context.get("reference", {}).get("status")
        != "preliminary_dft"
    ):
        raise ValueError("DFT evidence status mismatch.")

    if (
        context.get("evidence_assessment", {})
        .get("ethylene_selectivity")
        != "not_predicted"
    ):
        raise ValueError("Unsupported FE prediction detected.")

    if (
        baseline.get("candidate_name")
        != design["proposal"]["candidate_name"]
    ):
        raise ValueError(
            "Baseline and design refer to different candidates."
        )

    source_hashes = {
        "design": sha256(DESIGN),
        "literature": sha256(LITERATURE),
        "computational_context": sha256(CONTEXT),
        "baseline_critique": sha256(BASELINE),
    }

    model = os.getenv("CRITIC_MODEL") or os.getenv(
        "OPENAI_MODEL", "gpt-5-mini"
    )

    print("\nCUSELECT-AI — LIVE EVIDENCE-AWARE CRITIC")
    print("=" * 65)
    print("Candidate:", design["proposal"]["candidate_name"])
    print("Model:", model)
    print("Literature: Approved evidence package")
    print("Computation: Preliminary EMT/MACE/DFT")
    print(
        "DFT SEP-NN:",
        context["reference"]["delta_sep_minus_nn_mev"],
        "meV",
    )
    print("Ethylene FE prediction: Not available")
    print("Previous critique: Preserved")
    print("Output:", OUTPUT)
    print("\nMaking one live LLM request...", flush=True)

    # The existing Scientific Critic validates literature
    # references and computational context before its API call.
    result = generate_critique(
        design,
        literature,
        model=model,
        computational_context=CONTEXT,
    )

    if result.get("agent") != "llm_scientific_critic":
        raise ValueError("Unexpected critic response.")

    if result.get("performance_prediction_available") is not False:
        raise ValueError("Unexpected performance prediction flag.")

    if "computational_evidence_provenance" not in result:
        raise ValueError(
            "Missing computational evidence provenance."
        )

    provenance = result["computational_evidence_provenance"]

    if (
        provenance.get("context_sha256")
        != source_hashes["computational_context"]
    ):
        raise ValueError("Context fingerprint mismatch.")

    record = {
        **result,
        "run_type": "evidence_aware_critique",
        "created_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_files": {
            "design": str(DESIGN.relative_to(ROOT)),
            "literature": str(LITERATURE.relative_to(ROOT)),
            "computational_context": str(
                CONTEXT.relative_to(ROOT)
            ),
            "baseline_critique": str(
                BASELINE.relative_to(ROOT)
            ),
        },
        "source_sha256": source_hashes,
        "dft_reference_status": "preliminary",
        "human_scientific_review_required": True,
    }

    # Exclusive creation: refuse to overwrite another result.
    with OUTPUT.open("x", encoding="utf-8") as file:
        json.dump(record, file, indent=2, ensure_ascii=False)
        file.write("\n")

    critique = record["critique"]

    print("\nLIVE CRITIQUE COMPLETED")
    print("=" * 65)
    print("Model:", record["model"])
    print(
        "Scientific findings:",
        len(critique["scientific_findings"]),
    )
    print(
        "Critical experiments:",
        len(critique["critical_experiments"]),
    )
    print(
        "Disposition:",
        critique["recommended_disposition"],
    )
    print(
        "Computational provenance:",
        provenance["validation"],
    )
    print("Saved:", OUTPUT)
    print("Previous outputs: Unchanged")
    print("Scientific validation: Pending human review")


if __name__ == "__main__":
    main()
