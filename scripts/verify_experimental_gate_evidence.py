"""CuSelect-AI — verify provenance of experimental gate evidence."""

# PSEUDOCODE
# 1. Read structured evidence records.
# 2. Match a human-reviewed gate to its evidence ID.
# 3. Verify the experiment identity and evidence type.
# 4. Locate the source file inside the allowed evidence directory.
# 5. Compare the file's actual SHA-256 to the recorded fingerprint.
# 6. Require observations, controls, limitations and review metadata.
# 7. Never equate file integrity with independent scientific truth.

import hashlib
import json
from pathlib import Path

EXPERIMENTS = (
    "Fabrication and stability qualification",
    "Matched-pattern electrolysis and transport accounting",
    "External-CO response and source-resolved tracing",
)

VALID_DECISIONS = {"qualified", "failed", "inconclusive"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def required_text(record, field):
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or empty field: {field}")
    return value


def verify_evidence_record(record, evidence_root):
    """Verify a record and the exact source-file bytes."""

    if not isinstance(record, dict):
        raise ValueError("Evidence record must be an object.")

    record_id = required_text(record, "record_id")
    experiment = required_text(record, "experiment")

    if experiment not in EXPERIMENTS:
        raise ValueError("Unknown experiment.")

    if record.get("evidence_type") != "experimental":
        raise ValueError(
            "Qualification requires experimental evidence."
        )

    relative = Path(required_text(record, "source_path"))

    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Unsafe evidence source path.")

    root = Path(evidence_root).resolve()
    source = (root / relative).resolve()

    if not source.is_relative_to(root):
        raise ValueError(
            "Evidence source escapes the allowed directory."
        )

    if not source.is_file():
        raise ValueError("Experimental source file missing.")

    expected = required_text(record, "source_sha256")

    if len(expected) != 64 or any(
        char not in "0123456789abcdef"
        for char in expected
    ):
        raise ValueError("Invalid SHA-256 fingerprint.")

    if sha256(source) != expected:
        raise ValueError("Experimental source hash mismatch.")

    for field in (
        "observations",
        "controls",
        "limitations",
    ):
        entries = record.get(field)

        if (
            not isinstance(entries, list)
            or not entries
            or any(
                not isinstance(item, str) or not item.strip()
                for item in entries
            )
        ):
            raise ValueError(
                f"Missing documented experimental {field}."
            )

    required_text(record, "reviewer")
    required_text(record, "review_rationale")
    required_text(record, "reviewed_at")

    if record.get("review_decision") not in VALID_DECISIONS:
        raise ValueError("Invalid scientific review decision.")

    return {
        "record_id": record_id,
        "experiment": experiment,
        "source_sha256": expected,
        "review_decision": record["review_decision"],
        "provenance_verified": True,
        "scientific_truth_independently_verified": False,
    }


def verify_gate_reference(review, registry, evidence_root):
    """Check a gate decision against a structured record."""

    if not isinstance(review, dict):
        raise ValueError("Invalid gate review.")

    if not isinstance(registry, dict):
        raise ValueError("Invalid evidence registry.")

    if registry.get("schema_version") != "1.0":
        raise ValueError("Unexpected evidence registry version.")

    records = registry.get("records")

    if not isinstance(records, list):
        raise ValueError("Registry records must be a list.")

    ids = [required_text(item, "record_id") for item in records]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate evidence record IDs.")

    reference = required_text(review, "evidence_reference")

    matching = [
        item for item in records
        if item["record_id"] == reference
    ]

    if len(matching) != 1:
        raise ValueError("Evidence reference not found.")

    result = verify_evidence_record(
        matching[0],
        evidence_root,
    )

    if review.get("experiment") != result["experiment"]:
        raise ValueError("Evidence belongs to another experiment.")

    if review.get("status") != result["review_decision"]:
        raise ValueError(
            "Gate status differs from evidence review decision."
        )

    if review.get("reviewer") != matching[0]["reviewer"]:
        raise ValueError("Reviewer identity mismatch.")

    if review.get("rationale") != matching[0]["review_rationale"]:
        raise ValueError("Review rationale mismatch.")

    return result
