#!/usr/bin/env python3
"""Reproduce the public BSEE Gulf jack-up and liftboat activity release."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import html
import io
import json
import os
import re
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import Request, urlopen

SOURCES = {
    "eWellWARRawData.zip": "https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip",
    "BoreholeRawData.zip": "https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip",
    "rigidlistdelimit.zip": "https://www.data.bsee.gov/Platform/Files/rigidlistdelimit.zip",
    "eWellAPDRawData.zip": "https://www.data.bsee.gov/Well/Files/eWellAPDRawData.zip",
    "eWellEORRawData.zip": "https://www.data.bsee.gov/Well/Files/eWellEORRawData.zip",
    "eWellAPMRawData.zip": "https://www.data.bsee.gov/Well/Files/eWellAPMRawData.zip",
}
MAX_DOWNLOAD_BYTES = 200_000_000
DEPTH_THRESHOLD_FT = 500
COLUMNS = (
    "activity_id",
    "api_well_number",
    "rig_name",
    "rig_id",
    "rig_type",
    "area_code",
    "block_number",
    "water_depth_ft",
    "borehole_water_depth_ft",
    "spud_date",
    "release_date",
    "activity_start_date",
    "activity_end_date",
    "operator",
    "rig_type_check",
    "type_check_types",
    "type_check_apd_ids",
    "type_check_rig_ids",
    "deep_water_flag",
    "quality_flags",
)
TYPE_CODES = {
    "JU": "JU",
    "JACKUP": "JU",
    "LB": "LB",
    "LIFTBOAT": "LB",
    "LIFT BOAT": "LB",
    "DS": "DS",
    "DRILLSHIP": "DS",
    "SS": "SS",
    "SEMISUBMERSIBLE": "SS",
    "SD": "SD",
    "DP SEMISUBMERSIBLE": "SD",
    "PF": "PF",
    "PLATFORM": "PF",
    "BR": "BR",
    "BARGE": "BR",
    "BARGE RIG": "BR",
    "SU": "SU",
    "SUBMERSIBLE": "SU",
}
TERMS_URL = "https://www.bsee.gov/bsee.gov/privacy-disclaimer"
RAW_INDEX_URL = "https://www.data.bsee.gov/Main/RawData.aspx"
DEPTH_REFERENCE_URL = (
    "https://www.bsee.gov/sites/bsee.gov/files/technology-and-research/"
    "td_1_oilandgasinfrastructure_01july2022_508.pdf"
)
FIELD_DEFINITIONS = {
    "activity_id": "WAR SN_WAR, unique report identifier; signed integer retained as text.",
    "api_well_number": "WAR API_WELL_NUMBER, exact BSEE borehole identifier; text, including leading zeroes.",
    "rig_name": "WAR RIG_NAME, spelling as published by BSEE.",
    "rig_id": "APM rig view RIG_ID_NUM, matched by case-insensitive, edge-trimmed rig name only.",
    "rig_type": "APM rig view RIG_TYPE_CODE: JU (jack-up) or LB (liftboat).",
    "area_code": "WAR SURF_AREA_CODE, surface area code.",
    "block_number": "WAR SURF_BLOCK_NUM, surface block; text, including leading zeroes.",
    "water_depth_ft": "WAR WATER_DEPTH, feet; empty when BSEE does not supply it.",
    "borehole_water_depth_ft": "Borehole WATER_DEPTH, feet; separately retained for comparison.",
    "spud_date": "Borehole WELL_SPUD_DATE, normalized to YYYY-MM-DD; borehole spud, not rig arrival.",
    "release_date": "Empty: no rig-release field exists in the inspected public WAR/borehole/EOR schemas.",
    "activity_start_date": "WAR WAR_START_DT, normalized to YYYY-MM-DD; reporting-period start.",
    "activity_end_date": "WAR WAR_END_DT, normalized to YYYY-MM-DD; reporting-period end, not rig release.",
    "operator": "WAR BUS_ASC_NAME, business associate/operator spelling as published by BSEE.",
    "rig_type_check": "agree, conflict or unavailable against other BSEE records joined by rig ID.",
    "type_check_types": "Distinct original APD RIG_TYPE_CODE / Rig ID List RIG_TYPE values, pipe-separated.",
    "type_check_apd_ids": "One representative SN_APD per observed type, pipe-separated; not all APDs.",
    "type_check_rig_ids": "Rig ID List identifiers used in the cross-check, pipe-separated.",
    "deep_water_flag": "true if either supplied depth exceeds 500 ft; unknown if a depth is missing/invalid and neither exceeds; otherwise false.",
    "quality_flags": "Pipe-separated screening annotations; release_date_unavailable applies to every row.",
}


def name_key(value: str) -> str:
    return value.strip().casefold()


def iso_date(value: str) -> str:
    try:
        return datetime.strptime(value.split()[0], "%m/%d/%Y").date().isoformat()
    except (ValueError, IndexError):
        return ""


def depth_value(value: str):
    try:
        number = Decimal(value)
        return number if number.is_finite() and number >= 0 else None
    except InvalidOperation:
        return None


def secondary_index(apds: list[dict], rig_list: list[dict]) -> dict:
    by_id = defaultdict(list)
    for apd in apds:
        if apd["RIG_ID_NUM"]:
            by_id[apd["RIG_ID_NUM"]].append(
                (apd["RIG_TYPE_CODE"], "apd", apd["SN_APD"])
            )
    for rig_row in rig_list:
        by_id[rig_row["RIG_ID"]].append((rig_row["RIG_TYPE"], "rig", rig_row["RIG_ID"]))
    return by_id


def check_type(rig_row: dict, secondary: dict) -> dict:
    evidence = secondary.get(rig_row["RIG_ID_NUM"], [])
    # One representative record per observed source/type is enough to audit the check.
    representatives = {}
    for kind, source, record_id in sorted(evidence):
        representatives.setdefault((kind, source), record_id)
    types = {kind for kind, _ in representatives}
    normalized = {TYPE_CODES.get(kind.upper(), kind) for kind in types}
    if not types:
        status = "unavailable"
    elif normalized == {rig_row["RIG_TYPE_CODE"]}:
        status = "agree"
    else:
        status = "conflict"
    return {
        "rig_type_check": status,
        "type_check_types": "|".join(sorted(types)),
        "type_check_apd_ids": "|".join(
            sorted(
                record
                for (_, source), record in representatives.items()
                if source == "apd"
            )
        ),
        "type_check_rig_ids": "|".join(
            sorted(
                record
                for (_, source), record in representatives.items()
                if source == "rig"
            )
        ),
    }


def derive_table(war, boreholes, rigs, apds, rig_list):
    """One row per WAR report; exact names only, no inferred rig classification."""
    borehole_index = {}
    for bore in boreholes:
        api = bore["API_WELL_NUMBER"]
        if api in borehole_index:
            raise ValueError("Duplicate borehole identity")
        borehole_index[api] = bore
    rig_index = defaultdict(list)
    for item in rigs:
        rig_index[name_key(item["RIG_NAME"])].append(item)
    secondary = secondary_index(apds, rig_list)
    type_checks = {r["RIG_ID_NUM"]: check_type(r, secondary) for r in rigs}
    seen, rows, excluded, anomaly_audit = set(), [], Counter(), []
    input_records = 0
    for report in war:
        input_records += 1
        record_id = report["SN_WAR"]
        if not record_id or record_id in seen:
            raise ValueError("Duplicate activity or missing activity identity")
        seen.add(record_id)
        start = iso_date(report["WAR_START_DT"])
        bore = borehole_index.get(report["API_WELL_NUMBER"])
        candidates = rig_index.get(name_key(report["RIG_NAME"]), [])
        if not start:
            reason = "invalid_activity_start"
        elif not "1997" <= start[:4] <= "2025":
            reason = "outside_year_range"
        elif bore is None:
            reason = "missing_borehole"
        elif bore["REGION_CODE"] != "G":
            reason = "outside_gulf"
        elif not candidates:
            reason = "unmatched_rig_name"
        elif len(candidates) != 1:
            reason = "ambiguous_rig_name"
        elif candidates[0]["RIG_TYPE_CODE"] not in {"JU", "LB"}:
            reason = "other_rig_type"
        else:
            reason = ""
        if report["WATER_DEPTH"] == "8831":
            anomaly_audit.append(
                {
                    "activity_id": record_id,
                    "api_well_number": report["API_WELL_NUMBER"],
                    "rig_name": report["RIG_NAME"],
                    "water_depth_ft": "8831",
                    "disposition": reason or "retained_flagged",
                }
            )
        if reason:
            excluded[reason] += 1
            continue
        rig_row = candidates[0]
        end = iso_date(report["WAR_END_DT"])
        spud = iso_date(bore["WELL_SPUD_DATE"])
        water, bore_water = depth_value(report["WATER_DEPTH"]), depth_value(
            bore["WATER_DEPTH"]
        )
        flags = ["release_date_unavailable"]
        if any(d is not None and d > DEPTH_THRESHOLD_FT for d in (water, bore_water)):
            deep = "true"
            flags.append("depth_above_500_ft")
        else:
            deep = "unknown" if water is None or bore_water is None else "false"
        if water is None:
            flags.append("invalid_or_missing_report_water_depth")
        if bore_water is None:
            flags.append("invalid_or_missing_borehole_water_depth")
        if water is not None and bore_water is not None and water != bore_water:
            flags.append("water_depth_disagreement")
        if not end or end < start:
            flags.append("invalid_activity_end")
        if not spud:
            flags.append("spud_date_unavailable")
        if report["RIG_NAME"].lstrip().startswith("*"):
            flags.append("generic_rig_identity")
        check = type_checks[rig_row["RIG_ID_NUM"]]
        if check["rig_type_check"] != "agree":
            flags.append("rig_type_check_" + check["rig_type_check"])
        rows.append(
            {
                "activity_id": record_id,
                "api_well_number": report["API_WELL_NUMBER"],
                "rig_name": report["RIG_NAME"],
                "rig_id": rig_row["RIG_ID_NUM"],
                "rig_type": rig_row["RIG_TYPE_CODE"],
                "area_code": report["SURF_AREA_CODE"],
                "block_number": report["SURF_BLOCK_NUM"],
                "water_depth_ft": report["WATER_DEPTH"],
                "borehole_water_depth_ft": bore["WATER_DEPTH"],
                "spud_date": spud,
                "release_date": "",
                "activity_start_date": start,
                "activity_end_date": end,
                "operator": report["BUS_ASC_NAME"],
                **check,
                "deep_water_flag": deep,
                "quality_flags": "|".join(sorted(flags)),
            }
        )
    rows.sort(key=lambda r: int(r["activity_id"]))
    years = Counter(r["activity_start_date"][:4] for r in rows)
    counts = {
        "input_records": input_records,
        "output_records": len(rows),
        "excluded": dict(excluded),
        "records_per_year": {str(y): years[str(y)] for y in range(1997, 2026)},
        "rig_types": dict(Counter(r["rig_type"] for r in rows)),
        "rig_type_checks": dict(Counter(r["rig_type_check"] for r in rows)),
        "deep_water_records": sum(r["deep_water_flag"] == "true" for r in rows),
        "source_8831_ft_record_audit": anomaly_audit,
    }
    return rows, counts


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1_048_576), b""):
            result.update(chunk)
    return result.hexdigest()


def write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
    if json.loads(path.read_text(encoding="utf-8")) != value:
        raise OSError("JSON readback differs")


def download_sources(raw_dir: Path) -> dict:
    """Retain immutable archives outside Git, with digests of read-back bytes."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name in (*SOURCES, "source_manifest.json"):
        if (raw_dir / name).exists():
            raise FileExistsError("Choose a new raw snapshot directory")
    manifest = {
        "owner": "worldenergydata",
        "source_id": "bsee-data-center",
        "sources": [],
    }
    for name, url in SOURCES.items():
        manifest["sources"].append(download_one(raw_dir, name, url))
    write_json(raw_dir / "source_manifest.json", manifest)
    verify_sources(raw_dir, manifest)
    return manifest


def retain_blob(raw_dir: Path, target: Path, entry: dict) -> dict:
    relative = f"blobs/sha256/{entry['sha256'][:2]}/{entry['sha256']}.zip"
    blob = raw_dir / relative
    blob.parent.mkdir(parents=True, exist_ok=True)
    if blob.exists():
        if digest(blob) != entry["sha256"]:
            raise ValueError("Retained blob digest mismatch")
    else:
        target.rename(blob)
    return {**entry, "archive_path": relative}


def download_one(raw_dir: Path, name: str, url: str) -> dict:
    if SOURCES.get(name) != url:
        raise ValueError("Source identity mismatch")
    request = Request(url, headers={"User-Agent": "worldenergydata-public-data/1.0"})
    target = raw_dir / name
    size = 0
    received = hashlib.sha256()
    # Exact membership in the fixed BSEE HTTPS allowlist is checked above.
    with (
        urlopen(request, timeout=60) as response,  # nosec B310 -- fixed BSEE HTTPS allowlist
        target.open("xb") as output,
    ):
        if response.geturl() != url:
            raise ValueError("Unexpected download redirect")
        while chunk := response.read(1_048_576):
            size += len(chunk)
            if size > MAX_DOWNLOAD_BYTES:
                raise ValueError("Download exceeds size bound")
            received.update(chunk)
            output.write(chunk)
    if digest(target) != received.hexdigest() or target.stat().st_size != size:
        raise ValueError("Download readback differs from received bytes")
    entry = {
        "file": name,
        "url": url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": digest(target),
        "size_bytes": size,
    }
    print(f"Retained {name}: {size} bytes", flush=True)
    return retain_blob(raw_dir, target, entry)


def verify_sources(raw_dir: Path, manifest: dict) -> None:
    entries = manifest["sources"]
    if len(entries) != len(SOURCES) or {e["file"] for e in entries} != set(SOURCES):
        raise ValueError("Incomplete or duplicate source set")
    for entry in entries:
        name = entry["file"]
        if entry["url"] != SOURCES[name]:
            raise ValueError("Source identity mismatch")
        if not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise ValueError("Source digest identity is invalid")
        expected_path = f"blobs/sha256/{entry['sha256'][:2]}/{entry['sha256']}.zip"
        if entry["archive_path"] != expected_path:
            raise ValueError("Source archive identity mismatch")
        path = raw_dir / expected_path
        if (
            path.stat().st_size != entry["size_bytes"]
            or digest(path) != entry["sha256"]
        ):
            raise ValueError(f"Source digest mismatch: {name}")


def read_rows(path: Path, member: str, required: set[str], fieldnames=None):
    """Read selected members without extracting any archive paths."""
    with zipfile.ZipFile(path) as archive:
        info = archive.getinfo(member)
        if info.file_size > 500_000_000:
            raise ValueError("Uncompressed member exceeds size bound")
        with archive.open(info) as raw:
            reader = csv.DictReader(
                io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""),
                fieldnames=fieldnames,
            )
            if not required.issubset(reader.fieldnames or []):
                raise ValueError(f"Missing columns in {member}")
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"Malformed row in {member}")
                yield row


def data_card(manifest: dict) -> str:
    counts = manifest["counts"]
    fields = "".join(
        f"<tr><td><code>{field}</code></td><td>{html.escape(description)}</td></tr>"
        for field, description in FIELD_DEFINITIONS.items()
    )
    years = "".join(
        f"<tr><td>{year}</td><td>{count:,}</td></tr>"
        for year, count in counts["records_per_year"].items()
    )
    sources = "".join(
        f'<li><a href="{entry["url"]}">{entry["file"]}</a>: '
        f'retrieved {entry["retrieved_at_utc"]}; SHA-256 <code>{entry["sha256"]}</code>.</li>'
        for entry in manifest["sources"]
    )
    exclusions = ", ".join(
        f"{name}: {count:,}" for name, count in sorted(counts["excluded"].items())
    )
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>US Gulf of Mexico jack-up and liftboat activity, 1997 to 2025</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#172b3a}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}}td,th{{border:1px solid #bbc8cf;padding:.5rem;text-align:left}}
code{{overflow-wrap:anywhere}}caption{{caption-side:bottom;text-align:left}}a{{color:#075985}}</style>
<h1>US Gulf of Mexico jack-up and liftboat activity, 1997 to 2025</h1>
<h2>Summary</h2>
<p>A BSEE-only, exact-name-matched subset contains {counts['output_records']:,} WAR reporting records
from {counts['input_records']:,} source reports. Each row represents one report, not one well, vessel visit or completed operation.
The subset contains {counts['rig_types'].get('JU', 0):,} jack-up and {counts['rig_types'].get('LB', 0):,} liftboat reports;
{counts['deep_water_records']:,} reports exceed the 500 ft screening threshold in at least one supplied depth and remain flagged.</p>
<h2>Revision history</h2>
<table><caption>Revision history.</caption><tr><th>Revision</th><th>Date</th><th>What changed and why</th></tr>
<tr><td>1</td><td>{manifest['retrieval_date']}</td><td>Initial release: BSEE activity subset with provenance, cross-checks and visible source limitations.</td></tr></table>
<h2>Download and scope</h2>
<p><a href="{manifest['table']['file']}">Download the UTF-8 CSV (gzip)</a>. The table has {len(COLUMNS)} columns.
The <a href="manifest.json">manifest</a> binds the compressed and uncompressed bytes and all retained source archives by SHA-256.</p>
<p>The stable URL pattern after merge is
<code>https://raw.githubusercontent.com/&lt;repository-owner&gt;/worldenergydata/main/data/modules/bsee/jackup_liftboat_activity/{manifest['table']['file']}</code>.
The default-branch URL will change on refresh; use a commit SHA in place of <code>main</code> for an immutable citation.</p>
<p>Selection uses WAR_START_DT from 1997-01-01 through 2025-12-31, Borehole REGION_CODE=G,
and APM rig view RIG_TYPE_CODE in JU/LB. Rig names are matched only after edge trimming and case folding;
the published WAR names are preserved. Unmatched and ambiguous names are excluded and counted, without guessing a rig class.
No fuzzy matching, contractor-page data or contact fields are used. The full Gulf activity population is not established by this subset.</p>
<h2>Sources, terms and refresh</h2>
<p>Owner: worldenergydata. Source catalog identities: bsee-data-center and bsee-ewell-war.
Retrieval date: {manifest['retrieval_date']}. Licence basis: US federal government public data.
<a href="{TERMS_URL}">BSEE's stated terms</a> permit distribution and copying of its public information,
request attribution and provide no warranty of accuracy or completeness.
The <a href="https://www.data.bsee.gov/Main/HtmlPage.aspx?page=Disclaimer">Data Center disclaimer</a> also applies.
No separate Creative Commons licence is asserted.</p>
<ul>{sources}</ul>
<p>The <a href="{RAW_INDEX_URL}">BSEE raw-download index</a> states daily updates for WAR, borehole, APD, APM and EOR.
Next planned refresh: <strong>{manifest['next_refresh_date']}</strong>, following that daily cadence rather than a quarterly default.
This is a planned date; the repository script does not install a scheduler.</p>
<h2>Field definitions</h2>
<table><caption>Published fields; depths are in feet and normalized dates use YYYY-MM-DD.</caption>
<tr><th>Field</th><th>Definition and source</th></tr>{fields}</table>
<p>Original definitions:
<a href="https://www.data.bsee.gov/Well/eWellWAR/FieldDefinitions.aspx">WAR</a>,
<a href="https://www.data.bsee.gov/Well/eWellAPD/FieldDefinitions.aspx">APD</a>,
<a href="https://www.data.bsee.gov/Well/eWellAPM/FieldDefinitions.aspx">APM</a>,
<a href="https://www.data.bsee.gov/Main/HtmlPage.aspx?page=borehole">borehole</a> and
<a href="https://www.data.bsee.gov/Main/HtmlPage.aspx?page=rigIDList">Rig ID List</a>.</p>
<h2>Screening and known limits</h2>
<p>The threshold is strictly greater than 500 ft, from BSEE-USCG,
<a href="{DEPTH_REFERENCE_URL}">Offshore Oil and Gas Infrastructure for the GOM, Technical Document 1</a>,
1 July 2022, Figure 4 (printed page 6), which gives jack-up water depths up to 500 ft.
This published upper range is used for plausibility screening, not as a record of the world's deepest achieved operation
or a vessel-specific operating limit. The same permissive threshold screens liftboats; a false flag does not establish vessel capability.</p>
<p>Depths are not corrected or substituted. A disagreement between WAR and borehole values is flagged.
A borehole depth may describe a subsea well rather than the rig's physical location; no elevation, leg length or geotechnical basis is supplied.
Blank/negative/non-numeric depths are retained and marked. Generic rig labels beginning with an asterisk are retained and flagged.</p>
<p>The nine 8,831 ft source WAR records identify <code>CR LUIGS</code> and have no exact name match in the coded rig view.
Their identifiers and exclusion reasons are preserved in <code>source_8831_ft_record_audit</code> in the manifest.
BSEE's coded rig view lists <code>GSF C.R. LUIGS</code> as DS (drillship), not JU.
No alias or jack-up classification is invented to place those nine records into this subset.
The 8,831 ft jack-up screening case is covered by an offline test; it is not a claim that such a retained source row exists.</p>
<p>Type cross-checks use other BSEE records by RIG_ID_NUM, including APD descriptions and the Rig ID List.
They test consistency between records, not independent physical inspection; current registry values may not describe a historical configuration.
Agreement: {counts['rig_type_checks'].get('agree', 0):,}; conflict: {counts['rig_type_checks'].get('conflict', 0):,};
unavailable: {counts['rig_type_checks'].get('unavailable', 0):,}. Missing secondary evidence is not treated as agreement.</p>
<p>Release dates are not established: the inspected WAR, borehole and EOR main schemas do not supply them.
Every release_date is empty and flagged. Reporting-period end and borehole total-depth date are not rig-release dates.
Spud dates describe the borehole and may precede the report by years. These records cannot establish rig visits,
utilisation, operating days, exposure or site-assessment suitability. Early years and historical name variants have incomplete coverage.</p>
<p>Exclusions (one reason per source record, in selection order): {exclusions}.
No depth or cross-check flag removes an otherwise selected row. Counts reflect records, not unique wells or rigs.</p>
<h2>Record counts per year</h2>
<table><caption>Retained WAR records, grouped by report-start year.</caption><tr><th>Year</th><th>Records</th></tr>{years}</table>
<h2>Reproduction and retention</h2>
<p>Raw archives remain outside Git under the configured <code>BSEE_JACKUP_RAW_DIR</code>, using the documented
<code>blobs/sha256/&lt;first-two-hex&gt;/&lt;sha256&gt;.zip</code> external-data layout.
This directory is the repository's external data root within the shared data store; no machine location is embedded in this release.
The raw files exceed the repository file-size limit and are not committed. They remain public BSEE downloads,
but a later download at the same URL may differ; digest-matched retained blobs are needed for exact reproduction.</p>
<pre>uv run --no-project python scripts/bsee/build_jackup_activity.py --raw-dir "$BSEE_JACKUP_RAW_DIR" --output-dir "$BSEE_JACKUP_OUTPUT_DIR"
uv run --no-project python scripts/bsee/build_jackup_activity.py --raw-dir "$BSEE_JACKUP_RAW_DIR" --reuse-manifest data/modules/bsee/jackup_liftboat_activity/manifest.json --output-dir "$BSEE_JACKUP_OUTPUT_DIR"
uv run --no-project python scripts/bsee/build_jackup_activity.py --verify-only --output-dir data/modules/bsee/jackup_liftboat_activity</pre>
<p>Use a new raw directory for a download and a new output directory for regeneration. No existing raw or release file is overwritten.
Offline tests: <code>tests/unit/bsee/data/test_jackup_activity.py</code> and <code>test_jackup_activity_release.py</code>.</p>
</html>
"""


def write_release(
    output: Path, rows: list[dict], counts: dict, source: dict, retrieval: str
) -> dict:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    raw = buffer.getvalue().encode("utf-8")
    table_path = output / "activity_1997_2025.csv.gz"
    with table_path.open("xb") as stream:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=stream, mtime=0, compresslevel=9
        ) as zipped:
            zipped.write(raw)
    if table_path.stat().st_size > 1_000_000:
        raise ValueError("Published table exceeds repository file-size limit")
    manifest = {
        **source,
        "schema_version": 1,
        "criteria_version": "1",
        "dataset_id": "us_gom_jackup_liftboat_activity_1997_2025",
        "source_ids": ["bsee-data-center", "bsee-ewell-war"],
        "retrieval_date": retrieval,
        "next_refresh_date": (
            date.fromisoformat(retrieval) + timedelta(days=1)
        ).isoformat(),
        "refresh_basis": {
            "cadence": "daily",
            "source_url": RAW_INDEX_URL,
            "automatic": False,
        },
        "licence": "US federal government public data; BSEE stated distribution and copying terms",
        "terms_url": TERMS_URL,
        "counts": counts,
        "depth_screening": {
            "threshold_ft": DEPTH_THRESHOLD_FT,
            "comparison": ">",
            "source_url": DEPTH_REFERENCE_URL,
            "locator": "Figure 4, printed page 6",
        },
        "raw_storage": "External content-addressed blobs relative to BSEE_JACKUP_RAW_DIR; no raw archive committed",
        "fields": FIELD_DEFINITIONS,
        "table": {
            "file": table_path.name,
            "sha256": digest(table_path),
            "size_bytes": table_path.stat().st_size,
            "uncompressed_sha256": hashlib.sha256(raw).hexdigest(),
            "uncompressed_size_bytes": len(raw),
            "columns": list(COLUMNS),
            "rows": len(rows),
        },
    }
    write_json(output / "manifest.json", manifest)
    card = output / "data_card.html"
    with card.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(data_card(manifest))
    if card.read_text(encoding="utf-8") != data_card(manifest):
        raise OSError("Data card readback differs")
    if verify_release(output) != rows:
        raise OSError("Table readback differs")
    return manifest


def verify_release(output: Path) -> list[dict]:
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    table = manifest["table"]
    path = output / "activity_1997_2025.csv.gz"
    if (
        table["file"] != path.name
        or digest(path) != table["sha256"]
        or path.stat().st_size != table["size_bytes"]
    ):
        raise ValueError("Published table digest/size mismatch")
    raw = gzip.decompress(path.read_bytes())
    if (
        hashlib.sha256(raw).hexdigest() != table["uncompressed_sha256"]
        or len(raw) != table["uncompressed_size_bytes"]
    ):
        raise ValueError("Uncompressed table digest/size mismatch")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    if reader.fieldnames != list(COLUMNS) or table["columns"] != list(COLUMNS):
        raise ValueError("Published schema mismatch")
    rows = list(reader)
    if len(rows) != table["rows"] or len(rows) != manifest["counts"]["output_records"]:
        raise ValueError("Published row count mismatch")
    if len({r["activity_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate published activity identity")
    for row in rows:
        if (
            row["rig_type"] not in {"JU", "LB"}
            or not "1997" <= row["activity_start_date"][:4] <= "2025"
        ):
            raise ValueError("Published selection mismatch")
    return rows


def build_release(raw_dir: Path, source: dict, output: Path) -> dict:
    verify_sources(raw_dir, source)
    paths = {
        entry["file"]: raw_dir / entry["archive_path"] for entry in source["sources"]
    }
    war = read_rows(
        paths["eWellWARRawData.zip"],
        "eWellWARRawData/mv_war_main.txt",
        {
            "SN_WAR",
            "API_WELL_NUMBER",
            "RIG_NAME",
            "WAR_START_DT",
            "WAR_END_DT",
            "WATER_DEPTH",
            "SURF_AREA_CODE",
            "SURF_BLOCK_NUM",
            "BUS_ASC_NAME",
        },
    )
    boreholes = read_rows(
        paths["BoreholeRawData.zip"],
        "BoreholeRawData/mv_boreholes_all.txt",
        {
            "API_WELL_NUMBER",
            "REGION_CODE",
            "WELL_SPUD_DATE",
            "WATER_DEPTH",
        },
    )
    rigs = list(
        read_rows(
            paths["eWellAPMRawData.zip"],
            "eWellAPMRawData/mv_apm_rig_view.txt",
            {
                "RIG_ID_NUM",
                "RIG_NAME",
                "RIG_TYPE_CODE",
            },
        )
    )
    apds = list(
        read_rows(
            paths["eWellAPDRawData.zip"],
            "eWellAPDRawData/mv_apd_main.txt",
            {
                "SN_APD",
                "RIG_ID_NUM",
                "RIG_TYPE_CODE",
            },
        )
    )
    rig_list = list(
        read_rows(
            paths["rigidlistdelimit.zip"],
            "rigidlistdelimit.txt",
            {
                "RIG_ID",
                "RIG_NAME",
                "RIG_TYPE",
            },
            fieldnames=["RIG_ID", "RIG_NAME", "RIG_TYPE"],
        )
    )
    rows, counts = derive_table(war, boreholes, rigs, apds, rig_list)
    if not rows:
        raise ValueError("Refusing to publish an empty activity release")
    output.mkdir(parents=True, exist_ok=False)
    retrieval = max(entry["retrieved_at_utc"][:10] for entry in source["sources"])
    return write_release(output, rows, counts, source, retrieval)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir", type=Path, default=os.environ.get("BSEE_JACKUP_RAW_DIR")
    )
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--reuse-manifest", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "data/modules/bsee/jackup_liftboat_activity",
    )
    args = parser.parse_args()
    if args.verify_only:
        print(
            f"Verified {len(verify_release(args.output_dir))} published activity records"
        )
        return
    if args.raw_dir is None:
        parser.error("Set BSEE_JACKUP_RAW_DIR or --raw-dir to external raw storage")
    raw_dir = args.raw_dir.resolve()
    root = Path(__file__).resolve().parents[2]
    if raw_dir == root or root in raw_dir.parents:
        parser.error("Raw storage must be outside this checkout")
    if not args.download_only and args.output_dir.exists():
        parser.error("Choose a new output directory; existing releases are retained")
    if args.reuse_manifest:
        source = json.loads(args.reuse_manifest.read_text(encoding="utf-8"))
        verify_sources(raw_dir, source)
    else:
        source = download_sources(raw_dir)
    if not args.download_only:
        manifest = build_release(raw_dir, source, args.output_dir)
        print(json.dumps(manifest["counts"], indent=2))


if __name__ == "__main__":
    main()
