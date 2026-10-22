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
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen


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


def _manifest(config: dict) -> dict:
    path = Path(config["data_dir"]) / "manifest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
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
                with path.open("xb") as stream:
                    for chunk in iter(lambda: response.read(1024 * 1024), b""):
                        stream.write(chunk)
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
            any(not row[key] for key in spec["keys"] + spec["required"]) for row in rows
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
            except ValueError:
                checks["invalid_dates"] += 1
        if len(pair) == 2:
            span = (pair[1] - pair[0]).days
            checks["reversed_dates"] += int(span < 0)
            if "max_span_days" in spec:
                checks["implausible_span"] += int(span + 1 > spec["max_span_days"])
    return {
        "rows": len(rows),
        "date_min": min(dates).isoformat() if dates else None,
        "date_max": max(dates).isoformat() if dates else None,
        "unit": spec["unit"],
        "checks": checks,
    }


def _quality(tables: dict, config: dict, population: set[str]) -> dict:
    result = {"status": "pass", "tables": {}, "failures": []}
    for name, spec in config["tables"].items():
        qa = _table_qa(tables[name], spec, "record" if name == "activity" else "day")
        result["tables"][name] = qa
        result["failures"].extend(
            f"{name}: {check} ({count})"
            for check, count in qa["checks"].items()
            if count
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
    result["failures"].extend(
        f"{name} ({count})" for name, count in joins.items() if count
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


def _products(tables: dict, config: dict, population: set[str], sources: list) -> dict:
    import pandas as pd

    from worldenergydata.bsee.analysis.war_rig_days import (
        BASIS_DRL_COM,
        rig_days_by_bore,
        rig_days_by_well,
    )

    war = pd.DataFrame(tables["war"])
    activity = pd.DataFrame(tables["activity"])
    joined = war.merge(activity, on="SN_WAR", how="left", validate="one_to_many")
    bores = rig_days_by_bore(joined, basis=BASIS_DRL_COM, population=sorted(population))
    wells = rig_days_by_well(joined, basis=BASIS_DRL_COM, population=sorted(population))
    calendar = []
    for row in tables["boreholes"]:
        if row["API_WELL_NUMBER"] in population:
            start, end = _date(row["WELL_SPUD_DATE"]), _date(row["TOTAL_DEPTH_DATE"])
            calendar.append(
                [row["API_WELL_NUMBER"], start.isoformat(), (end - start).days]
            )
    annual = Counter(
        (str(_date(row["WAR_START_DT"]).year), row["WELL_ACTIVITY_CD"])
        for row in joined.to_dict("records")
    )

    def total(series):
        value = series.sum(min_count=1)
        return None if pd.isna(value) else float(value)

    headlines = {
        "calendar_median_days": statistics.median(row[2] for row in calendar),
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
            ["api12 [identifier]", "spud_date [date]", "calendar_days [day]"],
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
            ],
            [
                [
                    r.api12,
                    None if pd.isna(r.drilling_days) else r.drilling_days,
                    None if pd.isna(r.completion_days) else r.completion_days,
                    r.pnd_days,
                    r.days_status,
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

    QA covers entire supplied tables, before population filtering. No charts or
    headline values are written on failure; only the QA receipt is retained.
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
        qa["sources"] = manifest["files"]
        qa["population_sha256"] = _digest(Path(config["population_csv"]))
        qa["workflow_sha256"] = _digest(Path(__file__))
        qa["scope"] = "entire supplied tables before population filtering"
        _json(output / "qa.json", qa)
        if qa["status"] != "pass":
            raise QualityError("QA not-evaluated: see qa.json")
    except (QualityError, KeyError, ValueError, OSError, zipfile.BadZipFile) as exc:
        if not (output / "qa.json").exists():
            _json(
                output / "qa.json", {"status": "not-evaluated", "failures": [str(exc)]}
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
    return _products(tables, config, population, manifest["files"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
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
