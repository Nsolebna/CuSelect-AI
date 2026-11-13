
# CuSelect-AI — Abstract Retrieval Tests
#
# PSEUDOCODE
# 1. Test abstract markup cleaning.
# 2. Simulate a successful Crossref abstract response.
# 3. Verify missing abstracts are recorded honestly.
# 4. Verify HTTP 429 retry behavior.
# 5. Verify caching prevents repeated API requests.
# 6. Verify publication metadata remains unchanged.

import io
import json
import sys
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cuselect.abstracts as abstracts


def test_abstract_cleaning():
    raw = (
        "<jats:p>CO<jats:sub>2</jats:sub> "
        "electroreduction on <b>Cu–Ag</b>.</jats:p>"
    )

    cleaned = abstracts.clean_abstract(raw)

    assert "electroreduction" in cleaned
    assert "Cu–Ag" in cleaned
    assert "<jats:" not in cleaned


def test_successful_abstract_retrieval(monkeypatch):
    def fake_urlopen(request, timeout):
        payload = {
            "message": {
                "abstract": (
                    "<jats:p>Cu Ag tandem catalysts "
                    "produce ethylene.</jats:p>"
                )
            }
        }

        return io.BytesIO(
            json.dumps(payload).encode()
        )

    monkeypatch.setattr(
        abstracts, "urlopen", fake_urlopen
    )

    result = abstracts.fetch_crossref_abstract(
        "10.1234/example"
    )

    assert result["abstract_status"] == "available"
    assert "ethylene" in result["abstract"]
    assert result["abstract_source"] == "Crossref"


def test_missing_abstract(monkeypatch):
    def fake_urlopen(request, timeout):
        return io.BytesIO(
            json.dumps({"message": {}}).encode()
        )

    monkeypatch.setattr(
        abstracts, "urlopen", fake_urlopen
    )

    result = abstracts.fetch_crossref_abstract(
        "10.1234/no-abstract"
    )

    assert result["abstract_status"] == "missing"
    assert result["abstract"] == ""


def test_rate_limit_retry(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(1)

        if len(calls) == 1:
            raise HTTPError(
                request.full_url,
                429,
                "Too Many Requests",
                {"Retry-After": "0"},
                None,
            )

        return io.BytesIO(
            json.dumps({
                "message": {"abstract": "<p>Test abstract</p>"}
            }).encode()
        )

    monkeypatch.setattr(
        abstracts, "urlopen", fake_urlopen
    )
    monkeypatch.setattr(
        abstracts.time, "sleep", lambda x: None
    )
    monkeypatch.setattr(
        abstracts.random, "uniform", lambda a, b: 0
    )

    result = abstracts.fetch_crossref_abstract(
        "10.1234/retry"
    )

    assert len(calls) == 2
    assert result["abstract_status"] == "available"


def test_abstract_cache_reuse(monkeypatch, tmp_path):
    calls = []

    def fake_fetch(doi):
        calls.append(doi)

        return {
            "doi": doi,
            "abstract": "A test abstract.",
            "abstract_status": "available",
            "abstract_source": "Crossref",
        }

    monkeypatch.setattr(
        abstracts,
        "fetch_crossref_abstract",
        fake_fetch,
    )

    papers = [
        {
            "doi": "10.1234/test",
            "title": "Test publication",
            "scientific_status": "unverified_discovery",
        }
    ]

    cache_path = tmp_path / "abstract_cache.json"

    first = abstracts.retrieve_abstracts(
        papers,
        cache_path=cache_path,
        delay_seconds=0,
    )

    second = abstracts.retrieve_abstracts(
        papers,
        cache_path=cache_path,
        delay_seconds=0,
    )

    assert len(calls) == 1
    assert first == second
    assert cache_path.exists()
    assert first[0]["title"] == "Test publication"
    assert first[0]["scientific_status"] == (
        "unverified_discovery"
    )
