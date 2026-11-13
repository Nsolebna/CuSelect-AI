"""Offline tests for evidence-aware catalyst revision."""

# PSEUDOCODE
# 1. Load the existing proposal, critique and revision.
# 2. Simulate the LLM with a fake client.
# 3. Verify computational evidence reaches the prompt.
# 4. Reject tampered context and modified critique.
# 5. Confirm no real API request is made.

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cuselect.agents.llm_revision_agent import (
    RevisedCandidate,
    generate_revision,
)

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/agent_runs"

CONTEXT = (
    ROOT / "data/processed/18_agent_evidence_context"
    / "agent_evidence_context_v1.json"
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def inputs():
    design = load(RUNS / "llm_design_proposals_v2.json")
    critique = load(
        RUNS / "llm_scientific_critique_with_dft_v3.json"
    )
    previous = load(
        RUNS / "llm_revised_candidate_v2.json"
    )

    revision = RevisedCandidate.model_validate(
        previous["revision"]
    )

    return design, critique, revision


class FakeClient:
    def __init__(self, revision):
        self.revision = revision
        self.calls = []
        self.responses = self

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            output_parsed=self.revision
        )


def test_computational_evidence_reaches_revision(inputs):
    design, critique, revision = inputs
    client = FakeClient(revision)

    result = generate_revision(
        design,
        critique,
        client=client,
        model="offline-mock",
        computational_context=CONTEXT,
    )

    assert len(client.calls) == 1

    prompt = json.loads(
        client.calls[0]["input"][1]["content"]
    )

    assert "computational_evidence" in prompt
    assert "computational_evidence_rules" in prompt
    assert "scientific_critique" in prompt

    assert result["source_files"]["critique"] == (
        "llm_scientific_critique_with_dft_v3.json"
    )

    assert (
        result["computational_evidence_provenance"]["status"]
        == "verified_for_revision"
    )


def test_tampered_context_rejected(inputs, tmp_path):
    design, critique, revision = inputs
    client = FakeClient(revision)

    context = copy.deepcopy(load(CONTEXT))
    context["reference"]["delta_sep_minus_nn_ev"] = 0.5

    path = tmp_path / "tampered.json"
    path.write_text(
        json.dumps(context),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        generate_revision(
            design,
            critique,
            client=client,
            model="offline-mock",
            computational_context=path,
        )

    assert client.calls == []


def test_modified_critique_rejected(inputs):
    design, critique, revision = inputs
    client = FakeClient(revision)

    changed = copy.deepcopy(critique)
    changed["critique"]["disposition_reason"] = (
        "Invented scientific conclusion."
    )

    with pytest.raises(ValueError):
        generate_revision(
            design,
            changed,
            client=client,
            model="offline-mock",
            computational_context=CONTEXT,
        )

    assert client.calls == []
