"""Research protocol is explicit, valid and contains no fabricated results."""
from pathlib import Path
from cuselect.protocol import load_research_protocol
from cuselect.project_checks import require_project_root, environment_snapshot

ROOT = Path(__file__).resolve().parents[1]

def test_project_root():
    assert require_project_root(ROOT) == ROOT.resolve()

def test_protocol_has_falsifiable_objective():
    record = load_research_protocol(ROOT / "configs/CU-001_protocol.json")
    assert record.campaign_id == "CU-001"
    assert record.task_type == "evidence_reliability"
    assert "false_advancement" in record.evaluation.primary_metric
    assert record.evaluation.evaluation_status == "planned_not_run"
    assert not record.known_model_boundaries.selectivity_predicted
    assert record.system.initial_candidates == ["CU-001-REF", "CU-001-AG1"]

def test_privacy_preserving_environment_snapshot():
    values = environment_snapshot()
    assert "python" in values and "packages" in values
    assert all(key not in values for key in ("hostname", "username", "serial", "token"))
