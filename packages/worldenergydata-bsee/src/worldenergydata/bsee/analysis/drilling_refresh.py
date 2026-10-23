"""Re-pull public WAR files and gate descriptive statistics on explicit QA.

Calendar cycle times and inclusive WAR interval unions are separate quantities.
Normalized activity tokens are counted without inventing service-code definitions.
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
from datetime import date, datetime, timezone
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


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _workflow_digest(path: Path) -> str:
    """Identify UTF-8 source text independently of checkout line endings."""
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def _manifest(config: dict) -> dict:
    path = Path(config["data_dir"]) / "manifest.json"
    if path.exists():
        result = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(result, dict)
            or not isinstance(result.get("files"), list)
            or any(
                not isinstance(entry, dict) or not isinstance(entry.get("file"), str)
                for entry in result["files"]
            )
        ):
            raise QualityError("invalid source manifest schema")
        return result
    return {"version": 1, "files": []}


def _source_name(source: dict) -> str:
    name = source["file"]
    if Path(name).name != name or "\\" in name or name in ("", ".", ".."):
        raise QualityError("source file must be a single filename")
    url = urlsplit(source["url"])
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise QualityError("source requires a public HTTPS URL")
    return name


def _check_redirect(source: dict, resolved_url: str) -> str:
    if not isinstance(resolved_url, str):
        raise NetworkBlocked("public source redirect URL is unavailable")
    target, requested = urlsplit(resolved_url), urlsplit(source["url"])
    if target.scheme != "https" or target.netloc.lower() != requested.netloc.lower():
        raise NetworkBlocked("public source redirect changes the HTTPS origin")
    return resolved_url


def record_download(
    config: dict,
    source: dict,
    path: Path,
    downloaded_at: str,
    http_status: int,
    *,
    resolved_url: str | None = None,
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
    if resolved_url is not None:
        entry["resolved_url"] = _check_redirect(source, resolved_url)
    result["files"] = [item for item in result["files"] if item["file"] != name]
    result["files"].append(entry)
    _json(Path(config["data_dir"]) / "manifest.json", result)
    return result


def _verified(config: dict, source: dict, entries: dict) -> Path:
    name = _source_name(source)
    path = Path(config["data_dir"]) / name
    entry = entries.get(name)
    if not entry or entry.get("url") != source["url"]:
        raise QualityError(f"missing source provenance: {name}")
    if (
        not {"size_bytes", "sha256", "http_status"}.issubset(entry)
        or type(entry["size_bytes"]) is not int
        or entry["size_bytes"] <= 0
        or not isinstance(entry["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is None
    ):
        raise QualityError("incomplete or invalid source archive provenance")
    if "resolved_url" in entry:
        try:
            _check_redirect(source, entry["resolved_url"])
        except NetworkBlocked as exc:
            raise QualityError("invalid resolved-source provenance") from exc
    try:
        observed = datetime.fromisoformat(entry["downloaded_at"].replace("Z", "+00:00"))
    except (KeyError, AttributeError, TypeError, ValueError) as exc:
        raise QualityError("missing or invalid source retrieval time") from exc
    if observed.utcoffset() is None or observed.utcoffset().total_seconds() != 0:
        raise QualityError("source retrieval time must be UTC")
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
                if not callable(getattr(response, "geturl", None)):
                    raise NetworkBlocked("public source redirect URL is unavailable")
                resolved_url = _check_redirect(source, response.geturl())
                headers = {
                    key.lower(): value
                    for key, value in getattr(response, "headers", {}).items()
                }
                length = headers.get("content-length")
                if length is not None and re.fullmatch(r"[0-9]+", length) is None:
                    raise NetworkBlocked("invalid Content-Length for public source")
                received = 0
                with path.open("xb") as stream:
                    for chunk in iter(lambda: response.read(1024 * 1024), b""):
                        stream.write(chunk)
                        received += len(chunk)
                if length is not None and received != int(length):
                    raise NetworkBlocked("public source Content-Length mismatch")
        except (URLError, TimeoutError, OSError, HTTPException) as exc:
            raise NetworkBlocked(
                f"BLOCKED-NETWORK: required URL {source['url']}"
            ) from exc
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        record_download(
            config, source, path, timestamp, status, resolved_url=resolved_url
        )
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
                record = {column: row[column].strip() for column in columns}
                if "WELL_ACTIVITY_CD" in record:
                    code = record["WELL_ACTIVITY_CD"].upper()
                    record["WELL_ACTIVITY_CD"] = "" if code in {"NAN", "NONE"} else code
                rows.append(record)
    return rows


def _timestamp(raw: str):
    for format_string in ("%m/%d/%Y", "%m/%d/%Y %I:%M:%S %p"):
        try:
            return datetime.strptime(raw, format_string)
        except ValueError:
            continue
    raise ValueError("unsupported or invalid public source date")


def _date(raw: str):
    return _timestamp(raw).date()


def _table_qa(rows: list[dict], spec: dict, expected_unit: str) -> dict:
    keys = [tuple(row[key] for key in spec["keys"]) for row in rows]
    counts = Counter(keys)
    checks = {
        "row_count": int(len(rows) < spec["min_rows"]),
        "duplicate_keys": sum(count - 1 for count in counts.values()),
        "missing_keys": sum(
            any(not row[key] for key in spec["keys"] + spec["required"]) for row in rows
        ),
        "invalid_api": sum(
            "API_WELL_NUMBER" in row
            and re.fullmatch(r"[0-9]{12}", row["API_WELL_NUMBER"]) is None
            for row in rows
        ),
        "invalid_war": sum(
            "SN_WAR" in row and re.fullmatch(r"-?[0-9]+", row["SN_WAR"]) is None
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
                value = _timestamp(row[column])
                dates.append(value.date())
                pair.append(value)
                checks["out_of_range_dates"] += int(
                    (
                        "date_min" in spec
                        and value.date() < date.fromisoformat(spec["date_min"])
                    )
                    or (
                        "date_max" in spec
                        and value.date() > date.fromisoformat(spec["date_max"])
                    )
                )
            except ValueError:
                checks["invalid_dates"] += 1
        if len(pair) == 2:
            span = (pair[1] - pair[0]).days
            checks["reversed_dates"] += int(span < 0)
            if "WAR_START_DT" in spec["dates"]:
                checks["implausible_span"] += int(span > MAX_PLAUSIBLE_SPAN_DAYS)
    return {
        "rows": len(rows),
        "date_min": min(dates).isoformat() if dates else None,
        "date_max": max(dates).isoformat() if dates else None,
        "unit": spec["unit"],
        "checks": checks,
        "criteria": {
            "min_rows": spec["min_rows"],
            "date_min": spec.get("date_min"),
            "date_max": spec.get("date_max"),
            "max_exclusive_span_days": (
                MAX_PLAUSIBLE_SPAN_DAYS if "WAR_START_DT" in spec["dates"] else None
            ),
        },
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


def _bore_quality(tables: dict, config: dict, population: set[str]) -> dict:
    groups = {name: {} for name in ("war", "boreholes")}
    for name, grouped in groups.items():
        for row in tables[name]:
            if row["API_WELL_NUMBER"] in population:
                grouped.setdefault(row["API_WELL_NUMBER"], []).append(row)
    activity = {row["SN_WAR"] for row in tables["activity"] if row["WELL_ACTIVITY_CD"]}
    result = {}
    for api in sorted(population):
        reasons = {}
        for name, quantity in (("war", "rig"), ("boreholes", "calendar")):
            rows = groups[name].get(api, [])
            checks = _table_qa(rows, config["tables"][name], "day")["checks"]
            reasons[quantity] = (
                [
                    check
                    for check in (
                        "missing_dates",
                        "invalid_dates",
                        "reversed_dates",
                        "implausible_span",
                        "out_of_range_dates",
                    )
                    if checks[check]
                ]
                if rows
                else ["missing_" + name]
            )
        reasons["reports_without_code"] = sum(
            row["SN_WAR"] not in activity for row in groups["war"].get(api, [])
        )
        result[api] = reasons
    return result


def _quality(tables: dict, config: dict, population: set[str]) -> dict:
    selected = _population_tables(tables, population)
    result = {"status": "pass", "tables": {}, "population_tables": {}, "failures": []}
    for name, spec in config["tables"].items():
        qa = _table_qa(tables[name], spec, "record" if name == "activity" else "day")
        result["tables"][name] = qa
        result["population_tables"][name] = _table_qa(
            selected[name], spec, "record" if name == "activity" else "day"
        )
        blocking = {
            "row_count",
            "duplicate_keys",
            "invalid_api",
            "invalid_war",
            "unit_check",
        }
        if name != "activity":
            blocking.add("missing_keys")
        result["failures"].extend(
            f"{name}: {check} ({count})"
            for check, count in qa["checks"].items()
            if count and check in blocking
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
    result["per_bore"] = _bore_quality(tables, config, population)
    result["failures"].extend(
        f"{name} ({count})"
        for name, count in joins.items()
        if count and name == "orphan_keys"
    )
    if config["basis"] != "DRL+COM":
        result["failures"].append("unsupported rig-day basis")
    if result["failures"]:
        result["status"] = "not-evaluated"
    return result


def _csv(path: Path, headers: list[str], rows: list[list]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)


QUALITY_REASONS = {
    "row_count": "The source row count is below the configured minimum.",
    "duplicate_keys": "Excess copies share a configured source key; no copy is selected.",
    "missing_keys": "A required key or code is blank, including missing-code sentinels.",
    "invalid_api": "The bore key is not a twelve-digit API identifier.",
    "invalid_war": "The report key is not a signed decimal integer identifier.",
    "missing_dates": "A required source date is blank; each blank date is counted.",
    "invalid_dates": "A source date cannot be read using the supported date formats.",
    "reversed_dates": "The source end date precedes its start date.",
    "implausible_span": "The exclusive WAR span exceeds the canonical plausibility limit.",
    "out_of_range_dates": "A source date is outside the configured inclusive date bounds.",
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
    field = "SN_WAR" if "SN_WAR" in row else "API_WELL_NUMBER"
    pattern = r"-?[0-9]+" if field == "SN_WAR" else r"[0-9]{12}"
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
            if any(not row[column] for column in spec["keys"] + spec["required"]):
                add(prefix + "missing_keys", row)
            if "API_WELL_NUMBER" in row and not re.fullmatch(
                r"[0-9]{12}", row["API_WELL_NUMBER"]
            ):
                add(prefix + "invalid_api", row)
            if "SN_WAR" in row and not re.fullmatch(r"-?[0-9]+", row["SN_WAR"]):
                add(prefix + "invalid_war", row)
            dates = []
            for column in spec["dates"]:
                if not row[column]:
                    add(prefix + "missing_dates", row)
                else:
                    try:
                        value = _timestamp(row[column])
                        dates.append(value)
                        if (
                            "date_min" in spec
                            and value.date() < date.fromisoformat(spec["date_min"])
                        ) or (
                            "date_max" in spec
                            and value.date() > date.fromisoformat(spec["date_max"])
                        ):
                            add(prefix + "out_of_range_dates", row)
                    except ValueError:
                        add(prefix + "invalid_dates", row)
            if len(dates) == 2:
                span = (dates[1] - dates[0]).days
                if span < 0:
                    add(prefix + "reversed_dates", row)
                if "WAR_START_DT" in spec["dates"] and span > MAX_PLAUSIBLE_SPAN_DAYS:
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


def write_data_quality(
    output: Path,
    defects: dict,
    reported: dict,
    *,
    synthetic: bool = False,
    blocking: bool = True,
    per_bore: dict | None = None,
) -> dict:
    """Validate and write a detection inventory, not independent exclusion proof.

    Reported occurrences must match detected key multisets. Per-bore decisions
    state which quantities lack sufficient evidence; no correction is claimed.
    """
    if defects.keys() != reported.keys():
        raise QualityError("defect accounting classes do not match")
    rows, accounting = [], {}
    for defect, records in sorted(defects.items()):
        if not records or Counter(records) != Counter(reported[defect]):
            raise QualityError("defect accounting does not cover every occurrence")
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
        accounting[defect] = {"reported": len(reported[defect])}
    headers = ["defect", "count", "example_id", "rule", "reason"]
    text = "Public data quality\n"
    if rows:
        text += (
            "Structural checks failed. All statistics are withheld.\n"
            if blocking
            else "Source defects are reported; quantity dispositions are recorded per bore.\n"
        )
        text += (
            "\n".join(
                f"{row['defect']}: {row['count']} reported. {row['reason']}"
                for row in rows
            )
            + "\n"
        )
        text += "Counts can overlap and must not be added to count distinct bores.\n"
    elif blocking:
        text += (
            "Refresh not evaluated: statistics are withheld. "
            "See qa.json for failed structural or basis criteria.\n"
        )
    else:
        text += "No source defects were detected by the configured checks.\n"
    result = {
        "columns": headers,
        "rows": rows,
        "accounting": accounting,
        "synthetic": synthetic,
        "public_data_quality": text,
        "basis": "Whole-source detection inventory; population quantities are judged per bore.",
        "blocking": blocking,
        "per_bore": per_bore or {},
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
    if quality.get("blocking", bool(quality["rows"])):
        raise QualityError("source defects exclude all statistics")
    import pandas as pd

    from worldenergydata.bsee.analysis.war_rig_days import (
        BASIS_DRL_COM,
        rig_days_by_bore,
        rig_days_by_well,
    )

    selected = _population_tables(tables, population)
    dispositions = quality["per_bore"]
    eligible = {api for api in population if not dispositions[api]["rig"]}
    war = pd.DataFrame(
        [row for row in selected["war"] if row["API_WELL_NUMBER"] in eligible],
        columns=list(tables["war"][0]),
    )
    activity = pd.DataFrame(tables["activity"])
    joined = war.merge(activity, on="SN_WAR", how="left", validate="one_to_many")
    bores = rig_days_by_bore(joined, basis=BASIS_DRL_COM, population=sorted(population))
    wells = rig_days_by_well(joined, basis=BASIS_DRL_COM, population=sorted(population))
    for api, reasons in dispositions.items():
        if reasons["rig"]:
            status = "not-evaluated: " + ", ".join(reasons["rig"])
            mask = bores["api12"].eq(api)
            for column in ("drilling_days", "completion_days", "pnd_days"):
                bores.loc[mask, column] = float("nan")
            for column in (
                "days_status",
                "drilling_days_status",
                "completion_days_status",
            ):
                bores.loc[mask, column] = status
            mask = wells["api10"].eq(api[:10])
            for column in ("drilling_days", "completion_days"):
                wells.loc[mask, column] = float("nan")
            wells.loc[mask, "overlap_days"] = float("nan")
            for column in ("drilling_days_status", "completion_days_status"):
                wells.loc[mask, column] = status
    for row in bores.itertuples():
        dispositions[row.api12]["drilling_status"] = row.drilling_days_status
        dispositions[row.api12]["completion_status"] = row.completion_days_status
    calendar = []
    milestones = {row["API_WELL_NUMBER"]: row for row in selected["boreholes"]}
    for api in sorted(population):
        reasons = dispositions[api]["calendar"]
        if reasons:
            calendar.append([api, None, None, "not-evaluated: " + ", ".join(reasons)])
        else:
            row = milestones[api]
            start, end = _date(row["WELL_SPUD_DATE"]), _date(row["TOTAL_DEPTH_DATE"])
            calendar.append([api, start.isoformat(), (end - start).days, "evaluated"])
    annual = Counter(
        (str(_date(row["WAR_START_DT"]).year), row["WELL_ACTIVITY_CD"])
        for row in joined.to_dict("records")
        if isinstance(row["WELL_ACTIVITY_CD"], str) and row["WELL_ACTIVITY_CD"]
    )

    def total(series):
        value = series.sum(min_count=1)
        return None if pd.isna(value) else float(value)

    durations = [row[2] for row in calendar if row[2] is not None]
    headlines = {
        "calendar_median_days": statistics.median(durations) if durations else None,
        "bore_drilling_days_sum": total(bores["drilling_days"]),
        "well_drilling_days_union": total(wells["drilling_days"]),
        "completion_days_sum": total(bores["completion_days"]),
        "activity_code_records": sum(annual.values()),
    }
    # Preserve absence of phase evidence as null rather than zero or NaN.
    headlines = {
        key: None if pd.isna(value) else value for key, value in headlines.items()
    }
    coverage = {
        "selected_bores": len(population),
        "calendar_evaluated_bores": len(durations),
        "drilling_evaluated_bores": int(bores["drilling_days"].notna().sum()),
        "completion_evaluated_bores": int(bores["completion_days"].notna().sum()),
    }
    coverage["status"] = (
        "complete"
        if all(value == len(population) for value in coverage.values())
        else "partial"
    )
    phase_status_counts = {
        phase: dict(Counter(bores[f"{phase}_days_status"]))
        for phase in ("drilling", "completion")
    }
    overlap = {
        "drilling_days": total(
            wells["drilling_days_additive"] - wells["drilling_days"]
        ),
        "all_war_days": total(wells["overlap_days"]),
        "selected_wells": len(wells),
        "wells_with_multiple_bores": int(wells["n_bores"].gt(1).sum()),
        "evaluated_wells": int(wells["overlap_days"].notna().sum()),
        "drilling_evaluated_wells": int(wells["drilling_days"].notna().sum()),
        "criterion": "Additive bore unions minus well unions, for evaluated wells; days.",
    }
    provenance = {
        "receipt": "qa.json",
        "synthetic": config.get("synthetic", False),
        "sources": sources,
        "population_sha256": _digest(Path(config["population_csv"])),
        "basis": BASIS_DRL_COM.describe(),
        "public_data_quality": quality["public_data_quality"],
        "coverage": coverage,
        "phase_status_counts": phase_status_counts,
        "overlap": overlap,
        "per_bore": dispositions,
        "criteria": {
            name: _table_qa([], spec, "record" if name == "activity" else "day")[
                "criteria"
            ]
            for name, spec in config["tables"].items()
        },
        "limits": [
            "Calendar spud-to-TD days are elapsed time; no learning or utilisation inference.",
            "DRL/COM attribution is a stated interpretation; PND remains separate.",
            "Activity values count code-bearing records, not interventions or service durations.",
            "API12 bore sums can overlap; API10 uses interval unions across sidetracks.",
            "Population follows the configured historical bore list, not new discoveries.",
            "Headlines cover evaluated bores only; coverage counts qualify every sum and median.",
            "A well union is not evaluated if any selected sibling bore "
            "has invalid or absent WAR evidence.",
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
                "drilling_status [category]",
                "completion_status [category]",
                "reports_without_code [record]",
            ],
            [
                [
                    r.api12,
                    None if pd.isna(r.drilling_days) else r.drilling_days,
                    None if pd.isna(r.completion_days) else r.completion_days,
                    None if pd.isna(r.pnd_days) else r.pnd_days,
                    r.days_status,
                    r.drilling_days_status,
                    r.completion_days_status,
                    dispositions[r.api12]["reports_without_code"],
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
                "drilling_status [category]",
                "completion_status [category]",
            ],
            [
                [
                    r.api10,
                    None if pd.isna(r.drilling_days) else r.drilling_days,
                    None if pd.isna(r.completion_days) else r.completion_days,
                    r.drilling_days_status,
                    r.completion_days_status,
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

    Structural checks cover entire tables. Population quantities with missing
    or invalid evidence stay null, with reasons and coverage counts.
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
            encoding="utf-8", newline=""
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
        if qa["status"] == "pass":
            qa["status"] = "pending-products"
        qa["sources"] = manifest["files"]
        qa["population_sha256"] = _digest(Path(config["population_csv"]))
        qa["workflow_sha256"] = _workflow_digest(Path(__file__))
        qa["workflow_digest_basis"] = "UTF-8 source text with LF line endings"
        qa["scope"] = (
            "global structural checks; row checks and quantities scoped to selected bores"
        )
        qa["criterion"] = (
            "Schema, provenance, row floors, identifier formats, duplicate keys, "
            "units and orphan keys must pass globally. Population quantities require "
            "valid dates within configured bounds; "
            "exclusive WAR spans must not exceed the canonical plausibility limit."
        )
        qa["basis"] = config["basis"]
        _json(output / "qa.json", qa)
        defects = _defect_records(tables, config, population, qa)
        quality = write_data_quality(
            output,
            defects,
            defects,
            synthetic=config.get("synthetic", False),
            blocking=bool(qa["failures"]),
            per_bore=qa["per_bore"],
        )
        qa["data_quality"] = quality
        _json(output / "qa.json", qa)
        if qa["failures"]:
            raise QualityError("QA not-evaluated: see qa.json")
    except Exception as exc:
        if isinstance(exc, OSError):
            message = f"configured file is unavailable ({type(exc).__name__})"
        elif isinstance(exc, QualityError):
            message = str(exc)
        else:
            message = f"source evaluation failed ({type(exc).__name__})"
        receipt = output / "qa.json"
        if receipt.exists():
            qa = json.loads(receipt.read_text(encoding="utf-8"))
            qa["status"] = "not-evaluated"
            if not message.startswith("QA not-evaluated"):
                qa["failures"].append(message)
            _json(receipt, qa)
        else:
            _json(
                receipt,
                {
                    "status": "not-evaluated",
                    "failures": [message],
                    "criterion": "Verified source schema, provenance and population are required.",
                    "basis": config.get("basis"),
                },
            )
        raise QualityError(message) from exc
    try:
        _json(
            output / "run_config.json",
            {
                "basis": config["basis"],
                "tables": config["tables"],
                "synthetic": config.get("synthetic", False),
            },
        )
        result = _products(tables, config, population, manifest["files"], quality)
        for key in ("headlines", "coverage", "phase_status_counts", "overlap"):
            qa[key] = result[key]
        _json(output / "data_quality.json", quality)
        qa["status"] = "pass"
        _json(output / "qa.json", qa)
    except Exception as exc:
        qa["status"] = "not-evaluated"
        message = f"product generation failed ({type(exc).__name__})"
        qa["failures"].append(message)
        _json(output / "qa.json", qa)
        raise QualityError(message) from exc
    result["qa_status"] = "pass"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        for key in ("data_dir", "output_dir"):
            value = getattr(args, key)
            if value is not None:
                config[key] = value.as_posix()
        if args.fetch:
            fetch(config)
        analyse(config)
    except (QualityError, NetworkBlocked, OSError, ValueError) as exc:
        print(
            f"configuration or output file is unavailable ({type(exc).__name__})"
            if isinstance(exc, OSError)
            else str(exc)
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
