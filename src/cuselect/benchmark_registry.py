"""Read-only registry of provisional experimental benchmarks."""

import json
from pathlib import Path


REQUIRED_FIELDS = {
    "benchmark_id",
    "doi",
    "catalyst",
    "product",
    "faradaic_efficiency_percent",
    "verification_status",
    "scientifically_verified",
    "approved_for_rag",
}


def validate_record(record):
    """Validate structure without asserting scientific accuracy."""

    if not isinstance(record, dict):
        raise ValueError("Benchmark must be a dictionary.")

    missing = REQUIRED_FIELDS - record.keys()

    if missing:
        raise ValueError(
            "Missing benchmark fields: " + ", ".join(sorted(missing))
        )

    if not str(record["benchmark_id"]).strip():
        raise ValueError("Benchmark ID is empty.")

    if not str(record["doi"]).strip():
        raise ValueError("DOI is empty.")

    if not str(record["catalyst"]).strip():
        raise ValueError("Catalyst is empty.")

    if not str(record["product"]).strip():
        raise ValueError("Product is empty.")

    fe = record["faradaic_efficiency_percent"]

    if isinstance(fe, bool) or not isinstance(fe, (int, float)):
        raise ValueError("FE must be numeric.")

    import math
    if not math.isfinite(fe) or not 0 <= fe <= 100:
        raise ValueError("FE must be finite and between 0 and 100.")

    # This registry is only for provisional candidates.
    if record["scientifically_verified"] is not False:
        raise ValueError(
            "Scientifically verified records require a separate "
            "approved evidence workflow."
        )

    if record["approved_for_rag"] is not False:
        raise ValueError(
            "Provisional benchmark cannot be approved for RAG."
        )

    return True


def load_benchmarks(project_root="."):
    """Read provisional benchmark JSON files without modifying them."""

    directory = (
        Path(project_root)
        / "data/processed/benchmark_candidates"
    )

    if not directory.exists():
        return {
            "records": [],
            "errors": [],
            "count": 0,
            "warning": "Benchmark candidate directory not found.",
        }

    records = []
    errors = []
    seen_ids = set()

    for path in sorted(directory.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            validate_record(record)

            benchmark_id = record["benchmark_id"]

            if benchmark_id in seen_ids:
                raise ValueError("Duplicate benchmark ID.")

            seen_ids.add(benchmark_id)
            records.append(record)

        except (OSError, ValueError, TypeError) as exc:
            errors.append({
                "file": path.name,
                "error": str(exc),
            })

    return {
        "records": records,
        "errors": errors,
        "count": len(records),
        "evidence_status": "provisional",
    }


def get_benchmarks_for_product(product, project_root="."):
    result = load_benchmarks(project_root)

    selected = [
        record for record in result["records"]
        if str(record["product"]).lower() == product.lower()
    ]

    return {
        **result,
        "records": selected,
        "count": len(selected),
        "filter_product": product,
    }
