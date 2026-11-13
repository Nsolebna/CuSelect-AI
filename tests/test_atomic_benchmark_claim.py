"""Tests for exclusive benchmark execution-directory claims."""

# PSEUDOCODE
# 1. Verify existing empty directories cannot be reused.
# 2. Verify repeated execution cannot claim the same directory.
# 3. Verify a fresh run still works with a fake client.
# 4. Confirm blocked attempts never reach the client.

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]

for folder in ("src", "scripts"):
    location = str(ROOT / folder)
    if location not in sys.path:
        sys.path.insert(0, location)

import run_live_critic_benchmark as runner

from capture_critic_benchmark_offline import MockClient


class FakeResponses:
    def __init__(self):
        self.mock = MockClient()
        self.calls = []

    def parse(self, *, model, input, text_format, reasoning, store):
        assert reasoning == {"effort": "high"}
        case_id = json.loads(
            input[1]["content"]
        )["benchmark_case_id"]

        self.calls.append(case_id)

        result = self.mock.responses.parse(
            model="MOCK-NO-API",
            input=input,
            text_format=text_format,
            store=store,
        )

        return SimpleNamespace(
            output_parsed=result.output_parsed,
            id=f"FAKE-RESPONSE-{case_id}",
            model="FAKE-TEST-MODEL",
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_existing_empty_directory_rejected(tmp_path):
    root = tmp_path / "existing_empty_run"
    root.mkdir()

    client = FakeClient()

    with pytest.raises(
        ValueError,
        match="already claimed",
    ):
        runner.execute_live(
            root,
            model="FAKE-TEST-MODEL",
            client=client,
        )

    assert client.responses.calls == []


def test_completed_directory_cannot_be_reused(tmp_path):
    root = tmp_path / "fresh_run"

    first_client = FakeClient()

    result = runner.execute_live(
        root,
        model="FAKE-TEST-MODEL",
        client=first_client,
    )

    assert result["successful_responses"] == 4

    second_client = FakeClient()

    with pytest.raises(
        ValueError,
        match="Existing run artifacts require manual review",
    ):
        runner.execute_live(
            root,
            model="FAKE-TEST-MODEL",
            client=second_client,
        )

    assert second_client.responses.calls == []


def test_fresh_directory_is_claimed(tmp_path):
    root = tmp_path / "new_run"
    client = FakeClient()

    result = runner.execute_live(
        root,
        model="FAKE-TEST-MODEL",
        client=client,
    )

    assert root.is_dir()
    assert (root / "manifest.json").is_file()
    assert (root / "reservations").is_dir()
    assert (root / "responses").is_dir()

    assert result["successful_responses"] == 4
    assert len(client.responses.calls) == 4
