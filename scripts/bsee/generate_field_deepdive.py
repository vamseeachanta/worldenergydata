#!/usr/bin/env python
"""Generate per-field deep-dive HTML reports from the all-fields atlas.

For each requested field this reads its metrics from the atlas CSV (one row
per field), builds a per-field annual production timeline straight from the
OGOR-A ``.bin`` archives, and writes a self-contained interactive HTML page.

Usage::

    .venv/bin/python scripts/bsee/generate_field_deepdive.py --field MC807
    .venv/bin/python scripts/bsee/generate_field_deepdive.py --top 20

The atlas CSV is produced by ``scripts/bsee/generate_all_fields_atlas.py``;
run that first if it is missing.  All inputs are real BSEE public data;
nothing is fabricated.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from worldenergydata.bsee.reports.field_deepdive import (
    build_field_timeline,
    render_field_deepdive,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("field_deepdive")

DEFAULT_ATLAS = Path("reports/bsee/all_fields/gom_all_fields_atlas.csv")
DEFAULT_OUT = Path("reports/bsee/field_deepdives")


def _select_fields(atlas: pd.DataFrame, field: str | None, top: int | None):
    """Return the atlas rows to render."""
    if field is not None:
        target = str(field).strip()
        codes = atlas["FIELD_CODE"].astype(str).str.strip()
        sub = atlas[codes == target]
        if sub.empty:
            raise SystemExit(
                f"Field code {target!r} not found in the atlas CSV. "
                "Check the code, or regenerate the atlas."
            )
        return sub
    if top is not None:
        if "CUM_OIL_MMBBL" not in atlas.columns:
            raise SystemExit("Atlas CSV has no CUM_OIL_MMBBL column to rank by.")
        ranked = atlas.copy()
        ranked["_oil"] = pd.to_numeric(ranked["CUM_OIL_MMBBL"], errors="coerce")
        ranked = ranked.sort_values("_oil", ascending=False).head(top)
        return ranked.drop(columns="_oil")
    raise SystemExit("Specify --field <CODE> or --top N.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--field", type=str, help="render one field by FIELD_CODE")
    group.add_argument(
        "--top", type=int, help="render the top-N fields by CUM_OIL_MMBBL"
    )
    parser.add_argument("--atlas-csv", type=Path, default=DEFAULT_ATLAS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--start-year", type=int, default=1996)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="OGOR bin dir (default: resolved bsee bin/historical_production_yearly)",
    )
    args = parser.parse_args()

    if not args.atlas_csv.exists():
        raise SystemExit(
            f"Atlas CSV not found: {args.atlas_csv}\n"
            "Run scripts/bsee/generate_all_fields_atlas.py first to build it."
        )

    atlas = pd.read_csv(args.atlas_csv)
    if "FIELD_CODE" not in atlas.columns:
        raise SystemExit("Atlas CSV is missing the required FIELD_CODE column.")

    selected = _select_fields(atlas, args.field, args.top)
    args.out.mkdir(parents=True, exist_ok=True)

    written = 0
    for _, row in selected.iterrows():
        code = str(row["FIELD_CODE"]).strip()
        if not code:
            continue
        timeline = build_field_timeline(
            code,
            data_dir=args.data_dir,
            start_year=args.start_year,
            end_year=args.end_year,
        )
        html = render_field_deepdive(row, timeline)
        out_path = args.out / f"{code}.html"
        out_path.write_text(html)
        logger.info(
            "Wrote %s (%d timeline years, %d chars)",
            out_path,
            len(timeline),
            len(html),
        )
        written += 1

    logger.info("Wrote %d deep-dive page(s) to %s", written, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
