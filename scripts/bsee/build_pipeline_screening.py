#!/usr/bin/env python3
"""Build a sourced pipeline screening inventory from retained public snapshots."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

from worldenergydata.bsee.pipeline_screening import (
    _active_permits,
    build_rows,
    enrich_rows,
    read_ndbc_stations,
    station_environment,
)
from worldenergydata.bsee.pipeline_screening_io import (
    _json_bytes,
    _write_once,
    cached_station_summaries,
    read_bulk_archive,
    validate_rows,
    write_artifacts,
)
from worldenergydata.bsee.pipeline_screening_sources import (
    fetch_ndbc_histories,
    retained_input_refs,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "data/modules/pipeline/screening"


def _arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "permit-zip",
        "location-zip",
        "station-xml",
        "source-ledger",
        "output",
        "cache",
        "execution-record",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--sediment-zip", type=Path)
    parser.add_argument("--status-dictionary", type=Path)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use retained responses; missing histories remain unknown",
    )
    return parser.parse_args()


def _criteria(path):
    files = [
        CONFIG / name for name in ("schema.yaml", "defaults.yaml", "revision.json")
    ]
    current = {
        name + "_sha256": hashlib.sha256(file.read_bytes()).hexdigest()
        for name, file in zip(("schema", "defaults", "revision"), files)
    }
    code = [
        Path(__file__),
        *(
            ROOT / "packages/worldenergydata-bsee/src/worldenergydata/bsee" / name
            for name in (
                "pipeline_screening.py",
                "pipeline_screening_io.py",
                "pipeline_screening_sources.py",
            )
        ),
    ]
    code.extend(
        ROOT / relative
        for relative in (
            "packages/worldenergydata-bsee/src/worldenergydata/bsee/data/schemas/pipeline.py",
            "packages/worldenergydata-bsee/src/worldenergydata/bsee/data/models/pipeline.py",
            "packages/worldenergydata-bsee/src/worldenergydata/bsee/data/scrapers/bsee_web.py",
            "packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/ndbc_client.py",
            "packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/eva.py",
        )
    )
    current["code_sha256"] = {
        file.relative_to(ROOT).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in code
    }
    if path.exists():
        saved = json.loads(path.read_text())
        if any(saved[key] != value for key, value in current.items()):
            raise ValueError("Criteria or code digest mismatch")
        return saved
    current["recorded_at"] = datetime.now(timezone.utc).isoformat()
    _write_once(path, _json_bytes(current))
    current["first_run_started_at"] = datetime.now(timezone.utc).isoformat()
    path.write_bytes(_json_bytes(current))
    return current


def _runtime_paths(store):
    paths = {
        "METOCEAN_CACHE_CACHE_PATH": "runtime/cache",
        "METOCEAN_STORAGE_BASE_PATH": "runtime",
        "METOCEAN_STORAGE_RAW_PATH": "runtime/raw",
        "METOCEAN_STORAGE_PROCESSED_PATH": "runtime/processed",
        "METOCEAN_LOG_FILE_PATH": "runtime/metocean.log",
    }
    for key, relative in paths.items():
        os.environ[key] = str(store / relative)


def _input_refs(args):
    ledger = {
        entry["file"]: entry for entry in json.loads(args.source_ledger.read_text())
    }
    from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper

    expected_urls = {
        args.permit_zip.name: BSEEWebScraper.URLS["pipeline_permit"],
        args.location_zip.name: BSEEWebScraper.URLS["pipeline_location"],
    }
    if args.status_dictionary:
        expected_urls[args.status_dictionary.name] = (
            "https://www.data.bsee.gov/Pipeline/PipelinePermits/FieldValues.aspx?domain=STATUS_CODES"
        )
    refs = []
    paths = [
        (args.permit_zip, "bsee-data-center"),
        (args.location_zip, "bsee-data-center"),
        (args.station_xml, "noaa-ndbc"),
    ]
    if args.sediment_zip:
        paths.append((args.sediment_zip, "usgs-layer-register"))
    if args.status_dictionary:
        paths.append((args.status_dictionary, "bsee-data-center"))
    for path, source_id in paths:
        entry = ledger[path.name]
        if (
            path.name in expected_urls
            and entry.get("url") is not None
            and entry["url"] != expected_urls[path.name]
        ):
            raise ValueError("Public bulk source address differs from refresh code")
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != entry["sha256"] or len(raw) != entry["bytes"]:
            raise ValueError("Input digest mismatch")
        blob = f"data/worldenergydata/blobs/sha256/{digest[:2]}/{digest}{path.suffix}"
        _write_once(args.cache / blob, raw)
        refs.append(
            {
                "path": "sources/" + path.name,
                "blob": blob,
                "bytes": len(raw),
                "sha256": digest,
                "source_id": source_id,
            }
        )
    return ledger, refs


def _sediment(path):
    if path is None:
        return []
    with zipfile.ZipFile(path) as archive:
        names = [
            name
            for name in archive.namelist()
            if Path(name).name.upper() == "GMX_EXT.TXT"
        ]
        if len(names) != 1:
            raise ValueError("Expected one public sediment table")
        return list(
            csv.DictReader(io.StringIO(archive.read(names[0]).decode("cp1252")))
        )


def _nearest_ids(rows, stations):
    ids = set()
    empty = {}
    for row in rows[::2]:
        station = station_environment(
            row["midpoint_latitude_deg"],
            row["midpoint_longitude_deg"],
            stations,
            {},
            empty,
        )
        if station["station_id"] is not None:
            ids.add(station["station_id"])
    return ids


def _core_rows(args, defaults, ledger):
    permits = list(
        read_bulk_archive(
            args.permit_zip, "permit", ledger[args.permit_zip.name]["sha256"]
        )
    )
    active = {permit.SEGMENT_NUM for permit, _ in _active_permits(permits, defaults)}
    locations = (
        row
        for row in read_bulk_archive(
            args.location_zip, "location", ledger[args.location_zip.name]["sha256"]
        )
        if row["SEGMENT_NUM"].strip() in active
    )
    rows = build_rows(permits, locations, defaults)
    print(
        f"Core: {len(rows)} case rows; {len(active)} screening-selected segments",
        flush=True,
    )
    return rows


def _history_provenance(args, defaults, ids, ledger, refs):
    source_register = [
        {**ledger[Path(ref["path"]).name], "source_id": ref["source_id"]}
        for ref in refs
    ]
    refs.extend(
        retained_input_refs(args.cache, ids, defaults["history_years"]["value"])
    )
    urls = {
        f"https://www.ndbc.noaa.gov/view_text_file.php?filename={station_id}h{year}.txt.gz&dir=data/historical/stdmet/"
        for station_id in ids
        for year in defaults["history_years"]["value"]
    }
    source_register.extend(
        entry
        for path in sorted((args.cache / "responses").glob("*.json"))
        if (entry := json.loads(path.read_text()))["url"] in urls
    )
    return source_register


def main():
    args = _arguments()
    for path in (args.output, args.cache, args.execution_record):
        if path.resolve() == ROOT or ROOT in path.resolve().parents:
            raise ValueError("Full output and runtime state require external locations")
    criteria = _criteria(args.execution_record)
    _runtime_paths(args.cache.resolve())
    defaults = yaml.safe_load((CONFIG / "defaults.yaml").read_text())
    schema = yaml.safe_load((CONFIG / "schema.yaml").read_text())
    revision = json.loads((CONFIG / "revision.json").read_text())
    ledger, refs = _input_refs(args)
    if args.status_dictionary and (
        ledger[args.status_dictionary.name]["sha256"]
        != defaults["status_meanings"]["basis_sha256"]
    ):
        raise ValueError("Status dictionary input digest mismatch")
    rows = _core_rows(args, defaults, ledger)
    stations = read_ndbc_stations(args.station_xml)
    ids = _nearest_ids(rows, stations)
    histories = fetch_ndbc_histories(
        ids,
        defaults["history_years"]["value"],
        args.cache,
        allow_network=not args.offline,
    )
    source_register = _history_provenance(args, defaults, ids, ledger, refs)
    summaries = cached_station_summaries(histories, args.cache, criteria)
    rows = enrich_rows(
        rows, defaults, stations, histories, _sediment(args.sediment_zip), summaries
    )
    validate_rows(rows, schema, defaults)
    manifest = write_artifacts(
        rows,
        args.output,
        revision,
        repository_root=ROOT,
        inputs=refs,
        store_root=args.cache,
        criteria=criteria,
        source_register=source_register,
    )
    print(
        f"Export: {manifest['rows']} rows; SHA-256 {manifest['payload']['sha256']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
