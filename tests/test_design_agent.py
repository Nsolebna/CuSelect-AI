
# PSEUDOCODE
# 1. Build isolated test metadata for the registered Cu(100) pair.
# 2. Confirm valid structural hypotheses are admitted.
# 3. Reject unknown, duplicated, and empty candidates.
# 4. Reject ineligible review/modeling states.
# 5. Reject inconsistent matched-pair metadata.
# 6. Ensure prediction requests are not handled as design tasks.

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.agents import ResearchTask, design_agent


@pytest.fixture
def geometry_records():
    common = {
        "chemical_formula": "Ag2Cu34",
        "facet": "100",
        "geometry_status": "unrelaxed",
        "structure_review_status": "pending_visual_review",
        "approved_for_modeling": "False",
    }

    return [
        {
            **common,
            "candidate_id": "CU-001-100-AG2-NN",
        },
        {
            **common,
            "candidate_id": "CU-001-100-AG2-SEP",
        },
    ]


def paired_task():
    return ResearchTask(
        task_id="D-01",
        task_type="structure_hypothesis",
        question="Compare adjacent and separated Ag pairs on Cu(100)",
        candidate_ids=(
            "CU-001-100-AG2-NN",
            "CU-001-100-AG2-SEP",
        ),
    )


def test_valid_pair_is_accepted(geometry_records):
    result = design_agent(paired_task(), geometry_records)

    assert result.status == "existing_unrelaxed_hypotheses_only"
    assert result.ids == paired_task().candidate_ids


def test_unknown_candidate_is_rejected(geometry_records):
    task = ResearchTask(
        "D-02",
        "structure_hypothesis",
        "Unknown catalyst",
        ("FAKE-CANDIDATE",),
    )

    result = design_agent(task, geometry_records)

    assert result.status == "unknown_candidate_id"
    assert result.ids == ()


def test_duplicate_candidates_are_rejected(geometry_records):
    task = ResearchTask(
        "D-03",
        "structure_hypothesis",
        "Duplicate candidates",
        ("CU-001-100-AG2-NN", "CU-001-100-AG2-NN"),
    )

    result = design_agent(task, geometry_records)

    assert result.status == "invalid_candidate_request"


def test_empty_candidates_are_rejected(geometry_records):
    task = ResearchTask(
        "D-04",
        "structure_hypothesis",
        "No candidates",
    )

    assert design_agent(
        task, geometry_records
    ).status == "invalid_candidate_request"


def test_model_approved_structure_is_rejected(geometry_records):
    geometry_records[0]["approved_for_modeling"] = "True"

    result = design_agent(paired_task(), geometry_records)

    assert result.status == "ineligible_structure_state"


def test_wrong_composition_is_rejected(geometry_records):
    geometry_records[0]["chemical_formula"] = "Ag1Cu35"

    result = design_agent(paired_task(), geometry_records)

    assert result.status == "inconsistent_paired_geometry"


def test_prediction_task_is_not_applicable(geometry_records):
    task = ResearchTask(
        "D-05",
        "predict_selectivity",
        "Predict ethylene FE",
    )

    result = design_agent(task, geometry_records)

    assert result.status == "not_applicable"
    assert result.ids == ()


def test_duplicate_registry_ids_fail_closed(geometry_records):
    geometry_records.append(dict(geometry_records[0]))

    with pytest.raises(ValueError):
        design_agent(paired_task(), geometry_records)
