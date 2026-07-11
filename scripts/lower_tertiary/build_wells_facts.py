#!/usr/bin/env python3
"""ABOUTME: Generate the per-well contract _wells.json from committed sources (#948).
ABOUTME: Joins the LT benchmark CSV (production) with the V30 extract (construction) on API12.

Single-sources the per-well timeline data that ``build_well_timelines.py`` and the
field-atlas Explorer consume. Before #948 the contract was hand-curated for Big
Foot only; this generalises it to every producing LT well the benchmark covers
(56 wells / 7 fields).

Sources (all committed — stdlib-only, no pandas / no FUSE):
  - reports/lower_tertiary/lt_well_benchmark_lower_tertiary_2010_latest.csv
        production: first_oil, cum_oil_mmbbl, uptime_pct, interventions
  - reports/lower_tertiary/data/all_fields_wells.json  (from the V30 xlsx)
        construction: spud, td, drilling/completion rig-days, tvd, well_name=slot
  - reports/lower_tertiary/lifecycle/_facts.json        per-field operator/host/play
  - reports/lower_tertiary/lifecycle/wells/_wells_overrides.json
        curated overlay: Big Foot mud weights + per-field lease/block

CONTRACT NOTES (all load-bearing, from the #948 plan review):
  * The V30 extract carries literal ``NaN`` tokens; every numeric is sanitised
    NaN/inf -> None, because a raw NaN is invalid JSON and would break the
    Explorer's JSON.parse when embedded into _explorer.json.
  * Benchmark ``drilling_days``/``completion_days`` are CALENDAR spans, NOT
    rig-days (they disagree with V30 on 36/55 wells) -> rig-days come ONLY from
    the V30 extract, never the benchmark.
  * ``cum_oil_mmbbl`` rounds to 1 dp and rig-days/tvd normalise to int to match
    the hand-curated Big Foot values exactly (identity-guarded).
"""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BENCH = REPO / "reports/lower_tertiary/lt_well_benchmark_lower_tertiary_2010_latest.csv"
V30 = REPO / "reports/lower_tertiary/data/all_fields_wells.json"
FACTS = REPO / "reports/lower_tertiary/lifecycle/_facts.json"
HERE = REPO / "reports/lower_tertiary/lifecycle/wells"
OVERRIDES = HERE / "_wells_overrides.json"
OUT = HERE / "_wells.json"

_SLOT_SANE = re.compile(r"[^A-Za-z0-9-]+")
_INT_HIST = re.compile(r"([A-Za-z][A-Za-z ]*?)\s+(\d{4}-\d{2}-\d{2})")


def field_id(bench_label: str) -> str:
    """'Jack St Malo' -> 'jack_st_malo' (matches the lifecycle field ids)."""
    return bench_label.strip().lower().replace(" ", "_")


def num(v, *, as_int=False, ndigits=None):
    """Coerce to float/int, mapping NaN/inf/blank -> None (invalid-JSON guard)."""
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    if as_int:
        return int(round(f))
    if ndigits is not None:
        return round(f, ndigits)
    return f


def parse_workovers(history: str) -> list[dict]:
    """'Workover 2020-08-30; Sidetrack 2019-01-02' -> [{date, type}, ...]."""
    if not history or not history.strip():
        return []
    return [{"date": d, "type": t.strip()} for t, d in _INT_HIST.findall(history)]


def load_v30_by_field() -> dict:
    data = json.loads(V30.read_text())
    return {fid: {w["api"]: w for w in blk["wells"]} for fid, blk in data.items()}


def build() -> dict:
    v30 = load_v30_by_field()
    overrides = json.loads(OVERRIDES.read_text())
    mud = overrides.get("mud_weight_ppg", {})
    field_blocks = overrides.get("fields", {})

    rows = list(csv.DictReader(BENCH.open(newline="", encoding="utf-8")))
    per_field_slots: dict[str, dict[str, list[str]]] = {}
    records = []
    for r in rows:
        fid = field_id(r["field"])
        api = r["api12"].strip()
        v = v30.get(fid, {}).get(api, {})
        slot = (v.get("well_name") or "").strip() or f"w{api[-4:]}"
        rec = {
            "api": api,
            "slot": slot,
            "field_id": fid,
            "spud_date": (v.get("spud") or None),
            "td_date": (v.get("td") or None),
            "drilling_rig_days": num(v.get("drilling_days"), as_int=True),
            "completion_rig_days": num(v.get("completion_days"), as_int=True),
            "max_tvd_ft": num(v.get("tvd_ft"), as_int=True),
            "mud_weight_ppg": mud.get(api),
            "first_oil": (r["first_oil"].strip() or None),
            "workovers": parse_workovers(r.get("intervention_history", "")),
            "cum_oil_mmbbl": num(r.get("cum_oil_mmbbl"), ndigits=1),
            "uptime_pct": num(r.get("uptime_pct")),
            "status": "producing",
        }
        records.append(rec)
        per_field_slots.setdefault(fid, {}).setdefault(slot, []).append(api)

    # Disambiguate slot collisions within a field: <slot>-<api last4>.
    for rec in records:
        apis = per_field_slots[rec["field_id"]][rec["slot"]]
        if len(apis) > 1:
            rec["slot"] = _SLOT_SANE.sub("-", f"{rec['slot']}-{rec['api'][-4:]}")
        else:
            rec["slot"] = _SLOT_SANE.sub("-", rec["slot"])

    records.sort(key=lambda x: (x["field_id"], x["spud_date"] or "9999", x["slot"]))

    fields = {}
    facts = {f["id"]: f for f in json.loads(FACTS.read_text())}
    for fid in sorted({r["field_id"] for r in records}):
        blk = dict(field_blocks.get(fid, {}))
        f = facts.get(fid, {})
        blk.setdefault("display_name", f.get("name", fid))
        blk.setdefault("operator", f.get("operator"))
        blk.setdefault("host", f.get("host_type"))
        blk.setdefault("play", f.get("play"))
        fields[fid] = blk

    return {"fields": fields, "wells": records}


def main():
    feed = build()
    text = json.dumps(feed, indent=1, ensure_ascii=False)
    if re.search(r"\bNaN\b|\bInfinity\b", text):
        raise AssertionError("NaN/Infinity token in generated _wells.json")
    OUT.write_text(text + "\n")
    by_field = {}
    for w in feed["wells"]:
        by_field[w["field_id"]] = by_field.get(w["field_id"], 0) + 1
    print(
        f"  wrote {OUT.name}  ({len(feed['wells'])} wells, {len(feed['fields'])} fields)"
    )
    for fid, n in sorted(by_field.items()):
        print(f"    {fid}: {n}")


if __name__ == "__main__":
    main()
