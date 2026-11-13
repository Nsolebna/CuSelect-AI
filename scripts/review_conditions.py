# CuSelect-AI — Condition Validation
# PSEUDOCODE:
# 1. Load the approved scientific evidence.
# 2. Find the Ag/Cu ethylene measurement.
# 3. Ask the reviewer to verify each condition.
# 4. Save condition decisions without changing approved evidence.

import json
from pathlib import Path
from datetime import date

source = Path("data/approved_evidence.json")
destination = Path("data/conditions_review.json")

with source.open(encoding="utf-8") as f:
    records = json.load(f)

matches = [
    r for r in records
    if r["doi"] == "10.1021/acsami.8b20545"
    and r["product"] == "ethylene"
]

if len(matches) != 1:
    raise SystemExit("Expected exactly one matching record.")

record = matches[0]

conditions = {
    "potential_v": (-1.1, "Table S1, page S-27"),
    "current_density_ma_cm2": (-5.5, "Table S1, page S-27"),
    "electrolyte": ("CO2-saturated 0.1 M KHCO3", "Page S-3"),
    "cell_configuration": ("H-type cell", "Page S-3"),
    "ag_content_percent": (6.0, "Figure S18, page S-23"),
}

reviewer = input("Reviewer name: ").strip()

if not reviewer:
    raise SystemExit("Reviewer name required.")

if destination.exists():
    with destination.open(encoding="utf-8") as f:
        reviews = json.load(f)
else:
    reviews = {}

measurement_id = record["measurement_id"]
existing = reviews.get(measurement_id, {})

field_reviews = existing.get("field_reviews", {})

for field, (value, source_location) in conditions.items():
    print("\nField:", field)
    print("Value:", value)
    print("Source:", source_location)

    answer = input("Verified? (yes/no/skip): ").strip().lower()

    if answer not in {"yes", "no"}:
        continue

    field_reviews[field] = {
        "value": value,
        "source": source_location,
        "status": (
            "human_verified" if answer == "yes"
            else "needs_correction"
        ),
        "reviewer": reviewer,
        "review_date": date.today().isoformat(),
    }

reviews[measurement_id] = {
    "measurement_id": measurement_id,
    "doi": record["doi"],
    "product": record["product"],
    "field_reviews": field_reviews,
}

# Save separately from the approved evidence file.
with destination.open("w", encoding="utf-8") as f:
    json.dump(reviews, f, indent=2, ensure_ascii=False)

print("\nCUSELECT-AI — CONDITION REVIEW SUMMARY")
print("Verified:", sum(
    x["status"] == "human_verified"
    for x in field_reviews.values()
))
print("Needs correction:", sum(
    x["status"] == "needs_correction"
    for x in field_reviews.values()
))
print("Saved:", destination)
