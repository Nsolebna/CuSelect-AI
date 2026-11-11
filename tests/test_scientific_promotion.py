"""Regression tests for the promotion gate."""

import json

from cuselect.scientific_promotion import (
    REQUIRED_CHECKS,
    promotion_preflight,
    sha256,
)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def fixture_root(tmp_path):
    data = tmp_path / "data"

    claim = {
        "evidence_id": "E-TEST",
        "paper_id": "P009",
        "doi": "10.1021/acsnanoscienceau.6c00129",
        "claim_paraphrase": "HOH Cu/Ag produces ethylene.",
        "claim_type": "experimental_observation",
        "source_extent": "full_text",
        "exact_source_location": "Results; Figure 4d",
        "catalyst_system": "HOH Cu/Ag",
        "target_or_observation": "ethylene",
        "review_status": "pending_source_review",
        "source_checked_by_human": False,
    }

    dossier = {
        "claim_id": "E-TEST",
        "paper_id": "P009",
        "doi": claim["doi"],
        "review_status": "awaiting_scientific_review",
        "performance_sources": ["Primary results text"],
        "methodology_sources": ["Flow-cell methods"],
        "figure": {"id": "fig4", "panel": "d"},
    }

    write_json(data / "reports/pending_scientific_claim.json", claim)
    write_json(data / "reports/hoh_cuag_evidence_dossier.json", dossier)

    registry = data / "papers.csv"
    registry.write_text(
        "paper_id,year,title,doi,kind,why_relevant\n"
        "P009,2026,Test,10.1021/acsnanoscienceau.6c00129,"
        "experimental,benchmark\n"
    )

    source = data / "raw/publications/PMC13692753.xml"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("<article/>")

    approval = {
        "claim_id": "E-TEST",
        "paper_id": "P009",
        "doi": claim["doi"],
        "decision": "approve",
        "reviewer": "reviewer@example.org",
        "timestamp": "2026-11-11T12:00:00+00:00",
        "reviewer_note": "Source independently checked.",
        "checks": {key: True for key in REQUIRED_CHECKS},
        "dossier_sha256": sha256(
            data / "reports/hoh_cuag_evidence_dossier.json"
        ),
        "claim_sha256": sha256(
            data / "reports/pending_scientific_claim.json"
        ),
        "source_xml_sha256": sha256(source),
        "rag_ingestion_status": "not_ingested",
    }

    write_json(
        data / "scientific_claim_approvals.json",
        {"E-TEST": approval},
    )

    return tmp_path


def test_valid_review_is_eligible_for_preflight(tmp_path):
    root = fixture_root(tmp_path)
    assert promotion_preflight(root)["eligible"] is True


def test_missing_approval_is_blocked(tmp_path):
    root = fixture_root(tmp_path)
    (root / "data/scientific_claim_approvals.json").unlink()
    assert promotion_preflight(root)["eligible"] is False


def test_rejected_decision_is_blocked(tmp_path):
    root = fixture_root(tmp_path)
    path = root / "data/scientific_claim_approvals.json"
    approvals = json.loads(path.read_text())
    approvals["E-TEST"]["decision"] = "reject"
    write_json(path, approvals)
    assert promotion_preflight(root)["eligible"] is False


def test_modified_source_is_blocked(tmp_path):
    root = fixture_root(tmp_path)
    source = root / "data/raw/publications/PMC13692753.xml"
    source.write_text("<article>changed</article>")
    result = promotion_preflight(root)
    assert result["eligible"] is False
    assert "source_xml_sha256_mismatch" in result["problems"]


def test_incomplete_scientific_review_is_blocked(tmp_path):
    root = fixture_root(tmp_path)
    path = root / "data/scientific_claim_approvals.json"
    approvals = json.loads(path.read_text())
    approvals["E-TEST"]["checks"]["correct_catalyst"] = False
    write_json(path, approvals)
    assert promotion_preflight(root)["eligible"] is False
