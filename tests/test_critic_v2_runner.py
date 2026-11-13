"""Offline validation tests for Scientific Critic v2."""

# PSEUDOCODE
# 1. Confirm the real v2 manifest is valid.
# 2. Substitute a modified scientific challenge in memory.
# 3. Verify the runner rejects the altered challenge.
# 4. Substitute modified system instructions in memory.
# 5. Verify the runner rejects the altered instructions.
# 6. Never execute model requests.

import copy
import json

import pytest

import plan_critic_v2_benchmark as planner
import run_critic_v2_benchmark as runner


def test_valid_v2_requests():
    plan, requests = runner.validate_execution_inputs()

    assert len(requests) == 4
    assert tuple(r["id"] for r in requests) == (
        "B01", "B02", "B03", "B06"
    )

    assert plan["automatic_retries"] == 0
    assert runner.dry_run()["actual_api_calls"] == 0

    assert plan["plan_sha256"] == (
        "61abb8dfb34606388c62976b27e845a"
        "097e800cf984fb319a29a4f1752fc22e7"
    )


def test_modified_scientific_input_rejected(monkeypatch):
    original_read = planner.Path.read_text

    def modified_read(path, *args, **kwargs):
        content = original_read(path, *args, **kwargs)

        if path == planner.MANIFEST_PATH:
            manifest = json.loads(content)
            manifest = copy.deepcopy(manifest)

            manifest["requests"][0]["messages"][1][
                "content"
            ] += "\nUNAUTHORIZED INPUT CHANGE"

            return json.dumps(manifest)

        return content

    monkeypatch.setattr(
        planner.Path,
        "read_text",
        modified_read,
    )

    with pytest.raises(ValueError):
        runner.validate_execution_inputs()


def test_modified_system_instructions_rejected(monkeypatch):
    original_read = planner.Path.read_text

    def modified_read(path, *args, **kwargs):
        content = original_read(path, *args, **kwargs)

        if path == planner.MANIFEST_PATH:
            manifest = json.loads(content)
            manifest = copy.deepcopy(manifest)

            manifest["requests"][0]["messages"][0][
                "content"
            ] += "\nUNAUTHORIZED INSTRUCTION"

            return json.dumps(manifest)

        return content

    monkeypatch.setattr(
        planner.Path,
        "read_text",
        modified_read,
    )

    with pytest.raises(ValueError):
        runner.validate_execution_inputs()
