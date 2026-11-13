"""Conservative comparison of provisional experimental benchmarks."""

from cuselect.benchmark_registry import get_benchmarks_for_product


CONDITION_FIELDS = [
    "cell_configuration",
    "electrolyte",
    "current_density_type",
    "potential_V_vs_RHE",
]


def compare_benchmarks(product, *, project_root="."):
    result = get_benchmarks_for_product(
        product,
        project_root=project_root,
    )

    records = result["records"]

    comparisons = []

    for record in records:
        missing = [
            field for field in CONDITION_FIELDS
            if (
                record.get(field) is None
                or record.get(field) == ""
                or str(record.get(field)).lower() == "unresolved"
            )
        ]

        comparisons.append({
            "benchmark_id": record["benchmark_id"],
            "catalyst": record["catalyst"],
            "doi": record["doi"],
            "product": record["product"],
            "faradaic_efficiency_percent": (
                record["faradaic_efficiency_percent"]
            ),
            "cell_configuration": record.get("cell_configuration"),
            "electrolyte": record.get("electrolyte"),
            "reported_current_density_mA_cm2": record.get(
                "reported_current_density_mA_cm2"
            ),
            "current_density_type": record.get(
                "current_density_type"
            ),
            "potential_V_vs_RHE": record.get(
                "potential_V_vs_RHE"
            ),
            "missing_conditions": missing,
            "scientifically_verified": False,
            "approved_for_rag": False,
        })

    comparisons.sort(
        key=lambda r: r["faradaic_efficiency_percent"],
        reverse=True,
    )

    # Sorting is only for display, not catalyst ranking.
    return {
        "product": product,
        "records": comparisons,
        "count": len(comparisons),
        "comparison_status": "descriptive_only",
        "ranking_validated": False,
        "scientific_warning": (
            "Reported measurements are displayed for inspection, "
            "not ranked as equivalent catalyst performance. "
            "Different operating conditions and incomplete "
            "measurement definitions prevent direct comparison."
        ),
        "registry_errors": result["errors"],
    }
