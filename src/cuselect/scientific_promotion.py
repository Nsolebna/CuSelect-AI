"""Read-only scientific evidence promotion preflight."""

import csv
import hashlib
import json
from pathlib import Path

from cuselect.evidence import EvidenceClaim, normalize_doi


REQUIRED_CHECKS = (
    "correct_catalyst",
    "correct_product",
    "fe_and_potential_attributed_correctly",
    "experimental_conditions_applicable",
    "figure_supports_claim",
)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def promotion_preflight(root):
    """Evaluate eligibility without modifying trusted data."""

    root = Path(root)
    data = root / "data"

    paths = {
        "claim": data / "reports/pending_scientific_claim.json",
        "dossier": data / "reports/hoh_cuag_evidence_dossier.json",
        "approval": data / "scientific_claim_approvals.json",
        "publication": data / "papers.csv",
        "source": data / "raw/publications/PMC13692753.xml",
    }

    problems = []

    for name, path in paths.items():
        if not path.is_file():
            problems.append(f"missing_{name}")

    if problems:
        return {"eligible": False, "problems": problems}

    try:
        raw_claim = load_json(paths["claim"])
        claim = EvidenceClaim.model_validate(raw_claim)
        dossier = load_json(paths["dossier"])
        approvals = load_json(paths["approval"])

        approval = approvals.get(claim.evidence_id)

        if not isinstance(approval, dict):
            return {
                "eligible": False,
                "claim_id": claim.evidence_id,
                "problems": ["human_approval_missing"],
            }

        # PSEUDOCODE
        # Confirm that claim, source dossier, publication,
        # and reviewer decision refer to the same evidence.
        for record in (dossier, approval):
            if record.get("doi") != claim.doi:
                problems.append("doi_mismatch")
            if record.get("paper_id") != claim.paper_id:
                problems.append("paper_id_mismatch")

        if dossier.get("claim_id") != claim.evidence_id:
            problems.append("dossier_claim_id_mismatch")

        if approval.get("claim_id") != claim.evidence_id:
            problems.append("approval_claim_id_mismatch")

        with paths["publication"].open(
            newline="", encoding="utf-8-sig"
        ) as f:
            rows = list(csv.DictReader(f))

        registered = [
            row for row in rows
            if row.get("paper_id") == claim.paper_id
            and normalize_doi(row.get("doi", "")) == claim.doi
        ]

        if len(registered) != 1:
            problems.append("publication_registration_invalid")

        if dossier.get("review_status") != "awaiting_scientific_review":
            problems.append("unexpected_dossier_status")

        if not dossier.get("performance_sources"):
            problems.append("performance_evidence_missing")

        if not dossier.get("methodology_sources"):
            problems.append("methods_evidence_missing")

        if dossier.get("figure", {}).get("id") != "fig4":
            problems.append("supporting_figure_mismatch")

        # Human approval is mandatory.
        if approval.get("decision") != "approve":
            problems.append("human_approval_not_granted")

        if not approval.get("reviewer"):
            problems.append("reviewer_missing")

        if not approval.get("timestamp"):
            problems.append("review_timestamp_missing")

        if not str(approval.get("reviewer_note", "")).strip():
            problems.append("scientific_justification_missing")

        checks = approval.get("checks", {})

        if not isinstance(checks, dict) or not all(
            checks.get(name) is True for name in REQUIRED_CHECKS
        ):
            problems.append("scientific_checks_incomplete")

        # Detect changes to the material after review.
        hashes = {
            "dossier_sha256": sha256(paths["dossier"]),
            "claim_sha256": sha256(paths["claim"]),
            "source_xml_sha256": sha256(paths["source"]),
        }

        for field, expected in hashes.items():
            if approval.get(field) != expected:
                problems.append(f"{field}_mismatch")

        if approval.get("rag_ingestion_status") != "not_ingested":
            problems.append("unexpected_ingestion_status")

        return {
            "eligible": not problems,
            "claim_id": claim.evidence_id,
            "paper_id": claim.paper_id,
            "reviewer": approval.get("reviewer"),
            "problems": sorted(set(problems)),
            "trusted_registry_modified": False,
            "rag_corpus_modified": False,
        }

    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return {
            "eligible": False,
            "problems": [f"invalid_input: {exc}"],
        }
