"""Re-pull public WAR files and gate descriptive statistics on explicit QA.

Calendar cycle times and inclusive WAR interval unions are separate quantities.
Raw activity tokens are counted without inventing service-code definitions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import statistics
import zipfile
from collections import Counter
from datetime import datetime, timezone
from http.client import HTTPException
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from worldenergydata.bsee.analysis.war_rig_days import MAX_PLAUSIBLE_SPAN_DAYS


class QualityError(ValueError):
    """Inputs cannot support evaluated statistics."""


class NetworkBlocked(RuntimeError):
    """A required public source could not be retrieved."""


def _json(path: Path, value: dict) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8", newline="\n") as stream:
        return json.load(stream)


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest(config: dict) -> dict:
    path = Path(config["data_dir"]) / "manifest.json"
    if path.exists():
        return _load_json(path)
    return {"version": 1, "files": []}


def _source_name(source: dict) -> str:
    name = source["file"]
    if Path(name).name != name or name in ("", ".", ".."):
        raise QualityError("source file must be a single filename")
    url = urlsplit(source["url"])
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise QualityError("source requires a public HTTPS URL")
    return name


def record_download(
    config: dict, source: dict, path: Path, downloaded_at: str, http_status: int
) -> dict:
    """Record a successful ZIP retrieval, including one made with curl.

    The caller supplies the observed UTC retrieval time and HTTP status.
    Recording a local file never fabricates a network observation.
    """
    name = _source_name(source)
    if http_status != 200 or not zipfile.is_zipfile(path):
        raise QualityError("public source is not an HTTP 200 ZIP archive")
    parsed = datetime.fromisoformat(downloaded_at.replace("Z", "+00:00"))
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise QualityError("download time must be UTC")
    if path != Path(config["data_dir"]) / name:
        raise QualityError("download file does not match configured destination")
    result = _manifest(config)
    entry = {
        "file": name,
        "url": source["url"],
        "downloaded_at": downloaded_at,
        "http_status": http_status,
        "size_bytes": path.stat().st_size,
        "sha256": _digest(path),
    }
    result["files"] = [item for item in result["files"] if item["file"] != name]
    result["files"].append(entry)
    _json(Path(config["data_dir"]) / "manifest.json", result)
    return result


def _verified(config: dict, source: dict, entries: dict) -> Path:
    name = _source_name(source)
    path = Path(config["data_dir"]) / name
    entry = entries.get(name)
    if not entry or entry["url"] != source["url"]:
        raise QualityError(f"missing source provenance: {name}")
    if (
        not path.is_file()
        or path.stat().st_size != entry["size_bytes"]
        or _digest(path) != entry["sha256"]
    ):
        raise QualityError(f"import digest mismatch: {name}")
    if entry["http_status"] != 200 or not zipfile.is_zipfile(path):
        raise QualityError(f"invalid source archive: {name}")
    return path


def fetch(config: dict, *, opener=urlopen) -> dict:
    """Download sequentially; resume only files whose recorded digests agree.

    Use a new configured data directory to request a new public vintage.
    Existing files are retained; failed partial downloads never enter a manifest.
    """
    directory = Path(config["data_dir"])
    directory.mkdir(parents=True, exist_ok=True)
    for source in config["sources"]:
        name = _source_name(source)
        entries = {entry["file"]: entry for entry in _manifest(config)["files"]}
        if name in entries:
            _verified(config, source, entries)
            continue
        path = directory / name
        if path.exists():
            raise QualityError(f"unrecorded source already exists: {name}")
        try:
            with opener(source["url"], timeout=180) as response:
                status = response.status
                expected = getattr(response, "headers", {}).get("Content-Length")
                with path.open("xb") as stream:
                    for chunk in iter(lambda: response.read(1024 * 1024), b""):
                        stream.write(chunk)
                if expected is not None and path.stat().st_size != int(expected):
                    raise NetworkBlocked("BLOCKED-NETWORK: Content-Length mismatch")
        except HTTPException as exc:
            raise NetworkBlocked("BLOCKED-NETWORK: incomplete HTTP response") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise NetworkBlocked(
                f"BLOCKED-NETWORK: required URL {source['url']}"
            ) from exc
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        record_download(config, source, path, timestamp, status)
    return _manifest(config)


def _read_table(path: Path, spec: dict) -> list[dict]:
    with zipfile.ZipFile(path) as archive:
        matches = [
            n for n in archive.namelist() if Path(n).name == spec["member"] + ".txt"
        ]
        if len(matches) != 1:
            raise QualityError("source member missing or ambiguous")
        with archive.open(matches[0]) as raw:
            reader = csv.DictReader(
                io.TextIOWrapper(raw, encoding="iso-8859-1", newline="")
            )
            columns = list(
                dict.fromkeys(spec["keys"] + spec["required"] + spec["dates"])
            )
            if not set(columns).issubset(reader.fieldnames or []):
                raise QualityError("required source columns missing")
            rows = []
            for row in reader:
                if None in row or any(row.get(column) is None for column in columns):
                    raise QualityError("malformed delimited source row")
                rows.append({column: row[column].strip() for column in columns})
    return rows


def _date(raw: str):
    for format_string in ("%m/%d/%Y", "%m/%d/%Y %I:%M:%S %p"):
        try:
            return datetime.strptime(raw, format_string).date()
        except ValueError:
            continue
    raise ValueError("unsupported or invalid public source date")


def _table_qa(rows: list[dict], spec: dict, expected_unit: str) -> dict:
    keys = [tuple(row[key] for key in spec["keys"]) for row in rows]
    counts = Counter(keys)
    checks = {
        "row_count": int(len(rows) < spec["min_rows"]),
        "duplicate_keys": sum(count - 1 for count in counts.values()),
        "missing_keys": sum(
            any(
                not row[key]
                for key in spec["keys"] + spec["required"]
                if key != "WELL_ACTIVITY_CD"
            )
            for row in rows
        ),
        "missing_activity_code": sum(row.get("WELL_ACTIVITY_CD") == "" for row in rows),
        "invalid_war_key": sum(
            "SN_WAR" in row and re.fullmatch(r"-?[0-9]+", row["SN_WAR"]) is None
            for row in rows
        ),
        "invalid_api": sum(
            "API_WELL_NUMBER" in row
            and re.fullmatch(r"[0-9]{12}", row["API_WELL_NUMBER"]) is None
            for row in rows
        ),
        "missing_dates": 0,
        "invalid_dates": 0,
        "reversed_dates": 0,
        "implausible_span": 0,
        "out_of_range_dates": 0,
        "unit_check": int(spec["unit"] != expected_unit),
    }
    dates = []
    for row in rows:
        pair = []
        for column in spec["dates"]:
            if not row[column]:
                checks["missing_dates"] += 1
                continue
            try:
                value = _date(row[column])
                dates.append(value)
                pair.append(value)
                checks["out_of_range_dates"] += int(
                    value.isoformat() < spec.get("date_min", "0001-01-01")
                    or value.isoformat() > spec.get("date_max", "9999-12-31")
                )
            except ValueError:
                checks["invalid_dates"] += 1
        if len(pair) == 2:
            span = (pair[1] - pair[0]).days
            checks["reversed_dates"] += int(span < 0)
            if "SN_WAR" in row:
                checks["implausible_span"] += int(span > MAX_PLAUSIBLE_SPAN_DAYS)
    return {
        "rows": len(rows),
        "date_min": min(dates).isoformat() if dates else None,
        "date_max": max(dates).isoformat() if dates else None,
        "unit": spec["unit"],
        "checks": checks,
    }


def _population_tables(tables: dict, population: set[str]) -> dict:
    war = [row for row in tables["war"] if row["API_WELL_NUMBER"] in population]
    keys = {row["SN_WAR"] for row in war}
    return {
        "war": war,
        "activity": [row for row in tables["activity"] if row["SN_WAR"] in keys],
        "boreholes": [
            row for row in tables["boreholes"] if row["API_WELL_NUMBER"] in population
        ],
    }


def _quality(tables: dict, config: dict, population: set[str], *, scoped=False) -> dict:
    result = {"status": "pass", "tables": {}, "failures": []}
    for name, spec in config["tables"].items():
        qa = _table_qa(tables[name], spec, "record" if name == "activity" else "day")
        result["tables"][name] = qa
        result["failures"].extend(
            f"{name}: {check} ({count})"
            for check, count in qa["checks"].items()
            if count
            and check
            in {
                "row_count",
                "duplicate_keys",
                "missing_keys",
                "invalid_api",
                "invalid_war_key",
                "unit_check",
            }
            and not (scoped and check == "row_count")
        )
    war_keys = {row["SN_WAR"] for row in tables["war"]}
    activity_keys = {row["SN_WAR"] for row in tables["activity"]}
    bore_keys = {row["API_WELL_NUMBER"] for row in tables["boreholes"]}
    war_apis = {row["API_WELL_NUMBER"] for row in tables["war"]}
    joins = {
        "orphan_keys": len(activity_keys - war_keys),
        "unattributed_reports": len(war_keys - activity_keys),
        "population_coverage": len(population - bore_keys) + len(population - war_apis),
    }
    result["joins"] = joins
    result["population_bores"] = len(population)
    if config["basis"] != "DRL+COM":
        result["failures"].append("unsupported rig-day basis")
    if result["failures"]:
        result["status"] = "not-evaluated"
    if not scoped:
        selected = _population_tables(tables, population)
        result["population_tables"] = _quality(
            selected, config, population, scoped=True
        )["tables"]
        result["bore_quality"] = []
        for api in sorted(population):
            bore = _quality(
                _population_tables(selected, {api}), config, {api}, scoped=True
            )
            result["bore_quality"].append(
                {
                    "api12": api,
                    "checks": {
                        name: {
                            key: count
                            for key, count in table["checks"].items()
                            if count and key != "row_count"
                        }
                        for name, table in bore["tables"].items()
                    },
                    "joins": bore["joins"],
                }
            )
    return result


def _csv(path: Path, headers: list[str], rows: list[list]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)


QUALITY_REASONS = {
    "row_count": "The source row count is below the configured minimum.",
    "duplicate_keys": "Excess copies share a configured source key; no copy is selected.",
    "missing_keys": "A required source key is blank.",
    "missing_activity_code": "An activity code is blank; coverage remains unattributed.",
    "invalid_war_key": "The report key is not a signed decimal integer.",
    "invalid_api": "The bore key is not a twelve-digit API identifier.",
    "missing_dates": "A required source date is blank; each blank date is counted.",
    "invalid_dates": "A source date cannot be read using the supported date formats.",
    "reversed_dates": "The source end date precedes its start date.",
    "implausible_span": (
        "The exclusive WAR span exceeds the canonical plausibility limit; retained and flagged."
    ),
    "out_of_range_dates": (
        "A date is outside the configured evaluation range; that quantity is not evaluated."
    ),
    "unit_check": "The configured unit does not match the required quantity.",
    "orphan_keys": "An activity report key has no matching WAR report.",
    "unattributed_reports": "A WAR report key has no matching activity record.",
    "population_coverage": (
        "A selected bore lacks a borehole or WAR join; missing joins are counted "
        "separately, so a bore can be counted twice."
    ),
}


def _public_key(row: dict) -> str:
    # Never export a free-text field, malformed key or fabricated row identifier.
    field, pattern = (
        ("SN_WAR", r"-?[0-9]+")
        if "SN_WAR" in row
        else ("API_WELL_NUMBER", r"[0-9]{12}")
    )
    value = row.get(field, "")
    if re.fullmatch(pattern, value):
        return value
    raise QualityError("defect has no publishable public record key")


def _defect_records(tables: dict, config: dict, population: set[str], qa: dict) -> dict:
    """Enumerate exactly the occurrences counted by QA, including missing joins.

    Duplicate counts describe excess copies, date counts describe fields, and
    join counts describe distinct missing keys. These are not unique bore counts.
    """
    defects = {}

    def add(defect, row):
        defects.setdefault(defect, []).append(_public_key(row))

    for name, spec in config["tables"].items():
        seen = set()
        rows = tables[name]
        for row in rows:
            prefix = name + "."
            key = tuple(row[column] for column in spec["keys"])
            if key in seen:
                add(prefix + "duplicate_keys", row)
            seen.add(key)
            if any(
                not row[column]
                for column in spec["keys"] + spec["required"]
                if column != "WELL_ACTIVITY_CD"
            ):
                add(prefix + "missing_keys", row)
            if row.get("WELL_ACTIVITY_CD") == "":
                add(prefix + "missing_activity_code", row)
            if "SN_WAR" in row and not re.fullmatch(r"-?[0-9]+", row["SN_WAR"]):
                add(prefix + "invalid_war_key", row)
            if "API_WELL_NUMBER" in row and not re.fullmatch(
                r"[0-9]{12}", row["API_WELL_NUMBER"]
            ):
                add(prefix + "invalid_api", row)
            dates = []
            for column in spec["dates"]:
                if not row[column]:
                    add(prefix + "missing_dates", row)
                else:
                    try:
                        value = _date(row[column])
                        dates.append(value)
                        if value.isoformat() < spec.get(
                            "date_min", "0001-01-01"
                        ) or value.isoformat() > spec.get("date_max", "9999-12-31"):
                            add(prefix + "out_of_range_dates", row)
                    except ValueError:
                        add(prefix + "invalid_dates", row)
            if len(dates) == 2:
                span = (dates[1] - dates[0]).days
                if span < 0:
                    add(prefix + "reversed_dates", row)
                if "SN_WAR" in row and span > MAX_PLAUSIBLE_SPAN_DAYS:
                    add(prefix + "implausible_span", row)
        for check in ("row_count", "unit_check"):
            if qa["tables"][name]["checks"][check]:
                if not rows:
                    raise QualityError("defect has no publishable public record key")
                add(name + "." + check, rows[0])
    war = {row["SN_WAR"]: row for row in tables["war"]}
    activity = {row["SN_WAR"]: row for row in tables["activity"]}
    for key in sorted(activity.keys() - war.keys()):
        add("orphan_keys", activity[key])
    for key in sorted(war.keys() - activity.keys()):
        add("unattributed_reports", war[key])
    for name in ("boreholes", "war"):
        available = {row["API_WELL_NUMBER"] for row in tables[name]}
        for api in sorted(population - available):
            add("population_coverage", {"API_WELL_NUMBER": api})
    expected = {
        f"{name}.{check}": count
        for name, table in qa["tables"].items()
        for check, count in table["checks"].items()
        if count
    }
    expected.update({key: count for key, count in qa["joins"].items() if count})
    if {key: len(records) for key, records in defects.items()} != expected:
        raise QualityError("defect accounting disagrees with source QA counts")
    return defects


def write_data_quality(output: Path, defects: dict, *, synthetic: bool = False) -> dict:
    """Report observations without claiming that every defect was excluded.

    Occurrences are reconciled with QA by the caller. The canonical rig-day
    implementation retains implausible spans and unattributed weeks, rejects
    reversed intervals, and exposes phase coverage separately.
    """
    rows = []
    for defect, records in sorted(defects.items()):
        if not records:
            raise QualityError("defect accounting has no occurrences")
        if any(
            not isinstance(key, str) or not re.fullmatch(r"-?[0-9]+", key)
            for key in records
        ):
            raise QualityError("example must be a public record key")
        check = defect.rsplit(".", 1)[-1]
        if check not in QUALITY_REASONS:
            raise QualityError("defect accounting has no stated reporting criterion")
        rows.append(
            {
                "defect": defect,
                "count": len(records),
                "example_id": min(records),
                "rule": "reported",
                "reason": QUALITY_REASONS[check],
            }
        )
    headers = ["defect", "count", "example_id", "rule", "reason"]
    text = "Public data quality\n"
    if rows:
        text += (
            "Row defects are reported; structural failures withhold all statistics.\n"
        )
        text += (
            "\n".join(
                f"{row['defect']}: {row['count']} reported. {row['reason']}"
                for row in rows
            )
            + "\n"
        )
        text += "Counts can overlap and must not be added to count distinct bores.\n"
    else:
        text += "No source defects were detected by the configured checks.\n"
    result = {
        "columns": headers,
        "rows": rows,
        "synthetic": synthetic,
        "public_data_quality": text,
        "basis": (
            "Whole-table observations; row diagnostics are also scoped per population bore in QA. "
            "No corrections applied."
        ),
    }
    _csv(
        output / "data_quality.csv",
        headers,
        [[row[key] for key in headers] for row in rows],
    )
    _json(output / "data_quality.json", result)
    (output / "public_data_quality.txt").write_text(
        text, encoding="utf-8", newline="\n"
    )
    return result


def _products(
    tables: dict, config: dict, population: set[str], sources: list, quality: dict
) -> dict:
    import pandas as pd

    from worldenergydata.bsee.analysis.war_rig_days import (
        BASIS_DRL_COM,
        rig_days_by_bore,
        rig_days_by_well,
    )

    tables = _population_tables(tables, population)
    war = pd.DataFrame(
        tables["war"],
        columns=config["tables"]["war"]["keys"]
        + config["tables"]["war"]["required"]
        + config["tables"]["war"]["dates"],
    )
    activity = pd.DataFrame(tables["activity"], columns=["SN_WAR", "WELL_ACTIVITY_CD"])
    spec = config["tables"]["war"]
    for index, row in war.iterrows():
        for column in spec["dates"]:
            try:
                value = _date(row[column])
            except ValueError:
                war.at[index, column] = ""
                continue
            war.at[index, column] = (
                value.strftime("%m/%d/%Y")
                if spec.get("date_min", "0001-01-01")
                <= value.isoformat()
                <= spec.get("date_max", "9999-12-31")
                else ""
            )
    rejected = Counter()
    for row in war.to_dict("records"):
        if (
            not row["WAR_START_DT"]
            or not row["WAR_END_DT"]
            or _date(row["WAR_END_DT"]) < _date(row["WAR_START_DT"])
        ):
            rejected[row["API_WELL_NUMBER"]] += 1
    joined = war.merge(activity, on="SN_WAR", how="left", validate="one_to_many")
    bores = rig_days_by_bore(joined, basis=BASIS_DRL_COM, population=sorted(population))
    # Count source reports before the activity join can duplicate their rows.
    bores["war_weeks_rejected"] = bores["api12"].map(rejected).fillna(0).astype(int)
    unusable = bores["days_status"].eq("no_war_activity") & bores[
        "war_weeks_rejected"
    ].gt(0)
    bores.loc[
        unusable, ["days_status", "drilling_days_status", "completion_days_status"]
    ] = "no_usable_war_interval"
    wells = rig_days_by_well(joined, basis=BASIS_DRL_COM, population=sorted(population))
    calendar = []
    boreholes = {row["API_WELL_NUMBER"]: row for row in tables["boreholes"]}
    for api in sorted(population):
        row = boreholes.get(api, {})
        try:
            start, end = _date(row["WELL_SPUD_DATE"]), _date(row["TOTAL_DEPTH_DATE"])
            spec = config["tables"]["boreholes"]
            valid = end >= start and all(
                spec.get("date_min", "0001-01-01")
                <= value.isoformat()
                <= spec.get("date_max", "9999-12-31")
                for value in (start, end)
            )
            calendar.append(
                [
                    api,
                    start.isoformat(),
                    (end - start).days if valid else None,
                    "EVALUATED" if valid else "NOT_EVALUATED",
                ]
            )
        except (KeyError, ValueError):
            calendar.append([api, None, None, "NOT_EVALUATED"])
    annual = Counter()
    for row in joined.to_dict("records"):
        if pd.isna(row["WELL_ACTIVITY_CD"]) or not row["WELL_ACTIVITY_CD"]:
            continue
        try:
            annual[(str(_date(row["WAR_START_DT"]).year), row["WELL_ACTIVITY_CD"])] += 1
        except ValueError:
            continue

    def total(series):
        value = series.sum(min_count=1)
        return None if pd.isna(value) else float(value)

    headlines = {
        "calendar_median_days": (
            statistics.median(row[2] for row in calendar if row[2] is not None)
            if any(row[2] is not None for row in calendar)
            else None
        ),
        "bore_drilling_days_sum": total(bores["drilling_days"]),
        "well_drilling_days_union": total(wells["drilling_days"]),
        "completion_days_sum": total(bores["completion_days"]),
        "activity_code_records": sum(annual.values()),
    }
    # Preserve absence of phase evidence as null rather than zero or NaN.
    headlines = {
        key: None if pd.isna(value) else value for key, value in headlines.items()
    }
    provenance = {
        "qa_status": "pass",
        "synthetic": config.get("synthetic", False),
        "sources": sources,
        "population_sha256": _digest(Path(config["population_csv"])),
        "basis": BASIS_DRL_COM.describe(),
        "public_data_quality": quality["public_data_quality"],
        "limits": [
            "Calendar spud-to-TD days are elapsed time; no learning or utilisation inference.",
            "DRL/COM attribution is a stated interpretation; PND remains separate.",
            "Activity values count code-bearing records, not interventions or service durations.",
            "API12 bore sums can overlap; API10 uses interval unions across sidetracks.",
            "Population follows the configured historical bore list, not new discoveries.",
        ],
    }
    output = Path(config["output_dir"])
    charts = {
        "calendar": (
            [
                "api12 [identifier]",
                "spud_date [date]",
                "calendar_days [day]",
                "status [category]",
            ],
            sorted(calendar),
            {"median_days": headlines["calendar_median_days"]},
        ),
        "completion": (
            ["api12 [identifier]", "completion_days [day]", "status [category]"],
            [
                [
                    r.api12,
                    None if pd.isna(r.completion_days) else r.completion_days,
                    r.completion_days_status,
                ]
                for r in bores.itertuples()
            ],
            {"bore_days_sum": headlines["completion_days_sum"]},
        ),
        "drilldown": (
            [
                "api12 [identifier]",
                "drilling_days [day]",
                "completion_days [day]",
                "pnd_days [day]",
                "days_status [category]",
                "war_weeks_rejected [record]",
                "war_weeks_implausible [record]",
                "war_weeks_unattributed [record]",
            ],
            [
                [
                    r.api12,
                    None if pd.isna(r.drilling_days) else r.drilling_days,
                    None if pd.isna(r.completion_days) else r.completion_days,
                    r.pnd_days,
                    r.days_status,
                    r.war_weeks_rejected,
                    r.war_weeks_implausible,
                    r.war_weeks_unattributed,
                ]
                for r in bores.itertuples()
            ],
            {"bore_count": len(bores)},
        ),
        "rig_day_basis": (
            [
                "api10 [identifier]",
                "drilling_days_union [day]",
                "completion_days_union [day]",
            ],
            [
                [
                    r.api10,
                    None if pd.isna(r.drilling_days) else r.drilling_days,
                    None if pd.isna(r.completion_days) else r.completion_days,
                ]
                for r in wells.itertuples()
            ],
            {
                "bore_sum_days": headlines["bore_drilling_days_sum"],
                "well_union_days": headlines["well_drilling_days_union"],
            },
        ),
        "activity": (
            ["year [year]", "activity_code [token]", "code_records [record]"],
            [[year, code, count] for (year, code), count in sorted(annual.items())],
            {"code_records": headlines["activity_code_records"]},
        ),
    }
    for name, (headers, values, numbers) in charts.items():
        _csv(output / f"{name}.csv", headers, values)
        _json(output / f"{name}.json", {**provenance, "headlines": numbers})
    result = {**provenance, "headlines": headlines}
    _json(output / "headlines.json", result)
    return result


def analyse(config: dict) -> dict:
    """Evaluate a manifest-backed vintage in a new, immutable output directory.

    Structural checks cover entire tables. Row diagnostics are reported per
    selected bore and do not prevent other bores or quantities being evaluated.
    """
    output = Path(config["output_dir"])
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("use a new output directory for each analysis attempt")
    output.mkdir(parents=True, exist_ok=True)
    try:
        manifest = _manifest(config)
        entries = {entry["file"]: entry for entry in manifest["files"]}
        paths = {
            source["file"]: _verified(config, source, entries)
            for source in config["sources"]
        }
        tables = {
            name: _read_table(paths[spec["file"]], spec)
            for name, spec in config["tables"].items()
        }
        with Path(config["population_csv"]).open(
            encoding="utf-8", newline="\n"
        ) as stream:
            population_rows = list(csv.DictReader(stream))
        population = {row["API_WELL_NUMBER"] for row in population_rows}
        if not population or any(
            re.fullmatch(r"[0-9]{12}", api) is None for api in population
        ):
            raise QualityError("population requires nonempty API12 identifiers")
        if len(population_rows) != len(population):
            raise QualityError("population duplicate keys")
        qa = _quality(tables, config, population)
        qa["sources"] = manifest["files"]
        qa["population_sha256"] = _digest(Path(config["population_csv"]))
        qa["workflow_sha256"] = _digest(Path(__file__))
        qa["scope"] = "whole-table structural checks; population-scoped row diagnostics"
        qa["criterion"] = (
            "Verified schema, provenance, key formats and unique keys are required; "
            "row defects are reported per bore."
        )
        qa["basis"] = config["basis"]
        _json(output / "qa.json", qa)
        defects = _defect_records(tables, config, population, qa)
        quality = write_data_quality(
            output, defects, synthetic=config.get("synthetic", False)
        )
        qa["data_quality"] = quality
        _json(output / "qa.json", qa)
        if qa["status"] != "pass":
            raise QualityError("QA not-evaluated: see qa.json")
    except (QualityError, KeyError, ValueError, OSError, zipfile.BadZipFile) as exc:
        receipt = output / "qa.json"
        if receipt.exists():
            qa = _load_json(receipt)
            qa["status"] = "not-evaluated"
            if not str(exc).startswith("QA not-evaluated"):
                qa["failures"].append(str(exc))
            _json(receipt, qa)
        else:
            _json(
                receipt,
                {
                    "status": "not-evaluated",
                    "failures": [str(exc)],
                    "criterion": "Verified source schema, provenance and population are required.",
                    "basis": config.get("basis"),
                },
            )
        raise QualityError(str(exc)) from exc
    _json(
        output / "run_config.json",
        {
            "basis": config["basis"],
            "tables": config["tables"],
            "synthetic": config.get("synthetic", False),
        },
    )
    return _products(tables, config, population, manifest["files"], quality)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args(argv)
    config = _load_json(args.config)
    for key in ("data_dir", "output_dir"):
        value = getattr(args, key)
        if value is not None:
            config[key] = str(value)
    try:
        if args.fetch:
            fetch(config)
        analyse(config)
    except (QualityError, NetworkBlocked, FileExistsError) as exc:
        print(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
