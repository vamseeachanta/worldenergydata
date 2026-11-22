"""Offline collection tests; request expectations are counted by hand.

For page size two and row counts (3, 1, 0), keyset pagination takes (2, 1, 1)
queries, plus one schema read per table: seven requests. These are synthetic
counts, not service limits. ArcGIS query semantics:
https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service-layer/
"""

import hashlib
import json
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

import pytest

from worldenergydata.modules.state_regulators.fetch import (
    FetchConfig,
    Fetcher,
    TermsDenied,
)
from worldenergydata.modules.state_regulators.fetch.storage import FetchResult
from worldenergydata.modules.state_regulators.indiana_dnr.collection import (
    collect_snapshot,
    plan_collection,
)
from worldenergydata.modules.state_regulators.indiana_dnr.inventory import (
    SERVICE_URL,
    build_inventory,
)


class FakeFetcher:
    def __init__(self, root):
        self.root = root
        self.urls = []
        self.cache = {}
        self.responses = []

    def fetch(self, url):
        if url in self.cache:
            return self.cache[url]
        self.urls.append(url)
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        payload = json.dumps(value).encode()
        digest = hashlib.sha256(payload).hexdigest()
        path = self.root / digest
        path.write_bytes(payload)
        result = FetchResult(
            path,
            {"url": url, "sha256": digest, "fetched_at": "2026-10-19T00:00:00Z"},
            False,
        )
        self.cache[url] = result
        return result


def metadata(table):
    join = ["igs_id", "igs_id", "permit_int"][table]
    names = {"objectid", join}
    if table == 0:
        names.update({"operator_name", "permit_number", "igs_int", "permit_int"})
    return {
        "objectIdField": "objectid",
        "maxRecordCount": 2,
        "fields": [{"name": name} for name in sorted(names)],
        "spatialReference": {"wkid": "synthetic-crs"},
    }


def page(*ids, more=False):
    return {
        "features": [{"attributes": {"objectid": i, "igs_id": str(i)}} for i in ids],
        "exceededTransferLimit": more,
    }


def test_dry_run_hand_count():
    plan = plan_collection(
        {"wells": 3, "completions": 1, "images": 0}, page_size=2, max_record_count=2
    )
    assert plan["metadata_requests"] == 3
    assert plan["query_requests_baseline"] == 4
    assert plan["total_requests_baseline"] == 7


@pytest.mark.parametrize("size,limit", [(0, 2), (3, 2), (True, 2)])
def test_invalid_page_size(size, limit):
    with pytest.raises(ValueError):
        plan_collection(
            {"wells": 0, "completions": 0, "images": 0},
            page_size=size,
            max_record_count=limit,
        )


def test_paginated_collect_and_repeat_without_network(tmp_path):
    fetcher = FakeFetcher(tmp_path)
    fetcher.responses = [
        metadata(0),
        page(1, 2, more=True),
        page(5),
        metadata(1),
        page(7),
        metadata(2),
        page(),
    ]
    snapshot = collect_snapshot(fetcher, page_size=2, max_query_pages=4)
    assert len(snapshot["wells"]) == 3
    assert len(snapshot["completions"]) == 1
    assert snapshot["images"] == []
    assert len(snapshot["source_pages"]) == 7
    assert snapshot["spatial_reference"] == {"wkid": "synthetic-crs"}
    urls = fetcher.urls.copy()
    assert collect_snapshot(fetcher, page_size=2, max_query_pages=4) == snapshot
    assert fetcher.urls == urls
    queries = [parse_qs(urlsplit(u).query) for u in urls if "/query?" in u]
    assert queries[0]["where"] == ["1=1"]
    assert queries[1]["where"] == ["objectid > 2"]
    assert queries[0]["orderByFields"] == ["objectid ASC"]


def test_resume_after_interruption_uses_prior_cached_pages(tmp_path):
    fetcher = FakeFetcher(tmp_path)
    fetcher.responses = [
        metadata(0),
        page(1, 2, more=True),
        RuntimeError("interrupted"),
    ]
    with pytest.raises(RuntimeError, match="interrupted"):
        collect_snapshot(fetcher, page_size=2, max_query_pages=4)
    fetcher.responses = [page(5), metadata(1), page(), metadata(2), page()]
    result = collect_snapshot(fetcher, page_size=2, max_query_pages=4)
    assert len(result["wells"]) == 3
    assert fetcher.urls.count(SERVICE_URL + "/0?f=json") == 1


@pytest.mark.parametrize(
    "bad_page",
    [
        {"error": {"code": 400}},
        page(1, 1, more=True),
        page(2, 1),
        {"features": [], "exceededTransferLimit": True},
    ],
)
def test_errors_duplicates_and_out_of_order_pages_rejected(tmp_path, bad_page):
    fetcher = FakeFetcher(tmp_path)
    fetcher.responses = [metadata(0), bad_page]
    with pytest.raises(ValueError):
        collect_snapshot(fetcher, page_size=2, max_query_pages=4)


def test_request_cap_stops_collection(tmp_path):
    fetcher = FakeFetcher(tmp_path)
    fetcher.responses = [metadata(0), page(1, 2, more=True)]
    with pytest.raises(ValueError, match="budget"):
        collect_snapshot(fetcher, page_size=2, max_query_pages=1)
    assert len(fetcher.urls) == 2


def test_terms_gate_without_network(tmp_path):
    fetcher = Fetcher(
        FetchConfig(cache_root=tmp_path, user_agent="Synthetic tests"), []
    )
    with pytest.raises(TermsDenied):
        collect_snapshot(fetcher, page_size=2, max_query_pages=4)


def test_changed_schema_is_not_silently_accepted(tmp_path):
    fetcher = FakeFetcher(tmp_path)
    fetcher.responses = [{**metadata(0), "objectIdField": "different"}]
    with pytest.raises(ValueError, match="schema"):
        collect_snapshot(fetcher, page_size=2, max_query_pages=4)


def test_missing_operator_column_cannot_be_reported_as_no_matches(tmp_path):
    fetcher = FakeFetcher(tmp_path)
    schema = metadata(0)
    schema["fields"] = [f for f in schema["fields"] if f["name"] != "operator_name"]
    fetcher.responses = [schema]
    with pytest.raises(ValueError, match="schema"):
        collect_snapshot(fetcher, page_size=2, max_query_pages=4)


def test_collection_output_is_inventory_input(tmp_path):
    """One well and its completion join; both counts are one by inspection."""
    fetcher = FakeFetcher(tmp_path)
    well = page(1)
    well["features"][0]["attributes"].update(
        operator_name="Synthetic LLC", permit_number="0007", permit_int=7
    )
    completion = page(11)
    completion["features"][0]["attributes"].update(igs_id=1, totaldepthdriller=1200)
    fetcher.responses = [
        metadata(0),
        well,
        metadata(1),
        completion,
        metadata(2),
        page(),
    ]
    snapshot = collect_snapshot(fetcher, page_size=2, max_query_pages=3)
    report = build_inventory(snapshot, operator="Synthetic")
    assert report["coverage"]["matched_wells"] == 1
    assert report["coverage"]["with_completions"] == 1
    assert report["wells"][0]["total_depth"][0]["driller"] == 1200
    assert report["source_pages"][1]["sha256"]


def test_collection_cli_dry_run_requires_no_network_config(tmp_path):
    """Two, one and one query pages plus three metadata reads give seven."""
    config = tmp_path / "plan.json"
    output = tmp_path / "result.json"
    config.write_text(
        json.dumps(
            {
                "row_counts": {"wells": 3, "completions": 1, "images": 0},
                "page_size": 2,
                "max_record_count": 2,
            }
        )
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.modules.state_regulators.indiana_dnr.collection",
            "--config",
            str(config),
            "--output",
            str(output),
            "--dry-run",
        ],
        check=True,
    )
    assert json.loads(output.read_text())["total_requests_baseline"] == 7
