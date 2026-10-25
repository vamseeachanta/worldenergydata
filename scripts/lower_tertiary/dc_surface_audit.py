"""Compare retained local D&C snapshots with the displayed source population.

Issue #1079 (2026), "Surfaces": exact count and membership comparisons only.
Matching snapshots establish consistency, not day-basis correctness, weekly
coverage, vintage-category validity, or external publication readiness.
No generator, network request, or publication is performed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path

LOCAL_SURFACES = {
    "validation": Path("reports/lower_tertiary/wo-april-2026-validation.md"),
    "listing": Path("reports/lower_tertiary/wo-april-2026-per-well-dc.md"),
    "drilldown": Path("reports/lower_tertiary/dc-drilldown.html"),
    "vintage": Path("reports/lower_tertiary/data/dc_vintage_diff.csv"),
}
PENDING = "NOT_EVALUATED"


def _plain(value):
    return re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value).replace("*", "").strip()


def _number(value):
    if value is None or value == "":
        return None
    plain = _plain(str(value))
    if "," in plain and not re.fullmatch(
        r"[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?", plain
    ):
        raise ValueError("invalid snapshot count")
    try:
        number = Decimal(plain.replace(",", ""))
    except InvalidOperation as error:
        raise ValueError("invalid snapshot count") from error
    if not number.is_finite() or number < 0 or number != number.to_integral_value():
        raise ValueError("invalid snapshot count")
    return int(number)


def _tables(text, required):
    """Read the named generated Markdown columns, excluding aggregate footers."""
    header = None
    for line in text.splitlines():
        if not line.startswith("|"):
            header = None
            continue
        cells = [_plain(c) for c in line.strip().strip("|").split("|")]
        if required.issubset(cells):
            header = cells
        elif header and cells and not re.fullmatch(r"[-: ]+", cells[0]):
            if len(cells) != len(header):
                raise ValueError("invalid snapshot table")
            if not cells[0].startswith("Total"):
                yield dict(zip(header, cells))


def _index(rows, key, columns, *, text_columns=()):
    result = {}
    for row in rows:
        identifier = row[key]
        if (
            not isinstance(identifier, str)
            or not identifier.strip()
            or identifier in result
        ):
            raise ValueError("invalid or duplicate snapshot identity")
        result[identifier] = {
            name: row[column] if name in text_columns else _number(row[column])
            for name, column in columns.items()
        }
    if not result:
        raise ValueError("empty snapshot population")
    return result


def _compare(expected, actual, level):
    findings = []
    for key in sorted(expected.keys() | actual.keys()):
        if key not in expected or key not in actual:
            findings.append(
                {
                    "level": level,
                    "key": key,
                    "kind": "extra" if key in actual else "missing",
                }
            )
            continue
        for metric, value in expected[key].items():
            if actual[key].get(metric) != value:
                findings.append(
                    {
                        "level": level,
                        "key": key,
                        "kind": "value",
                        "metric": metric,
                        "expected": value,
                        "actual": actual[key].get(metric),
                    }
                )
    return findings


def _expected(bores):
    by_bore = {
        b["api12"]: {"development": b["development"], **b["before"]} for b in bores
    }
    by_dev = {}
    for name in sorted({b["development"] for b in bores}):
        group = [b for b in bores if b["development"] == name]
        # Issue #1079: full-development totals need every contributing bore.
        by_dev[name] = {
            "bores": len(group),
            **{
                metric: None if any(v is None for v in values) else sum(values)
                for metric in ("drilling_days", "completion_days", "dc_days")
                for values in [[b["before"][metric] for b in group]]
            },
        }
    return by_bore, by_dev


def _markdown(surface, text, by_bore, by_dev):
    if surface == "validation":
        columns = {"bores": "WED bores", "dc_days": "WED D&C"}
        return _compare(
            {name: {key: row[key] for key in columns} for name, row in by_dev.items()},
            _index(
                _tables(text, {"Development", *columns.values()}),
                "Development",
                columns,
            ),
            "development",
        )
    columns = {
        "bores": "Bores (wed)",
        "drilling_days": "Drilling",
        "completion_days": "Completion",
        "dc_days": "D&C (wed)",
    }
    findings = _compare(
        by_dev,
        _index(
            _tables(text, {"Development", *columns.values()}), "Development", columns
        ),
        "development",
    )
    columns = {
        "drilling_days": "Drilling",
        "completion_days": "Completion",
        "dc_days": "D&C",
    }
    findings.extend(
        _compare(
            {api: {key: row[key] for key in columns} for api, row in by_bore.items()},
            _index(_tables(text, {"API12", *columns.values()}), "API12", columns),
            "bore",
        )
    )
    return findings


def _csv_rows(text, required):
    """Validate the schema before duplicate or missing cells can be hidden."""
    rows = csv.reader(StringIO(text), strict=True)
    header = next(rows, [])
    if len(header) != len(set(header)) or not required.issubset(header):
        raise ValueError("invalid snapshot CSV header")
    for cells in rows:
        if len(cells) != len(header):
            raise ValueError("invalid snapshot CSV row width")
        yield dict(zip(header, cells))


def _structured(surface, text, by_bore, by_dev):
    if surface == "vintage":
        columns = {
            "development": "dev",
            "drilling_days": "drill_wed",
            "completion_days": "compl_wed",
        }
        rows = _csv_rows(text, {"api12", *columns.values()})
        actual = _index(rows, "api12", columns, text_columns={"development"})
        expected = {
            api: {key: row[key] for key in columns} for api, row in by_bore.items()
        }
        return _compare(expected, actual, "bore")
    # The committed generator emits JSON in this declaration; no JavaScript executes.
    match = re.search(
        r"(?:^|<script>)\s*const DATA\s*=\s*(.+);\s*$", text, re.MULTILINE
    )
    if not match:
        raise ValueError("missing snapshot payload")
    data = json.loads(match[1])
    columns = {
        "development": "field",
        "drilling_days": "drill",
        "completion_days": "compl",
    }
    actual = _index(data["bores"], "api", columns, text_columns={"development"})
    expected = {api: {key: row[key] for key in columns} for api, row in by_bore.items()}
    findings = _compare(expected, actual, "bore")
    columns = {"bores": "bores", "drilling_days": "drill", "completion_days": "compl"}
    findings.extend(
        _compare(
            {name: {key: row[key] for key in columns} for name, row in by_dev.items()},
            _index(data["fields"], "name", columns),
            "development",
        )
    )
    return findings


def audit_surfaces(root: Path, bores: list[dict]) -> dict:
    """Fail closed on missing/malformed snapshots, retaining relative provenance."""
    by_bore, by_dev = _expected(bores)
    snapshots = []
    for surface, relative in LOCAL_SURFACES.items():
        snapshot = {
            "surface": surface,
            "path": relative.as_posix(),
            "status": PENDING,
            "sha256": None,
            "findings": [],
        }
        path = root / relative
        if path.is_file():
            content = path.read_bytes()
            snapshot["sha256"] = hashlib.sha256(content).hexdigest()
            try:
                text = content.decode("utf-8")
                reader = (
                    _markdown if surface in {"validation", "listing"} else _structured
                )
                snapshot["findings"] = reader(surface, text, by_bore, by_dev)
                snapshot["status"] = "MISMATCH" if snapshot["findings"] else "MATCH"
            except (csv.Error, ValueError, KeyError, TypeError, AttributeError):
                snapshot["status"] = "INVALID"
                snapshot["findings"] = [{"kind": "invalid snapshot schema or count"}]
        snapshots.append(snapshot)
    local_status = (
        "MISMATCH"
        if any(s["status"] in {"MISMATCH", "INVALID"} for s in snapshots)
        else "MATCH" if all(s["status"] == "MATCH" for s in snapshots) else PENDING
    )
    snapshots.extend(
        {
            "surface": surface,
            "status": PENDING,
            "reason": "External publication was not inspected.",
        }
        for surface in ("dataset", "website")
    )
    return {
        "status": PENDING,
        "reason": "Local displayed counts only; external publication and basis correctness are not certified.",
        "local_status": local_status,
        "surfaces": snapshots,
    }
