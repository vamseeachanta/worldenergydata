#!/usr/bin/env python3
"""Fetch + ingest myshiptracking.com particulars for roster vessels (#988).

Seeds from ``intervention_osv_roster.yml`` (vessels with both IMO and MMSI),
fetches each particulars page (rate-limited), caches the raw HTML gzipped
under ``_data/raw/myshiptracking/pages/`` with a sha256 manifest, parses
design particulars via ``parsers.myshiptracking``, and writes a raw parquet
source (``_data/raw/myshiptracking/particulars.parquet``) for the fuse
pipeline. AIS-state values (current draught, speed) are not ingested.

Usage:
    python scripts/vessel_fleet/ingest_myshiptracking.py [--offline]

``--offline`` re-parses the cached pages only (no network) — the drift-check
analogue for this source family.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import logging
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(_PROJECT_ROOT / "packages/worldenergydata-vessel_fleet/src"))

from worldenergydata.vessel_fleet.parsers.myshiptracking import (
    parse_particulars_html,
    vessel_url,
)
from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_DATA_DIR = (
    _PROJECT_ROOT
    / "packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/_data"
)
_ROSTER = (
    _PROJECT_ROOT
    / "packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/data/intervention_osv_roster.yml"
)
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_RATE_SECONDS = 1.5


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="re-parse cached pages only (no network)",
    )
    args = parser.parse_args()

    roster = yaml.safe_load(open(_ROSTER))
    vessels = roster if isinstance(roster, list) else roster.get("vessels", [])
    seeds = [v for v in vessels if v.get("imo") and v.get("mmsi")]
    logger.info("Roster: %d vessels, %d with IMO+MMSI", len(vessels), len(seeds))

    pages_dir = _DATA_DIR / "raw/myshiptracking/pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _DATA_DIR / "raw/myshiptracking/manifest.yaml"
    manifest = (
        yaml.safe_load(open(manifest_path)) if manifest_path.exists() else None
    ) or {"source_family": "ais_particulars_page", "files": {}}

    records = []
    misses = []
    for vessel in seeds:
        name = vessel["vessel_name"]
        url = vessel_url(vessel["mmsi"], vessel["imo"], name)
        cache = pages_dir / f"imo-{vessel['imo']}.html.gz"

        if cache.exists():
            html = gzip.decompress(cache.read_bytes()).decode("utf-8", "replace")
        elif args.offline:
            misses.append(name)
            continue
        else:
            logger.info("Fetching %s", name)
            raw = _fetch(url)
            cache.write_bytes(gzip.compress(raw))
            manifest["files"][cache.name] = {
                "url": url,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "retrieved": str(date.today()),
            }
            time.sleep(_RATE_SECONDS)
            html = raw.decode("utf-8", "replace")

        particulars = parse_particulars_html(html)
        if not particulars:
            misses.append(name)
            logger.warning("No particulars for %s (%s)", name, url)
            continue

        records.append(
            {
                "VESSEL_NAME": name,
                "VESSEL_CATEGORY": "intervention_vessel",
                "VESSEL_TYPE": vessel.get("vessel_type"),
                "OWNER": vessel.get("owner"),
                "DATA_SOURCE": "myshiptracking",
                "DATA_SOURCE_URL": url,
                "DIMENSION_CONFIDENCE": "registry",
                **particulars,
            }
        )

    yaml.safe_dump(manifest, open(manifest_path, "w"), sort_keys=True)
    store = ParquetStore(base_dir=_DATA_DIR / "raw/myshiptracking")
    store.save(records, "particulars.parquet")
    store.export_csv("particulars.parquet", "particulars.csv")
    logger.info(
        "Wrote %d particulars records; %d misses: %s",
        len(records),
        len(misses),
        ", ".join(misses) or "none",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
