"""CuSelect-AI — End-to-end deterministic agent pipeline."""

# PSEUDOCODE
# 1. Load approved literature evidence and condition reviews.
# 2. Build a fresh evidence package.
# 3. Generate design hypotheses.
# 4. Critique each hypothesis.
# 5. Score research readiness.
# 6. Coordinate revisions.
# 7. Check identities and scientific safeguards.
# 8. Save all five outputs.

from pathlib import Path

from cuselect.agents.literature_package_agent import (
    read_json,
    atomic_write,
    build_evidence_package,
)
from cuselect.agents.template_design_agent import generate_proposals
from cuselect.agents.critic_agent import critique_designs
from cuselect.agents.scoring_agent import score_designs
from cuselect.agents.coordinator import coordinate

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
RUNS = DATA / "agent_runs"

OUTPUT_NAMES = {
    "literature": "literature_evidence_v1.json",
    "design": "design_proposals_v1.json",
    "critique": "scientific_critiques_v1.json",
    "scoring": "research_readiness_scores_v1.json",
    "coordination": "coordinated_designs_v1.json",
}


def validate_pipeline(outputs):
    """Check essential cross-agent scientific invariants."""

    literature = outputs["literature"]
    designs = outputs["design"]
    critiques = outputs["critique"]
    scores = outputs["scoring"]
    coordinated = outputs["coordination"]

    evidence_ids = [
        item["measurement_id"]
        for item in literature["evidence"]
    ]

    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("Duplicate evidence measurement IDs.")

    candidate_ids = [
        item["id"] for item in designs["candidates"]
    ]

    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("Duplicate design candidate IDs.")

    if not candidate_ids:
        raise ValueError("No catalyst hypotheses generated.")

    expected = set(candidate_ids)

    for name, ids in [
        (
            "critique",
            [
                item["candidate_id"]
                for item in critiques["critiques"]
            ],
        ),
        (
            "scoring",
            [
                item["candidate_id"]
                for item in scores["candidates"]
            ],
        ),
        (
            "coordination",
            [
                item["candidate_id"]
                for item in coordinated["candidates"]
            ],
        ),
    ]:
        if len(ids) != len(expected) or set(ids) != expected:
            raise ValueError(
                f"Candidate mismatch in {name} output."
            )

    for item in designs["candidates"]:
        if item.get("predicted_fe_percent") is not None:
            raise ValueError("Unsupported FE prediction.")

        if not set(item["evidence_measurement_ids"]).issubset(
            set(evidence_ids)
        ):
            raise ValueError("Untraceable design evidence.")

    for item in scores["candidates"]:
        total = item["scores"]["total"]

        if not 0 <= total <= 100:
            raise ValueError("Invalid research-readiness score.")

        if item.get("predicted_fe_percent") is not None:
            raise ValueError("Unsupported FE prediction.")

    for item in coordinated["candidates"]:
        if len(item["evolution"]) != 3:
            raise ValueError("Incomplete candidate evolution.")

        if item.get("predicted_fe_percent") is not None:
            raise ValueError("Unsupported FE prediction.")

    return True


def build_pipeline(evidence, condition_reviews):
    """Execute all five agents using fresh in-memory outputs."""

    literature = build_evidence_package(
        evidence, condition_reviews
    )

    designs = generate_proposals(literature)
    critiques = critique_designs(designs, literature)
    scores = score_designs(designs, critiques, literature)
    coordinated = coordinate(designs, critiques, scores)

    outputs = {
        "literature": literature,
        "design": designs,
        "critique": critiques,
        "scoring": scores,
        "coordination": coordinated,
    }

    validate_pipeline(outputs)
    return outputs


def run_pipeline(save=True):
    """Run from approved source files; optionally save outputs."""

    evidence = read_json(DATA / "approved_evidence.json")
    condition_reviews = read_json(
        DATA / "conditions_review.json",
        default={},
    )

    outputs = build_pipeline(evidence, condition_reviews)

    if save:
        RUNS.mkdir(parents=True, exist_ok=True)

        for name, filename in OUTPUT_NAMES.items():
            atomic_write(RUNS / filename, outputs[name])

    return outputs
