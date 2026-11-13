"""Evidence-constrained discovery selection for CuSelect-AI."""

from cuselect.agents.pipeline import run_pipeline


PRODUCT_LABELS = {
    "Ethylene (C₂H₄)": "ethylene",
    "Ethanol (C₂H₅OH)": "ethanol",
    "Carbon monoxide (CO)": "co",
    "Formate (HCOO⁻)": "formate",
    "Other / not specified": None,
}


def discover_for_request(objective, target_product, discovery_focus):
    """Select relevant baseline hypotheses without inventing evidence."""

    objective = str(objective).strip()
    if not objective:
        raise ValueError("Research objective cannot be empty.")

    product = PRODUCT_LABELS.get(target_product)
    if product is None:
        return {
            "status": "unsupported",
            "message": "Select a specific supported target product.",
            "candidates": [],
        }

    if discovery_focus != "Cu-based catalysts":
        return {
            "status": "unsupported",
            "message": (
                "This catalyst focus is not yet supported by "
                "the reviewed baseline design templates."
            ),
            "candidates": [],
        }

    outputs = run_pipeline(save=False)

    evidence = {
        record["measurement_id"]: record
        for record in outputs["literature"]["evidence"]
    }

    designs = {
        item["id"]: item
        for item in outputs["design"]["candidates"]
    }

    selected = []

    for result in outputs["coordination"]["candidates"]:
        candidate_id = result["candidate_id"]
        design = designs[candidate_id]

        matching = [
            evidence[mid]
            for mid in design["evidence_measurement_ids"]
            if mid in evidence
            and evidence[mid]["product"] == product
        ]

        if not matching:
            continue

        selected.append({
            "candidate_id": candidate_id,
            "name": design["name"],
            "hypothesis": design["hypothesis"],
            "key_uncertainty": design["key_uncertainty"],
            "proposed_experiment": design["proposed_experiment"],
            "supporting_doi": design["source_doi"],
            "matching_evidence_ids": [
                record["measurement_id"] for record in matching
            ],
            "matching_observations": [
                {
                    "product": record["product"],
                    "reported_fe_percent": record["fe_percent"],
                    "conditions_complete": record["conditions_complete"],
                }
                for record in matching
            ],
            "status": "untested_design_hypothesis",
            "predicted_fe_percent": None,
        })

    if not selected:
        return {
            "status": "insufficient_evidence",
            "message": (
                "No existing design template has approved "
                "product-specific evidence for this request."
            ),
            "candidates": [],
        }

    return {
        "status": "baseline_candidates_available",
        "objective": objective,
        "target_product": product,
        "discovery_focus": discovery_focus,
        "generation_method": "approved_evidence_template_selection",
        "message": (
            "These are predefined, evidence-linked hypotheses, "
            "not newly generated or validated catalyst designs. "
            "The free-text objective is recorded but is not yet "
            "semantically interpreted."
        ),
        "candidates": selected,
    }
