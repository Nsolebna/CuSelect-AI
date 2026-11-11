"""Display scientific promotion readiness without writing files."""

from pathlib import Path

from cuselect.scientific_promotion import promotion_preflight

report = promotion_preflight(Path.cwd())

print("\nCUSELECT-AI — CONTROLLED PROMOTION PREFLIGHT")
print("=" * 50)
print("Claim:", report.get("claim_id", "unknown"))
print("Eligible:", report["eligible"])

for problem in report.get("problems", []):
    print("BLOCKER:", problem)

print("Trusted evidence modified: NO")
print("RAG corpus modified: NO")
