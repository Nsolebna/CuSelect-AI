
# CuSelect-AI — Scientific Evidence Validation
#
# PSEUDOCODE
# 1. Receive extracted measurement candidates.
# 2. Check DOI, product, FE, units, and source provenance.
# 3. Identify missing or inconsistent measurement context.
# 4. Create human-review records.
# 5. Require original-publication evidence for approval.
# 6. Require an explicit human review decision.
# 7. Record reviewer, date, source location and justification.
# 8. Never automatically approve extracted claims.
# 9. Keep the original extracted measurements unchanged.

import copy
import json
import math
import os

from datetime import date
from pathlib import Path


ALLOWED_PRODUCTS = {
    "ethylene",
    "ethanol",
    "c2_product_class",
}

ALLOWED_DECISIONS = {
    "approved",
    "rejected",
    "needs_revision",
}


def validate_measurement(measurement):
    """
    Perform structural and consistency checks.

    This function does not verify experimental truth.
    """

    # PSEUDOCODE
    # 1. Validate the measurement's required fields.
    # 2. Check FE bounds and percentage units.
    # 3. Identify missing measurement provenance.
    # 4. Check the consistency of operating conditions.
    # 5. Return errors and review warnings.

    if not isinstance(measurement, dict):
        raise ValueError("Measurement must be a dictionary")

    errors = []
    warnings = []

    identifier = measurement.get("measurement_id")
    doi = measurement.get("doi")
    product = measurement.get("product")
    value = measurement.get("value")
    unit = measurement.get("unit")

    if not isinstance(identifier, str) or not identifier.strip():
        errors.append("missing_measurement_id")

    if (
        not isinstance(doi, str)
        or not doi.strip().lower().startswith("10.")
    ):
        errors.append("invalid_doi")

    if product not in ALLOWED_PRODUCTS:
        errors.append("unsupported_product")

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 100
    ):
        errors.append("invalid_fe_value")

    if unit != "%":
        errors.append("invalid_fe_unit")

    if measurement.get("measurement_type") != "faradaic_efficiency":
        errors.append("invalid_measurement_type")

    if not str(measurement.get("exact_source_text") or "").strip():
        errors.append("missing_source_text")

    if not str(measurement.get("source_provider") or "").strip():
        errors.append("missing_source_provider")

    if not str(measurement.get("source_type") or "").strip():
        errors.append("missing_source_type")

    # Contextual consistency checks.

    potential = measurement.get("potential_v")
    reference = measurement.get("reference_electrode")

    if potential is not None:
        if (
            isinstance(potential, bool)
            or not isinstance(potential, (int, float))
            or not math.isfinite(potential)
        ):
            errors.append("invalid_potential")
        if not reference:
            warnings.append("potential_reference_missing")

    current = measurement.get("current_density_ma_cm2")

    if current is not None:
        if (
            isinstance(current, bool)
            or not isinstance(current, (int, float))
            or not math.isfinite(current)
        ):
            errors.append("invalid_current_density")
        if measurement.get("current_density_type") not in {
            "total", "partial"
        }:
            warnings.append("current_density_type_unclear")

    ag_content = measurement.get("ag_content_percent")

    if ag_content is not None:
        if (
            isinstance(ag_content, bool)
            or not isinstance(ag_content, (int, float))
            or not math.isfinite(ag_content)
            or not 0 <= ag_content <= 100
        ):
            errors.append("invalid_ag_composition")

        if measurement.get("ag_percentage_basis") in {
            None, "unknown"
        }:
            warnings.append("ag_composition_basis_unknown")

    if potential is None:
        warnings.append("potential_not_reported_in_candidate")

    if current is None:
        warnings.append("current_density_not_reported_in_candidate")

    if measurement.get("conditions_verified") is not True:
        warnings.append("operating_conditions_unverified")

    return {
        "passed_structural_checks": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "scientifically_verified": False,
    }


def create_review_queue(measurements):
    """Create review records without approving evidence."""

    if not isinstance(measurements, list):
        raise ValueError("Measurements must be a list")

    queue = []
    seen_ids = set()

    for measurement in measurements:
        validation = validate_measurement(measurement)
        identifier = measurement.get("measurement_id")

        if identifier in seen_ids:
            raise ValueError(
                f"Duplicate measurement ID: {identifier}"
            )

        seen_ids.add(identifier)

        queue.append({
            "measurement_id": identifier,
            "measurement": copy.deepcopy(measurement),
            "automatic_validation": validation,
            "review_status": "pending_human_review",
            "review": None,
        })

    return queue


def record_review(
    review_record,
    decision,
    reviewer,
    review_date,
    source_location,
    supporting_excerpt,
    justification,
    human_confirmed=False,
):
    """
    Record an explicit human scientific review decision.

    Approval requires comparison with the original
    publication, not only an abstract or API metadata.

    Returns a new record without modifying the original.
    """

    if not isinstance(review_record, dict):
        raise ValueError("Invalid review record")

    if review_record.get("review_status") != "pending_human_review":
        raise ValueError("Record is not awaiting review")

    if decision not in ALLOWED_DECISIONS:
        raise ValueError("Invalid review decision")

    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("Reviewer identity is required")

    try:
        parsed_date = date.fromisoformat(review_date)
    except (TypeError, ValueError):
        raise ValueError(
            "review_date must use YYYY-MM-DD"
        ) from None

    if parsed_date > date.today():
        raise ValueError("Review date cannot be in the future")

    if not isinstance(justification, str) or not justification.strip():
        raise ValueError("Review justification is required")

    validation = review_record.get("automatic_validation", {})
    measurement = review_record.get("measurement", {})

    if decision == "approved":
        # Explicit human confirmation is mandatory.
        if human_confirmed is not True:
            raise ValueError(
                "Human verification is required for approval"
            )

        # Revalidate rather than trusting a stored flag.
        current_validation = validate_measurement(measurement)

        if (
            not validation.get("passed_structural_checks")
            or not current_validation["passed_structural_checks"]
        ):
            raise ValueError(
                "Structural validation failed"
            )

        if (
            not isinstance(source_location, str)
            or not source_location.strip()
        ):
            raise ValueError(
                "Original publication source location required"
            )

        if (
            not isinstance(supporting_excerpt, str)
            or not supporting_excerpt.strip()
        ):
            raise ValueError(
                "Supporting source excerpt required"
            )

        # A review must be based on a primary publication
        # source such as a figure, table, or full-text page.
        # This field is a human declaration, not a
        # machine-verifiable guarantee.
        if not source_location.startswith(
            ("full_text:", "supporting_information:")
        ):
            raise ValueError(
                "Approval requires a primary-source location"
            )

    updated = copy.deepcopy(review_record)

    updated["review_status"] = decision
    updated["review"] = {
        "decision": decision,
        "reviewer": reviewer.strip(),
        "review_date": review_date,
        "source_location": source_location,
        "supporting_excerpt": supporting_excerpt,
        "justification": justification.strip(),
        "human_confirmed": human_confirmed is True,
    }

    return updated


def get_approved_evidence(review_queue):
    """
    Return only structurally valid, explicitly approved
    evidence records with review metadata.
    """

    approved = []

    for record in review_queue:
        if record.get("review_status") != "approved":
            continue

        review = record.get("review") or {}

        if (
            review.get("decision") != "approved"
            or review.get("human_confirmed") is not True
            or not str(review.get("reviewer") or "").strip()
            or not str(review.get("source_location") or "").startswith(
                ("full_text:", "supporting_information:")
            )
            or not str(review.get("supporting_excerpt") or "").strip()
        ):
            continue

        measurement = record.get("measurement", {})

        if not validate_measurement(measurement)[
            "passed_structural_checks"
        ]:
            continue

        approved.append({
            **copy.deepcopy(measurement),
            "review_status": "approved",
            "review": copy.deepcopy(review),
        })

    return approved


def save_json(path, data):
    """Save review data using atomic replacement."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_name(path.name + ".tmp")

    try:
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary, path)

    finally:
        temporary.unlink(missing_ok=True)
