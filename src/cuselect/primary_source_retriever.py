"""Read-only retrieval of accessible Europe PMC full-text XML."""

import re
import xml.etree.ElementTree as ET

import requests

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def retrieve_primary_source(doi):
    doi = str(doi).strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi.org/", "", doi, flags=re.I)

    if not doi.startswith("10.") or "/" not in doi:
        raise ValueError("A valid DOI is required.")

    session = requests.Session()

    search = session.get(
        BASE + "/search",
        params={
            "query": f'DOI:"{doi}"',
            "format": "json",
            "resultType": "core",
            "pageSize": 10,
        },
        timeout=25,
    )
    search.raise_for_status()

    matches = search.json().get("resultList", {}).get("result", [])

    matches = [
        p for p in matches
        if str(p.get("doi") or "").lower() == doi.lower()
    ]

    if not matches:
        return {
            "doi": doi,
            "status": "not_indexed",
            "sections": [],
        }

    paper = matches[0]
    pmcid = paper.get("pmcid")

    if not pmcid:
        return {
            "doi": doi,
            "status": "no_full_text_identifier",
            "title": paper.get("title"),
            "sections": [],
        }

    response = session.get(
        f"{BASE}/{pmcid}/fullTextXML",
        timeout=35,
    )

    if response.status_code in (403, 404):
        return {
            "doi": doi,
            "pmcid": pmcid,
            "status": "full_text_unavailable",
            "sections": [],
        }

    response.raise_for_status()

    if len(response.content) > 15_000_000:
        raise RuntimeError("Full-text XML exceeds safety limit.")

    root = ET.fromstring(response.content)

    sections = []

    for section in root.findall(".//body//sec"):
        # Use direct paragraphs to avoid duplicating nested sections.
        paragraphs = section.findall("./p")

        if not paragraphs:
            continue

        title_node = section.find("./title")
        title = (
            " ".join(title_node.itertext()).strip()
            if title_node is not None
            else "Untitled section"
        )

        text = "\n".join(
            " ".join("".join(p.itertext()).split())
            for p in paragraphs
        )

        if text.strip():
            sections.append({
                "section": title,
                "text": text,
            })

    return {
        "doi": doi,
        "pmcid": pmcid,
        "title": paper.get("title"),
        "status": "full_text_available",
        "source": "Europe PMC fullTextXML",
        "sections": sections,
        "section_count": len(sections),
        "scientifically_verified": False,
        "approved_for_rag": False,
    }
