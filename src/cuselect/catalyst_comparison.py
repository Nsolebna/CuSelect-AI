
"""Read-only catalyst comparison with evidence safeguards."""

import json
from pathlib import Path


def compare_existing_candidates(project_root):
    root = Path(project_root).resolve()

    approved_path = root / "data/approved_evidence.json"
    benchmark_path = (
        root / "data/processed/benchmark_candidates"
        / "CUSELECT-BENCH-001.json"
    )

    approved = json.loads(
        approved_path.read_text(encoding="utf-8")
    )
    benchmark = json.loads(
        benchmark_path.read_text(encoding="utf-8")
    )

    if not isinstance(approved, list):
        raise ValueError("Expected approved evidence list.")

    records = []

    for item in approved:
        if (
            item.get("product") != "ethylene"
            or item.get("measurement_type")
            != "faradaic_efficiency"
        ):
            continue

        issues = []

        if item.get("qualifier"):
            issues.append(
                "FE has qualifier: "
                + str(item["qualifier"])
            )

        if item.get("conditions_verified") is not True:
            issues.append(
                "Operating conditions not fully verified"
            )

        if (
            item.get("review_status") != "approved"
            or item.get("review", {}).get(
                "human_confirmed"
            ) is not True
        ):
            issues.append(
                "FE human approval not confirmed"
            )

        records.append({
            "record_id": item.get("measurement_id"),
            "doi": item.get("doi"),
            "catalyst": item.get("title"),
            "product": "ethylene",
            "fe_percent": item.get("value"),
            "fe_qualifier": item.get("qualifier"),
            "reported_current_density": (
                item.get("current_density_ma_cm2")
            ),
            "current_density_type": (
                item.get("current_density_type")
            ),
            "cell_configuration": (
                item.get("cell_configuration")
            ),
            "evidence_status": item.get("review_status"),
            "conditions_verified": (
                item.get("conditions_verified") is True
            ),
            "issues": issues,
        })

    excerpt = str(
        benchmark.get("source_excerpt") or ""
    ).lower()

    fe = benchmark.get("faradaic_efficiency_percent")

    product_supported_by_excerpt = (
        "ethylene" in excerpt or "c2h4" in excerpt
    )

    value_supported_by_excerpt = (
        fe is not None and str(fe) in excerpt
    )

    benchmark_issues = [
        "Provisional measurement; human approval pending",
        "Stored excerpt has not been human-verified as "
        "supporting the reported ethylene FE and its "
        "experimental conditions",
    ]

    if not (
        product_supported_by_excerpt
        and value_supported_by_excerpt
    ):
        benchmark_issues.append(
            "Stored excerpt does not independently support "
            "both the reported ethylene product and FE value"
        )

    if benchmark.get("current_density_type") in (
        None, "", "unresolved"
    ):
        benchmark_issues.append(
            "Current-density definition unresolved"
        )

    if not benchmark.get("electrolyte"):
        benchmark_issues.append(
            "Electrolyte not confirmed"
        )

    records.append({
        "record_id": benchmark.get("benchmark_id"),
        "doi": benchmark.get("doi"),
        "catalyst": benchmark.get("catalyst"),
        "product": benchmark.get("product"),
        "fe_percent": fe,
        "fe_qualifier": None,
        "reported_current_density": (
            benchmark.get(
                "reported_current_density_mA_cm2"
            )
        ),
        "current_density_type": (
            benchmark.get("current_density_type")
        ),
        "cell_configuration": (
            benchmark.get("cell_configuration")
        ),
        "evidence_status": "provisional",
        "conditions_verified": False,
        "issues": benchmark_issues,
    })

    return {
        "records": records,
        "ranking_allowed": False,
        "comparison_status": (
            "descriptive_only_conditions_not_comparable"
        ),
        "conclusion": (
            "The available measurements can be described, "
            "but they do not establish a defensible "
            "performance ranking."
        ),
        "files_modified": False,
    }
