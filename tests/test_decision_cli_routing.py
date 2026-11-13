"""Regression tests for safe experiment-selector routing."""

# PSEUDOCODE
# 1. Run the legacy CLI without authorization.
# 2. Confirm it refuses operational execution.
# 3. Run it explicitly in simulation mode.
# 4. Confirm the simulation remains available.

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/adaptive_experiment_selector.py"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_legacy_cli_requires_simulation_flag():
    result = run_cli()

    assert result.returncode != 0
    assert "simulation-only" in result.stderr


def test_explicit_simulation_still_works():
    result = run_cli("--simulation-only")

    assert result.returncode == 0
    assert "ADAPTIVE EXPERIMENT SELECTOR" in result.stdout
    assert "Human scientific approval: Required" in result.stdout
