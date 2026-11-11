"""Versioned scientific evidence export.

PSEUDOCODE
1. Check the controlled scientific promotion gate.
2. Refuse export when human approval is absent.
3. Load and validate the structured scientific claim.
4. Create a content-addressed versioned package.
5. Preserve the existing trusted RAG corpus.
"""

import hashlib
import json
import os
from pathlib import Path

from cuselect.evidence import EvidenceClaim
from cuselect.scientific_promotion import promotion_preflight


def canonical_json(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def prepare_export(root):
    """Construct an export package without writing files."""

    root = Path(root)
    report = promotion_preflight(root)

    if not report.get("eligible", False):
        return {
            "exportable": False,
            "blockers": report.get("problems", []),
            "package": None,
        }

    data = root / "data"

    claim_path = data / "reports/pending_scientific_claim.json"
    approval_path = data / "scientific_claim_approvals.json"

    claim = EvidenceClaim.model_validate(
        json.loads(claim_path.read_text(encoding="utf-8"))
    )

    approvals = json.loads(
        approval_path.read_text(encoding="utf-8")
    )

    approval = approvals[claim.evidence_id]

    # This is a staging package, not an immutable audit ledger.
    payload = {
        "schema_version": "1.0",
        "evidence_id": claim.evidence_id,
        "paper_id": claim.paper_id,
        "doi": claim.doi,
        "claim": claim.model_dump(mode="json"),
        "review": approval,
        "source_sha256": approval["source_xml_sha256"],
    }

    package_hash = sha256_bytes(canonical_json(payload))

    package = {
        "package_type": "scientific_evidence",
        "package_version": package_hash[:16],
        "payload_sha256": package_hash,
        "payload": payload,
    }

    return {
        "exportable": True,
        "blockers": [],
        "package": package,
    }


def export_approved_claim(root):
    """Export to a new versioned directory; never overwrite."""

    root = Path(root)
    result = prepare_export(root)

    if not result["exportable"]:
        return result

    package = result["package"]

    destination = (
        root / "data/processed/scientific_evidence_versions"
        / package["package_version"]
    )

    destination.mkdir(parents=True, exist_ok=True)
    target = destination / "evidence_package.json"

    contents = canonical_json(package)

    # Exclusive creation prevents overwriting existing packages.
    try:
        fd = os.open(
            str(target),
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError:
        if target.read_bytes() != contents:
            raise RuntimeError(
                "Existing package content mismatch"
            )
    else:
        with os.fdopen(fd, "wb") as f:
            f.write(contents)

    return {
        "exportable": True,
        "package_version": package["package_version"],
        "package_path": str(target),
        "trusted_registry_modified": False,
        "rag_corpus_modified": False,
    }
