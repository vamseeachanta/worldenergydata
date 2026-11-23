"""Regional lookup of station-level empirical wave statistics."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from worldenergydata.metocean.empirical import EXPECTED_UNITS, summarize_observations
from worldenergydata.metocean.source_register import load_register

_RAW_SHA256 = re.compile(r"[0-9a-fA-F]{64}")


def _wave_inputs(records, station_regions, digests):
    """Record source-file lineage while streaming validated rows to the summary."""
    families = {s["id"]: s["family"] for s in load_register()["sources"]}
    for row in records:
        station, source = row.get("station_id"), row.get("source_id")
        if not isinstance(station, str) or station not in station_regions:
            raise ValueError(f"No region mapping for station {station}")
        if not isinstance(source, str) or source not in families:
            raise ValueError(f"Unregistered observation source: {source}")
        if families[source].endswith(("_forecast", "_hindcast")):
            raise ValueError(f"Modelled source cannot supply observations: {source}")
        if row.get("variable") not in EXPECTED_UNITS:
            raise ValueError("Expected a wave observation variable")
        digest = row.get("raw_sha256")
        if not isinstance(digest, str) or not _RAW_SHA256.fullmatch(digest):
            raise ValueError("raw_sha256 must contain 64 hexadecimal characters")
        canonical = digest.lower()
        digests[station, source].add(canonical)
        yield row if canonical == digest else {**row, "raw_sha256": canonical}


def build_site_climate_index(
    records: Iterable[Mapping[str, Any]],
    station_regions: Mapping[str, str],
    *,
    station_metadata: Mapping[str, Any],
    unique_timestamps: bool = False,
) -> dict:
    """Index verified wave observations using caller-assigned region labels.

    Supply the decoded first-set station metadata and rows from read_rows for
    the selected archive versions. Digest lists identify input files for a
    station and source, including candidates in a unique-timestamp comparison.
    """
    if not isinstance(unique_timestamps, bool):
        raise ValueError("unique_timestamps must be a boolean")
    station_ids = {station["id"] for station in station_metadata["stations"]}
    for station, region in station_regions.items():
        if station not in station_ids:
            raise ValueError(f"Unlisted station: {station}")
        if not isinstance(region, str) or not region.strip():
            raise ValueError(f"Missing region for station {station}")

    digests = defaultdict(set)
    inputs = _wave_inputs(records, station_regions, digests)
    entries = defaultdict(list)
    for summary in summarize_observations(inputs, unique_timestamps=unique_timestamps):
        station, source = summary["station_id"], summary["source_id"]
        entries[station_regions[station], station, source].append(summary)

    return {
        "schema_version": 1,
        "readiness": "observations_only",
        "duplicate_policy": (
            "unique_timestamps" if unique_timestamps else "original_rows"
        ),
        "entries": [
            {
                "region": region,
                "station_id": station,
                "source_id": source,
                "input_raw_sha256": sorted(digests[station, source]),
                "summaries": entries[region, station, source],
            }
            for region, station, source in sorted(entries)
        ],
    }
