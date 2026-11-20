#!/usr/bin/env python3
"""Fetch the public pipeline, riser and platform sources named in the
field-development road map BSEE data review, with one source manifest per
dataset group.

Raw files are written once to a caller-owned store outside the repository
(``--raw-root``); only the manifests are written into the repository.

Rules this script keeps:
- official public hosts only (allow-list below); HTTPS; no sign-in;
- sequential requests with a per-host pause (EDX asks for 15 s);
- a generic User-Agent with no personal name or e-mail;
- raw files are never overwritten; a new retrieval date gets a new folder;
- every file is read back and hashed (SHA-256) after it is saved.

Standard library only, so it runs on a storage host without the package
environment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

USER_AGENT = "WorldEnergyData-public-fetcher/1.0 (public research; sequential requests)"
HOST_PAUSE_S = {
    "www.data.bsee.gov": 2.0,
    "www.bsee.gov": 3.0,
    "edx.netl.doe.gov": 15.0,  # robots.txt Crawl-Delay
    "www.osti.gov": 3.0,
}

BSEE_TERMS = {
    "terms_url": "https://www.bsee.gov/bsee/privacy-policy#copyright",
    "statement": (
        "Generally, materials produced by federal agencies belong to the public "
        "domain and may be reproduced without permission."
    ),
    "disclaimer_url": "https://www.data.bsee.gov/Main/HtmlPage.aspx?page=Disclaimer",
    "limitations": (
        "Working database; errors may exist. Not a legal document; not for "
        "navigational use. Third-party materials may carry restrictions."
    ),
    "access": "Free direct download, no account.",
}
EDX_TERMS = {
    "terms_url": "https://edx.netl.doe.gov/dataset/us-offshore-pipeline-and-reported-incident-datasets",
    "license": "Creative Commons Attribution (cc-by), as stated on the EDX dataset record.",
    "attribution": (
        "Romeo, L., Pfander, I., Duran, R., Sabbatino, M., Schooley, C., "
        "Wenzlick, M., Wingo, P., Zaengle, D., Bauer, J. U.S. Offshore Pipeline "
        "and Reported Incident Datasets. National Energy Technology Laboratory "
        "(NETL), US Department of Energy. DOI 10.18141/2280823."
    ),
    "access": "Free direct download from EDX storage, no account.",
    "robots": "EDX robots.txt sets Crawl-Delay 15; /api/ and resource_download paths are not used.",
}

D = "https://www.data.bsee.gov"
EDX = "https://edx.netl.doe.gov/storage/f/edx"

# group -> (manifest path in repo, list of sources)
GROUPS: dict[str, dict] = {
    "bsee_pipeline": {
        "manifest": "data/modules/bsee/pipeline_risers/source_manifest.json",
        "title": "BSEE pipeline, platform and decommissioning public files (road map rows A14, A17 to A22, A26)",
        "terms": BSEE_TERMS,
        "sources": [
            (
                "A17",
                "Pipeline Masters (delimited)",
                f"{D}/Pipeline/Files/pplmastdelimit.zip",
                "One record per segment: origin and destination, size code, product, status, MAOP, min and max water depth, dates, operator code.",
            ),
            (
                "A17",
                "Pipeline Masters record layout",
                f"{D}/Main/HtmlPage.aspx?page=pipelineMasters",
                "Field layout for the masters file.",
            ),
            (
                "A18",
                "Pipeline Permits raw data (segments and submittals)",
                f"{D}/Pipeline/Files/PipePermRawData.zip",
                "Two CSV files: segments and permit submittals with free-text description. Refreshed here for a 20 Nov 2026 snapshot; a 15 Oct 2026 copy is recorded in data/modules/pipeline/screening/sources.json.",
            ),
            (
                "A18",
                "Pipeline status code values",
                f"{D}/Pipeline/PipelinePermits/FieldValues.aspx?domain=STATUS_CODES",
                "Code list for segment status.",
            ),
            (
                "A19",
                "Pipeline Location with Appurtenance (delimited)",
                f"{D}/Pipeline/Files/ppldtappdelimit.zip",
                "As-built points with appurtenance type. The all-versions location raw file is already held (15 Oct 2026).",
            ),
            (
                "A19",
                "Pipeline Location with Appurtenance record layout",
                f"{D}/Main/HtmlPage.aspx?page=pipelineLocationApp",
                "Field layout.",
            ),
            (
                "A21",
                "Pipeline Histories (delimited)",
                f"{D}/Pipeline/Files/2100delimit.zip",
                "Dated history lines per segment.",
            ),
            (
                "A21",
                "Pipeline Histories record layout",
                f"{D}/Main/HtmlPage.aspx?page=pipelineHistories",
                "Field layout.",
            ),
            (
                "A21",
                "ROW Descriptions raw data",
                f"{D}/Pipeline/Files/RowDescRawData.zip",
                "Right-of-way descriptions.",
            ),
            (
                "A20",
                "Mapping: Pipelines file geodatabase",
                f"{D}/Mapping/Files/Pipelines.gdb.zip",
                "Pipeline arcs, Esri file geodatabase.",
            ),
            (
                "A20",
                "Mapping: Pipelines shapefile (ppl_arcs)",
                f"{D}/Mapping/Files/ppl_arcs.zip",
                "Pipeline arcs, shapefile.",
            ),
            (
                "A20",
                "Mapping: Platforms file geodatabase",
                f"{D}/Mapping/Files/Platforms.gdb.zip",
                "Platform points, Esri file geodatabase.",
            ),
            (
                "A20",
                "Mapping: Platforms shapefile",
                f"{D}/Mapping/Files/platform.zip",
                "Platform points, shapefile.",
            ),
            (
                "A22",
                "Scanned Documents index raw data",
                f"{D}/Other/Files/ScannedDocsRawData.zip",
                "Index of scanned pipeline maps, ROW files, plans, well and lease files. The scanned PDFs themselves were not bulk-downloaded.",
            ),
            (
                "A26",
                "Decommissioning Cost Estimates raw data",
                f"{D}/Leasing/Files/DecomCostEstRawData.zip",
                "P50, P70 and P90 estimates per well, platform and pipeline segment; totals per lease, ROW and RUE.",
            ),
            (
                "A14",
                "Platform Structures raw data",
                f"{D}/Platform/Files/PlatStrucRawData.zip",
                "Structure type (for example SEMI, SPAR, TLP, MTLP, FPSO), install and removal dates, water depth.",
            ),
            (
                "terms",
                "BSEE Data Center disclaimer",
                f"{D}/Main/HtmlPage.aspx?page=Disclaimer",
                "Terms of use page.",
            ),
        ],
    },
    "bsee_research": {
        "manifest": "data/modules/bsee/research_reports/source_manifest.json",
        "title": "BSEE Technical Assessment Program riser reports named in the road map (row A27)",
        "terms": BSEE_TERMS,
        "sources": [
            (
                "A27",
                "TAP 572 Deepwater Riser Design, Fatigue Life and Standards Study",
                "https://www.bsee.gov/sites/bsee.gov/files/research-reports/572aa.pdf",
                "Final report PDF; research record https://www.bsee.gov/research-record/tap-572-deepwater-riser-fatigue-life-modeling-standard-study",
            ),
            (
                "A27",
                "TAP 531 SCR Integrity Management",
                "https://www.bsee.gov/sites/bsee.gov/files/tap-technical-assessment-program/531aa.pdf",
                "Report PDF; research record https://www.bsee.gov/research-record/tap-531-scr-integrity-management",
            ),
            (
                "A27",
                "TAP 622 Marine growth on risers",
                "https://www.bsee.gov/sites/bsee.gov/files/tap-technical-assessment-program/622aa.pdf",
                "Report PDF.",
            ),
        ],
    },
    "doe_netl_offshore_pipelines": {
        "manifest": "data/modules/pipeline_safety/netl_offshore_pipelines/source_manifest.json",
        "title": "U.S. Offshore Pipeline and Reported Incident Datasets (NETL, US DOE; road map row A28)",
        "terms": EDX_TERMS,
        "sources": [
            (
                "A28",
                "OSTI dataset record 2280823",
                "https://www.osti.gov/dataexplorer/biblio/dataset/2280823",
                "Landing page; DOI 10.18141/2280823 resolves to the EDX record.",
            ),
            (
                "A28",
                "EDX dataset record",
                "https://edx.netl.doe.gov/dataset/us-offshore-pipeline-and-reported-incident-datasets",
                "Dataset page with licence.",
            ),
            (
                "A28",
                "ReadMe (PDF)",
                f"{EDX}/2026/04/2026-04-09T16:24:06.290674/420a8d05-bace-4609-90f1-865db5d8df8d/U.S.OffshorePipelineandReportedIncidentDatasetsReadMe.pdf",
                "Dataset ReadMe.",
            ),
            (
                "A28",
                "Pipeline locations data dictionary (CSV)",
                f"{EDX}/2024/01/2024-01-17T19:16:55.580Z/18edf57c-0cb5-4f17-8bab-60551d26ed41/pipeline_location_data_dictionary.csv",
                "Field definitions with original source references.",
            ),
            (
                "A28",
                "Pipeline incidents data dictionary (CSV)",
                f"{EDX}/2024/01/2024-01-22T19:47:25.510Z/466b42b7-eac9-42a6-8c51-e07e944b5ef0/pipeline_incidents_data_dictionary.csv",
                "Field definitions.",
            ),
            (
                "A28",
                "Pipeline incidents (CSV)",
                f"{EDX}/2024/01/2024-01-11T16:43:09.673Z/f4591f7b-dd94-4029-8518-1a7ad2edf7e7/pipeline_incidents.csv",
                "More than 900 reported incidents, 1986 to 2021.",
            ),
            (
                "A28",
                "Pipeline locations (CSV)",
                f"{EDX}/2024/01/2024-01-17T17:42:00.024Z/6552781b-fa36-44a5-8fa5-9896edd09495/pipeline_locations.csv",
                "More than 80,000 points with matched attributes.",
            ),
            (
                "A28",
                "Pipeline locations file geodatabase (ZIP)",
                f"{EDX}/2025/03/2025-03-11T16:00:30.008896/83a86c80-c3da-4b1b-9bf5-1f46ad285188/pipelines_us_offshore.gdb.zip",
                "Same points as a feature class.",
            ),
        ],
    },
}

ALLOWED_HOSTS = set(HOST_PAUSE_S)


def _validate(url: str) -> None:
    p = urlparse(url)
    if (
        p.scheme != "https"
        or p.hostname not in ALLOWED_HOSTS
        or p.username
        or p.password
    ):
        raise ValueError(f"Rejected source URL: {url}")


class _NoCrossHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_NoCrossHostRedirect)
_last_hit: dict[str, float] = {}


def _pause(host: str) -> None:
    wait = HOST_PAUSE_S[host] - (time.monotonic() - _last_hit.get(host, -1e9))
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.monotonic()


def _filename(url: str) -> str:
    p = urlparse(url)
    name = Path(p.path).name or "index"
    if p.query:
        q = p.query.replace("=", "-").replace("&", "_")
        name = f"{Path(name).stem}_{q}.html"
    elif "." not in name:
        name += ".html"
    return name


def download(url: str, dest_dir: Path) -> dict:
    _validate(url)
    host = urlparse(url).hostname
    dest = dest_dir / _filename(url)
    if dest.exists():
        raise FileExistsError(f"{dest.name} already exists; use a new retrieval folder")
    dest_dir.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        _pause(host)
        try:
            h = hashlib.sha256()
            size = 0
            with _OPENER.open(req, timeout=120) as resp, part.open("wb") as out:
                status = resp.status
                headers = {k.lower(): v for k, v in resp.headers.items()}
                final_url = resp.geturl()
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    h.update(chunk)
                    out.write(chunk)
                    size += len(chunk)
            break
        except urllib.error.HTTPError as err:
            part.unlink(missing_ok=True)
            if err.code in (401, 403, 429) or err.code < 500 or attempt == 2:
                return {"source_url": url, "http_status": err.code, "error": str(err)}
        except (urllib.error.URLError, TimeoutError) as err:
            part.unlink(missing_ok=True)
            if attempt == 2:
                return {"source_url": url, "http_status": None, "error": str(err)}
    head = part.open("rb").read(4096).lower()
    if any(m in head for m in (b"verify you are human", b"captcha", b"access denied")):
        part.unlink()
        return {
            "source_url": url,
            "http_status": status,
            "error": "access challenge page; stopped",
        }
    os.replace(part, dest)
    digest = _sha_file(dest)
    if digest != h.hexdigest():
        raise OSError(f"Readback hash mismatch for {dest.name}")
    return {
        "file": dest.name,
        "source_url": url,
        "final_url": final_url,
        "http_status": status,
        "retrieved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "size_bytes": size,
        "sha256": digest,
        "content_type": headers.get("content-type"),
        "publisher_last_modified": headers.get("last-modified"),
    }


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def schema_notes(path: Path) -> dict:
    """Describe what is inside a file without copying its content."""
    notes: dict = {}
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            members = [i for i in z.infolist() if not i.is_dir()]
            notes["zip_members"] = len(members)
            listed = []
            for info in members[:40]:
                row = {"name": info.filename, "size_bytes": info.file_size}
                if info.filename.lower().endswith((".txt", ".csv", ".dat")):
                    with z.open(info) as f:
                        first = f.readline(8192).decode("latin-1").strip()
                        lines = 1 + sum(1 for _ in f)
                    row.update(_header_note(first))
                    row["line_count"] = lines
                listed.append(row)
            notes["members"] = listed
            gdbs = sorted(
                {
                    m.filename.split(".gdb/")[0] + ".gdb"
                    for m in members
                    if ".gdb/" in m.filename
                }
            )
            if gdbs:
                notes["file_geodatabases"] = gdbs
    elif path.suffix.lower() == ".csv":
        with path.open("rb") as f:
            notes.update(
                _header_note(f.readline(16384).decode("utf-8", "replace").strip())
            )
            notes["line_count"] = 1 + sum(1 for _ in f)
    return notes


_HEADER_FIELD = re.compile(r"^[A-Za-z][A-Za-z0-9_ ./()%-]{0,60}$")


def _header_note(first_line: str) -> dict:
    """Record a header row's field names; never record a data row, which can
    carry company or facility names."""
    fields = [f.strip().strip('"') for f in first_line.split(",")]
    if (
        fields
        and all(
            _HEADER_FIELD.match(f) and not any(c.isdigit() for c in f[:1])
            for f in fields
        )
        and sum(f.isupper() or "_" in f for f in fields) >= len(fields) / 2
    ):
        return {"header_fields": fields[:80], "field_count": len(fields)}
    return {
        "header_fields": None,
        "field_count": len(fields),
        "note": "no header row; see the record layout page",
    }


def refresh_manifest(manifest_path: Path, raw_root: Path) -> None:
    """Re-verify each held file's SHA-256 and size against its manifest entry
    and rewrite the schema notes; fetch records are kept as they were."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        if "file" not in entry:
            continue
        path = raw_root / manifest["group"] / manifest["retrieval"] / entry["file"]
        if (
            path.stat().st_size != entry["size_bytes"]
            or _sha_file(path) != entry["sha256"]
        ):
            raise OSError(f"Held file differs from its manifest entry: {entry['file']}")
        entry["schema"] = schema_notes(path)
        entry["verified_at_utc"] = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--raw-root",
        type=Path,
        required=True,
        help="external raw store (outside the repo)",
    )
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument(
        "--retrieval", default=datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    ap.add_argument(
        "--group", action="append", choices=sorted(GROUPS), help="limit to groups"
    )
    ap.add_argument(
        "--verify",
        action="store_true",
        help="no download: re-hash held files against the manifests and refresh schema notes",
    )
    args = ap.parse_args(argv)
    repo = args.repo.resolve()
    raw_root = args.raw_root.resolve()
    if raw_root == repo or repo in raw_root.parents:
        raise SystemExit("Raw store must be outside the repository")
    if args.verify:
        for gid in args.group or list(GROUPS):
            refresh_manifest(repo / GROUPS[gid]["manifest"], raw_root)
            print(f"verified {gid}")
        return 0
    failures = 0
    for gid in args.group or list(GROUPS):
        group = GROUPS[gid]
        dest_dir = raw_root / gid / args.retrieval
        entries = []
        for row_id, title, url, notes in group["sources"]:
            rec = download(url, dest_dir)
            rec = {"roadmap_row": row_id, "title": title, **rec, "notes": notes}
            if "error" in rec:
                failures += 1
                print(f"FAIL {gid} {title}: {rec['error']}", file=sys.stderr)
            else:
                rec["stored_at"] = (
                    f"external raw store: {gid}/{args.retrieval}/{rec['file']}"
                )
                rec["schema"] = schema_notes(dest_dir / rec["file"])
                print(f"ok   {gid} {rec['file']} {rec['size_bytes']:,} bytes")
            entries.append(rec)
        manifest = {
            "group": gid,
            "title": group["title"],
            "retrieval": args.retrieval,
            "fetched_by": "scripts/bsee/fetch_fielddev_public_sources.py",
            "user_agent": USER_AGENT,
            "terms": group["terms"],
            "storage": "Raw files are kept outside git in the external raw store under the path given per file; only this manifest is in git.",
            "total_bytes": sum(e.get("size_bytes", 0) for e in entries),
            "files": entries,
        }
        out = repo / group["manifest"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
