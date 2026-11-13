"""CuSelect-AI: Literature evidence packaging agent."""

# PSEUDOCODE
# 1. Read human-approved experimental evidence.
# 2. Read separately reviewed experimental conditions.
# 3. Validate IDs, FE ranges, and human-review decisions.
# 4. Join conditions using measurement_id.
# 5. Preserve uncertainty, qualifiers, and source locations.
# 6. Export an evidence package for downstream agents.

import json
import math
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "data" / "approved_evidence.json"
CONDITIONS = ROOT / "data" / "conditions_review.json"
OUTPUT = ROOT / "data" / "agent_runs" / "literature_evidence_v1.json"


def read_json(path, default=None):
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8") as file:
        return json.load(file)


def atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary = tempfile.mkstemp(
        dir=path.parent,
        prefix=".literature_",
        suffix=".json",
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)
            file.write("\n")

        os.replace(temporary, path)

    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def build_evidence_package(evidence, condition_reviews):
    if not isinstance(evidence, list):
        raise ValueError("Approved evidence must be a list.")

    if not isinstance(condition_reviews, dict):
        raise ValueError("Condition reviews must be a dictionary.")

    seen_ids = set()
    items = []

    for record in evidence:
        if not isinstance(record, dict):
            raise ValueError("Evidence record must be an object.")

        measurement_id = record["measurement_id"]
        doi = record["doi"]
        review = record.get("review") or {}
        value = record["value"]

        if measurement_id in seen_ids:
            raise ValueError(f"Duplicate ID: {measurement_id}")

        seen_ids.add(measurement_id)

        if (
            record.get("review_status") != "approved"
            or review.get("human_confirmed") is not True
            or review.get("decision") != "approved"
        ):
            raise ValueError(f"Unapproved record: {measurement_id}")

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 100
            or record.get("unit") != "%"
        ):
            raise ValueError(f"Invalid FE: {measurement_id}")

        condition_entry = condition_reviews.get(
            measurement_id, {}
        )

        if not isinstance(condition_entry, dict):
            raise ValueError("Invalid condition-review entry.")

        if condition_entry and (
            condition_entry.get("measurement_id") != measurement_id
            or condition_entry.get("doi") != doi
            or condition_entry.get("product") != record["product"]
        ):
            raise ValueError(
                f"Condition-review identity mismatch: {measurement_id}"
            )

        field_reviews = condition_entry.get(
            "field_reviews", {}
        )

        if not isinstance(field_reviews, dict):
            raise ValueError("Invalid field_reviews structure.")

        verified_conditions = {}
        unresolved_conditions = {}

        for field, info in field_reviews.items():
            if not isinstance(info, dict):
                raise ValueError(f"Invalid field: {field}")

            if info.get("status") == "human_verified":
                verified_conditions[field] = {
                    "value": info.get("value"),
                    "unit": info.get("unit"),
                    "source": info.get("source"),
                    "reviewer": info.get("reviewer"),
                    "review_date": info.get("review_date"),
                }
            else:
                unresolved_conditions[field] = {
                    "value": info.get("value"),
                    "status": info.get("status", "unknown"),
                }

        items.append({
            "measurement_id": measurement_id,
            "doi": doi,
            "title": record.get("title"),
            "product": record["product"],
            "fe_percent": value,
            "fe_qualifier": record.get("qualifier"),
            "fe_review": {
                "status": "approved",
                "source_location": review.get("source_location"),
                "supporting_excerpt": review.get(
                    "supporting_excerpt"
                ),
                "reviewer": review.get("reviewer"),
            },
            "verified_conditions": verified_conditions,
            "unresolved_conditions": unresolved_conditions,
            "conditions_complete": (
                record.get("conditions_verified") is True
            ),
            "raw_conditions_are_provisional": (
                record.get("conditions_verified") is not True
            ),
        })

    return {
        "schema_version": "1.0",
        "agent": "literature_agent",
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "objective": (
            "Provide reviewed literature evidence for "
            "Cu-based CO2-to-ethylene catalyst design."
        ),
        "summary": {
            "measurements": len(items),
            "publications": len({
                item["doi"] for item in items
            }),
            "products": dict(Counter(
                item["product"] for item in items
            )),
            "verified_condition_fields": sum(
                len(item["verified_conditions"])
                for item in items
            ),
        },
        "scientific_constraints": [
            "Do not interpret C2-product FE as ethylene FE.",
            "Do not treat provisional conditions as verified.",
            "Do not rank intrinsic catalyst performance using FE alone.",
            "Do not invent experimental measurements.",
            "Distinguish observed performance from design hypotheses.",
        ],
        "evidence": items,
    }


def main():
    evidence = read_json(EVIDENCE)
    condition_reviews = read_json(CONDITIONS, default={})

    package = build_evidence_package(
        evidence,
        condition_reviews,
    )

    atomic_write(OUTPUT, package)

    print("\nCUSELECT-AI — LITERATURE AGENT v1")
    print("=" * 55)

    for key, value in package["summary"].items():
        print(f"{key}: {value}")

    print("\nSaved:", OUTPUT)
    print("Source evidence files: unchanged")


if __name__ == "__main__":
    main()
