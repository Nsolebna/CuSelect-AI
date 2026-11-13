"""Save discovered hypotheses as provisional research cases."""

import json
import os
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timezone

from cuselect.research_cases import load_cases


def save_discovery_case(
    project_root,
    *,
    title,
    hypothesis,
    research_question,
    sources=None,
):
    root = Path(project_root).resolve()

    title = str(title).strip()
    hypothesis = str(hypothesis).strip()
    research_question = str(research_question).strip()

    if not title or not hypothesis or not research_question:
        raise ValueError(
            "Title, hypothesis and research question are required."
        )

    if sources is None:
        sources = []

    if not isinstance(sources, list):
        raise ValueError("Sources must be a list.")

    # Create a distinct identity for each research hypothesis.
    candidate_id = "DISC-" + uuid.uuid4().hex[:12].upper()

    case = {
        "case_id": "CASE-" + candidate_id,
        "candidate_id": candidate_id,
        "source_type": "discovery_hypothesis",
        "title": title,
        "hypothesis": hypothesis,
        "research_question": research_question,
        "sources": sources,
        "review_status": "provisional",
        "validation_status": "not_assessed",
        "decision_status": "not_assessed",
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    # Reuse the existing research-case registry.
    cases = load_cases(root)
    if any(
        item.get("case_id") == case["case_id"]
        for item in cases
    ):
        raise RuntimeError("Duplicate research-case ID.")

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
            json.dump(cases, file, indent=2, ensure_ascii=False)
            file.write("\n")

        os.replace(temporary, destination)

    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    return case
