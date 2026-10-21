"""Deterministic, self-contained reporting of BSEE record characterisation."""

from __future__ import annotations

import csv
import hashlib
import html
import json
from datetime import datetime
from pathlib import Path


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def json_bytes(value):
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode()


def format_value(value):
    if value is None:
        return "not established"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def _text(value):
    return html.escape(format_value(value), quote=True)


def validate_run_record(record, criteria_digest):
    if record["criteria_sha256"] != criteria_digest:
        raise ValueError("criteria digest differs from the recorded bytes")
    start = datetime.fromisoformat(
        record["first_run_started_at"].replace("Z", "+00:00")
    )
    recorded = datetime.fromisoformat(
        record["criteria_recorded_at"].replace("Z", "+00:00")
    )
    if recorded.tzinfo is None or start.tzinfo is None or recorded >= start:
        raise ValueError("criteria recording must precede the first run")


def _validate_revision(revision):
    history = revision["history"]
    if not history or history[-1]["revision"] != revision["revision"]:
        raise ValueError("newest revision history row must match the declared revision")
    if len({x["revision"] for x in history}) != len(history):
        raise ValueError("revision history contains duplicate issues")
    return history


def _table(rows, columns, caption):
    head = "".join(f"<th>{_text(label)}</th>" for key, label in columns)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{_text(r.get(key))}</td>" for key, label in columns)
        + "</tr>"
        for r in rows
    )
    if not rows:
        body = f'<tr><td colspan="{len(columns)}">No classified records in the supplied data.</td></tr>'
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div><p class="caption">{_text(caption)}</p>'


def _chart(rows, category, caption):
    totals = {}
    for row in rows:
        totals[row[category]] = totals.get(row[category], 0) + row["records"]
    if not totals:
        return "<p>No dated or undated records supplied.</p>"
    maximum = max(totals.values())
    bars = ""
    for index, (key, count) in enumerate(sorted(totals.items())):
        y = index * 28 + 20
        width = 420 * count / maximum if maximum else 0
        bars += f'<text x="0" y="{y}">{_text(key)}</text><rect x="100" y="{y - 13}" width="{width:.1f}" height="17"/><text x="530" y="{y}">{count}</text>'
    return f'<figure><svg role="img" aria-label="{_text(caption)}" viewBox="0 0 660 {len(totals) * 28 + 10}">{bars}</svg><figcaption>{_text(caption)}</figcaption></figure>'


def _summary(result):
    items = "".join(
        f'<li>{_text(key.replace("_", " "))}: <strong data-metric="{key}" data-value="{_text(value)}">{_text(value)}</strong></li>'
        for key, value in result["summary"].items()
    )
    return (
        '<section id="summary"><h2>Executive Summary</h2><p>The supplied snapshots establish record counts and descriptive distributions.</p><ul>'
        + items
        + "</ul><p>These counts do not establish intervention event rates or completion design performance.</p></section>"
    )


def _revision(revision):
    rows = _validate_revision(revision)
    return (
        '<section id="revision-history"><h2>Revision history</h2>'
        + _table(
            rows,
            [
                ("revision", "Revision"),
                ("date", "Date"),
                ("change", "What changed and why"),
            ],
            "Revision record retained with the analysis criteria.",
        )
        + "</section>"
    )


def _catalogue(result):
    rows = result.get("catalogue", [])
    columns = [
        ("publisher_name", "Dataset"),
        ("member", "Table"),
        ("status", "Availability"),
        ("retrieved_at", "Retrieved UTC"),
        ("years", "Years covered"),
        ("record_count", "Records"),
        ("sha256", "File SHA-256"),
    ]
    body = _table(
        rows,
        columns,
        "Catalogue of the exact source files used, unavailable downloads and held samples examined.",
    )
    details = "".join(
        f'<details><summary>{_text(r["member"])}</summary><p>Source: <a href="{_text(r["url"])}">{_text(r["url"])}</a></p><p>{_text(r.get("reason", ""))}</p><p>Fields: {_text(", ".join(r.get("fields", [])))}</p><p>Member SHA-256: {_text(r.get("member_sha256"))}</p>'
        + (
            f'<p>Archive SHA-256: {_text(r["archive_sha256"])}</p>'
            if "archive_sha256" in r
            else ""
        )
        + "</details>"
        for r in rows
    )
    return (
        '<section id="catalogue"><h2>Data catalogue</h2>'
        + body
        + details
        + "</section>"
    )


def _coverage(result):
    rows = [
        {"measure": k.replace("_", " "), "count": v}
        for k, v in result["quality"].items()
    ]
    return (
        '<section id="limits"><h2>Data limits and coverage</h2><ul>'
        + "".join(f"<li>{_text(x)}</li>" for x in result["limits"])
        + "</ul>"
        + _table(
            rows,
            [
                ("measure", "Coverage or consistency measure"),
                ("count", "Records or API12 groups"),
            ],
            "Missing and conflicting values are reported without substituting a true zero.",
        )
        + "</section>"
    )


def _completion_distributions(result):
    strata = [
        ("field", "Field code"),
        ("water_depth_band", "Water depth band (ft)"),
        ("era", "Calendar era"),
        ("status", "Completion status code"),
        ("records", "Records"),
    ]
    eor = [
        ("field", "Field code"),
        ("water_depth_band", "Water depth band (ft)"),
        ("era", "Borehole-status era"),
        ("subsea_flag", "Reported subsea flag"),
        ("records", "Records"),
    ]
    body = "<section><h2>Completion characterisation</h2><p>Completion design types are not established. Status distributions use completion dates; subsea flags use EOR borehole-status cohorts and remain separate.</p>"
    body += _chart(
        result["completions_by_year"],
        "year",
        "Completion records by recorded completion year; counts, not installation rates.",
    )
    body += _table(
        result["completion_strata"],
        strata,
        "API Lookup completion status by field, water depth and completion-date era.",
    )
    body += _table(
        result["eor_completion_strata"],
        eor,
        "EOR reported subsea flags; no historical design-type attribution is inferred.",
    )
    return body + "</section>"


def _activity_distributions(result):
    annual = [
        ("year", "Year or unknown"),
        ("code", "Raw operation code"),
        ("records", "Records"),
        ("wells", "Recorded API12 groups"),
    ]
    body = "<section><h2>Intervention activity characterisation</h2>"
    body += _chart(
        result["eor_by_year_type"], "code", "EOR records by published operation code."
    )
    body += _table(
        result["eor_by_year_type"],
        annual,
        "EOR counts by borehole-status year and operation code; these are not intervention event years.",
    )
    body += _table(
        result["war_by_year_type"],
        annual,
        "WAR counts by report-start year and raw activity code.",
    )
    body += _table(
        result["war_vocabulary"],
        [
            ("code", "Code"),
            ("label", "Supported label"),
            ("provenance", "Meaning provenance"),
        ],
        "WAR labels from the canonical repository vocabulary; unknown meanings remain unlabelled.",
    )
    body += _table(
        result.get("eor_vocabulary", []),
        [("VALUE", "Code"), ("ABBREVIATION", "Published operation label")],
        "EOR labels from the operation-code member of the supplied source archive.",
    )
    return body + "</section>"


def _outliers(result):
    wells = sorted(
        (r for r in result["per_well"] if r["outlier"]),
        key=lambda r: (-r["workover_records"], r["api12"]),
    )
    fields = result["per_field"]
    limits = result["outliers"]
    body = "<section><h2>Record-count frequencies and outliers</h2><p>Well flags compare EOR workover record counts. Field flags compare workover records per recorded well. Strict quantile cutoffs exclude ties. Unknown fields do not enter field comparisons.</p>"
    for kind in ["well", "field"]:
        thresholds = limits[kind + "_thresholds"]
        display = (
            ", ".join(format_value(x) for x in thresholds)
            if thresholds
            else "not established"
        )
        body += f"<p>{kind.title()} lower and upper thresholds: {_text(display)}.</p>"
    body += f"<p>First {min(20, len(wells))} of {len(wells)} flagged well identifiers are shown; all well counts are retained in per_well.csv.</p>"
    body += _table(
        wells[:20],
        [
            ("api12", "API12"),
            ("field", "Field code"),
            ("workover_records", "Workover records"),
            ("outlier", "Count flag"),
        ],
        "Highest-count flagged wells in the supplied reporting population; no operating judgment is implied.",
    )
    body += _table(
        fields,
        [
            ("field", "Field code"),
            ("recorded_wells", "Recorded wells"),
            ("workover_records", "Workover records"),
            ("workover_records_per_recorded_well", "Records per recorded well"),
            ("outlier", "Frequency flag"),
        ],
        "Field record frequencies; unequal observation periods preclude rate comparisons.",
    )
    return body + "</section>"


def _activity_strata(result):
    if "activity_strata" not in result:
        return ""
    classification = result["operator_classification"]
    body = (
        '<section id="activity-strata"><h2>Area and operator-class record counts</h2>'
        "<p>Each source is partitioned separately by its declared year, bottom area, "
        "operator class and raw code. Completion codes describe status. "
        "Distinct well counts are not additive across cells.</p>"
        f'<p>Operator classification: {_text(classification["status"])}. '
        f'{_text(classification["basis"])}</p><ul>'
        + "".join(f"<li>{_text(s)}</li>" for s in classification["sources"])
        + "</ul>"
    )
    for source, rows in sorted(result["activity_strata"].items()):
        body += f"<h3>{_text(source.upper())}</h3>"
        body += _chart(rows, "area", f"{source.upper()} records by bottom area code.")
        if classification["status"] == "SUPPLIED":
            body += _chart(
                rows,
                "operator_class",
                f"{source.upper()} records by supplied operator class.",
            )
        body += _table(
            rows,
            [
                ("year", "Year or unknown"),
                ("area", "Bottom area code"),
                ("operator_class", "Operator class"),
                ("code", "Raw code"),
                ("records", "Records"),
                ("wells", "Recorded API12 groups"),
            ],
            "All records retained, including unknown dimensions; cell well counts exclude missing APIs.",
        )
    return body + "</section>"


def render_report(
    result,
    revision,
    *,
    title="Completion and intervention activity characterisation",
):
    _validate_revision(revision)
    style = "body{font:16px system-ui,sans-serif;max-width:1200px;margin:auto;padding:2rem;color:#243746;background:#fff}h1,h2{color:#243746}table{border-collapse:collapse;width:100%;font-size:13px}td,th{border:1px solid #ccd4dc;padding:6px;text-align:left;overflow-wrap:anywhere}th{background:#eef4f5}.table-wrap{overflow:auto}.caption,figcaption{font-size:13px;color:#475569}svg{width:100%;max-width:780px}svg rect{fill:#167d8d}svg text{font-size:13px}details{margin:1rem 0}"
    title = _text(title)
    start = f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{title}</title><style>{style}</style></head><body data-revision="{_text(revision["revision"])}"><h1>{title}</h1><p>Revision {_text(revision["revision"])}. Public BSEE snapshots; descriptive record counts.</p>'
    method = (
        '<section id="method"><h2>Method and parameters</h2>'
        + _table(
            [{"measure": k, "basis": v} for k, v in result["method"].items()],
            [("measure", "Measure"), ("basis", "Basis")],
            "All frequencies are record counts over the supplied archive.",
        )
        + "<p>Parameters: "
        + _text(json.dumps(result["parameters"], sort_keys=True))
        + "</p></section>"
    )
    return (
        start
        + _summary(result)
        + _revision(revision)
        + method
        + _catalogue(result)
        + _completion_distributions(result)
        + _activity_distributions(result)
        + _activity_strata(result)
        + _outliers(result)
        + _coverage(result)
        + "</body></html>\n"
    )


def _write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_results(result, output):
    separate = {"per_well", "war_per_well", "completion_strata"}
    compact = {k: v for k, v in result.items() if k not in separate}
    for key in sorted(separate):
        compact[key + "_file"] = key + ".csv"
    # Compact encoding and tabular sidecars retain the complete distributions
    # within the file-size hook limit without rounding calculation values.
    (output / "results.json").write_text(
        json.dumps(
            compact,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_csv(
        output / "completion_strata.csv",
        ["field", "water_depth_band", "era", "status", "records"],
        result["completion_strata"],
    )


def write_products(result, revision, output_dir, provenance=None):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.html").write_text(
        render_report(result, revision), encoding="utf-8", newline="\n"
    )
    _write_results(result, output)
    _write_csv(
        output / "per_well.csv",
        [
            "api12",
            "eor_records",
            "workover_records",
            "field",
            "candidate_war_records",
            "outlier",
        ],
        result["per_well"],
    )
    _write_csv(
        output / "war_per_well.csv",
        ["api12", "war_records", "candidate_war_records", "field"],
        result["war_per_well"],
    )
    manifest = {
        "revision": revision["revision"],
        "summary": result["summary"],
        "provenance": provenance or {},
        "outputs": [
            {
                "file": name,
                "size_bytes": (output / name).stat().st_size,
                "sha256": digest(output / name),
            }
            for name in [
                "report.html",
                "results.json",
                "per_well.csv",
                "war_per_well.csv",
                "completion_strata.csv",
            ]
        ],
    }
    (output / "manifest.json").write_bytes(json_bytes(manifest))
    return manifest
