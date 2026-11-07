# CuSelect-AI — Research Watcher CLI tests
#
# PSEUDOCODE
# 1. Simulate the Research Watcher engine.
# 2. Verify preview is the default.
# 3. Verify explicit preview never requests saving.
# 4. Verify --save requests controlled persistence.
# 5. Verify custom command-line arguments.
# 6. Verify errors return nonzero exit codes.
# 7. Reject conflicting operating modes.
# 8. Verify the help command.

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cuselect.watcher_cli as cli


@pytest.fixture
def simulated_engine(monkeypatch):
    calls = []

    def fake_scan(**kwargs):
        calls.append(kwargs)

        return {
            "retrieved_count": 30,
            "previously_seen_count": 30,
            "newly_seen_count": 0,
            "new_papers": [],
            "history_saved": kwargs["persist_history"],
        }

    monkeypatch.setattr(
        cli,
        "scan_and_digest",
        fake_scan,
    )

    return calls


def test_default_mode_is_preview(simulated_engine, capsys):
    result = cli.main([])

    assert result == 0
    assert len(simulated_engine) == 1

    assert simulated_engine[0]["persist_history"] is False

    output = capsys.readouterr().out

    assert "SCIENTIFIC RESEARCH DIGEST" in output
    assert "History saved: NO" in output


def test_explicit_preview_is_read_only(simulated_engine):
    result = cli.main(["--preview"])

    assert result == 0
    assert simulated_engine[0]["persist_history"] is False


def test_save_mode_requests_persistence(
    simulated_engine, capsys
):
    result = cli.main(["--save"])

    assert result == 0
    assert simulated_engine[0]["persist_history"] is True

    output = capsys.readouterr().out

    assert "History saved: YES" in output


def test_custom_arguments_are_forwarded(simulated_engine):
    result = cli.main([
        "--preview",
        "--history", "example/history.json",
        "--query", "Cu Ag CO2RR",
        "--rows", "12",
        "--minimum-results", "8",
    ])

    assert result == 0

    arguments = simulated_engine[0]

    assert arguments["history_path"] == "example/history.json"
    assert arguments["query"] == "Cu Ag CO2RR"
    assert arguments["rows"] == 12
    assert arguments["minimum_results"] == 8


def test_engine_failure_returns_error(monkeypatch, capsys):
    def fail(**kwargs):
        raise OSError("Simulated Crossref failure")

    monkeypatch.setattr(
        cli,
        "scan_and_digest",
        fail,
    )

    result = cli.main(["--save"])

    assert result == 1

    error = capsys.readouterr().err

    assert "RESEARCH WATCHER FAILED" in error
    assert "Simulated Crossref failure" in error


def test_conflicting_modes_are_rejected():
    with pytest.raises(SystemExit) as error:
        cli.main(["--preview", "--save"])

    assert error.value.code == 2


def test_help_command_exits_successfully(capsys):
    with pytest.raises(SystemExit) as result:
        cli.main(["--help"])

    assert result.value.code == 0

    output = capsys.readouterr().out

    assert "--preview" in output
    assert "--save" in output
    assert "--history" in output
