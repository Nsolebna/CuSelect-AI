"""Offline tests of revision-only recovery."""

# PSEUDOCODE
# 1. Create a simulated interrupted research run.
# 2. Replace OpenAI with a fake, local client.
# 3. Verify recovery reuses the saved critique.
# 4. Block duplicate requests.
# 5. Preserve evidence after failures.
# 6. Reject source changes during recovery.

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS))

from check_research_recovery import (
    sha256,
)
import check_research_recovery as validator

spec = importlib.util.spec_from_file_location(
    "cuselect_resume_test",
    SCRIPTS / "resume_research_cycle.py",
)
resume_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resume_module)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(
        json.dumps(value, indent=2),
        encoding="utf-8",
    )


class FakeOpenAI:
    """Records simulated calls; never contacts the API."""

    instances = []

    def __init__(self, **kwargs):
        self.settings = kwargs
        self.calls = []
        self.responses = SimpleNamespace(parse=self.parse)
        self.instances.append(self)

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_parsed=None)


@pytest.fixture
def interrupted_run(tmp_path, monkeypatch):
    run = tmp_path / "interrupted_run"
    run.mkdir()

    # Copy source bytes for safe, isolated mutation tests.
    sources = dict(validator.SOURCES)
    original_literature = sources["literature"]

    literature_copy = tmp_path / "literature.json"
    literature_copy.write_bytes(
        original_literature.read_bytes()
    )
    sources["literature"] = literature_copy

    monkeypatch.setattr(
        validator, "SOURCES", sources
    )
    monkeypatch.setattr(
        resume_module, "SOURCES", sources
    )

    original = (
        ROOT / "data/agent_runs"
        / "llm_scientific_critique_with_dft_v3.json"
    )

    critique = read(original)

    critique["source_sha256"] = {
        name: sha256(path)
        for name, path in sources.items()
    }

    critique_path = run / "scientific_critique.json"
    write(critique_path, critique)

    write(run / "failure.json", {
        "status": "failed",
        "failed_stage": "revision_agent",
        "llm_requests_attempted": 1,
        "saved_critique_available": True,
        "saved_critique_sha256": sha256(critique_path),
        "saved_revision_available": False,
        "automatic_dft_execution": False,
    })

    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "offline-test-not-a-real-key",
    )
    monkeypatch.setattr(
        resume_module, "load_dotenv", lambda *args: None
    )
    monkeypatch.setattr(
        resume_module, "OpenAI", FakeOpenAI
    )

    FakeOpenAI.instances.clear()

    return run


def install_fake_revision(monkeypatch, fail=False, hook=None):
    calls = []

    def fake_revision(
        design,
        critique,
        client=None,
        model=None,
        computational_context=None,
        critique_source_path=None,
    ):
        calls.append({
            "critique": critique,
            "source": critique_source_path,
        })

        # Simulate exactly one LLM request.
        client.responses.parse(
            model=model,
            input="offline-test",
        )

        if hook is not None:
            hook()

        if fail:
            raise RuntimeError(
                "Simulated revision failure"
            )

        return {
            "agent": "llm_revision_agent",
            "predicted_fe_percent": None,
            "critic_findings_expected": 6,
            "critic_findings_addressed": 6,
            "revision": {
                "candidate_name": "Offline revised catalyst",
                "controlled_experiments": [
                    {"name": "Matched-pattern study"}
                ],
                "next_decision_gate": (
                    "Require human scientific review."
                ),
            },
        }

    monkeypatch.setattr(
        resume_module,
        "generate_revision",
        fake_revision,
    )

    return calls


def test_dry_run_makes_no_request(
    interrupted_run, monkeypatch
):
    calls = install_fake_revision(monkeypatch)

    plan = resume_module.resume(
        interrupted_run,
        execute_live=False,
    )

    assert plan["remaining_request_allowance"] == 1
    assert calls == []
    assert not (
        interrupted_run / "resume_attempt.json"
    ).exists()


def test_successful_recovery_uses_saved_critique(
    interrupted_run, monkeypatch
):
    calls = install_fake_revision(monkeypatch)

    original_path = (
        interrupted_run / "scientific_critique.json"
    )
    original_hash = sha256(original_path)

    resume_module.resume(
        interrupted_run,
        execute_live=True,
    )

    assert len(calls) == 1
    assert Path(calls[0]["source"]) == original_path
    assert calls[0]["critique"] == read(original_path)

    assert sha256(original_path) == original_hash
    assert (
        interrupted_run / "revised_candidate.json"
    ).is_file()
    assert (
        interrupted_run / "research_run.json"
    ).is_file()
    assert (
        interrupted_run / "resume_attempt.json"
    ).is_file()

    assert read(
        interrupted_run / "research_run.json"
    )["status"] == "completed_pending_human_review"

    assert len(FakeOpenAI.instances) == 1
    assert FakeOpenAI.instances[0].settings[
        "max_retries"
    ] == 0
    assert len(FakeOpenAI.instances[0].calls) == 1


def test_second_recovery_is_blocked(
    interrupted_run, monkeypatch
):
    calls = install_fake_revision(monkeypatch)

    resume_module.resume(
        interrupted_run,
        execute_live=True,
    )

    with pytest.raises(
        RuntimeError,
        match="already reserved",
    ):
        resume_module.resume(
            interrupted_run,
            execute_live=True,
        )

    assert len(calls) == 1


def test_failure_preserves_original_critique(
    interrupted_run, monkeypatch
):
    install_fake_revision(monkeypatch, fail=True)

    critique_path = (
        interrupted_run / "scientific_critique.json"
    )
    before = sha256(critique_path)

    with pytest.raises(
        RuntimeError,
        match="Simulated revision failure",
    ):
        resume_module.resume(
            interrupted_run,
            execute_live=True,
        )

    assert sha256(critique_path) == before
    assert (
        interrupted_run / "resume_attempt.json"
    ).exists()
    assert (
        interrupted_run / "resume_failure.json"
    ).exists()
    assert not (
        interrupted_run / "revised_candidate.json"
    ).exists()

    failure = read(
        interrupted_run / "resume_failure.json"
    )
    assert failure["automatic_retry_allowed"] is False


def test_source_changed_during_recovery_is_rejected(
    interrupted_run, monkeypatch
):
    literature = resume_module.SOURCES["literature"]

    def modify_source():
        record = read(literature)
        record["summary"] = (
            "Altered while the revision was running."
        )
        write(literature, record)

    install_fake_revision(
        monkeypatch,
        hook=modify_source,
    )

    with pytest.raises(
        ValueError,
        match="Source changed during recovery: literature",
    ):
        resume_module.resume(
            interrupted_run,
            execute_live=True,
        )

    assert not (
        interrupted_run / "revised_candidate.json"
    ).exists()
    assert (
        interrupted_run / "resume_failure.json"
    ).exists()
