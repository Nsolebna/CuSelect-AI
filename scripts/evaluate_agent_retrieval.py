"""Evaluate live literature retrieval against trusted scientific evidence.

PSEUDOCODE
1. Load the authoritative approved corpus.
2. Execute supported and unsupported scientific questions.
3. Compare actual citations and decisions with expected results.
4. Verify that unapproved evidence never enters the response.
5. Save a reproducible evaluation report.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from cuselect.agents import ResearchTask
from cuselect.evidence_store import load_verified_corpus
from cuselect.orchestrator import run_research_workflow


ROOT = Path.cwd()

CASES = [
    {
        "name": "ethylene_fe",
        "question": "What is the ethylene Faradaic efficiency for AgCu NW?",
        "expected_decision": "evidence_only",
        "expected_id": "E-P005-FE-C2H4-001",
    },
    {
        "name": "ethanol_fe",
        "question": "What is the ethanol Faradaic efficiency for Ag1Cu NW?",
        "expected_decision": "evidence_only",
        "expected_id": "E-P005-FE-ETOH-001",
    },
    {
        "name": "unapproved_p009",
        "question": "What is the ethylene Faradaic efficiency for HOH Cu/Ag?",
        "expected_decision": "abstain",
        "expected_id": None,
    },
    {
        "name": "unsupported_prediction",
        "question": "Predict the best Cu catalyst for ethylene production",
        "expected_decision": "abstain",
        "expected_id": None,
    },
]

records = load_verified_corpus(ROOT)
trusted_ids = {r["evidence_id"] for r in records}

assert all(
    r["paper_id"] != "P009" for r in records
), "Unapproved P009 publication found in trusted evidence"

results = []

for mode in ("legacy", "dynamic"):
    for case in CASES:
        task = ResearchTask(
            task_id=f"EVAL-{mode}-{case['name']}",
            task_type="source_question",
            question=case["question"],
        )

        result = run_research_workflow(
            task,
            project_root=ROOT,
            literature_mode=mode,
        )

        cited_ids = [
            c["evidence_id"] for c in result["citations"]
        ]

        expected_ids = (
            [case["expected_id"]]
            if case["expected_id"] else []
        )

        citation_safe = set(cited_ids) <= trusted_ids
        decision_correct = (
            result["decision"] == case["expected_decision"]
        )
        citation_correct = cited_ids == expected_ids

        passed = (
            citation_safe
            and decision_correct
            and citation_correct
        )

        results.append({
            "mode": mode,
            "case": case["name"],
            "expected_decision": case["expected_decision"],
            "actual_decision": result["decision"],
            "expected_ids": expected_ids,
            "cited_ids": cited_ids,
            "citation_safe": citation_safe,
            "passed": passed,
        })

        print(
            f"{mode:8} | {case['name']:24} | "
            f"{'PASS' if passed else 'FAIL'}"
        )

report = {
    "evaluation_version": "1.0",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "trusted_corpus_size": len(records),
    "cases": results,
    "passed": sum(r["passed"] for r in results),
    "total": len(results),
}

path = ROOT / "data/reports/agent_retrieval_evaluation.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print("\nCUSELECT-AI — RETRIEVAL EVALUATION")
print("=" * 45)
print(f"Passed: {report['passed']}/{report['total']}")
print("Report:", path)
print("Trusted corpus: UNCHANGED")

if report["passed"] != report["total"]:
    raise SystemExit(
        "Evaluation failed. Do not enable dynamic retrieval by default."
    )
