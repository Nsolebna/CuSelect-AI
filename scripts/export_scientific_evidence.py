"""Controlled scientific evidence export CLI."""

from pathlib import Path

from cuselect.scientific_export import export_approved_claim

result = export_approved_claim(Path.cwd())

print("\nCUSELECT-AI — VERSIONED EVIDENCE EXPORT")
print("=" * 48)

if not result["exportable"]:
    print("Status: BLOCKED")

    for blocker in result.get("blockers", []):
        print("Reason:", blocker)

    print("No evidence exported.")
else:
    print("Status: EXPORTED")
    print("Version:", result["package_version"])
    print("Package:", result["package_path"])

print("Existing trusted RAG corpus: UNCHANGED")
