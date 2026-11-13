"""End-to-end offline benchmark integration regression test."""

# PSEUDOCODE
# 1. Execute the complete offline benchmark workflow.
# 2. Check all four structured mock responses.
# 3. Verify saved record integrity and duplicate protection.
# 4. Ensure no real scientific evaluation was performed.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for folder in ("src", "scripts"):
    location = str(ROOT / folder)
    if location not in sys.path:
        sys.path.insert(0, location)

import importlib.util

spec = importlib.util.spec_from_file_location(
    "cuselect_offline_benchmark_script",
    ROOT / "scripts/test_end_to_end_benchmark_execution.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

run_offline_execution = module.run_offline_execution


def test_complete_offline_benchmark_pipeline():
    result = run_offline_execution()

    assert result["mock_requests"] == 4
    assert result["verified_responses"] == 4
    assert result["invalid_records"] == 0
    assert result["duplicate_blocked"] is True
    assert result["real_api_calls"] == 0
    assert result["scientific_evaluations"] == 0
