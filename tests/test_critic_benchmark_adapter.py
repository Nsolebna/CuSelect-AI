"""Offline tests for the CuSelect-AI critic benchmark adapter."""

# PSEUDOCODE
# 1. Prepare all four scientific benchmark requests.
# 2. Verify each request contains its intended question.
# 3. Ensure assessment criteria remain hidden.
# 4. Check that input fingerprints are reproducible.
# 5. Check that changing a question changes its fingerprint.
# 6. Reject invalid benchmark identities.

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

for directory in (ROOT / "src", ROOT / "scripts"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import prepare_critic_benchmark_requests as adapter

from cuselect.agents.llm_critic_agent import (
    ScientificCritique,
)


def test_four_requests_use_correct_schema():
    requests = adapter.prepare_requests()

    assert len(requests) == 4
    assert {r["id"] for r in requests} == {
        "B01", "B02", "B03", "B06"
    }

    assert all(
        r["text_format"] is ScientificCritique
        for r in requests
    )


def test_each_request_contains_only_its_own_question():
    packets = json.loads(
        adapter.BENCHMARK.read_text(encoding="utf-8")
    )
    requests = adapter.prepare_requests()

    questions = {
        case["id"]: case["scientific_input"]
        for case in packets["cases"]
    }

    for request in requests:
        user_message = request["messages"][1]["content"]

        assert questions[request["id"]] in user_message

        for other_id, other_question in questions.items():
            if other_id != request["id"]:
                assert other_question not in user_message


def test_rubric_criteria_not_exposed():
    packets = json.loads(
        adapter.BENCHMARK.read_text(encoding="utf-8")
    )
    cases = {
        case["id"]: case
        for case in packets["cases"]
    }

    for request in adapter.prepare_requests():
        serialized = json.dumps(
            request["messages"],
            sort_keys=True,
            ensure_ascii=False,
        )

        criteria = (
            cases[request["id"]]["required_elements"]
            + cases[request["id"]]["forbidden_conclusions"]
        )

        assert all(
            criterion not in serialized
            for criterion in criteria
        )


def test_fingerprints_are_reproducible():
    first = adapter.prepare_requests()
    second = adapter.prepare_requests()

    for a, b in zip(first, second):
        assert a["id"] == b["id"]
        assert a["input_sha256"] == b["input_sha256"]
        assert a["request_sha256"] == b["request_sha256"]
        assert a["instruction_sha256"] == b["instruction_sha256"]


def test_modified_question_changes_fingerprint(
    tmp_path, monkeypatch
):
    original = json.loads(
        adapter.BENCHMARK.read_text(encoding="utf-8")
    )

    modified = copy.deepcopy(original)
    modified["cases"][0]["scientific_input"] += (
        " Additional hypothetical condition."
    )

    path = tmp_path / "modified_benchmark.json"
    path.write_text(
        json.dumps(modified),
        encoding="utf-8",
    )

    before = adapter.prepare_requests()

    monkeypatch.setattr(
        adapter,
        "BENCHMARK",
        path,
    )

    after = adapter.prepare_requests()

    assert (
        before[0]["input_sha256"]
        != after[0]["input_sha256"]
    )
    assert (
        before[0]["request_sha256"]
        != after[0]["request_sha256"]
    )


def test_duplicate_case_identity_rejected(
    tmp_path, monkeypatch
):
    original = json.loads(
        adapter.BENCHMARK.read_text(encoding="utf-8")
    )

    modified = copy.deepcopy(original)
    modified["cases"][1]["id"] = "B01"

    path = tmp_path / "duplicate_cases.json"
    path.write_text(
        json.dumps(modified),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        adapter,
        "BENCHMARK",
        path,
    )

    with pytest.raises(
        ValueError,
        match="Invalid benchmark case identifiers",
    ):
        adapter.prepare_requests()
