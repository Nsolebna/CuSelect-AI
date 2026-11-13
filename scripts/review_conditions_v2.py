
# CuSelect-AI — Reusable Experimental Condition Reviewer v2
#
# PSEUDOCODE:
# 1. Load approved measurements and existing condition reviews.
# 2. Let the scientist choose a measurement.
# 3. Display previously reviewed fields.
# 4. Let the scientist enter a value and primary-source location.
# 5. Require explicit confirmation before verification.
# 6. Save condition reviews without modifying approved FE data.

import json
import os
import tempfile
from datetime import date
from pathlib import Path

EVIDENCE_PATH = Path("data/approved_evidence.json")
REVIEW_PATH = Path("data/conditions_review.json")

FIELD_NAMES = {
    "1": ("potential_v", "V vs RHE"),
    "2": ("current_density_ma_cm2", "mA/cm2"),
    "3": ("current_density_type", ""),
    "4": ("electrolyte", ""),
    "5": ("cell_configuration", ""),
    "6": ("ag_content_percent", "%"),
    "7": ("ag_percentage_basis", ""),
    "8": ("reference_electrode", ""),
    "9": ("catalyst_architecture", ""),
    "10": ("other_condition", ""),
}


def load_json(path, default):
    if not path.exists():
        return default

    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_json_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=".condition_review_",
        suffix=".json",
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        os.replace(temp_path, path)

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def main():
    evidence = load_json(EVIDENCE_PATH, [])
    reviews = load_json(REVIEW_PATH, {})

    if not isinstance(evidence, list) or not isinstance(reviews, dict):
        raise SystemExit("Unexpected evidence or review JSON structure.")

    records = [
        r for r in evidence
        if r.get("review_status") == "approved"
        and (r.get("review") or {}).get("human_confirmed") is True
    ]

    if not records:
        raise SystemExit("No approved measurements found.")

    print("\nCUSELECT-AI — CONDITION REVIEWER v2")
    print("=" * 65)

    for index, record in enumerate(records, 1):
        print(
            f'{index}. {record["product"]} | '
            f'{record["value"]}% | {record["doi"]}'
        )

    choice = input("\nSelect a record number: ").strip()

    if not choice.isdigit() or not 1 <= int(choice) <= len(records):
        raise SystemExit("Invalid record selection.")

    record = records[int(choice) - 1]
    measurement_id = record["measurement_id"]

    reviewer = input("Reviewer name: ").strip()

    if not reviewer:
        raise SystemExit("Reviewer name required.")

    entry = reviews.get(measurement_id, {
        "measurement_id": measurement_id,
        "doi": record["doi"],
        "product": record["product"],
        "field_reviews": {},
    })

    if not isinstance(entry, dict):
        raise SystemExit("Invalid existing review entry.")

    field_reviews = entry.setdefault("field_reviews", {})

    if not isinstance(field_reviews, dict):
        raise SystemExit("Invalid field_reviews structure.")

    while True:
        print("\n" + "=" * 65)
        print("SELECTED MEASUREMENT")
        print("DOI:", record["doi"])
        print("Product:", record["product"])
        print("FE:", record["value"], "%")

        print("\nExisting condition reviews:")

        if not field_reviews:
            print("No fields reviewed yet.")

        for name, info in field_reviews.items():
            print(
                f'{name}: {info.get("value")} '
                f'[{info.get("status")}]'
            )

        print("\nAvailable condition fields:")

        for number, (name, unit) in FIELD_NAMES.items():
            print(f"{number}. {name} {unit}")

        print("0. Finish and save")

        selection = input("\nSelect field: ").strip()

        if selection == "0":
            break

        if selection not in FIELD_NAMES:
            print("Invalid field.")
            continue

        field, unit = FIELD_NAMES[selection]

        # Preserve existing approvals unless explicitly reviewed again.
        if field in field_reviews:
            old = field_reviews[field]
            print("\nExisting review:", old)

            confirm = input(
                "Review this field again? (yes/no): "
            ).strip().lower()

            if confirm != "yes":
                continue

        value_text = input(
            f"Enter reported value ({unit or 'text'}): "
        ).strip()

        if not value_text:
            print("Value is required.")
            continue

        if field in {
            "potential_v",
            "current_density_ma_cm2",
            "ag_content_percent",
        }:
            try:
                value = float(value_text)
            except ValueError:
                print("A numeric value is required.")
                continue
        else:
            value = value_text

        source = input(
            "Exact primary-source location (figure/table/page): "
        ).strip()

        if not source:
            print("Source location required.")
            continue

        print("\nPROPOSED CONDITION REVIEW")
        print("Field:", field)
        print("Value:", value)
        print("Unit:", unit)
        print("Source:", source)

        decision = input(
            "Confirmed against primary source? (yes/no/skip): "
        ).strip().lower()

        if decision == "skip":
            continue

        if decision not in {"yes", "no"}:
            print("Invalid decision; no change made.")
            continue

        note = input("Review note (optional): ").strip()

        status = (
            "human_verified"
            if decision == "yes"
            else "needs_correction"
        )

        field_reviews[field] = {
            "value": value,
            "unit": unit,
            "source": source,
            "status": status,
            "reviewer": reviewer,
            "review_date": date.today().isoformat(),
            "note": note,
        }

        # Save after every completed review to reduce data loss.
        reviews[measurement_id] = entry
        save_json_atomic(REVIEW_PATH, reviews)
        print("Review saved.")

    reviews[measurement_id] = entry
    save_json_atomic(REVIEW_PATH, reviews)

    print("\nCUSELECT-AI — REVIEW SUMMARY")
    print("=" * 65)
    print("DOI:", record["doi"])

    statuses = [
        info.get("status")
        for info in field_reviews.values()
    ]

    print("Verified fields:", statuses.count("human_verified"))
    print("Needs correction:", statuses.count("needs_correction"))
    print("Saved:", REVIEW_PATH)
    print("Original approved evidence: unchanged")


if __name__ == "__main__":
    main()
