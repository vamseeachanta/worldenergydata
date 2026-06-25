# ABOUTME: Generate the SubseaIQ→BSEE block crosswalk from full OGOR-A field codes.
# ABOUTME: Issue #569 (epic #567) — local generator (reads /mnt/ace OGOR .bin).
"""
Build ``data/modules/offshore_assets/curated/subseaiq_bsee_block_crosswalk.csv``.

The join logic lives in (and is unit-tested via)
``worldenergydata.field_development.subseaiq``; this script is the *local* glue
that supplies the full BSEE field-code universe from the OGOR-A ``.bin`` pickles
on ``/mnt/ace`` (not in the repo — needs ``make data`` / the native mount).

OGOR-A ``.bin`` quirk: ``pd.read_pickle`` consumes the first data row as the
header, so columns are positional — the field code is at index 13 (e.g.
``WD030``). We also re-add the consumed header token.

Run:
    .venv/bin/python scripts/field_development/build_subseaiq_bsee_crosswalk.py
"""

from __future__ import annotations

import csv
import glob
from pathlib import Path

import pandas as pd

from worldenergydata.field_development.subseaiq import (
    build_bsee_crosswalk,
    crosswalk_summary,
    load_subseaiq_fields,
)

OGOR_DIR = Path(
    "/mnt/ace/worldenergydata/data/modules/bsee/bin/historical_production_yearly"
)
OUT = (
    Path(__file__).parents[2]
    / "data"
    / "modules"
    / "offshore_assets"
    / "curated"
    / "subseaiq_bsee_block_crosswalk.csv"
)
FIELD_CODE_COL = 13  # positional, per the OGOR-A header-consumed quirk


def ogor_field_codes() -> set[str]:
    """All unique OGOR-A field codes across every year file on /mnt/ace."""
    codes: set[str] = set()
    files = sorted(glob.glob(str(OGOR_DIR / "ogora*.bin")))
    if not files:
        raise SystemExit(f"No OGOR .bin files found under {OGOR_DIR} — mount /mnt/ace.")
    for p in files:
        df = pd.read_pickle(p)
        if df.shape[1] > FIELD_CODE_COL:
            codes |= set(df.iloc[:, FIELD_CODE_COL].dropna().astype(str).str.strip())
            codes.add(str(df.columns[FIELD_CODE_COL]).strip())
    codes.discard("")
    print(f"OGOR files: {len(files)} | unique field codes: {len(codes)}")
    return codes


def main() -> None:
    rows = build_bsee_crosswalk(ogor_field_codes())
    # Enrich with host concept + operator from production_facilities.csv.
    enriched = {
        f.name: (f.concept_type.value if f.concept_type else "", f.operator or "")
        for f in load_subseaiq_fields(enrich_facilities=True)
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "og_field_name",
                "block",
                "bsee_block_code",
                "match_type",
                "matched",
                "host_concept",
                "operator",
            ]
        )
        for r in rows:
            concept, operator = enriched.get(r.field_name, ("", ""))
            w.writerow(
                [
                    r.field_name,
                    r.block,
                    r.bsee_block_key or "",
                    r.match_type,
                    int(r.matched),
                    concept,
                    operator,
                ]
            )
    s = crosswalk_summary(rows)
    pct = 100 * s["matched"] / s["total"] if s["total"] else 0
    enr = sum(1 for r in rows if enriched.get(r.field_name, ("", ""))[0])
    print(f"wrote {OUT}")
    print(
        f"GoM fields: {s['total']} | matched: {s['matched']} ({pct:.0f}%) "
        f"| unparsed block: {s['unparsed']} | with host concept: {enr}"
    )


if __name__ == "__main__":
    main()
