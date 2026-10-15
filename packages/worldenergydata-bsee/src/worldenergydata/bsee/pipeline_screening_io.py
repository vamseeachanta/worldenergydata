"""Deterministic screening exports, provenance QA and external payload storage."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
import re
from collections import Counter
from pathlib import Path

_SOURCE = re.compile(r"^(PUBLIC|DERIVED|DEFAULT):[A-Za-z0-9_.-]+$")
_CLASSES = ("PUBLIC", "DERIVED", "DEFAULT")


def qa_counts(rows):
    """Count data cells by provenance class; reject missing or orphan sources."""
    classes = Counter()
    fields = {key for key in rows[0] if not key.endswith("_source")} if rows else set()
    by_field = {key: dict.fromkeys((*_CLASSES, "unknown"), 0) for key in sorted(fields)}
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
            by_field[key]["unknown"] += row[key] is None
    return {
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


def _table(headers, rows, caption):
    headings = "".join(f"<th>{html.escape(str(value))}</th>" for value in headers)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{html.escape(str(value))}</td>" for value in row)
        + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{headings}</tr></thead><tbody>{body}</tbody></table><p>{html.escape(caption)}</p>"


def _qa_page(counts, revision):
    history = _table(
        ("Revision", "Date", "What changed", "Why"),
        [
            [row[key] for key in ("revision", "date", "changed", "why")]
            for row in revision["history"]
        ],
        "Table 1. Revision history.",
    )
    classes = _table(
        ("Source class", "Cells (count)"),
        counts["source_classes"].items(),
        "Table 2. Data cells by source class; source columns are excluded.",
    )
    fields = _table(
        (
            "Field",
            "Public (cells)",
            "Derived (cells)",
            "Default (cells)",
            "Unknown (cells)",
        ),
        [
            [key, *(values[k] for k in (*_CLASSES, "unknown"))]
            for key, values in counts["by_field"].items()
        ],
        "Table 3. Provenance and unknown values by field. Unknown is a null, distinct from zero.",
    )
    return (
        '<!doctype html>\n<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        "<title>Pipeline screening database QA</title><style>body{font:16px system-ui;margin:2rem;max-width:90rem;color:#17212b}"
        "table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:.4rem;text-align:left}h2{margin-top:2rem}</style>"
        f'<body data-revision="{html.escape(revision["revision"])}"><h1>Pipeline screening database QA</h1>'
        f'<h2>Summary</h2><p>{counts["rows"]} case rows represent {counts["segments"]} screening-selected segments. '
        "This is a screening input inventory. It does not establish installed properties or stability acceptance.</p>"
        "<h2>Revision history</h2>"
        + history
        + "<h2>Source counts</h2>"
        + classes
        + fields
        + "<h2>Limits</h2><ul><li>Published abandoned, removed and out meanings supplement the existing inactive-status rule. Dictionary-undefined codes are excluded. Cancelled, combined and proposed statuses can remain under this exclusion rule; selection does not establish installation or present operation. Identical permit engineering joins collapse; conflicting values reject.</li>"
        "<li>Geometry uses published coordinates and spherical distances; no datum transformation is performed.</li><li>Maximum depth cannot establish minimum depth; absent burial design is not exposed design.</li>"
        "<li>Nominal size can be an OD proxy. Hoop sizing includes no design factor, corrosion allowance, tolerance or collapse check.</li>"
        "<li>Local schedule lookup does not establish installed wall. Public outputs require source rights and edition qualification.</li>"
        "<li>NDBC fits are independent marginal extrapolations. Retained record span does not establish coverage, coincident design conditions or site transfer.</li>"
        "<li>Nearest sediment texture does not establish route geotechnical properties. Sample distance is retained; friction is a labelled assumption.</li>"
        "<li>Unknown coating, concrete and contents properties require an evidenced basis before use in stability calculations.</li>"
        "<li>Current and wave direction defaults do not establish seabed storm conditions.</li></ul></body></html>\n"
    ).encode()


def _source_metadata(entry):
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
            "path": "data/modules/pipeline/screening/full.csv",
            "bytes": len(full),
            "sha256": digest,
            "blob": blob,
            "disposition": "MOVE",
            "re_downloadable": True,
            "regenerator": "scripts/bsee/build_pipeline_screening.py",
            "second_copy_status": "not_verified",
        },
    }
    return manifest


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
):
    """Build a bounded sample and QA; keep full bytes in an external CAS layout."""
    history = revision.get("history", [])
    if not history or history[-1].get("revision") != revision.get("revision"):
        raise ValueError("Declared revision differs from newest revision history row")
    counts = qa_counts(rows)
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
        "sample.csv": _csv_bytes(rows[:100]),
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
            if not reader.fieldnames or "SEGMENT_NUM" not in reader.fieldnames:
                raise ValueError("Missing pipeline identifier header")
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ValueError("Duplicate bulk header")
            for record in reader:
                if kind == "location":
                    record["POINT_NUM"] = record.get("POINT_NUM") or record.get(
                        "ASBUILT_SEQ_NUM"
                    )
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


def cached_station_summaries(histories, store, criteria):
    """Reuse completed station computations only for identical inputs and code."""
    from worldenergydata.bsee.pipeline_screening import _station_record_summary

    summaries = {}
    for station_id, records in sorted(histories.items()):
        values = [
            [r.observation_time.isoformat(), r.wave_height_m, r.dominant_wave_period_s]
            for r in records
        ]
        key = hashlib.sha256(
            _json_bytes(
                {"station": station_id, "records": values, "criteria": criteria}
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
            summary = _station_record_summary(records)
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
