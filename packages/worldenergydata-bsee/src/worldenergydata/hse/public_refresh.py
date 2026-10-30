"""Reproducible public INCINV refresh; standard library only.

Counts describe investigation records, not exposure-normalized incident rates.
QA fails closed before classification. No raw narratives or identities are exported.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import logging
import subprocess
import sys
import types
import zipfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

SOURCE_URL = "https://www.data.bsee.gov/Other/Files/IncInvRawData.zip"
HEADLINES = "drilling-hse-patterns-2026-07-05.json"
INVENTORY = "intervention-hse-patterns-2026-05-18-explore.json"
HTML = "drilling-hse-patterns-2026-07-05.html"
CHARTS = {
    "drilling-phase-values": "drill_subactivity_distribution",
    "drilling-severity-values": "drill_severity_proxy",
    "drilling-year-values": "drill_by_year",
    "drilling-area-values": "drill_top_areas",
}
KEYS = ("DATE_OCCURRED", "MILITARY_TIME", "AREA_BLOCK", "ACCIDENT_TYPE")
COLUMNS = (*KEYS, "LEASE_NUMBER", "PANEL_DISTRICT", "STATUS")
# Analyst-selected inventory terms; basis and limitations: docs/hse/public-refresh.md.
KEYWORDS = (
    "workover",
    "intervention",
    "wireline",
    "coil tubing",
    "coiled tubing",
    "snubbing",
    "well control",
    "well work",
    "p&a",
    "plug and abandon",
)


class QAError(ValueError):
    """Source integrity or QA did not qualify the input for analysis."""


class NetworkError(RuntimeError):
    """The public source could not be downloaded."""


def _utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _download(url, destination):
    """Use curl without credentials; retain response bytes and status on disk."""
    response = subprocess.run(
        [
            "curl",
            "--location",
            "--fail",
            "--connect-timeout",
            "30",
            "--max-time",
            "180",
            "--output",
            str(destination),
            "--dump-header",
            str(destination.with_suffix(".headers")),
            "--write-out",
            "%{http_code}",
            url,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    status = response.stdout.strip()
    # Reset on every response so redirect headers cannot describe the final body.
    headers = {}
    header_path = destination.with_suffix(".headers")
    if header_path.exists():
        for line in header_path.read_bytes().decode("latin-1").splitlines():
            if line.startswith("HTTP/"):
                headers = {}
            elif ":" in line:
                key, value = line.split(":", 1)
                headers[key.lower()] = value.strip()
    evidence = {
        "etag": headers.get("etag"),
        "last_modified": headers.get("last-modified"),
    }
    _write_json(
        destination.with_suffix(".request.json"),
        {
            "url": url,
            "requested_at": _utc(),
            "http_status": status,
            "curl_exit_code": response.returncode,
            **evidence,
        },
    )
    if response.returncode or status != "200":
        raise NetworkError(f"BLOCKED-NETWORK: {url}; HTTP {status or 'unavailable'}")
    return {"http_status": int(status), **evidence}


def _verify_public_files(data_dir, entries):
    """Require successful retrieval and an extracted member matching its archive."""
    if len(entries) != 2 or {entry["file"] for entry in entries} != {
        "IncInvRawData.zip",
        "mv_acc_investigations.txt",
    }:
        raise QAError("provenance: incomplete public download")
    if any(
        type(entry.get("http_status")) is not int or entry["http_status"] != 200
        for entry in entries
    ):
        raise QAError("provenance: public retrieval requires HTTP 200")
    member = "IncInvRawData/mv_acc_investigations.txt"
    entry = next(e for e in entries if e["file"] == "mv_acc_investigations.txt")
    if entry.get("archive_member") != member:
        raise QAError("provenance: unexpected archive member")
    with zipfile.ZipFile(data_dir / "IncInvRawData.zip") as archive:
        payload = archive.read(member)
    if (
        len(payload) != entry["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != entry["sha256"]
    ):
        raise QAError("provenance: extracted file differs from archive member")


def _verified_files(data_dir, manifest, source_kind):
    try:
        if (
            manifest["source_kind"] not in {"public", "synthetic"}
            or manifest["source_kind"] != source_kind
        ):
            raise QAError("provenance: source kind mismatch")
        entries = manifest["files"]
        if not isinstance(entries, list) or not entries:
            raise QAError("provenance: empty or invalid manifest entries")
        for entry in entries:
            name = entry["file"]
            if Path(name).name != name:
                raise QAError("provenance: file must be a basename")
            path = data_dir / name
            if (
                path.stat().st_size != entry["size_bytes"]
                or _digest(path) != entry["sha256"]
            ):
                raise QAError("integrity: size or SHA-256 mismatch")
            if entry["url"] != SOURCE_URL:
                raise QAError("provenance: unexpected source URL")
            stamp = datetime.fromisoformat(
                entry["downloaded_at"].replace("Z", "+00:00")
            )
            if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
                raise QAError("provenance: download date must be UTC")
            if stamp > datetime.now(timezone.utc):
                raise QAError("provenance: future download date")
        if manifest["source_kind"] == "public":
            _verify_public_files(data_dir, entries)
        return entries
    except QAError:
        raise
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        RuntimeError,
        zipfile.BadZipFile,
    ) as exc:
        raise QAError("provenance: missing or invalid manifest evidence") from exc


def fetch(config):
    """Download and extract the exact public member; resume verified downloads.

    A manifest is sealed only after the archive and extracted member exist.
    No arbitrary ZIP paths are extracted. The raw archive stays outside Git.
    """
    data_dir = Path(config["data_dir"])
    data_dir.mkdir(parents=True, exist_ok=True)
    url = config["url"]
    if url != SOURCE_URL:
        raise ValueError("Only the configured public INCINV source is supported")
    manifest_path = data_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        _verified_files(data_dir, manifest, "public")
        return manifest
    archive = data_dir / "IncInvRawData.zip"
    response_evidence = _download(url, archive)
    stamp = _utc()
    member = "IncInvRawData/mv_acc_investigations.txt"
    with zipfile.ZipFile(archive) as zipped:
        raw = data_dir / "mv_acc_investigations.txt"
        raw.write_bytes(zipped.read(member))
    entries = []
    for path in (archive, raw):
        entries.append(
            {
                "file": path.name,
                "url": url,
                "downloaded_at": stamp,
                **response_evidence,
                "size_bytes": path.stat().st_size,
                "sha256": _digest(path),
            }
        )
    entries[1]["archive_member"] = member
    manifest = {"source_kind": "public", "files": entries}
    _verified_files(data_dir, manifest, "public")
    _write_json(manifest_path, manifest)
    return manifest


def _load_classifier(taxonomy):
    """Load the canonical taxonomy without optional database dependencies.

    Restore every module entry after loading; callers' package imports survive.
    Class methods retain their original module globals and canonical definitions.
    """
    taxonomy = Path(taxonomy)
    names = (
        "worldenergydata",
        "worldenergydata.common",
        "worldenergydata.common.logging",
        "worldenergydata.safety_analysis",
        "worldenergydata.safety_analysis.taxonomy",
    )
    base = names[-1]
    modules = ("activity_definitions", "activity_registry", "incident_classifier")
    saved = {
        name: sys.modules.get(name)
        for name in (*names, *(f"{base}.{m}" for m in modules))
    }
    try:
        for name in names:
            shell = types.ModuleType(name)
            shell.__path__ = []
            sys.modules[name] = shell
        sys.modules["worldenergydata.common.logging"].get_logger = logging.getLogger
        for module in modules:
            name = f"{base}.{module}"
            spec = importlib.util.spec_from_file_location(
                name, taxonomy / f"{module}.py"
            )
            loaded = importlib.util.module_from_spec(spec)
            sys.modules[name] = loaded
            spec.loader.exec_module(loaded)
        return loaded.IncidentClassifier()
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def _severity(text):
    """Analyst-defined first-match proxy, not a regulatory severity ranking.

    Vocabulary: BSEE NTL 2019-N05, Definitions (30 CFR 250.188 categories).
    LTA denotes lost-time accident; RW/JT denotes restricted work/job transfer;
    $25k matches source damage-category text, not an inflation-adjusted cutoff.
    Ranking and additional screening terms are explained in docs/hse/public-refresh.md.
    """
    text = text.lower()
    for terms, label in (
        (("fatality",), "fatality"),
        (("blowout", "explosion"), "major"),
        (("lta", "rw/jt", "injury"), "injury_lost_time"),
        (("fire", "pollution", "collision", "$25k"), "serious"),
        (("evacuation", "muster", "shutdown"), "evacuation_muster"),
    ):
        if any(term in text for term in terms):
            return label
    return "other"


def _qualify(config, qa):
    data_dir = Path(config["data_dir"])
    try:
        manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
        entries = _verified_files(data_dir, manifest, config["source_kind"])
        entry = next(e for e in entries if e["file"] == config["source_file"])
    except QAError:
        raise
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        raise QAError("provenance: missing or invalid manifest evidence") from exc
    if (config["quantity"], config["unit"]) != ("investigation records", "count"):
        raise QAError("unit: only investigation records [count] is supported")
    qa["unit_check"] = "investigation records [count]; no exposure denominator"
    try:
        text = (
            (data_dir / entry["file"])
            .read_bytes()
            .decode(config.get("encoding", "latin-1"))
        )
        with io.StringIO(text, newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if (
                not reader.fieldnames
                or not set(COLUMNS).issubset(reader.fieldnames)
                or len(reader.fieldnames) != len(set(reader.fieldnames))
            ):
                raise QAError("schema: required columns absent")
            rows = list(reader)
    except (UnicodeError, csv.Error) as exc:
        raise QAError("schema: unreadable CSV") from exc
    qa["row_count"] = len(rows)
    if not rows:
        raise QAError("row_count: empty source")
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise QAError("schema: malformed row")
    rows = [{k: v.strip() for k, v in row.items()} for row in rows]
    qa["missing_keys"] = sum(any(not row[key] for key in KEYS) for row in rows)
    qa["key_columns"] = list(KEYS)
    if qa["missing_keys"]:
        raise QAError("missing_keys: required composite key fields are blank")
    qa["duplicate_keys"] = len(rows) - len(
        {tuple(row[k] for k in KEYS) for row in rows}
    )
    if qa["duplicate_keys"]:
        raise QAError("duplicate_keys: repeated composite key")
    try:
        dates = [
            datetime.strptime(row["DATE_OCCURRED"], "%m/%d/%Y").date() for row in rows
        ]
        lower = date.fromisoformat(config["earliest_date"])
        upper = date.fromisoformat(config.get("latest_date", date.today().isoformat()))
        # A historical download cannot contain incidents after its retrieval date.
        upper = min(
            upper,
            datetime.fromisoformat(
                entry["downloaded_at"].replace("Z", "+00:00")
            ).date(),
        )
        if min(dates) < lower or max(dates) > upper:
            raise ValueError("outside configured range")
    except ValueError as exc:
        raise QAError("date_range: invalid or out-of-range incident date") from exc
    qa["date_range"] = [min(dates).isoformat(), max(dates).isoformat()]
    qa["missing_optional_leases"] = sum(not row["LEASE_NUMBER"] for row in rows)
    return rows, manifest


def _csv_outputs(out, result=None):
    for name, field in CHARTS.items():
        with (out / f"{name}.csv").open("w", encoding="utf-8", newline="\n") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["category", "investigation records [count]"])
            if result:
                writer.writerows(result[field].items())


def invalidate(config, reason):
    """Mark existing public artifacts unevaluated before a refresh begins."""
    out = Path(config["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    qa = {"status": "not_evaluated", "reason": reason}
    for name in (HEADLINES, INVENTORY, "incinv-qa.json", "incinv-manifest.json"):
        _write_json(out / name, qa)
    _csv_outputs(out)
    (out / HTML).write_text(
        '<!DOCTYPE html><html lang="en"><meta charset="utf-8">'
        "<title>HSE analysis not evaluated</title><h1>Not evaluated</h1>"
        "<p>Input QA has not qualified this refresh. See incinv-qa.json.</p></html>\n",
        encoding="utf-8",
        newline="\n",
    )
    return out, qa


def analyze(config):
    """Validate manifest and rows, then write aggregates and per-chart values.

    Prior outputs are marked not evaluated before any attempt. A failed QA
    cannot leave a successful JSON or values CSV from an earlier execution.
    """
    out, qa = invalidate(config, "refresh incomplete")
    try:
        rows, manifest = _qualify(config, qa)
    except (QAError, OSError, KeyError, TypeError, ValueError) as exc:
        qa["reason"] = (
            str(exc) if isinstance(exc, QAError) else "configuration: invalid input"
        )
        _write_json(out / "incinv-qa.json", qa)
        for name in (HEADLINES, INVENTORY):
            _write_json(out / name, {"status": "not_evaluated", "reason": qa["reason"]})
        raise QAError(qa["reason"]) from exc
    qa.update(status="pass", reason="all required checks passed")
    _write_json(out / "incinv-qa.json", qa)
    _write_json(out / "incinv-manifest.json", manifest)
    classifier = _load_classifier(config["taxonomy_dir"])
    classified = [(row, classifier.classify(row, source="bsee")) for row in rows]
    drill = [(row, result) for row, result in classified if result.activity == "DRILL"]

    def distribution(values):
        return dict(Counter(values).most_common())

    years = Counter(
        datetime.strptime(row["DATE_OCCURRED"], "%m/%d/%Y").year for row, _ in drill
    )

    def confidence_bucket(confidence):
        if confidence >= 0.90:
            return "direct_code(>=0.90)"
        if confidence >= 0.70:
            return "keyword_high(0.70-0.89)"
        if confidence >= 0.50:
            return "keyword_medium(0.50-0.69)"
        return "keyword_low(<0.50)"

    first_year = date.fromisoformat(qa["date_range"][0]).year
    last_year = date.fromisoformat(qa["date_range"][1]).year
    result = {
        "status": "evaluated",
        "generated_at": _utc(),
        "source": manifest,
        "source_file": config["source_file"],
        "quantity": "investigation records",
        "unit": "count",
        "methodology": "Canonical IncidentClassifier(source='bsee'), activity == DRILL; "
        "severity is an analyst-defined first-match accident-type proxy, "
        "not a regulatory ranking or injury or fatality counts. "
        "Vocabulary: BSEE NTL 2019-N05, Definitions; see docs/hse/public-refresh.md.",
        "incinv_total_records": len(rows),
        "drill_total": len(drill),
        "incinv_date_range": qa["date_range"],
        "drill_pct_of_incinv": round(100 * len(drill) / len(rows), 1),
        "activity_distribution_all_incinv": distribution(
            r.activity for _, r in classified
        ),
        "drill_subactivity_distribution": distribution(r.subactivity for _, r in drill),
        "drill_match_method": distribution(r.match_method for _, r in drill),
        "drill_confidence_buckets": distribution(
            confidence_bucket(r.confidence) for _, r in drill
        ),
        "drill_severity_proxy": distribution(
            _severity(row["ACCIDENT_TYPE"]) for row, _ in drill
        ),
        "drill_by_year": {
            str(year): years[year] for year in range(first_year, last_year + 1)
        },
        "drill_year_range": [min(years), max(years)] if years else None,
        "drill_top_areas": distribution(
            row["AREA_BLOCK"].split()[0] for row, _ in drill
        ),
        "drill_distinct_leases": len(
            {row["LEASE_NUMBER"] for row, _ in drill if row["LEASE_NUMBER"]}
        ),
        "limitations": [
            "Investigation records are not a complete incident census or a risk rate.",
            "Operational phases are derived from accident-type text, not reported service types.",
            "Composite keys detect exact event signatures; "
            "no public unique incident ID is supplied.",
            "Lease is optional; no operator identity, narrative or asset name is exported.",
        ],
    }
    inventory = {
        "status": "evaluated",
        "source": manifest,
        "source_file": config["source_file"],
        "quantity": "investigation records",
        "unit": "count",
        "total_rows": len(rows),
        "date_range": qa["date_range"],
        "missing_optional_leases": qa["missing_optional_leases"],
        "activity_distribution": result["activity_distribution_all_incinv"],
        "intervention_keyword_hits": {
            keyword: sum(keyword in row["ACCIDENT_TYPE"].lower() for row in rows)
            for keyword in KEYWORDS
        },
        "keyword_basis": "Literal case-insensitive ACCIDENT_TYPE matches; categories overlap; "
        "these are inventory signals, not confirmed interventions.",
        "war_join": {
            "status": "not_evaluated",
            "reason": "Public INCINV has no API well key; "
            "local databases and well activity reports are outside this refresh.",
        },
    }
    _csv_outputs(out, result)
    _write_json(out / INVENTORY, inventory)
    _write_json(out / HEADLINES, result)
    return result


def load_config(path, *, data_dir=None, output_dir=None):
    """Resolve configured paths relative to the config's declared base folder."""
    path = Path(path).resolve()
    config = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent / config.get("base_dir", ".")
    for key in ("data_dir", "output_dir", "taxonomy_dir"):
        config[key] = base / config[key]
    if data_dir is not None:
        config["data_dir"] = Path(data_dir)
    if output_dir is not None:
        config["output_dir"] = Path(output_dir)
    return config
