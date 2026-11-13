
# CuSelect-AI — Multi-Source Abstract Tests
#
# PSEUDOCODE
# 1. Verify OpenAlex abstract reconstruction.
# 2. Reject malformed indexes.
# 3. Test a successful DOI lookup.
# 4. Confirm Crossref abstracts are never overwritten.
# 5. Confirm missing abstracts are recovered.
# 6. Verify cached results are reused.
# 7. Confirm scientific status remains unverified.

import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cuselect.multi_source_abstracts as msa


def test_reconstruct_abstract():
    inverted = {
        "CuAg": [0],
        "produces": [1],
        "ethylene": [2],
    }

    assert msa.reconstruct_abstract(inverted) == (
        "CuAg produces ethylene"
    )


def test_reconstruct_rejects_invalid_index():
    assert msa.reconstruct_abstract(None) == ""

    assert msa.reconstruct_abstract({
        "CuAg": [0],
        "ethylene": [2],
    }) == ""


def test_openalex_success(monkeypatch):
    payload = {
        "doi": "https://doi.org/10.1234/example",
        "id": "https://openalex.org/W12345",
        "abstract_inverted_index": {
            "CuAg": [0],
            "produces": [1],
            "ethylene": [2],
        },
    }

    def fake_urlopen(request, timeout):
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(msa, "urlopen", fake_urlopen)

    result = msa.fetch_openalex_abstract(
        "10.1234/example"
    )

    assert result["abstract_status"] == "available"
    assert result["abstract_source"] == "OpenAlex"
    assert result["abstract"] == (
        "CuAg produces ethylene"
    )


def test_crossref_abstract_is_preserved(
    monkeypatch, tmp_path
):
    def forbidden_fetch(doi):
        raise AssertionError(
            "OpenAlex should not be called"
        )

    monkeypatch.setattr(
        msa, "fetch_openalex_abstract", forbidden_fetch
    )

    papers = [{
        "doi": "10.1234/existing",
        "title": "Existing paper",
        "abstract": "Original Crossref abstract",
        "abstract_status": "available",
        "abstract_source": "Crossref",
        "scientific_status": "unverified_discovery",
    }]

    results = msa.enrich_with_openalex(
        papers,
        cache_path=tmp_path / "cache.json",
        delay_seconds=0,
    )

    assert results[0]["abstract"] == (
        "Original Crossref abstract"
    )

    assert results[0]["abstract_source"] == "Crossref"


def test_fallback_and_cache_reuse(monkeypatch, tmp_path):
    calls = []

    def fake_fetch(doi):
        calls.append(doi)

        return {
            "doi": doi,
            "abstract": "Recovered CuAg abstract",
            "abstract_status": "available",
            "abstract_source": "OpenAlex",
            "openalex_id": "https://openalex.org/W12345",
        }

    monkeypatch.setattr(
        msa, "fetch_openalex_abstract", fake_fetch
    )

    papers = [{
        "doi": "10.1234/missing",
        "title": "CuAg paper",
        "abstract": "",
        "abstract_status": "missing",
        "abstract_source": "Crossref",
        "scientific_status": "unverified_discovery",
    }]

    cache = tmp_path / "openalex_cache.json"

    first = msa.enrich_with_openalex(
        papers,
        cache_path=cache,
        delay_seconds=0,
    )

    second = msa.enrich_with_openalex(
        papers,
        cache_path=cache,
        delay_seconds=0,
    )

    assert len(calls) == 1
    assert first == second
    assert cache.exists()

    assert first[0]["abstract_status"] == "available"
    assert first[0]["abstract_source"] == "OpenAlex"
    assert first[0]["scientific_status"] == (
        "unverified_discovery"
    )


def test_missing_openalex_abstract(monkeypatch, tmp_path):
    def fake_fetch(doi):
        return msa.empty_result(doi, "missing")

    monkeypatch.setattr(
        msa, "fetch_openalex_abstract", fake_fetch
    )

    papers = [{
        "doi": "10.1234/missing",
        "abstract": "",
        "abstract_status": "missing",
        "scientific_status": "unverified_discovery",
    }]

    results = msa.enrich_with_openalex(
        papers,
        cache_path=tmp_path / "cache.json",
        delay_seconds=0,
    )

    assert results[0]["abstract"] == ""
    assert results[0]["abstract_status"] == "missing"
