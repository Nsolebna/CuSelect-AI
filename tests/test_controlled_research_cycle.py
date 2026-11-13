"""Offline tests for controlled CuSelect-AI orchestration."""

# PSEUDOCODE
# 1. Import the controlled runner.
# 2. Replace external LLM calls with simulated responses.
# 3. Verify the complete critic-to-revision sequence.
# 4. Verify that no third request is permitted.
# 5. Simulate a revision failure and inspect saved records.
# 6. Never modify the original project research outputs.

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SCRIPT = SCRIPTS / "run_controlled_research_cycle.py"

# The runner imports the planner from the scripts directory.
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location(
    "cuselect_controlled_runner", SCRIPT
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class FakeOpenAI:
    """Never contacts an external API."""

    def __init__(self, **kwargs):
        self.settings = kwargs
        self.calls = []
        self.responses = SimpleNamespace(parse=self.parse)

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_parsed=None)


@pytest.fixture
def sandbox(monkeypatch, tmp_path):
    """Redirect orchestration output into a temporary folder."""

    output = tmp_path / "research_cycle_001"

    sources = {
        "design": sha256(runner.DESIGN),
        "literature": sha256(runner.LITERATURE),
        "computational_context": sha256(runner.CONTEXT),
    }

    plan = {
        "run_id": "research_cycle_001",
        "candidate": "Patterned Ag-island Cu foil",
        "source_sha256": sources,
    }

    monkeypatch.setattr(runner, "OUTPUT_DIR", output)
    monkeypatch.setattr(
        runner,
        "validate_plan",
        lambda: plan,
    )

    # Fake credentials are used only with FakeOpenAI.
    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "offline-test-not-a-real-key",
    )
    monkeypatch.setattr(runner, "OpenAI", FakeOpenAI)

    return output


def install_fake_agents(monkeypatch, fail_revision=False):
    """Simulate both agents while exercising the runner."""

    observed = {}

    def fake_critic(
        design,
        literature,
        client=None,
        model=None,
        computational_context=None,
    ):
        client.responses.parse(
            model=model,
            input="offline-critic-test",
        )

        return {
            "agent": "llm_scientific_critic",
            "candidate_name": (
                design["proposal"]["candidate_name"]
            ),
            "computational_evidence_provenance": {
                "validation": "provenance_and_scope_checked"
            },
            "critique": {
                "scientific_findings": [
                    {
                        "category": "evidence",
                        "finding": "Further validation needed.",
                    }
                ],
            },
        }

    def fake_revision(
        design,
        critique,
        client=None,
        model=None,
        computational_context=None,
        critique_source_path=None,
    ):
        observed["critique"] = critique
        observed["critique_source_path"] = (
            critique_source_path
        )

        if fail_revision:
            raise RuntimeError(
                "Simulated revision failure"
            )

        client.responses.parse(
            model=model,
            input="offline-revision-test",
        )

        return {
            "agent": "llm_revision_agent",
            "predicted_fe_percent": None,
            "critic_findings_expected": 1,
            "critic_findings_addressed": 1,
            "revision": {
                "candidate_name": "Revised test candidate",
                "controlled_experiments": [
                    {
                        "name": "Matched-pattern control"
                    }
                ],
                "next_decision_gate": (
                    "Human review before advancement."
                ),
            },
        }

    monkeypatch.setattr(
        runner, "generate_critique", fake_critic
    )
    monkeypatch.setattr(
        runner, "generate_revision", fake_revision
    )

    return observed


def test_default_mode_does_not_execute(
    monkeypatch, sandbox
):
    def forbidden():
        raise AssertionError(
            "Live execution should not occur."
        )

    monkeypatch.setattr(
        runner, "execute_live", forbidden
    )
    monkeypatch.setattr(
        sys, "argv", ["run_controlled_research_cycle.py"]
    )

    runner.main()

    assert not sandbox.exists()


def test_successful_two_stage_execution(
    monkeypatch, sandbox
):
    observed = install_fake_agents(monkeypatch)

    runner.execute_live()

    critic_path = sandbox / "scientific_critique.json"
    revision_path = sandbox / "revised_candidate.json"
    summary_path = sandbox / "research_run.json"

    assert critic_path.is_file()
    assert revision_path.is_file()
    assert summary_path.is_file()

    saved_critic = read(critic_path)
    saved_revision = read(revision_path)
    summary = read(summary_path)

    # The revision receives the saved critique, including
    # its newly recorded source fingerprints.
    assert observed["critique"] == saved_critic
    assert (
        Path(observed["critique_source_path"])
        == critic_path
    )

    assert saved_revision["agent"] == "llm_revision_agent"
    assert summary["llm_requests_attempted"] == 2
    assert summary["new_dft_calculations"] == 0
    assert summary["findings_addressed"] == 1
    assert summary["output_sha256"]["critique"] == (
        sha256(critic_path)
    )

    assert not (sandbox / "failure.json").exists()


def test_third_request_is_blocked():
    fake = FakeOpenAI(max_retries=0)
    budget = runner.RequestBudget(fake, maximum=2)

    budget.responses.parse(model="offline", input="1")
    budget.responses.parse(model="offline", input="2")

    with pytest.raises(
        RuntimeError,
        match="request budget exhausted",
    ):
        budget.responses.parse(
            model="offline", input="3"
        )

    assert budget.attempts == 2
    assert len(fake.calls) == 2


def test_revision_failure_preserves_critique(
    monkeypatch, sandbox
):
    install_fake_agents(
        monkeypatch, fail_revision=True
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated revision failure",
    ):
        runner.execute_live()

    critic_path = sandbox / "scientific_critique.json"
    failure_path = sandbox / "failure.json"

    assert critic_path.is_file()
    assert failure_path.is_file()
    assert not (
        sandbox / "revised_candidate.json"
    ).exists()

    failure = read(failure_path)

    assert failure["status"] == "failed"
    assert failure["failed_stage"] == "revision_agent"
    assert failure["saved_critique_available"] is True
    assert failure["llm_requests_attempted"] == 1
