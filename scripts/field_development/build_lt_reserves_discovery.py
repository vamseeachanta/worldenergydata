#!/usr/bin/env python3
# ABOUTME: Builds the curated Lower Tertiary reserves + discovery-date table
# ABOUTME: from BOEM FieldReserves Table 4 + deepqual bins (issue #847).
"""Curate per-development BOEM recoverable reserves + discovery dates.

Inputs (raw bins, refreshed by scripts/refresh_bsee_all.py):
- fieldreserves_tables/2023_tables_xlsx_public__2023_table_4_final.bin —
  raw header=None grid of BOEM's annual Table 4 (all GoM fields, keyed on
  FIELD_NAME_CODE, Original/Remaining BOE reserves P10/P50/P90/MEAN +
  cumulative production, 31-Dec-2023 vintage).
- deepqual/mv_deep_water_field_leases.bin — one row per lease:
  FIELD_NAME_CODE, FLD_DISCVR_DATE, FLD_FIRST_PROD (field-level first
  production — preferred), FIRST_PROD_DATE (per-LEASE first production —
  fallback, min across the field's leases). Verified on Buckskin: field
  level 6/1/2019 vs lease dates 2019/2022/2026.

Bridge: config/input/lt_field_name_codes.yaml (committed, reviewed).

Outputs (data/modules/offshore_assets/curated/):
- lt_reserves_discovery.csv — one row per LT development, with citation
  columns (SOURCE_NAME/URL/VINTAGE/ACCESS_DATE). STOIIP is intentionally
  absent: no government STOIIP source exists; operator/announced figures
  stay a separately-cited column elsewhere (owner decision on #847).
- lt_reserves_discrepancies.csv — emitted whenever BOEM original reserves
  differ from the operator-announced figure by more than 20%.

Usage:
  python scripts/field_development/build_lt_reserves_discovery.py \
      [--repo-root PATH] [--access-date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import datetime as _dt
from pathlib import Path

import pandas as pd
import yaml

VINTAGE = "31-Dec-2023"
SOURCE_NAME = "BOEM Reserves Inventory Program, 2023 Tables (Table 4)"
SOURCE_URL = (
    "https://www.data.boem.gov/FieldReserves/Files/2023%20Tables%20xlsx%20Public.zip"
)
DEEPQUAL_SOURCE = "BSEE Deepwater Qualified Fields (DeepQualRawData.zip)"

#: Operator-announced recoverable figures (MMboe, FID press) — the WO
#: April 2026 Table 4 column. Used only for the discrepancy cross-check.
OPERATOR_ANNOUNCED_MMBOE = {
    "Anchor": 440,
    "Jack St Malo": 500,
    "Stones": 250,
}
DISCREPANCY_THRESHOLD = 0.20

T4_BIN = "data/modules/bsee/bin/fieldreserves_tables/2023_tables_xlsx_public__2023_table_4_final.bin"
DEEPQUAL_BIN = "data/modules/bsee/bin/deepqual/mv_deep_water_field_leases.bin"
BRIDGE = "config/input/lt_field_name_codes.yaml"
OUT_CSV = "data/modules/offshore_assets/curated/lt_reserves_discovery.csv"
OUT_DISC = "data/modules/offshore_assets/curated/lt_reserves_discrepancies.csv"


def load_bridge(path: Path) -> dict[str, list[str]]:
    """Return {development name: [FIELD_NAME_CODE, ...]}."""
    raw = yaml.safe_load(Path(path).read_text())
    return {
        dev: [entry["code"] for entry in entries]
        for dev, entries in raw["developments"].items()
    }


def parse_table4(raw: pd.DataFrame) -> pd.DataFrame:
    """Tidy the raw header=None Table 4 grid.

    Locates the header row by the 'Rank' cell; data starts three rows
    below (header, nickname, P10/P50/P90/MEAN sub-header). Column
    positions are fixed relative to the Rank column — the sheet layout
    (16 columns) is stable within a vintage; the known-answer test pins
    real values so a silent layout change fails loudly.
    """
    rank_hits = raw.index[
        raw.apply(lambda r: r.astype(str).str.strip().eq("Rank").any(), axis=1)
    ]
    if len(rank_hits) == 0:
        raise ValueError("Table 4 grid: no 'Rank' header row found")
    header_row = rank_hits[0]
    rank_col = (
        raw.loc[header_row].astype(str).str.strip().eq("Rank").idxmax()
    )
    c = rank_col  # columns are offsets from Rank
    data = raw.iloc[header_row + 3 :]
    data = data[data[c].notna()]
    tidy = pd.DataFrame(
        {
            "FIELD_NAME_CODE": data[c + 1].astype(str).str.strip(),
            "FIELD_NICKNAME": data[c + 2].astype(str).str.strip(),
            "DISC_YEAR": pd.to_numeric(data[c + 3], errors="coerce").astype("Int64"),
            "WATER_DEPTH_FT": pd.to_numeric(data[c + 4], errors="coerce"),
            "FIELD_TYPE": data[c + 5].astype(str).str.strip(),
            "ORIG_RESERVES_MEAN_MMBOE": pd.to_numeric(data[c + 9], errors="coerce"),
            "CUM_PROD_MMBOE": pd.to_numeric(data[c + 10], errors="coerce"),
            "REM_RESERVES_MEAN_MMBOE": pd.to_numeric(data[c + 14], errors="coerce"),
        }
    )
    return tidy.reset_index(drop=True)


def build_lt_table(
    bridge: dict[str, list[str]],
    t4: pd.DataFrame,
    deepqual: pd.DataFrame,
    vintage: str,
    access_date: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate Table 4 + deepqual per LT development.

    Multi-code developments sum reserves/production across codes and take
    the earliest discovery / first-production date. Developments absent
    from the vintage (post-vintage first oil or pre-FID) keep their row
    with NULL reserves and ``RESERVES_BOOKED = N``.
    """
    t4i = t4.set_index("FIELD_NAME_CODE")
    dq = deepqual.copy()
    dq["FIELD_NAME_CODE"] = dq["FIELD_NAME_CODE"].astype(str).str.strip()
    for col in ("FLD_DISCVR_DATE", "FLD_FIRST_PROD", "FIRST_PROD_DATE"):
        dq[col] = (
            pd.to_datetime(dq[col], errors="coerce")
            if col in dq.columns
            else pd.NaT
        )
    # Per field code: earliest dates; field-level first prod preferred
    # over the per-lease minimum.
    dqi = dq.groupby("FIELD_NAME_CODE").agg(
        _disc=("FLD_DISCVR_DATE", "min"),
        _fp_field=("FLD_FIRST_PROD", "min"),
        _fp_lease=("FIRST_PROD_DATE", "min"),
    )
    dqi["_first_prod"] = dqi["_fp_field"].fillna(dqi["_fp_lease"])

    rows = []
    discrepancies = []
    for dev, codes in bridge.items():
        booked = [c for c in codes if c in t4i.index]
        orig = t4i.loc[booked, "ORIG_RESERVES_MEAN_MMBOE"].sum() if booked else None
        cum = t4i.loc[booked, "CUM_PROD_MMBOE"].sum() if booked else None
        rem = t4i.loc[booked, "REM_RESERVES_MEAN_MMBOE"].sum() if booked else None

        dq_codes = [c for c in codes if c in dqi.index]

        def _min_iso(col: str) -> str | None:
            vals = dqi.loc[dq_codes, col].dropna() if dq_codes else []
            return min(vals).date().isoformat() if len(vals) else None

        disc_date = _min_iso("_disc")
        first_prod = _min_iso("_first_prod")

        rows.append(
            {
                "DEV_NAME": dev,
                "FIELD_NAME_CODES": "+".join(codes),
                "RESERVES_BOOKED": "Y" if booked else "N",
                "BOEM_ORIG_RESERVES_MEAN_MMBOE": orig,
                "BOEM_CUM_PROD_MMBOE": cum,
                "BOEM_REM_RESERVES_MEAN_MMBOE": rem,
                "DISCOVERY_DATE": disc_date,
                "FIRST_PROD_DATE": first_prod,
                "RESERVES_VINTAGE": vintage,
                "SOURCE_NAME": SOURCE_NAME,
                "SOURCE_URL": SOURCE_URL,
                "DATES_SOURCE": DEEPQUAL_SOURCE,
                "ACCESS_DATE": access_date,
            }
        )

        announced = OPERATOR_ANNOUNCED_MMBOE.get(dev)
        if announced and orig is not None and booked:
            if abs(orig - announced) / announced > DISCREPANCY_THRESHOLD:
                discrepancies.append(
                    {
                        "DEV_NAME": dev,
                        "BOEM_ORIG_RESERVES_MEAN_MMBOE": orig,
                        "OPERATOR_ANNOUNCED_MMBOE": announced,
                        "DELTA_PCT": round(100 * (orig - announced) / announced, 1),
                        "UNITS": "MMBOE",
                        "RESERVES_VINTAGE": vintage,
                    }
                )

    return pd.DataFrame(rows), pd.DataFrame(
        discrepancies,
        columns=[
            "DEV_NAME",
            "BOEM_ORIG_RESERVES_MEAN_MMBOE",
            "OPERATOR_ANNOUNCED_MMBOE",
            "DELTA_PCT",
            "UNITS",
            "RESERVES_VINTAGE",
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    parser.add_argument(
        "--access-date", default=_dt.date.today().isoformat()
    )
    args = parser.parse_args()
    root = (
        Path(args.repo_root)
        if args.repo_root
        else Path(__file__).resolve().parents[2]
    )

    bridge = load_bridge(root / BRIDGE)
    t4 = parse_table4(pd.read_pickle(root / T4_BIN))
    deepqual = pd.read_pickle(root / DEEPQUAL_BIN)

    curated, discrepancies = build_lt_table(
        bridge, t4, deepqual, vintage=VINTAGE, access_date=args.access_date
    )
    curated.to_csv(root / OUT_CSV, index=False)
    discrepancies.to_csv(root / OUT_DISC, index=False)
    print(f"Wrote {OUT_CSV} ({len(curated)} developments)")
    print(f"Wrote {OUT_DISC} ({len(discrepancies)} discrepancies)")


if __name__ == "__main__":
    main()
