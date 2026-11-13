"""CuSelect-AI — scientific benchmark runner, offline v1."""

# PSEUDOCODE
# 1. Read the versioned benchmark dataset.
# 2. Validate the six scenario identifiers.
# 3. Execute B04 using the real evidence validator.
# 4. Execute B05 using the real adaptive gate selector.
# 5. Mark scenarios requiring LLM reasoning as not evaluated.
# 6. Report passed, failed and pending cases separately.
# 7. Never call an API or modify experimental evidence.

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_experimental_gate_evidence import (
    sha256,
    verify_gate_reference,
)
from adaptive_experiment_selector import (
    select_next,
    EXPECTED,
)

DATASET = (
    ROOT / "data/benchmarks/scientific_scenarios_v1.json"
)

REASONING_CASES = {"B01", "B02", "B03", "B06"}


def write_json(path, value):
    path.write_text(
        json.dumps(value, indent=2),
        encoding="utf-8",
    )


def test_invalid_provenance():
    """B04: a mismatched hash must reject the evidence."""

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "synthetic_observations.json"

        write_json(source, {
            "synthetic_fixture": True,
            "observation": "Software test only.",
        })

        record = {
            "record_id": "BENCHMARK-B04",
            "experiment": EXPECTED[0],
            "evidence_type": "experimental",
            "source_path": source.name,
            "source_sha256": sha256(source),
            "observations": ["Synthetic observation"],
            "controls": ["Synthetic control"],
            "limitations": ["Not real experimental data"],
            "reviewer": "BENCHMARK TEST",
            "review_rationale": "Test integrity enforcement",
            "review_decision": "qualified",
            "reviewed_at": "2026-11-09T00:00:00Z",
        }

        registry = {
            "schema_version": "1.0",
            "records": [record],
        }

        review = {
            "experiment": EXPECTED[0],
            "status": "qualified",
            "reviewer": record["reviewer"],
            "evidence_reference": record["record_id"],
            "rationale": record["review_rationale"],
        }

        # Establish that the original synthetic fixture
        # has valid file provenance.
        verify_gate_reference(review, registry, root)

        # Change the source without updating its fingerprint.
        write_json(source, {
            "synthetic_fixture": True,
            "observation": "Deliberately changed evidence.",
        })

        try:
            verify_gate_reference(review, registry, root)
        except ValueError as error:
            if "hash mismatch" in str(error):
                return True, "Modified source rejected"
            return False, f"Unexpected rejection: {error}"

        return False, "Tampered evidence was accepted"


def test_invalid_prerequisites():
    """B05: experiment 2 cannot qualify before experiment 1."""

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "contradictory_gates.json"

        write_json(path, {
            "schema_version": "1.0",
            "reviews": [{
                "experiment": EXPECTED[1],
                "status": "qualified",
                "reviewer": "BENCHMARK TEST",
                "evidence_reference": "SYNTHETIC-B05",
                "rationale": (
                    "Contradictory gate for software testing."
                ),
            }],
        })

        try:
            select_next(path)
        except ValueError as error:
            if "unqualified prerequisites" in str(error):
                return True, "Contradictory qualification rejected"
            return False, f"Unexpected rejection: {error}"

        return False, "Invalid qualification was accepted"


def run_benchmarks():
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    scenarios = data["scenarios"]

    ids = [item["id"] for item in scenarios]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate benchmark IDs.")

    expected = {f"B{i:02d}" for i in range(1, 7)}

    if set(ids) != expected:
        raise ValueError("Unexpected benchmark scenarios.")

    evaluators = {
        "B04": test_invalid_provenance,
        "B05": test_invalid_prerequisites,
    }

    results = []

    for scenario in scenarios:
        identifier = scenario["id"]

        if identifier in REASONING_CASES:
            results.append({
                "id": identifier,
                "status": "not_evaluated",
                "method": "requires_scientific_reasoning_review",
                "detail": (
                    "No scientific reasoning assessment "
                    "has been performed."
                ),
            })
            continue

        passed, detail = evaluators[identifier]()

        results.append({
            "id": identifier,
            "status": "passed" if passed else "failed",
            "method": "deterministic_execution",
            "detail": detail,
        })

    return {
        "benchmark": "CuSelect-AI Scientific Scenarios v1",
        "total_scenarios": len(results),
        "deterministic_passed": sum(
            item["status"] == "passed" for item in results
        ),
        "deterministic_failed": sum(
            item["status"] == "failed" for item in results
        ),
        "not_evaluated": sum(
            item["status"] == "not_evaluated"
            for item in results
        ),
        "results": results,
        "scientific_reliability_established": False,
    }


def main():
    report = run_benchmarks()

    print("\nCUSELECT-AI — SCIENTIFIC BENCHMARK EXECUTION")
    print("=" * 65)

    for item in report["results"]:
        print(
            f"{item['id']}: "
            f"{item['status'].upper()} — {item['detail']}"
        )

    print("\nSUMMARY")
    print("Total scenarios:", report["total_scenarios"])
    print("Deterministic passed:", report["deterministic_passed"])
    print("Deterministic failed:", report["deterministic_failed"])
    print("Not evaluated:", report["not_evaluated"])
    print("Scientific reliability established: No")
    print("Real API requests: 0")
    print("New DFT calculations: 0")
    print("Project files modified: 0")

    if report["deterministic_failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
