"""CuSelect-AI — provenance-gated experiment selection."""

# PSEUDOCODE
# 1. Load the saved scientific gate decisions.
# 2. Require an evidence registry for non-pending decisions.
# 3. Verify every evidence reference and source fingerprint.
# 4. Reject synthetic fixtures for operational qualification.
# 5. Invoke the existing adaptive decision engine.
# 6. Keep all decisions advisory and subject to human review.

import argparse
import json
from pathlib import Path

from adaptive_experiment_selector import (
    DEFAULT_GATES,
    select_next,
)

from verify_experimental_gate_evidence import (
    verify_gate_reference,
)

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_REGISTRY = (
    ROOT / "data/experimental_evidence/registry.json"
)

DEFAULT_EVIDENCE_ROOT = (
    ROOT / "data/experimental_evidence"
)


def select_verified(
    gates_path=None,
    registry_path=None,
    evidence_root=None,
):
    gates = Path(
        gates_path if gates_path is not None
        else DEFAULT_GATES
    )

    registry_path = Path(
        registry_path if registry_path is not None
        else DEFAULT_REGISTRY
    )

    evidence_root = Path(
        evidence_root if evidence_root is not None
        else DEFAULT_EVIDENCE_ROOT
    )

    # No real decisions exist yet: retain pending defaults.
    if not gates.is_file():
        if gates.resolve() != DEFAULT_GATES.resolve():
            raise FileNotFoundError(gates)

        result = select_next()
        result["evidence_verification"] = (
            "no_qualification_claims"
        )
        return result

    gate_record = json.loads(
        gates.read_text(encoding="utf-8")
    )

    if gate_record.get("schema_version") != "1.0":
        raise ValueError("Unsupported gate schema.")

    reviews = gate_record.get("reviews")

    if not isinstance(reviews, list):
        raise ValueError("Invalid gate reviews.")

    active = [
        review for review in reviews
        if review.get("status") != "pending"
    ]

    if active:
        if not registry_path.is_file():
            raise ValueError(
                "Evidence registry required for "
                "non-pending scientific gate decisions."
            )

        registry = json.loads(
            registry_path.read_text(encoding="utf-8")
        )

        for review in active:
            verified = verify_gate_reference(
                review,
                registry,
                evidence_root,
            )

            source_record = next(
                item for item in registry["records"]
                if item["record_id"] == verified["record_id"]
            )

            # A declared synthetic record cannot be
            # accepted as operational qualification evidence.
            if source_record.get("synthetic_fixture") is not False:
                raise ValueError(
                    "Evidence record not admitted as "
                    "a non-synthetic operational source."
                )

            source = (
                evidence_root
                / source_record["source_path"]
            )

            # JSON fixtures declaring themselves synthetic
            # must never unlock operational research gates.
            if source.suffix.lower() == ".json":
                content = json.loads(
                    source.read_text(encoding="utf-8")
                )

                if not isinstance(content, dict):
                    raise ValueError(
                        "Expected structured JSON evidence."
                    )

                if content.get("synthetic_fixture") is not False:
                    raise ValueError(
                        "Source is not identified as "
                        "non-synthetic experimental evidence."
                    )

    result = select_next(gates)

    result["evidence_verification"] = (
        "file_provenance_checked"
        if active
        else "no_qualification_claims"
    )

    result["scientific_validation"] = (
        "pending_independent_review"
    )

    result["limitations"].append(
        "Evidence provenance and declared source type "
        "do not establish genuine measurements, "
        "reviewer identity or scientific validity."
    )

    return result


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--gates", type=Path)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--evidence-root", type=Path)

    args = parser.parse_args()

    result = select_verified(
        args.gates,
        args.registry,
        args.evidence_root,
    )

    print("\nCUSELECT-AI — VERIFIED EXPERIMENT SELECTION")
    print("=" * 60)

    print(
        "Evidence verification:",
        result["evidence_verification"],
    )

    print(
        "Recommended experiment:",
        result["recommendation"]["experiment"],
    )

    print(
        "Recommended action:",
        result["recommendation"]["action"],
    )

    print("Independent scientific review: Required")
    print("API requests: 0")
    print("Files modified: 0")


if __name__ == "__main__":
    main()
