"""Bounded, resumable official ArcGIS collection; no PDMS or PDF crawling.

Table identifiers/record limits are from Indiana GIS metadata (2026-10-20):
https://gisdata.in.gov/server/rest/services/Hosted/OilAndGasWells/FeatureServer
Query parameters, object-id ordering and exceededTransferLimit semantics:
https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service-layer/
No numeric rate, retry or page limit is invented here: callers configure the
shared fetcher and provide a page size no larger than the published limit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode

from ..fetch import FetchConfig, Fetcher, TermsCheck
from ..fetch.storage import atomic_json
from .inventory import SERVICE_URL, features

# Official table ids and relationship keys, as published in the service metadata.
TABLES = {
    "wells": (0, "igs_id"),
    "completions": (1, "igs_id"),
    "images": (2, "permit_int"),
}


def _page_size(page_size: int, max_record_count: int) -> None:
    if (
        type(page_size) is not int
        or type(max_record_count) is not int
        or not 0 < page_size <= max_record_count
    ):
        raise ValueError("page_size must be positive and within the service limit")


def plan_collection(
    row_counts: dict[str, int], *, page_size: int, max_record_count: int
) -> dict:
    """Offline baseline: floor(rows / page size) + one terminal query per table.

    Independent counting identity, not a physical equation. Full terminal pages
    may need an empty probe. Early transfer limits, changes and retries can add
    requests; the configured query cap and shared request budget still apply.
    Counts and record limits must be supplied with their own source evidence.
    """
    _page_size(page_size, max_record_count)
    if set(row_counts) != set(TABLES) or any(
        type(n) is not int or n < 0 for n in row_counts.values()
    ):
        raise ValueError("Provide nonnegative row counts for every table")
    queries = sum(n // page_size + 1 for n in row_counts.values())
    return {
        "metadata_requests": len(TABLES),
        "query_requests_baseline": queries,
        "total_requests_baseline": queries + len(TABLES),
        "assumptions": "Supplied row counts; full pages; excludes retries and cache hits.",
        "terms_permission": "NOT_EVALUATED; collection uses the shared fetcher gate",
    }


def collect_snapshot(
    fetcher: Fetcher,
    *,
    page_size: int,
    max_query_pages: int,
    source_url: str = SERVICE_URL,
) -> dict:
    """Collect sequentially, using deterministic URLs for cache-based resume.

    No partial snapshot is returned. The fetcher's verified page cache and
    persisted budgets survive interruption. New extraction vintages need a new
    cache directory; reusing a cache intentionally resumes the same extraction.
    """
    if type(page_size) is not int or page_size <= 0:
        raise ValueError("page_size must be positive")
    if type(max_query_pages) is not int or max_query_pages <= 0:
        raise ValueError("A positive query-page budget is required")
    source_url = source_url.rstrip("/")
    snapshot = {"source_url": source_url, "source_pages": []}
    queries = 0

    def read(url):
        result = fetcher.fetch(url)
        value = json.loads(result.path.read_text())
        if not isinstance(value, dict) or "error" in value:
            raise ValueError("ArcGIS returned an invalid response or error")
        snapshot["source_pages"].append(result.metadata.copy())
        return value

    for name, (table, join_key) in TABLES.items():
        layer = f"{source_url}/{table}"
        metadata = read(f"{layer}?f=json")
        field_names = {f["name"] for f in metadata.get("fields", [])}
        required = {"objectid", join_key}
        if name == "wells":
            required.update({"operator_name", "permit_number", "igs_int", "permit_int"})
        if metadata.get("objectIdField") != "objectid" or not required.issubset(
            field_names
        ):
            raise ValueError("Unexpected Indiana schema; inspect before collection")
        _page_size(page_size, metadata.get("maxRecordCount"))
        if name == "wells":
            snapshot["spatial_reference"] = metadata.get("spatialReference")
        rows, cursor = [], None
        while True:
            if queries >= max_query_pages:
                raise ValueError(
                    "Query-page budget exhausted; cached pages retained for resume"
                )
            params = {
                "f": "json",
                "where": "1=1" if cursor is None else f"objectid > {cursor}",
                "outFields": "*",
                "orderByFields": "objectid ASC",
                "resultRecordCount": page_size,
                "returnGeometry": "true" if name == "wells" else "false",
            }
            queries += 1
            value = read(f"{layer}/query?{urlencode(params)}")
            # Transfer-limited pages are valid here because collection continues.
            batch = features({"features": value.get("features")})
            if value.get("exceededTransferLimit") and not batch:
                raise ValueError("Transfer-limited empty page made no progress")
            for feature in batch:
                oid = feature["attributes"].get("objectid")
                if type(oid) is not int or (cursor is not None and oid <= cursor):
                    raise ValueError("Invalid, duplicate or unordered objectid")
                cursor = oid
            rows.extend(batch)
            if value.get("exceededTransferLimit") is False or (
                not value.get("exceededTransferLimit") and len(batch) < page_size
            ):
                break
        snapshot[name] = rows
    times = [p["fetched_at"] for p in snapshot["source_pages"]]
    snapshot["captured_at"] = max(times)
    snapshot["capture_started_at"] = min(times)
    snapshot["capture_note"] = (
        "Sequential extraction; not a transactional service snapshot."
    )
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if args.dry_run:
        result = plan_collection(
            config["row_counts"],
            page_size=config["page_size"],
            max_record_count=config["max_record_count"],
        )
    else:
        fetcher = Fetcher(
            FetchConfig(**config["fetch"]), [TermsCheck(**t) for t in config["terms"]]
        )
        result = collect_snapshot(
            fetcher,
            page_size=config["page_size"],
            max_query_pages=config["max_query_pages"],
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(args.output, result)


if __name__ == "__main__":
    main()
