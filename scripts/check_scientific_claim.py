"""CuSelect-AI: source-grounded scientific claim screening.

PSEUDOCODE
1. Load the original publication.
2. Check article identity.
3. Locate catalyst, product, FE, and potential together.
4. Locate the flow-cell experimental methodology.
5. Check the supporting performance figure.
6. Report missing evidence without granting approval.
"""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

XML = Path("data/raw/publications/PMC13692753.xml")
OUTPUT = Path("data/reports/scientific_quality_gate.json")


def normalize(text):
    return re.sub(
        r"\s+", " ",
        text.lower().replace("−", "-").replace("–", "-")
    )


root = ET.parse(XML).getroot()

paragraphs = [
    normalize("".join(p.itertext()))
    for p in root.iter("p")
]

dois = [
    x.text.strip().lower()
    for x in root.findall(".//article-meta/article-id")
    if x.get("pub-id-type") == "doi" and x.text
]

performance = [
    p for p in paragraphs
    if all(term in p for term in (
        "hoh cu/ag", "ethylene", "60.37", "-1.3 v"
    ))
]

methods = [
    p for p in paragraphs
    if all(term in p for term in (
        "flow-cell", "0.1 m khco3", "ag/agcl", "rhe"
    ))
]

figures = {
    fig.get("id"): normalize("".join(fig.itertext()))
    for fig in root.findall(".//fig")
}

checks = {
    "doi_matches": (
        "10.1021/acsnanoscienceau.6c00129" in dois
    ),
    "performance_context_found": bool(performance),
    "flow_cell_methods_found": bool(methods),
    "figure_4_is_product_distribution": (
        "fig4" in figures
        and "product distributions" in figures["fig4"]
    ),
}

report = {
    "claim": {
        "catalyst": "HOH Cu/Ag",
        "product": "ethylene",
        "fe_percent": 60.37,
        "potential_v_vs_rhe": -1.3,
    },
    "checks": checks,
    "source_evidence": {
        "performance_paragraphs": performance,
        "methodology_paragraphs": methods,
        "performance_figure": "fig4",
    },
    "screening_passed": all(checks.values()),
    "scientifically_verified": False,
    "human_review_required": True,
    "rag_ingestion_status": "not_ingested",
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nCUSELECT-AI — SCIENTIFIC QUALITY GATE")
print("=" * 45)

for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FLAGGED'}")

print("\nScreening passed:", report["screening_passed"])
print("Scientific approvals: 0")
print("Report:", OUTPUT)
