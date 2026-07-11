#!/usr/bin/env python3
"""ABOUTME: Generate the global Explorer feed (_atlas_feed.json) from the curated
ABOUTME: 2,149-field catalog + freshness-scorecard badges + GoM roster dedup (#947).

Federates ``data/modules/offshore_assets/curated/fields.csv`` (84 countries)
into the field-atlas funnel:

- ``countries``: one row per coverage country with its data-density badge from
  the shared ``catalog_badges`` rule (US hardcoded RICH; module countries via
  catalog_status; no-module countries SAMPLE — reference inventory only).
- ``fields``: every catalog row EXCEPT the GoM rows already represented by the
  hand-curated 120-entry ``_roster.json`` (dedup below). All rows carry
  ``density_tier: "roadmap"`` — the catalog holds name/block/status only, and
  the page defines tiers per FIELD (the country-level badge is a separate
  dimension; conflating them would fake data density, plan r1 finding 3).

Dedup (plan D3, measured in review): exact-normalized-name first; a
parenthetical-stripped fallback applies ONLY when the stripped key matches
exactly one catalog row — this protects distinct fields like
``Big Bend (Noble)`` vs ``Big Bend (Petrobras)`` from a false merge.

Country names are normalized to the roster's spelling (``US`` -> ``USA``).
Stdlib-only by the deploy-parity convention (#850).
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from catalog_badges import badge_for, load_scorecard  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CURATED = PROJECT_ROOT / "data" / "modules" / "offshore_assets" / "curated"
FIELDS_CSV = CURATED / "fields.csv"
COVERAGE_CSV = CURATED / "coverage_summary.csv"
SCORECARD = PROJECT_ROOT / "data" / "freshness-scorecard.json"
HERE = PROJECT_ROOT / "reports" / "field-atlas"
ROSTER = HERE / "_roster.json"
OUT = HERE / "_atlas_feed.json"

_PUNCT = re.compile(r"[^a-z0-9]+")
_PARENS = re.compile(r"\([^)]*\)")


def norm_exact(name: str) -> str:
    return _PUNCT.sub("", name.casefold())


def norm_stripped(name: str) -> str:
    return _PUNCT.sub("", _PARENS.sub("", name).casefold())


def dedup_gom(roster_names: list[str], gom_rows: list[dict]):
    """Return (suppressed_row_ids, per_name_report, roster_unmatched).

    Exact-first; ambiguity-guarded parenthetical fallback (#947 plan D3).
    Suppression is keyed by ROW IDENTITY (``id(row)``), NOT by ``FIELD_ID`` —
    the catalog reuses FIELD_ID across unrelated rows (1,582 unique ids over
    2,149 rows; one id appears 12x), so an id-keyed suppression silently
    removes unrelated fields.
    """
    by_exact: dict[str, list[dict]] = defaultdict(list)
    by_stripped: dict[str, list[dict]] = defaultdict(list)
    for r in gom_rows:
        by_exact[norm_exact(r["FIELD_NAME"])].append(r)
        by_stripped[norm_stripped(r["FIELD_NAME"])].append(r)

    suppressed: set[int] = set()
    report: dict[str, list[str]] = {}
    roster_unmatched: list[str] = []
    for name in roster_names:
        hits = by_exact.get(norm_exact(name))
        if not hits:
            candidates = by_stripped.get(norm_stripped(name), [])
            # Ambiguity guard: a stripped key shared by >1 DISTINCT catalog
            # rows (e.g. Big Bend (Noble) / Big Bend (Petrobras)) must never
            # be suppressed by a single roster entry.
            hits = candidates if len(candidates) == 1 else None
        if hits:
            report[name] = [r["FIELD_NAME"] for r in hits]
            suppressed.update(id(r) for r in hits)
        else:
            roster_unmatched.append(name)
    return suppressed, report, roster_unmatched


def _field_entry(r: dict) -> dict:
    is_gom = bool(r["US_GOM_FLAG"].strip())
    country = "USA" if r["COUNTRY"] == "US" else r["COUNTRY"]
    depth = r["WATER_DEPTH_FT"].strip()
    return {
        "catalog_id": r["FIELD_ID"],
        "name": r["FIELD_NAME"],
        "country": country,
        "domain": "offshore",
        "region": "US Gulf of Mexico" if is_gom else country,
        "block": r["BLOCK"].strip() or None,
        "status": r["CURRENT_STATUS"].strip() or None,
        "reserve_type": r["RESERVE_TYPE"].strip() or None,
        "water_depth_ft": int(depth) if depth.isdigit() else None,
        "density_tier": "roadmap",
        "gom": is_gom,
    }


def build() -> dict:
    catalog = list(csv.DictReader(FIELDS_CSV.open(newline="", encoding="utf-8")))
    roster = json.loads(ROSTER.read_text())
    statuses = load_scorecard(SCORECARD)

    countries = []
    with COVERAGE_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or row[0] != "by_country":
                continue
            raw = row[1]
            badge, module, _status = badge_for(raw, statuses)
            countries.append(
                {
                    "country": "USA" if raw == "US" else raw,
                    "fields": int(row[2] or 0),
                    "facilities": int(row[3] or 0),
                    "badge": badge,
                    "module": module,
                }
            )
    countries.sort(key=lambda c: c["country"])

    gom_rows = [r for r in catalog if r["US_GOM_FLAG"].strip()]
    suppressed, report, roster_unmatched = dedup_gom(
        [e["name"] for e in roster], gom_rows
    )

    fields = [
        _field_entry(r)
        for r in catalog
        if not (r["US_GOM_FLAG"].strip() and id(r) in suppressed)
    ]
    fields.sort(key=lambda e: (e["country"], e["name"]))

    gom_tail = sum(1 for e in fields if e["gom"])
    if len(suppressed) + gom_tail != len(gom_rows):
        raise AssertionError(
            f"dedup invariant broken: {len(suppressed)} suppressed + "
            f"{gom_tail} kept != {len(gom_rows)} catalog GoM rows"
        )
    print(
        f"  dedup: {len(report)} roster names suppressed {len(suppressed)} "
        f"catalog GoM rows; {gom_tail} GoM tail rows kept (sums to {len(gom_rows)})"
    )
    multi = {k: v for k, v in report.items() if len(v) > 1}
    if multi:
        print(f"  multi-row suppressions (exact-name duplicates): {multi}")
    if roster_unmatched:
        print(f"  roster names with NO catalog row: {roster_unmatched}")

    return {
        "meta": {
            "generated_by": "scripts/field_atlas/build_atlas_feed.py",
            "issue": 947,
            "source": "data/modules/offshore_assets/curated/fields.csv",
        },
        "countries": countries,
        "fields": fields,
    }


def main():
    feed = build()
    OUT.write_text(json.dumps(feed, indent=1, ensure_ascii=False) + "\n")
    print(
        f"  wrote {OUT.name}  ({len(feed['countries'])} countries, "
        f"{len(feed['fields'])} fields)"
    )


if __name__ == "__main__":
    main()
