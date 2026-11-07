
# CuSelect-AI — Phase II
# File: tests/test_evidence_store.py
#
# PSEUDOCODE
# 1. Copy the evidence registry, corpus, and manifest
#    into an isolated temporary test directory.
# 2. Confirm that valid copies are accepted.
# 3. Tamper with the corpus without updating its hash.
# 4. Tamper with a scientific claim and update its hash.
# 5. Revoke human approval in the copied registry.
# 6. Introduce duplicate or unapproved evidence.
# 7. Require the trusted loader to reject all invalid cases.
# 8. Never modify original research files.

import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.evidence_store import (
    EvidenceIntegrityError,
    load_verified_corpus,
)


REGISTRY = Path(
    "data/references/02_human_reviewed_claims.csv"
)

CORPUS = Path(
    "data/processed/06_rag_prototype/"
    "06_retrieval_corpus.jsonl"
)

MANIFEST = Path(
    "data/processed/06_rag_prototype/"
    "06_retrieval_manifest.json"
)


@pytest.fixture
def project_copy(tmp_path):
    """Create isolated copies of all three evidence files."""

    for relative_path in (REGISTRY, CORPUS, MANIFEST):
        destination = tmp_path / relative_path
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        shutil.copy2(
            ROOT / relative_path,
            destination,
        )

    return tmp_path


def read_corpus(project):
    path = project / CORPUS

    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def save_corpus(project, records, *, update_manifest):
    path = project / CORPUS

    payload = "".join(
        json.dumps(record, ensure_ascii=False) + "\n"
        for record in records
    )

    path.write_text(payload, encoding="utf-8")

    if update_manifest:
        manifest_path = project / MANIFEST
        manifest = json.loads(manifest_path.read_text())

        manifest["corpus_sha256"] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

        manifest["records"] = len(records)

        manifest_path.write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )


def change_registry_field(project, field, value):
    path = project / REGISTRY

    with path.open(
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file)
        fields = reader.fieldnames
        rows = list(reader)

    rows[0][field] = value

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def test_valid_evidence_is_accepted(project_copy):
    records = load_verified_corpus(project_copy)

    assert len(records) == 3


def test_corpus_hash_tampering_is_rejected(project_copy):
    records = read_corpus(project_copy)

    records[0]["claim_paraphrase"] += " ALTERED"

    save_corpus(
        project_copy,
        records,
        update_manifest=False,
    )

    with pytest.raises(EvidenceIntegrityError):
        load_verified_corpus(project_copy)


def test_rehashed_false_claim_is_rejected(project_copy):
    records = read_corpus(project_copy)

    records[0]["claim_paraphrase"] = (
        "Fabricated scientific observation"
    )

    save_corpus(
        project_copy,
        records,
        update_manifest=True,
    )

    with pytest.raises(EvidenceIntegrityError):
        load_verified_corpus(project_copy)


@pytest.mark.parametrize(
    "field,value",
    [
        ("review_status", "pending_review"),
        ("source_checked_by_human", "False"),
    ],
)
def test_revoked_approval_is_rejected(
    project_copy,
    field,
    value,
):
    change_registry_field(project_copy, field, value)

    with pytest.raises(EvidenceIntegrityError):
        load_verified_corpus(project_copy)


def test_duplicate_evidence_id_is_rejected(project_copy):
    records = read_corpus(project_copy)

    records.append(dict(records[0]))

    save_corpus(
        project_copy,
        records,
        update_manifest=True,
    )

    with pytest.raises(EvidenceIntegrityError):
        load_verified_corpus(project_copy)


def test_unapproved_new_record_is_rejected(project_copy):
    records = read_corpus(project_copy)

    new_record = dict(records[0])
    new_record["evidence_id"] = "E-AUTO-NEW-001"
    new_record["review_status"] = "pending_review"

    records.append(new_record)

    save_corpus(
        project_copy,
        records,
        update_manifest=True,
    )

    with pytest.raises(EvidenceIntegrityError):
        load_verified_corpus(project_copy)


# PSEUDOCODE
# 1. Alter retrieval text without changing structured scientific fields.
# 2. Recalculate the corpus hash to simulate a manipulated export.
# 3. Confirm the trusted loader rejects the altered text.
# 4. Repeat with a fabricated FE value in retrieval text.
# 5. Use temporary files only.

def test_rehashed_retrieval_text_injection_is_rejected(project_copy):
    records = read_corpus(project_copy)

    records[0]["text"] += (
        "\nScientific conclusion: proven commercial performance."
    )

    save_corpus(
        project_copy,
        records,
        update_manifest=True,
    )

    with pytest.raises(EvidenceIntegrityError):
        load_verified_corpus(project_copy)


def test_rehashed_retrieval_fe_manipulation_is_rejected(project_copy):
    records = read_corpus(project_copy)

    target = next(
        record
        for record in records
        if record["evidence_id"] == "E-P005-FE-C2H4-001"
    )

    assert "54.9%" in target["text"]

    target["text"] = target["text"].replace(
        "54.9%",
        "99.9%",
    )

    save_corpus(
        project_copy,
        records,
        update_manifest=True,
    )

    with pytest.raises(EvidenceIntegrityError):
        load_verified_corpus(project_copy)
