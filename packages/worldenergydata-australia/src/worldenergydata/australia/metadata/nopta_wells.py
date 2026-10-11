"""Bounded NOPTA wells retrieval; no depth or field linkage is inferred.

Endpoints and columns were observed in the regulator listing on 2026-10-11.
The service/item do not state a reuse licence. Do not redistribute fetched rows
until source-specific rights are established. Synthetic fixtures are separate.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LISTING_URL = "https://gis.spatial.nopta.gov.au/gis/rest/services/Public?f=json"
LAYER_URL = "https://gis.spatial.nopta.gov.au/gis/rest/services/Public/Wells/FeatureServer/0"
QUERY_URL = LAYER_URL + "/query"
TERMS_URL = "https://www.nopta.gov.au/copyright.html"
ROBOTS_URL = "https://gis.spatial.nopta.gov.au/robots.txt"
REVIEWED_TERMS_SHA256 = "8683b7e3b731e4cdcb27b7939d88dc774329721a5f1c2dd5f18ab7e3083ce8f4"
CONTACT = "https://github.com/vamseeachanta/worldenergydata"
USER_AGENT = "worldenergydata Australia wells metadata; contact " + CONTACT
REQUIRED_FIELDS = ("OBJECTID", "Uwi", "WellName", "Latitude", "Longitude", "TitleNumber")
QUERY_KEYS = {"f", "where", "outFields", "returnGeometry", "resultOffset",
              "resultRecordCount", "orderByFields"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> Any:
        raise ValueError("redirect refused")


open_request = urllib.request.build_opener(NoRedirect()).open


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def evidence(data: bytes, url: str, retrieved_at: Optional[str] = None) -> Dict[str, Any]:
    return {"source_url": url, "retrieved_at_utc": retrieved_at or
            datetime.now(timezone.utc).isoformat(), "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def get_bytes(url: str, *, max_bytes: int = 2_000_000) -> bytes:
    """One request, bounded response, no redirects/retries/credentials."""
    parsed = urllib.parse.urlsplit(url)
    base = urllib.parse.urlunsplit(parsed._replace(query="", fragment=""))
    if base not in {QUERY_URL, TERMS_URL, ROBOTS_URL} or parsed.fragment:
        raise ValueError("destination not permitted")
    pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    if (base != QUERY_URL and pairs) or any(k not in QUERY_KEYS for k, _ in pairs):
        raise ValueError("query parameter not permitted")
    if len({k for k, _ in pairs}) != len(pairs):
        raise ValueError("duplicate query parameters")
    if not 0 < max_bytes <= 2_000_000:
        raise ValueError("invalid byte cap")
    time.sleep(2)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with open_request(request, timeout=30) as response:
        if response.status != 200:
            raise ValueError("unexpected HTTP status")
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("response byte cap exceeded")
    return bytes(data)


def access_preflight() -> List[Dict[str, Any]]:
    """Record robots and website terms; website terms do not license the layer."""
    records = []
    try:
        robots = get_bytes(ROBOTS_URL)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        records.append({"source_url": ROBOTS_URL, "status": 404,
                        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                        "terms": "not stated by the source"})
    else:
        if robots.lstrip().startswith(b"<"):
            raise ValueError("robots challenge page; access refused")
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(robots.decode("utf-8").splitlines())
        if not parser.can_fetch(USER_AGENT, QUERY_URL):
            raise ValueError("robots refuses automated access")
        records.append(evidence(robots, ROBOTS_URL))
    terms = get_bytes(TERMS_URL)
    # Any changed bytes void the reviewed access assessment, including additions
    # retaining the licence sentence while forbidding automation.
    if hashlib.sha256(terms).hexdigest() != REVIEWED_TERMS_SHA256:
        raise ValueError("terms changed or challenge page; review required")
    records.append(evidence(terms, TERMS_URL))
    return records


def parse_layer(metadata: Dict[str, Any]) -> Dict[str, Any]:
    if "error" in metadata:
        raise ValueError("ArcGIS metadata error")
    names = {field["name"] for field in metadata.get("fields", [])}
    capabilities = metadata.get("advancedQueryCapabilities", {})
    if not set(REQUIRED_FIELDS) <= names or metadata.get("objectIdField") != "OBJECTID":
        raise ValueError("required source fields missing")
    if not capabilities.get("supportsPagination") or not capabilities.get("supportsOrderBy"):
        raise ValueError("stable pagination unavailable")
    maximum = metadata.get("maxRecordCount")
    if type(maximum) is not int or maximum <= 0:
        raise ValueError("invalid maxRecordCount")
    sr = metadata.get("spatialReference", {})
    if sr.get("wkid") != 4283:
        raise ValueError("unreviewed spatial reference")
    return {"max_record_count": maximum, "spatial_reference": sr, "fields": sorted(names)}


def _coordinate(value: Any, limit: int) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("invalid coordinate")
    if not math.isfinite(value) or abs(value) > limit:
        raise ValueError("coordinate outside range")
    return float(value)


def normalize_page(page: Dict[str, Any], layer: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "error" in page or not isinstance(page.get("features"), list):
        raise ValueError("invalid ArcGIS page")
    sr = page.get("spatialReference", layer["spatial_reference"])
    if sr.get("wkid") != layer["spatial_reference"].get("wkid"):
        raise ValueError("spatial reference mismatch")
    rows = []
    for feature in page["features"]:
        a = feature["attributes"]
        rows.append({"object_id": a["OBJECTID"], "well_identifier": a.get("Uwi"),
                     "well_name": a.get("WellName"), "title_number": a.get("TitleNumber"),
                     "field_name": None, "water_depth": None, "water_depth_unit": None,
                     "water_depth_datum": None, "latitude": _coordinate(a.get("Latitude"), 90),
                     "longitude": _coordinate(a.get("Longitude"), 180),
                     "spatial_reference": sr, "source_columns": a})
    return rows


def fetch_wells(
    metadata: Dict[str, Any], *, where: str = "OBJECTID <= 5",
    max_pages: int = 3, max_total_bytes: int = 5_000_000
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Fetch a bounded sample; caps fail instead of silently truncating."""
    layer = parse_layer(metadata)
    if type(max_pages) is not int or not 1 <= max_pages <= 3:
        raise ValueError("invalid page cap")
    if not 0 < max_total_bytes <= 5_000_000 or not isinstance(where, str) or len(where) > 500:
        raise ValueError("invalid query limits")
    records = access_preflight()
    rows: List[Dict[str, Any]] = []
    seen: set[int] = set()
    offset, total = 0, 0
    page_size = min(layer["max_record_count"], 100)
    for _ in range(max_pages):
        params = {"f": "json", "where": where, "outFields": "*", "returnGeometry": "false",
                  "orderByFields": "OBJECTID", "resultOffset": offset,
                  "resultRecordCount": page_size}
        url = QUERY_URL + "?" + urllib.parse.urlencode(params)
        remaining = max_total_bytes - total
        if remaining <= 0:
            raise ValueError("total byte cap exceeded")
        raw = get_bytes(url, max_bytes=min(2_000_000, remaining))
        total += len(raw)
        if total > max_total_bytes:
            raise ValueError("total byte cap exceeded")
        records.append(evidence(raw, url))
        page = json.loads(raw)
        batch = normalize_page(page, layer)
        if len(batch) > page_size:
            raise ValueError("page exceeds requested record count")
        for row in batch:
            identity = row["object_id"]
            if type(identity) is not int or identity in seen:
                raise ValueError("invalid or duplicate object id")
            if seen and identity <= max(seen):
                raise ValueError("unstable ordering")
            seen.add(identity)
        rows.extend(batch)
        more = page.get("exceededTransferLimit")
        if more is False or (more is None and len(batch) < page_size):
            return rows, records
        if not batch:
            raise ValueError("pagination made no progress")
        offset += len(batch)
    raise ValueError("page cap exceeded")


def fixture_manifest(raw: bytes) -> Dict[str, Any]:
    sample = json.loads(raw)
    if sample.get("synthetic") is not True:
        raise ValueError("fixture must be labelled synthetic")
    layer = parse_layer(sample["layer"])
    rows = [row for page in sample["pages"] for row in normalize_page(page, layer)]
    return {"synthetic": True, "intended_use": "offline software tests only",
            "source_url": "urn:synthetic:nopta-wells-test",
            "retrieval_date_utc": None, "licence": "not applicable: synthetic test inputs",
            "attribution": "Synthetic test inputs; no source well records reproduced.",
            "fixture_size_bytes": len(raw), "fixture_sha256": hashlib.sha256(raw).hexdigest(),
            "normalized_rows_sha256": hashlib.sha256(json_bytes(rows)).hexdigest(),
            "rows": len(rows), "listing_url": LISTING_URL,
            "source_layer_reuse": {
                "licence": "not stated by the source",
                "attribution": "not stated by the source",
                "redistribution_confirmed": False,
                "item_url": ("https://portal.spatial.nopta.gov.au/portal/sharing/rest/"
                             "content/items/12886c0431a842aca665a4ecd618f091?f=json"),
                "checked_date_utc": "2026-10-11",
                "website_terms_url": TERMS_URL,
                "website_attribution_instruction": (
                    "Content contained herein should be attributed as ©  Commonwealth of "
                    "Australia (Department of Industry) [year], NOPTA "
                    "[name of document or page containing the content]."
                ),
            }}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--layer", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.fixture is not None and args.layer is None:
        result = fixture_manifest(args.fixture.read_bytes())
    elif args.layer is not None and args.fixture is None:
        rows, records = fetch_wells(json.loads(args.layer.read_bytes()))
        result = {"synthetic": False, "rows": rows, "requests": records,
                  "listing_url": LISTING_URL, "layer_url": LAYER_URL + "?f=json",
                  "licence": "not stated by the source",
                  "attribution": "not stated by the source",
                  "redistribution_confirmed": False}
    else:
        parser.error("select exactly one of --fixture or --layer")
    args.output.write_bytes(json_bytes(result))


if __name__ == "__main__":
    main()
