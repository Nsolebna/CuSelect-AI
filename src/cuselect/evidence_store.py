
# CuSelect-AI — Phase II
# Module: src/cuselect/evidence_store.py
#
# PSEUDOCODE
# 1. Load the human-reviewed evidence registry.
# 2. Load the RAG corpus and its manifest.
# 3. Verify the corpus SHA-256 and record counts.
# 4. Reject duplicate or missing evidence identifiers.
# 5. Require source-checked, human-verified registry records.
# 6. Compare all shared scientific fields with the registry.
# 7. Return verified records only when every check passes.
# 8. Never modify scientific records or grant new approval.

import csv
import hashlib
import json
from pathlib import Path


FIELD_MAPPING = {
    "paper_id": "paper_id",
    "doi": "doi",
    "claim_paraphrase": "claim_paraphrase",
    "source_extent": "source_extent",
    "exact_source_location": "source_location",
    "catalyst_system": "catalyst_system",
    "target_or_observation": "target_or_observation",
    "conditions": "conditions",
    "faradaic_efficiency_percent": "faradaic_efficiency_percent",
    "fe_product": "fe_product",
    "review_status": "review_status",
    "split_group": "split_group",
}


# PSEUDOCODE
# 1. Read only fields from the approved registry record.
# 2. Reconstruct the exact retrieval-text format from Notebook 06.
# 3. Preserve optional measurements only when they are recorded.
# 4. Return the expected text without changing evidence.

def build_expected_retrieval_text(row: dict) -> str:
    """Reconstruct Notebook 06 retrieval text from registry fields."""

    parts = [
        f"Catalyst system: {row['catalyst_system']}",
        f"Observation: {row['target_or_observation']}",
        f"Reviewed claim: {row['claim_paraphrase']}",
    ]

    if row["fe_product"].strip():
        parts.append(
            f"Faradaic efficiency product: {row['fe_product']}"
        )

    if row["faradaic_efficiency_percent"].strip():
        parts.append(
            "Faradaic efficiency percent: "
            f"{row['faradaic_efficiency_percent']}%"
        )

    if row["conditions"].strip():
        parts.append(
            f"Reported conditions: {row['conditions']}"
        )

    parts.append(
        f"Source location: {row['exact_source_location']}"
    )

    return "\n".join(parts)



class EvidenceIntegrityError(ValueError):
    """Raised when evidence integrity checks fail."""


def load_verified_corpus(
    project_root: str | Path = ".",
) -> list[dict]:
    """
    Load the reviewed RAG snapshot with integrity checks.

    This validates consistency with the local review registry.
    It does not independently authenticate the original papers.
    """

    root = Path(project_root)

    registry_path = (
        root
        / "data/references/02_human_reviewed_claims.csv"
    )

    corpus_path = (
        root
        / "data/processed/06_rag_prototype/"
        "06_retrieval_corpus.jsonl"
    )

    manifest_path = (
        root
        / "data/processed/06_rag_prototype/"
        "06_retrieval_manifest.json"
    )

    # Read the registry and check its schema.
    with registry_path.open(
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        required_columns = {
            "evidence_id",
            "source_checked_by_human",
            *FIELD_MAPPING.keys(),
        }

        if not required_columns.issubset(
            set(reader.fieldnames or [])
        ):
            raise EvidenceIntegrityError(
                "Required evidence registry columns are missing"
            )

        registry = list(reader)

    # Read the RAG corpus without executing any content.
    with corpus_path.open(encoding="utf-8") as file:
        corpus = [
            json.loads(line)
            for line in file
            if line.strip()
        ]

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    # Validate exported bytes against the recorded digest.
    actual_sha = hashlib.sha256(
        corpus_path.read_bytes()
    ).hexdigest()

    if actual_sha != manifest.get("corpus_sha256"):
        raise EvidenceIntegrityError(
            "RAG corpus SHA-256 does not match its manifest"
        )

    if not corpus:
        raise EvidenceIntegrityError("RAG corpus is empty")

    if (
        type(manifest.get("records")) is not int
        or manifest["records"] != len(corpus)
    ):
        raise EvidenceIntegrityError(
            "RAG corpus record count does not match manifest"
        )

    if manifest.get("verified_claims_only") is not True:
        raise EvidenceIntegrityError(
            "Manifest does not declare verified-only evidence"
        )

    registry_by_id = {}
    corpus_by_id = {}

    # Duplicate evidence IDs invalidate the registry.
    for record in registry:
        evidence_id = record.get("evidence_id", "").strip()

        if not evidence_id or evidence_id in registry_by_id:
            raise EvidenceIntegrityError(
                "Missing or duplicate registry evidence ID"
            )

        registry_by_id[evidence_id] = record

    # Duplicate evidence IDs invalidate the exported corpus.
    for record in corpus:
        if not isinstance(record, dict):
            raise EvidenceIntegrityError(
                "Invalid RAG corpus record"
            )

        evidence_id = record.get("evidence_id")

        if (
            not isinstance(evidence_id, str)
            or not evidence_id.strip()
            or evidence_id in corpus_by_id
        ):
            raise EvidenceIntegrityError(
                "Missing or duplicate corpus evidence ID"
            )

        corpus_by_id[evidence_id] = record

    # Only independently reviewed registry records are eligible.
    approved_ids = {
        evidence_id
        for evidence_id, record in registry_by_id.items()
        if record["review_status"].strip() == "human_verified"
        and record["source_checked_by_human"]
        .strip().lower() == "true"
    }

    if not approved_ids:
        raise EvidenceIntegrityError(
            "No human-approved evidence records found"
        )

    if set(corpus_by_id) != approved_ids:
        raise EvidenceIntegrityError(
            "Corpus IDs do not match approved registry IDs"
        )

    # Compare the shared scientific fields.
    for evidence_id, exported in corpus_by_id.items():
        source = registry_by_id[evidence_id]

        if (
            not isinstance(exported.get("text"), str)
            or not exported["text"].strip()
        ):
            raise EvidenceIntegrityError(
                f"Missing retrieval text: {evidence_id}"
            )

        for registry_field, corpus_field in FIELD_MAPPING.items():
            source_value = source[registry_field].strip()
            exported_value = exported.get(corpus_field)

            if not isinstance(exported_value, str):
                raise EvidenceIntegrityError(
                    f"Invalid {corpus_field}: {evidence_id}"
                )

            if source_value != exported_value.strip():
                raise EvidenceIntegrityError(
                    f"Evidence mismatch: {evidence_id}, "
                    f"field {registry_field}"
                )

        if not all(
            source[field].strip()
            for field in (
                "doi",
                "source_extent",
                "exact_source_location",
            )
        ):
            raise EvidenceIntegrityError(
                f"Incomplete provenance: {evidence_id}"
            )

        expected_text = build_expected_retrieval_text(source)

        if exported["text"] != expected_text:
            raise EvidenceIntegrityError(
                f"Retrieval text mismatch: {evidence_id}"
            )

    publication_count = len({
        record["paper_id"]
        for record in corpus
    })

    if (
        type(manifest.get("source_publications")) is not int
        or manifest["source_publications"] != publication_count
    ):
        raise EvidenceIntegrityError(
            "Source-publication count mismatch"
        )

    return corpus
