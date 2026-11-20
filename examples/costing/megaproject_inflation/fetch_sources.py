"""Download the public price series behind the mega-project cost inflation article and record them in sources.csv.

Each series is a monthly CSV from FRED (Federal Reserve Bank of St. Louis), which republishes the US Bureau of Labor
Statistics producer and consumer price indexes and the US Energy Information Administration Brent price. Every file is
saved as downloaded under data/, and sources.csv records its title, publisher, URL, retrieval time (UTC), SHA-256,
first and last observation and row count. The quoted S&P Global (formerly IHS) Upstream Capital Costs Index values are
read from the repository's curated file; sources.csv records that file's SHA-256 too.

Usage (from the repository root):
  python examples/costing/megaproject_inflation/fetch_sources.py            # download and write sources.csv
  python examples/costing/megaproject_inflation/fetch_sources.py --check    # re-hash the saved files only
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
REPO = HERE.parents[2]
UCCI_FILE = REPO / "data" / "modules" / "cost" / "curated" / "cost_component_timeseries.csv"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
FRED_PAGE = "https://fred.stlouisfed.org/series/{sid}"

# series id, short key, title as published on FRED, original publisher
SERIES = [
    ("CPIAUCSL", "cpi", "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average",
     "U.S. Bureau of Labor Statistics"),
    ("PCU213111213111", "drilling", "Producer Price Index by Industry: Drilling Oil and Gas Wells",
     "U.S. Bureau of Labor Statistics"),
    ("PCU213112213112", "support", "Producer Price Index by Industry: Support Activities for Oil and Gas Operations",
     "U.S. Bureau of Labor Statistics"),
    ("PCU333132333132", "machinery", "Producer Price Index by Industry: Oil and Gas Field Machinery and Equipment "
     "Manufacturing", "U.S. Bureau of Labor Statistics"),
    ("WPU1017", "steel_mill", "Producer Price Index by Commodity: Metals and Metal Products: Steel Mill Products",
     "U.S. Bureau of Labor Statistics"),
    ("WPU101706", "steel_pipe", "Producer Price Index by Commodity: Metals and Metal Products: Steel Pipe and Tube",
     "U.S. Bureau of Labor Statistics"),
    ("PCU336611336611", "shipbuilding", "Producer Price Index by Industry: Ship Building and Repairing",
     "U.S. Bureau of Labor Statistics"),
    ("PCU541330541330", "engineering", "Producer Price Index by Industry: Engineering Services",
     "U.S. Bureau of Labor Statistics"),
    ("MCOILBRENTEU", "brent", "Crude Oil Prices: Brent - Europe (monthly)", "U.S. Energy Information Administration"),
]

FIELDS = ["key", "series_id", "title", "publisher", "distributor", "url", "licence", "retrieved_utc", "sha256",
          "first_observation", "last_observation", "rows", "local_file"]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def summarise(raw: bytes) -> tuple[str, str, int]:
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8"))))[1:]
    rows = [r for r in rows if len(r) == 2 and r[1] not in ("", ".")]
    return rows[0][0], rows[-1][0], len(rows)


def download(sid: str) -> bytes:
    req = urllib.request.Request(FRED_CSV.format(sid=sid), headers={"User-Agent": "worldenergydata-example/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed https host
        return resp.read()


def ucci_row(retrieved: str) -> dict:
    raw = UCCI_FILE.read_bytes()
    rows = [r for r in csv.DictReader(io.StringIO(raw.decode("utf-8"))) if r["COMPONENT"] == "index_ucci"]
    years = sorted(r["YEAR"] for r in rows)
    return {"key": "ucci_quoted", "series_id": "index_ucci (quoted values)",
            "title": "S&P Global (formerly IHS) Upstream Capital Costs Index, values quoted in the trade press",
            "publisher": "S&P Global (proprietary index)", "distributor": "trade press; each row cites its article",
            "url": "data/modules/cost/curated/cost_component_timeseries.csv",
            "licence": "proprietary index; only values published in press articles are used, each with its citation",
            "retrieved_utc": f"values read {min(r['ACCESSED_DATE'] for r in rows)}; file hashed {retrieved}",
            "sha256": sha256(raw), "first_observation": years[0],
            "last_observation": years[-1], "rows": len(rows),
            "local_file": "data/modules/cost/curated/cost_component_timeseries.csv"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="re-hash the saved files against sources.csv")
    a = ap.parse_args(argv)
    src = HERE / "sources.csv"
    if a.check:
        bad = []
        for r in csv.DictReader(src.open(encoding="utf-8")):
            p = (REPO / r["local_file"]) if r["key"] == "ucci_quoted" else (HERE / r["local_file"])
            if sha256(p.read_bytes()) != r["sha256"]:
                bad.append(r["key"])
        print("sources check:", "ok" if not bad else f"hash mismatch {bad}")
        return 1 if bad else 0
    DATA.mkdir(exist_ok=True)
    out = []
    for sid, key, title, publisher in SERIES:
        raw = download(sid)
        now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        (DATA / f"{sid}.csv").write_bytes(raw)
        first, last, n = summarise(raw)
        out.append({"key": key, "series_id": sid, "title": title, "publisher": publisher,
                    "distributor": "FRED, Federal Reserve Bank of St. Louis", "url": FRED_PAGE.format(sid=sid),
                    "licence": "US government data, public domain; cite FRED and the publisher",
                    "retrieved_utc": now, "sha256": sha256(raw), "first_observation": first,
                    "last_observation": last, "rows": n, "local_file": f"data/{sid}.csv"})
    out.append(ucci_row(out[-1]["retrieved_utc"]))
    with src.open("w", encoding="utf-8", newline="\n") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print(f"wrote {len(out)} rows to sources.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
