
# CuSelect-AI — Human Evidence Review
#
# PSEUDOCODE
# 1. Load the scientific review queue.
# 2. Select the Cu-Ag ethylene and ethanol measurements.
# 3. Request human confirmation against the source.
# 4. Record source references and supporting text.
# 5. Back up the queue before changing it.
# 6. Export approved measurements.

import json
import shutil
from pathlib import Path
from datetime import date, datetime

from cuselect.evidence_validation import (
    record_review,
    get_approved_evidence,
    save_json,
)

queue_path = Path("data/evidence_review_queue.json")
export_path = Path("data/approved_evidence.json")

doi = "10.1021/acsami.8b20545"

locations = {
    "ethylene": "supporting_information:Table S1, page S-27; Figure S18, page S-23",
    
}

with queue_path.open(encoding="utf-8") as file:
    queue = json.load(file)

reviewer = input("Reviewer name: ").strip()

if not reviewer:
    raise SystemExit("Reviewer name is required")

updated = 0

for index, record in enumerate(queue):
    measurement = record["measurement"]

    if measurement["doi"].lower() != doi:
        continue

    product = measurement["product"]

    if product not in locations:
        continue

    if record["review_status"] != "pending_human_review":
        print(f"Already reviewed: {product}")
        continue

    print("\n" + "=" * 50)
    print("Product:", product)
    print("FE:", measurement["value"], "%")
    print("Source:", locations[product])
    print("Extracted text:", measurement["exact_source_text"])

    confirmed = input(
        "Confirmed against original figure? (yes/no): "
    ).strip().lower()

    if confirmed != "yes":
        print("Left pending.")
        continue

    excerpt = input(
        "Enter exact supporting text from publication: "
    ).strip()

    if not excerpt:
        print("No excerpt entered. Left pending.")
        continue

    queue[index] = record_review(
        review_record=record,
        decision="approved",
        reviewer=reviewer,
        review_date=date.today().isoformat(),
        source_location=locations[product],
        supporting_excerpt=excerpt,
        justification=(
            "Product-specific FE manually checked "
            "against the original publication. "
            "Operating conditions require separate review."
        ),
        human_confirmed=True,
    )

    updated += 1

if updated:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = queue_path.with_name(
        f"evidence_review_queue_backup_{timestamp}.json"
    )

    shutil.copy2(queue_path, backup)
    save_json(queue_path, queue)

    print("\nBackup created:", backup)

approved = get_approved_evidence(queue)
save_json(export_path, approved)

print("\nCUSELECT-AI — REVIEW SUMMARY")
print("=" * 50)
print("Newly approved:", updated)
print("Total approved:", len(approved))
print(
    "Remaining pending:",
    sum(
        record["review_status"] == "pending_human_review"
        for record in queue
    ),
)
print("Approved evidence file:", export_path)
