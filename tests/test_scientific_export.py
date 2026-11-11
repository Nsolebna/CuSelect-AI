"""Tests for controlled scientific export."""

from unittest.mock import patch

from cuselect.scientific_export import (
    canonical_json,
    export_approved_claim,
    prepare_export,
    sha256_bytes,
)


def test_canonical_hash_is_independent_of_key_order():
    a = {"paper_id": "P009", "value": 60.37}
    b = {"value": 60.37, "paper_id": "P009"}

    assert sha256_bytes(canonical_json(a)) == sha256_bytes(
        canonical_json(b)
    )


def test_missing_approval_blocks_export(tmp_path):
    with patch(
        "cuselect.scientific_export.promotion_preflight",
        return_value={
            "eligible": False,
            "problems": ["human_approval_missing"],
        },
    ):
        result = export_approved_claim(tmp_path)

    assert result["exportable"] is False
    assert not (
        tmp_path / "data/processed/scientific_evidence_versions"
    ).exists()


def test_preparation_does_not_write_files(tmp_path):
    with patch(
        "cuselect.scientific_export.promotion_preflight",
        return_value={
            "eligible": False,
            "problems": ["human_approval_missing"],
        },
    ):
        result = prepare_export(tmp_path)

    assert result["package"] is None
    assert list(tmp_path.iterdir()) == []
