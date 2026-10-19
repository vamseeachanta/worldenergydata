"""Fetch, fingerprint and check the public incident-analysis inputs.

Raw payloads remain outside the repository. Counts describe rows, not unique
worldwide events. GISIS is deliberately excluded from this collection.
"""

import argparse
import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import pandas as pd
from requests import HTTPError, RequestException, get

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "config/marine_safety_input_manifest.json"
UNKNOWN = "NOT_EVALUATED"
SOURCES = (
    {
        "id": "canadian_tsb",
        "path": "canadian_tsb/occurrence.csv",
        "url": "https://www.tsb.gc.ca/sites/default/files/stats/"
        "MARSISdb_MDOTW_VW_OCCURRENCE_PUBLIC.csv",
        "landing_url": "https://open.canada.ca/data/en/dataset/"
        "ad8d1b73-df09-4521-9bdb-61c529328218",
    },
    {
        "id": "dlp_historical",
        "path": "dlp_historical/Accidents_1995-2012.csv",
        "url": "https://raw.githubusercontent.com/data-liberation-project/"
        "boating-accident-reports-1995-2012-muckrock/"
        "e637c182915bdc441e63a13641eaaf9a2c541463/data/converted/Accidents.csv",
        "landing_url": "https://github.com/data-liberation-project/"
        "boating-accident-reports-1995-2012-muckrock",
    },
)
REQUIRED_COLUMNS = {
    "canadian_tsb": {
        "OccID",
        "OccDate",
        "Summary",
        "AccIncTypeDisplayEng",
        "TotalDeaths",
    },
    "dlp_historical": {
        "BARDID",
        "Date",
        "Redactednarrative",
        "AccidentEvent1",
        "Numberdeaths",
    },
}


def sha256(path):
    """Hash the retained bytes without loading a large export into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_source(path, source_id):
    frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    missing = REQUIRED_COLUMNS[source_id] - set(frame.columns)
    if missing:
        raise ValueError(f"Required columns missing for {source_id}: {sorted(missing)}")
    return frame


def normalize(frame, source_id):
    """Normalize the two public schemas without deduplication or date filtering."""
    tsb = source_id == "canadian_tsb"

    def column(name, default=""):
        return frame[name].fillna(default) if name in frame else default

    def number(name):
        return pd.to_numeric(column(name, 0), errors="raise")

    return pd.DataFrame(
        {
            "incident_id": column("OccID" if tsb else "BARDID"),
            "date": pd.to_datetime(
                column("OccDate" if tsb else "Date"), errors="coerce", format="mixed"
            ),
            "vessel_name": "",
            "description": column("Summary" if tsb else "Redactednarrative"),
            "severity": column("OccClassDisplayEng", "Unknown") if tsb else "Unknown",
            "location": column("ProvinceDisplayEng") if tsb else column("State"),
            "fatalities": number("TotalDeaths" if tsb else "Numberdeaths"),
            "injuries": (
                number("TotalMinorInjuries") + number("TotalSeriousInjuries")
                if tsb
                else number("Numberinjured")
            ),
            "incident_type": column(
                "AccIncTypeDisplayEng" if tsb else "AccidentEvent1"
            ),
            "source": "Canadian TSB" if tsb else "DLP Historical",
        },
        index=frame.index,
    )


def analyse_frames(frames):
    combined = pd.concat(
        [normalize(frame, source_id) for source_id, frame in frames.items()],
        ignore_index=True,
    )
    retained = combined[combined["description"].str.strip().ne("")].copy()
    foundering = retained[
        retained["incident_type"].str.contains(
            "founder|capsiz|sinking", case=False, na=False
        )
    ]
    fatality = retained[retained["fatalities"] > 0]
    counts = {
        "input_rows": len(combined),
        "excluded_empty_description_rows": len(combined) - len(retained),
        "analysed_rows": len(retained),
        "foundering_rows": len(foundering),
        "fatal_incident_rows": len(fatality),
    }
    return {
        "all_incidents": retained,
        "hatch": retained,
        "foundering": foundering,
        "fatality": fatality,
        "counts": counts,
    }


def load_inputs(raw_dir, manifest_path=DEFAULT_MANIFEST):
    """Require both files, their recorded digests and exact count agreement."""
    if raw_dir is None:
        raise FileNotFoundError("Required incident input directory: supply --input-dir")
    root = Path(raw_dir).resolve()
    manifest = json.loads(Path(manifest_path).read_text())
    sources = manifest["sources"]
    if sorted(source["id"] for source in sources) != sorted(REQUIRED_COLUMNS):
        raise ValueError("Manifest must contain exactly the two public sources")
    frames = {}
    for source in sources:
        path = (root / source["path"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Input path must remain inside the raw input directory")
        if not path.is_file():
            raise FileNotFoundError(
                f"Required incident input missing: {source['path']}"
            )
        if source["status"] != "FETCHED":
            raise ValueError(
                f"Input is NOT_EVALUATED: {source['id']}; run the fetch script"
            )
        if sha256(path) != source["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {source['id']}")
        frame = read_source(path, source["id"])
        if len(frame) != source["row_count"]:
            raise ValueError(f"Count agreement failed: {source['id']} row_count")
        frames[source["id"]] = frame
    result = analyse_frames(frames)
    if result["counts"] != manifest["counts"]:
        raise ValueError("Count agreement failed: analysis differs from manifest")
    result["manifest"] = manifest
    return result


def fetch_inputs(raw_dir, manifest_path=DEFAULT_MANIFEST):
    """Retain immutable downloads and record unavailable sources explicitly."""
    root = Path(raw_dir).resolve()
    if root == REPO_ROOT or REPO_ROOT in root.parents:
        raise ValueError("Raw input directory must be outside the repository")
    manifest = {
        "schema_version": 1,
        "dataset": "public-marine-incident-inputs",
        "method_version": "public-input-row-counts-v1",
        "units": "records",
        "readiness": "unavailable",
        "sources": [],
        "excluded_sources": [
            {
                "id": "imo_gisis",
                "reason": "Requires an account and manual export; excluded.",
            }
        ],
        "counts": UNKNOWN,
    }
    frames = {}
    for definition in SOURCES:
        source = dict(definition)
        source.update(
            dict.fromkeys(("download_date_utc", "sha256", "row_count"), UNKNOWN)
        )
        source["status"] = UNKNOWN
        source["attempted_at_utc"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        try:
            with tempfile.TemporaryDirectory(prefix="marine-input-") as scratch:
                temporary = Path(scratch) / "input.csv"
                with (
                    get(source["url"], timeout=60, stream=True) as response,
                    temporary.open("wb") as stream,
                ):
                    response.raise_for_status()
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, stream)
                frame = read_source(temporary, source["id"])
                digest = sha256(temporary)
                relative = Path("sha256") / digest / Path(source["path"]).name
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    if sha256(destination) != digest:
                        raise ValueError("Retained input digest mismatch")
                else:
                    with (
                        destination.open("xb") as stream,
                        temporary.open("rb") as incoming,
                    ):
                        shutil.copyfileobj(incoming, stream)
                if sha256(destination) != digest:
                    raise ValueError("Saved input digest mismatch")
                source.update(
                    status="FETCHED",
                    path=relative.as_posix(),
                    sha256=digest,
                    download_date_utc=datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    row_count=len(frame),
                )
                frames[source["id"]] = frame
        except HTTPError as error:
            source["error"] = (
                f"HTTP {error.response.status_code}: {error.response.reason}"
            )
        except (RequestException, TimeoutError):
            source["error"] = "Network request failed or timed out"
        manifest["sources"].append(source)
    if len(frames) == len(SOURCES):
        manifest["counts"] = analyse_frames(frames)["counts"]
        manifest["readiness"] = "count-agreement-only"
    output = Path(manifest_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    if json.loads(output.read_text()) != manifest:
        raise ValueError("Saved manifest readback failed")
    return manifest


def provenance_html(manifest):
    """Render the same provenance and count definitions used by agreement checks."""
    rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{escape(str(source[key]))}</td>"
            for key in (
                "id",
                "url",
                "download_date_utc",
                "sha256",
                "row_count",
                "status",
            )
        )
        + "</tr>"
        for source in manifest["sources"]
    )
    counts = manifest["counts"]
    count_text = (
        "NOT_EVALUATED — not yet re-derived; both public inputs are required."
        if counts == UNKNOWN
        else escape(json.dumps(counts, sort_keys=True))
    )
    return f"""<section class="section" id="input-provenance">
<h2>Public-input analysis basis</h2>
<p>Summary: combined and filtered record counts: {count_text}</p>
<h3>Revision history</h3>
<table><tr><th>Revision</th><th>Date</th><th>What changed and why</th></tr>
<tr><td>1</td><td>2026-10-19</td><td>Public-input provenance and count agreement
are recorded because the historical total could not be sourced.</td></tr></table>
<h3>Sources and counts</h3>
<table><tr><th>Source</th><th>Download URL</th><th>Downloaded (UTC)</th>
<th>SHA-256</th><th>Records</th><th>Status</th></tr>{rows}</table>
<p>IMO GISIS is excluded because it requires an account and manual export.
A blocked download has no measured count or digest. Earlier charts on this page
remain unverified; they are not results of this public-input run.</p>
<p>Method: concatenate public records without deduplication or date filtering;
remove missing, empty and whitespace-only descriptions; select foundering rows
by case-insensitive founder|capsiz|sinking in the incident type; select fatal
incident rows by deaths greater than zero. Missing death counts are treated as
zero for selection, so unreported deaths cannot be counted. Counts are records,
not unique global events. Hatch detection and detailed charts remain unverified.</p>
</section>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify retained inputs without downloading",
    )
    args = parser.parse_args()
    if args.check:
        result = load_inputs(args.raw_dir, args.manifest)
        print(json.dumps(result["counts"], indent=2))
        return 0
    manifest = fetch_inputs(args.raw_dir, args.manifest)
    for source in manifest["sources"]:
        print(
            f"{source['id']}: {source['status']}; {source.get('error', 'downloaded')}"
        )
    return 0 if manifest["counts"] != UNKNOWN else 1


if __name__ == "__main__":
    raise SystemExit(main())
