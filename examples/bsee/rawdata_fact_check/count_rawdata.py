"""Count new-well permits by rig type and incident investigations from BSEE raw data.

Downloads two public raw data files from the BSEE Data Center
(https://www.data.bsee.gov/Main/RawData.aspx), US federal government data:

- Application for Permit to Drill (APDRawData.zip)
- Incident Investigations (IncInvRawData.zip)

and prints the counts as JSON. With ``--out`` it also writes the counts as CSV.

Counting rules
- A new-well permit is counted once per well (API well number): the permit with the
  lowest SN_APD among the "New Well" permits of that well in the Gulf of Mexico region
  (REGION_CODE "G"), by the year of its requested spud date, with the rig type that
  permit names. Wells whose first permit gives no requested spud date are left out and
  counted in ``no_spud_date``.
- Rig types are reported as named in RIG_TYPE_CODE. Types with fewer than 1 % of the
  permits counted (barge, barge rig, well intervention vessel, blank) are grouped as
  "Other", and the grouping is printed with the counts.
- Investigations are counted by kind (DISTRICT or PANEL) and status (as listed).

Usage (standard library only; network is needed only when a file is not in --data-dir):

    python examples/bsee/rawdata_fact_check/count_rawdata.py --data-dir bsee-raw
    python examples/bsee/rawdata_fact_check/count_rawdata.py --data-dir bsee-raw --out out
    python examples/bsee/rawdata_fact_check/count_rawdata.py --self-test
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import re
import statistics
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

FILES = {
    "APDRawData.zip": "https://www.data.bsee.gov/Well/Files/APDRawData.zip",
    "IncInvRawData.zip": "https://www.data.bsee.gov/Other/Files/IncInvRawData.zip",
}
APD_MEMBER = "mv_apd_main_all.txt"
INV_MEMBER = "mv_acc_investigations.txt"

# RIG_TYPE_CODE value -> label; every other value is grouped as "Other"
MAJOR = {
    "JACKUP": "Jack-up",
    "DRILLSHIP": "Drillship",
    "SEMISUBMERSIBLE": "Semisubmersible",
    "DP SEMISUBMERSIBLE": "DP semisubmersible",
    "PLATFORM": "Platform rig",
    "SUBMERSIBLE": "Submersible",
}
LABELS = list(MAJOR.values()) + ["Other"]
DATE = re.compile(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})")


def mdy(text):
    """Return (year, month, day) from an m/d/yyyy string, or None."""
    m = DATE.match(text or "")
    return (int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else None


def fetch(data_dir: Path) -> dict:
    """Download any file not yet in data_dir; return name -> (path, sha256, retrieved)."""
    data_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, url in FILES.items():
        path = data_dir / name
        retrieved = "already in data dir"
        if not path.exists():
            with urllib.request.urlopen(
                url, timeout=300
            ) as resp:  # nosec B310 (fixed https URL)
                path.write_bytes(resp.read())
            retrieved = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        out[name] = {
            "path": path.as_posix(),
            "sha256": digest,
            "retrieved_utc": retrieved,
        }
    return out


def read_member(zip_path: Path, member: str) -> list[dict]:
    """Read one delimited text file from a BSEE zip as a list of dicts."""
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.endswith(member)]
        if len(names) != 1:
            raise SystemExit(f"{member} not found once in {zip_path.name}: {names}")
        raw = zf.read(names[0]).decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(raw, newline="")))


def first_new_well_permits(apd_rows: list[dict]) -> list[dict]:
    """One permit per well: the lowest SN_APD among its Gulf of Mexico New Well permits."""
    best = {}
    for r in apd_rows:
        if r["PERMIT_TYPE"].strip() != "New Well" or r["REGION_CODE"].strip() != "G":
            continue
        api = r["API_WELL_NUMBER"].strip()
        sn = int(r["SN_APD"])
        if api not in best or sn < int(best[api]["SN_APD"]):
            best[api] = r
    return list(best.values())


def rig_label(code: str) -> str:
    return MAJOR.get((code or "").strip().upper(), "Other")


def count_permits(permits: list[dict], first_year: int, last_year: int) -> dict:
    """Permits per requested spud year and rig type, with water depth by rig type."""
    years = range(first_year, last_year + 1)
    table = {y: collections.Counter() for y in years}
    depth = collections.defaultdict(list)
    other_codes = collections.Counter()
    no_spud_date = 0
    for r in permits:
        d = mdy(r["REQ_SPUD_DATE"])
        if not d:
            no_spud_date += 1
            continue
        if d[0] not in table:
            continue
        label = rig_label(r["RIG_TYPE_CODE"])
        table[d[0]][label] += 1
        if label == "Other":
            other_codes[r["RIG_TYPE_CODE"].strip().upper() or "(blank)"] += 1
        if r["WATER_DEPTH"].strip():
            depth[label].append(float(r["WATER_DEPTH"]))
    rows = [
        {"year": y, "total": sum(table[y].values()), **{k: table[y][k] for k in LABELS}}
        for y in years
    ]
    totals = {k: sum(row[k] for row in rows) for k in LABELS}
    water = {
        k: {
            "n": len(v),
            "median_ft": statistics.median(v),
            "min_ft": min(v),
            "max_ft": max(v),
        }
        for k, v in depth.items()
    }
    return {
        "years": [first_year, last_year],
        "by_year": rows,
        "totals": totals,
        "all": sum(totals.values()),
        "water_depth": water,
        "other_grouped": dict(other_codes),
        "no_spud_date": no_spud_date,
    }


def count_investigations(inv_rows: list[dict]) -> dict:
    dates = sorted(d for d in (mdy(r["DATE_OCCURRED"]) for r in inv_rows) if d)
    kind_status = collections.Counter(
        f'{r["PANEL_DISTRICT"].strip()} {r["STATUS"].strip()}' for r in inv_rows
    )
    pending = [r for r in inv_rows if r["STATUS"].strip() == "Pending"]
    return {
        "records": len(inv_rows),
        "fields": list(inv_rows[0].keys()) if inv_rows else [],
        "first_incident": dates[0] if dates else None,
        "last_incident": dates[-1] if dates else None,
        "by_kind_and_status": dict(sorted(kind_status.items())),
        "pending_panel_incidents": sorted(
            mdy(r["DATE_OCCURRED"])
            for r in pending
            if r["PANEL_DISTRICT"].strip() == "PANEL"
        ),
        "pending_district_by_year": dict(
            sorted(
                collections.Counter(
                    mdy(r["DATE_OCCURRED"])[0]
                    for r in pending
                    if r["PANEL_DISTRICT"].strip() == "DISTRICT"
                ).items()
            )
        ),
    }


def write_csv(out_dir: Path, result: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = result["permits"]["by_year"]
    with open(
        out_dir / "new-well-permits-by-rig-type.csv",
        "w",
        encoding="utf-8",
        newline="\n",
    ) as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with open(out_dir / "counts.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, indent=1)
        f.write("\n")


def self_test() -> None:
    """Hand-worked synthetic case; no files or network needed."""

    def apd(sn, api, ptype, region, spud, rig, wd):
        return {
            "SN_APD": str(sn),
            "API_WELL_NUMBER": api,
            "PERMIT_TYPE": ptype,
            "REGION_CODE": region,
            "REQ_SPUD_DATE": spud,
            "RIG_TYPE_CODE": rig,
            "WATER_DEPTH": wd,
        }

    rows = [
        apd(5, "A", "New Well", "G", "3/1/2005", "JACKUP", "100"),
        apd(
            2, "A", "New Well", "G", "1/1/2005", "JACKUP", "90"
        ),  # lower SN_APD wins for A
        apd(3, "B", "New Well", "G", "6/1/2005", "DRILLSHIP", "5000"),
        apd(
            4, "C", "Revised New Well", "G", "6/1/2005", "JACKUP", "80"
        ),  # not a New Well
        apd(6, "D", "New Well", "P", "6/1/2005", "JACKUP", "80"),  # Pacific region
        apd(7, "E", "New Well", "G", "2/2/2006", "Barge Rig", "12"),  # grouped as Other
        apd(
            8, "F", "New Well", "G", "", "JACKUP", "50"
        ),  # no requested spud date: left out
    ]
    p = count_permits(first_new_well_permits(rows), 2005, 2006)
    # Hand count: 2005 holds A (jack-up, 90 ft) and B (drillship); 2006 holds E (Other).
    assert p["by_year"][0]["total"] == 2 and p["by_year"][0]["Jack-up"] == 1
    assert p["by_year"][0]["Drillship"] == 1 and p["by_year"][1]["Other"] == 1
    assert p["water_depth"]["Jack-up"]["median_ft"] == 90.0  # A's first permit, not 100
    assert p["other_grouped"] == {"BARGE RIG": 1} and p["all"] == 3
    assert p["no_spud_date"] == 1  # well F
    inv = count_investigations(
        [
            {
                "DATE_OCCURRED": "7/26/2020",
                "PANEL_DISTRICT": "PANEL",
                "STATUS": "Pending",
            },
            {
                "DATE_OCCURRED": "1/4/1995",
                "PANEL_DISTRICT": "DISTRICT",
                "STATUS": "Complete",
            },
        ]
    )
    assert inv["records"] == 2 and inv["first_incident"] == (1995, 1, 4)
    assert inv["pending_panel_incidents"] == [(2020, 7, 26)]
    print("self-test passed")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--data-dir",
        type=Path,
        default=Path("bsee-raw"),
        help="folder for the two zip files; missing files are downloaded",
    )
    ap.add_argument("--out", type=Path, help="folder for the CSV and JSON outputs")
    ap.add_argument("--first-year", type=int, default=2005)
    ap.add_argument("--last-year", type=int, default=datetime.now(timezone.utc).year)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if a.self_test:
        self_test()
        return 0
    files = fetch(a.data_dir)
    permits = first_new_well_permits(
        read_member(Path(files["APDRawData.zip"]["path"]), APD_MEMBER)
    )
    result = {
        "files": files,
        "permits": count_permits(permits, a.first_year, a.last_year),
        "investigations": count_investigations(
            read_member(Path(files["IncInvRawData.zip"]["path"]), INV_MEMBER)
        ),
    }
    if a.out:
        write_csv(a.out, result)
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
