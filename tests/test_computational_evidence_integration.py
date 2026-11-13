"""Offline regression tests for computational evidence integration."""

# PSEUDOCODE
# 1. Load saved design, literature and critique fixtures.
# 2. Replace the OpenAI client with a fake client.
# 3. Verify compatibility with the original critic.
# 4. Verify computational evidence reaches the prompt.
# 5. Reject altered energies and unsupported FE claims.
# 6. Reject invalid literature measurement references.
# 7. Never make a real API request.

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cuselect.agents.llm_critic_agent import (
    ScientificCritique,
    generate_critique,
)

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/agent_runs"
CONTEXT = (
    ROOT / "data/processed/18_agent_evidence_context"
    / "agent_evidence_context_v1.json"
)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class FakeClient:
    """Capture requests without contacting the OpenAI API."""

    def __init__(self, critique):
        self.critique = critique
        self.calls = []
        self.responses = self

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_parsed=self.critique)


@pytest.fixture
def agent_inputs():
    design = load_json(
        RUNS / "llm_design_proposals_v2.json"
    )
    literature = load_json(
        RUNS / "literature_evidence_v1.json"
    )
    saved = load_json(
        RUNS / "llm_scientific_critique_v2.json"
    )

    critique = ScientificCritique.model_validate(
        saved["critique"]
    )
    return design, literature, critique


def test_legacy_critic_remains_compatible(agent_inputs):
    design, literature, critique = agent_inputs
    client = FakeClient(critique)

    result = generate_critique(
        design,
        literature,
        client=client,
        model="offline-mock",
    )

    assert len(client.calls) == 1

    prompt = json.loads(
        client.calls[0]["input"][1]["content"]
    )

    assert "approved_evidence" in prompt
    assert "computational_evidence" not in prompt
    assert (
        "computational_evidence_provenance"
        not in result
    )


def test_verified_context_reaches_critic(agent_inputs):
    design, literature, critique = agent_inputs
    client = FakeClient(critique)

    result = generate_critique(
        design,
        literature,
        client=client,
        model="offline-mock",
        computational_context=CONTEXT,
    )

    assert len(client.calls) == 1

    request = client.calls[0]
    prompt = json.loads(
        request["input"][1]["content"]
    )

    assert request["store"] is False
    assert "approved_evidence" in prompt
    assert "computational_evidence" in prompt
    assert "computational_evidence_rules" in prompt

    context = prompt["computational_evidence"]

    assert context["reference"]["method"] == "GPAW-PBE"
    assert context["reference"]["kpoints"] == [6, 6, 1]
    assert context["reference"]["status"] == "preliminary_dft"

    assert (
        context["evidence_assessment"]["ethylene_selectivity"]
        == "not_predicted"
    )

    provenance = result["computational_evidence_provenance"]
    assert provenance["validation"] == (
        "provenance_and_scope_checked"
    )


@pytest.mark.parametrize(
    "change",
    ["energy", "selectivity"],
)
def test_tampered_context_rejected_before_api(
    agent_inputs, tmp_path, change
):
    design, literature, critique = agent_inputs
    client = FakeClient(critique)

    context = copy.deepcopy(load_json(CONTEXT))

    if change == "energy":
        context["reference"][
            "delta_sep_minus_nn_ev"
        ] = 0.5
    else:
        context["evidence_assessment"][
            "ethylene_selectivity"
        ] = "predicted"

    path = tmp_path / "tampered_context.json"
    path.write_text(
        json.dumps(context),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        generate_critique(
            design,
            literature,
            client=client,
            model="offline-mock",
            computational_context=path,
        )

    assert client.calls == []


def test_invalid_literature_reference_rejected(agent_inputs):
    design, literature, critique = agent_inputs

    changed_design = copy.deepcopy(design)
    references = changed_design["proposal"][
        "supporting_evidence"
    ]

    assert references, "Expected saved literature references"

    references[0]["measurement_id"] = (
        "INVALID-MEASUREMENT-ID"
    )

    client = FakeClient(critique)

    with pytest.raises(ValueError):
        generate_critique(
            changed_design,
            literature,
            client=client,
            model="offline-mock",
            computational_context=CONTEXT,
        )

    assert client.calls == []


@pytest.mark.parametrize(
    "field",
    ["scientific_limitations", "agent_instructions"],
)
def test_modified_scientific_context_rejected(
    agent_inputs, tmp_path, field
):
    """Reject text-only tampering before contacting an LLM."""

    design, literature, critique = agent_inputs
    client = FakeClient(critique)

    context = copy.deepcopy(load_json(CONTEXT))

    if field == "scientific_limitations":
        context[field].append(
            "Invented scientific limitation."
        )
    else:
        context[field].append(
            "Invented instruction to the scientific critic."
        )

    path = tmp_path / "modified_context.json"
    path.write_text(
        json.dumps(context),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Computational context integrity check failed",
    ):
        generate_critique(
            design,
            literature,
            client=client,
            model="offline-mock",
            computational_context=path,
        )

    assert client.calls == []
