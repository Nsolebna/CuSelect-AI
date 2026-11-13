
"""Persistent research-case references for CuSelect-AI.

Cases link to existing records. They do not approve evidence.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_cases(project_root):
    path = Path(project_root) / "data/research_cases.json"

    if not path.exists():
        return []

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise ValueError("Research-case registry must be a list.")

    return data


def create_case(project_root, candidate_id, benchmark_path):
    root = Path(project_root).resolve()
    source = (root / benchmark_path).resolve()

    if not source.is_relative_to(root):
        raise ValueError("Benchmark path outside project.")

    if not source.is_file():
        raise FileNotFoundError(source)

    benchmark = json.loads(source.read_text(encoding="utf-8"))

    if not isinstance(benchmark, dict):
        raise ValueError("Benchmark must be a JSON object.")

    candidate_id = str(candidate_id).strip()

    if not candidate_id:
        raise ValueError("Candidate ID is required.")

    cases = load_cases(root)
    case_id = "CASE-" + candidate_id

    for case in cases:
        if case.get("case_id") == case_id:
            return case, False

    case = {
        "case_id": case_id,
        "candidate_id": candidate_id,
        "source_type": "provisional_benchmark",
        "benchmark_path": str(source.relative_to(root)),
        "review_status": "provisional",
        "validation_status": "not_assessed",
        "decision_status": "not_assessed",
        "created_at": _utc_now(),
    }

    cases.append(case)

    destination = root / "data/research_cases.json"
    destination.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary = tempfile.mkstemp(
        dir=destination.parent,
        prefix=".research_cases_",
        suffix=".tmp",
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(cases, file, indent=2)
            file.write("\n")
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    return case, True


def get_case(project_root, candidate_id):
    """Return an existing case, without modifying the registry."""
    case_id = "CASE-" + str(candidate_id).strip()

    for case in load_cases(project_root):
        if case.get("case_id") == case_id:
            return case

    return None


def save_validation_assessment(project_root, candidate_id, assessment):
    """Persist an automated assessment without approving evidence."""
    import copy

    root = Path(project_root).resolve()
    candidate_id = str(candidate_id).strip()

    if not candidate_id:
        raise ValueError("Candidate ID is required.")

    if not isinstance(assessment, dict):
        raise ValueError("Assessment must be a dictionary.")

    if assessment.get("benchmark_id") != candidate_id:
        raise ValueError("Assessment benchmark ID does not match.")

    if assessment.get("assessment_type") != "automated_evidence_check":
        raise ValueError("Unsupported assessment type.")

    cases = load_cases(root)
    case_id = "CASE-" + candidate_id

    matches = [
        index for index, case in enumerate(cases)
        if case.get("case_id") == case_id
    ]

    if len(matches) != 1:
        raise ValueError(
            "Expected exactly one existing research case."
        )

    index = matches[0]
    case = copy.deepcopy(cases[index])

    if case.get("candidate_id") != candidate_id:
        raise ValueError("Research-case candidate mismatch.")

    saved = copy.deepcopy(assessment)
    saved["assessment_type"] = "automated_evidence_check"
    saved["human_approved"] = False
    saved["scientifically_verified"] = False
    saved["saved_at"] = _utc_now()

    case["validation_assessment"] = saved
    case["validation_status"] = "automated_assessed"
    case["updated_at"] = saved["saved_at"]

    # Preserve review_status, source references and decision_status.
    cases[index] = case

    destination = root / "data/research_cases.json"
    destination.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary = tempfile.mkstemp(
        dir=destination.parent,
        prefix=".research_cases_",
        suffix=".tmp",
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(cases, file, indent=2)
            file.write("\n")

        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    return case
