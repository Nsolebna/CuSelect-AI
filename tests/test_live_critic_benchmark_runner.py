"""Offline integration tests for the live benchmark runner."""

# PSEUDOCODE
# 1. Replace the real API with a fake structured-response client.
# 2. Simulate a request failure after reservation.
# 3. Verify successful capture of four responses.
# 4. Simulate a disk-write failure after a response arrives.
# 5. Ensure uncertain requests cannot be automatically repeated.
# 6. Never contact an external model provider.

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

from capture_critic_benchmark_offline import (
    MockClient,
)
from inspect_completed_benchmark_recovery import (
    inspect_completed_recovery,
)


class FakeResponses:
    def __init__(self, fail_on=None):
        self.mock = MockClient()
        self.calls = []
        self.fail_on = fail_on

    def parse(self, *, model, input, text_format, reasoning, store):
        assert reasoning == {"effort": "high"}
        payload = json.loads(input[1]["content"])
        case_id = payload["benchmark_case_id"]

        self.calls.append(case_id)

        if case_id == self.fail_on:
            raise RuntimeError("SIMULATED API FAILURE")

        result = self.mock.responses.parse(
            model="MOCK-NO-API",
            input=input,
            text_format=text_format,
            store=store,
        )

        # These values test record serialization only.
        # They are NOT real provider metadata.
        return SimpleNamespace(
            output_parsed=result.output_parsed,
            id=f"FAKE-RESPONSE-{case_id}",
            model="FAKE-PROVIDER-MODEL",
        )


class FakeClient:
    def __init__(self, fail_on=None):
        self.responses = FakeResponses(fail_on=fail_on)


def test_api_failure_keeps_reservation(tmp_path):
    root = tmp_path / "failed_run"
    client = FakeClient(fail_on="B01")

    with pytest.raises(
        RuntimeError, match="SIMULATED API FAILURE"
    ):
        runner.execute_live(
            root,
            model="FAKE-REQUESTED-MODEL",
            client=client,
        )

    assert client.responses.calls == ["B01"]

    report = inspect_completed_recovery(root)

    assert report["uncertain"] == 1
    assert report["not_reserved"] == 3
    assert report["response_integrity_verified"] == 0

    # A rerun must encounter the previous reservation
    # before submitting any additional request.
    new_client = FakeClient()

    with pytest.raises(
        ValueError, match="Existing run artifacts require manual review"
    ):
        runner.execute_live(
            root,
            model="FAKE-REQUESTED-MODEL",
            client=new_client,
        )

    assert new_client.responses.calls == []


def test_four_fake_responses_are_saved(tmp_path):
    root = tmp_path / "successful_run"
    client = FakeClient()

    result = runner.execute_live(
        root,
        model="FAKE-REQUESTED-MODEL",
        client=client,
    )

    assert result["successful_responses"] == 4
    assert client.responses.calls == [
        "B01", "B02", "B03", "B06"
    ]

    report = inspect_completed_recovery(root)

    assert report["response_integrity_verified"] == 4
    assert report["invalid_records"] == 0
    assert report["uncertain"] == 0

    # These fake responses are structurally valid,
    # but their declared provider origin is not real.
    assert all(
        item["provider_origin_independently_verified"]
        is False
        for item in report["cases"]
    )

    assert all(
        item["scientific_accuracy_established"]
        is False
        for item in report["cases"]
    )


def test_response_save_failure_stops_execution(
    tmp_path, monkeypatch
):
    root = tmp_path / "save_failure_run"
    client = FakeClient()

    original_write = runner.write_new_json

    def failing_write(path, data):
        if Path(path).parent.name == "responses":
            raise OSError("SIMULATED DISK WRITE FAILURE")

        return original_write(path, data)

    monkeypatch.setattr(
        runner,
        "write_new_json",
        failing_write,
    )

    with pytest.raises(
        OSError, match="SIMULATED DISK WRITE FAILURE"
    ):
        runner.execute_live(
            root,
            model="FAKE-REQUESTED-MODEL",
            client=client,
        )

    assert client.responses.calls == ["B01"]

    report = inspect_completed_recovery(root)

    assert report["uncertain"] == 1
    assert report["response_integrity_verified"] == 0

    # Once the response save fails, the case remains
    # reserved and cannot be automatically resubmitted.
    with pytest.raises(
        ValueError, match="Existing run artifacts require manual review"
    ):
        runner.execute_live(
            root,
            model="FAKE-REQUESTED-MODEL",
            client=FakeClient(),
        )
