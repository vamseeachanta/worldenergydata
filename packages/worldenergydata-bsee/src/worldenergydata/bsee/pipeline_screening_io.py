"""Deterministic screening exports, provenance QA and external payload storage."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from collections import Counter
from pathlib import Path

from worldenergydata.bsee.pipeline_screening_page import _qa_page
from worldenergydata.bsee.pipeline_screening_qa import engineering_qa, stratified_sample

_SOURCE = re.compile(r"^(PUBLIC|DERIVED|DEFAULT|UNKNOWN):[A-Za-z0-9_.-]+$")
_CLASSES = ("PUBLIC", "DERIVED", "DEFAULT", "UNKNOWN")


def qa_counts(rows):
    """Count data cells by provenance class; reject missing or orphan sources."""
    classes = Counter()
    fields = {key for key in rows[0] if not key.endswith("_source")} if rows else set()
    by_field = {key: dict.fromkeys(_CLASSES, 0) for key in sorted(fields)}
    expected = fields | {key + "_source" for key in fields}
    for row in rows:
        if set(row) != expected:
            raise ValueError("Every field requires exactly one sibling source column")
        for key in fields:
            source = row[key + "_source"]
            if not isinstance(source, str) or not _SOURCE.fullmatch(source):
                raise ValueError("Invalid source tag")
            if isinstance(row[key], float) and not math.isfinite(row[key]):
                raise ValueError("Nonfinite screening value")
            category = source.split(":", 1)[0]
            classes[category] += 1
            by_field[key][category] += 1
            if (row[key] is None) != (category == "UNKNOWN"):
                raise ValueError(
                    "Null values require UNKNOWN provenance, and UNKNOWN requires null"
                )
    return {
        **engineering_qa(rows),
        "rows": len(rows),
        "segments": len({row["segment_id"] for row in rows}),
        "source_classes": {key: classes[key] for key in _CLASSES},
        "by_field": by_field,
    }


def _csv_bytes(rows):
    stream = io.StringIO(newline="")
    bases = (
        sorted(key for key in rows[0] if not key.endswith("_source")) if rows else []
    )
    fields = [column for key in bases for column in (key, key + "_source")]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                key: str(value).lower() if isinstance(value, bool) else value
                for key, value in row.items()
            }
        )
    return stream.getvalue().encode("utf-8")


def _json_bytes(value):
    return (
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode()


def _write_once(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("Existing output contains different bytes")
        return
    with path.open("xb") as stream:
        stream.write(payload)
    if path.read_bytes() != payload:
        raise ValueError("Output readback differs")


def _source_metadata(entry):
    required = ("title", "publisher", "terms_of_use", "url", "retrieved_at")
    if any(not entry.get(key) for key in required):
        raise ValueError("Missing required source metadata")
    terms = entry["terms_of_use"]
    if (
        not isinstance(terms, dict)
        or not terms.get("statement")
        or not terms.get("url")
    ):
        raise ValueError("Missing required source metadata terms")
    value = dict(entry)
    value.setdefault(
        "source_version",
        "sha256:" + value["sha256"] if "sha256" in value else "unverified",
    )
    value.setdefault(
        "source_vintage",
        {
            "state": "unknown",
            "reason": "Publisher effective date is not established by this snapshot.",
        },
    )
    if value.get("source_id") == "usgs-layer-register":
        value["source_version"] = "USGS Data Series 146, 2006, edition 1.0"
        value["source_vintage"] = {
            "state": "unknown",
            "reason": "The release is dated 2006; assigned sample observation dates are not established.",
        }
    return value


def _payload_manifest(rows, revision, inputs, full):
    digest = hashlib.sha256(full).hexdigest()
    blob = f"data/worldenergydata/blobs/sha256/{digest[:2]}/{digest}.csv"
    manifest = {
        "schema_version": "1",
        "dataset_id": "pipeline-screening",
        "owner": "worldenergydata",
        "readiness_status": "partial",
        "intended_use": "screening_inventory_only",
        "source_freshness": {
            "state": "unverified",
            "reason": "Publisher effective dates and observation coverage are not qualified by the collector.",
        },
        "revision": revision["revision"],
        "rows": len(rows),
        "sample_rows": min(100, len(rows)),
        "inputs": [_source_metadata(entry) for entry in inputs],
        "payload": {
            "path": "full.csv",
            "path_scope": "external_destination",
            "bytes": len(full),
            "sha256": digest,
            "blob": blob,
            "disposition": "MOVE",
            "re_downloadable": False,
            "regenerator": "scripts/bsee/build_pipeline_screening.py",
            "second_copy_status": "not_verified",
        },
    }
    return manifest


def _validate_revision(revision):
    history = revision.get("history", [])
    if not history or history[-1].get("revision") != revision.get("revision"):
        raise ValueError("Declared revision differs from newest revision history row")


def write_artifacts(
    rows,
    output_dir,
    revision,
    *,
    repository_root,
    inputs=(),
    store_root=None,
    criteria=None,
    source_register=None,
    selection_counts=None,
):
    """Build a bounded sample and QA; keep full bytes in an external CAS layout."""
    _validate_revision(revision)
    counts = qa_counts(rows)
    counts["selection"] = selection_counts or {}
    output, repository = Path(output_dir).resolve(), Path(repository_root).resolve()
    if output == repository or repository in output.parents:
        raise ValueError("Full dataset must remain outside the repository")
    full = _csv_bytes(rows)
    manifest = _payload_manifest(rows, revision, inputs, full)
    blob = manifest["payload"]["blob"]
    if criteria is not None:
        manifest["criteria"] = criteria
    store = Path(store_root).resolve() if store_root is not None else output
    if store == repository or repository in store.parents:
        raise ValueError("External store must remain outside the repository")
    _write_once(store / blob, full)
    artifacts = {
        "sample.csv": _csv_bytes(stratified_sample(rows)),
        "qa.json": _json_bytes(counts),
        "qa.html": _qa_page(counts, revision),
    }
    if source_register is not None:
        artifacts["sources.json"] = _json_bytes(
            [_source_metadata(entry) for entry in source_register]
        )
    manifest["artifacts"] = [
        {
            "path": name,
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        for name, content in sorted(artifacts.items())
    ]
    artifacts["manifest.json"] = _json_bytes(manifest)
    for name, content in artifacts.items():
        _write_once(output / name, content)
    return manifest


def read_bulk_archive(path, kind, expected_sha256):
    """Read the segment member, preserving IDs and mapping the live point alias."""
    import zipfile

    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Input digest mismatch")
    members = {
        "permit": "mv_pipeperm_segments.txt",
        "location": "mv_pipelinelocation.txt",
    }
    if kind not in members:
        raise ValueError("Unknown bulk archive kind")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = [
            name for name in archive.namelist() if Path(name).name == members[kind]
        ]
        if len(names) != 1:
            raise ValueError("Expected one pipeline bulk member")
        with archive.open(names[0]) as stream:
            reader = csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"))
            required = {
                "permit": {
                    "SEGMENT_NUM",
                    "STATUS_CODE",
                    "PPL_SIZE_CODE",
                    "PROD_CODE",
                    "SEG_LENGTH",
                    "MAOP_PRSS",
                },
                "location": {"SEGMENT_NUM", "ASBUILT_SEQ_NUM", "LATITUDE", "LONGITUDE"},
            }[kind]
            if not reader.fieldnames or not required <= set(reader.fieldnames):
                raise ValueError("Missing required bulk header columns")
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ValueError("Duplicate bulk header")
            for record in reader:
                if kind == "location":
                    record["POINT_NUM"] = record["ASBUILT_SEQ_NUM"]
                yield record


def validate_rows(rows, schema, defaults):
    """Validate the output contract, including default-key traceability."""
    qa_counts(rows)
    definitions = schema["fields"]
    expected = set(definitions) | {key + "_source" for key in definitions}
    for row in rows:
        if set(row) != expected:
            raise ValueError("Schema field coverage differs")
        for field, definition in definitions.items():
            source = row[field + "_source"]
            if (
                source.startswith("DEFAULT:")
                and source.split(":", 1)[1] not in defaults
            ):
                raise ValueError("Unknown default key")
            value = row[field]
            if value is None:
                if not definition["nullable"]:
                    raise ValueError("Required field is unknown")
                continue
            kind = definition["type"]
            valid = {
                "string": isinstance(value, str),
                "boolean": isinstance(value, bool),
                "integer": isinstance(value, int) and not isinstance(value, bool),
                "number": isinstance(value, (int, float))
                and not isinstance(value, bool),
            }
            if kind not in valid or not valid[kind]:
                raise ValueError("Output field type differs")


def fetch_payload(manifest, store, destination):
    """Restore external bytes only after checking the relative locator and digest."""
    from pathlib import PurePosixPath

    payload = manifest["payload"]
    locator = PurePosixPath(payload["blob"])
    if locator.is_absolute() or ".." in locator.parts or "\\" in payload["blob"]:
        raise ValueError("Payload locator must be relative")
    root = Path(store).resolve()
    blob = (root / locator).resolve()
    if root not in blob.parents:
        raise ValueError("Payload locator must remain relative to storage")
    content = blob.read_bytes()
    if (
        len(content) != payload["bytes"]
        or hashlib.sha256(content).hexdigest() != payload["sha256"]
    ):
        raise ValueError("Payload digest or size mismatch")
    _write_once(Path(destination), content)
    return Path(destination)


def cached_station_summaries(histories, store, criteria, stations=()):
    """Reuse completed station computations only for identical inputs and code."""
    from worldenergydata.bsee.pipeline_screening import _station_record_summary

    summaries = {}
    positions = {s.station_id: s for s in stations}
    for station_id, records in sorted(histories.items()):
        station = positions.get(station_id)
        atlantic = station is None or (
            -100 <= station.longitude <= 20 and 0 <= station.latitude <= 65
        )
        values = [
            [r.observation_time.isoformat(), r.wave_height_m, r.dominant_wave_period_s]
            for r in records
        ]
        key = hashlib.sha256(
            _json_bytes(
                {
                    "station": station_id,
                    "records": values,
                    "criteria": criteria,
                    "atlantic": atlantic,
                }
            )
        ).hexdigest()
        path = Path(store) / "station-results" / (key + ".json")
        if path.exists():
            saved = json.loads(path.read_text())
            if (
                saved["key"] != key
                or saved["sha256"]
                != hashlib.sha256(_json_bytes(saved["result"])).hexdigest()
            ):
                raise ValueError("Completed station digest mismatch")
            summary = saved["result"]
            state = "reused"
        else:
            summary = _station_record_summary(records, atlantic=atlantic)
            saved = {
                "key": key,
                "result": summary,
                "sha256": hashlib.sha256(_json_bytes(summary)).hexdigest(),
            }
            _write_once(path, _json_bytes(saved))
            state = "retained"
        summaries[station_id] = summary
        print(f"Station {station_id}: summary {state}", flush=True)
    return summaries
