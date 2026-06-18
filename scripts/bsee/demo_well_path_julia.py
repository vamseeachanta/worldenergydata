#!/usr/bin/env python3
"""Render 3D well paths for the Julia field (BSEE lease G20351, Walker Ridge).

Drives the existing BSEE well-path pipeline + the two shared 3D renderers
(Plotly and Three.js) against REAL BSEE directional-survey data.

.. note::

   **The directional-survey data is NOT in this git repo.** It lives at an
   OFF-REPO data location: ``data/modules/bsee/bin/dsptsdelimit/`` is excluded
   by ``.gitignore`` (``/data/modules/bsee/bin`` + ``**/*.bin``) per the
   project's Local Data Pattern (``docs/data/LOCAL_DATA_PATTERN.md``) — the
   ~140 MB ZIP / 1.17 GB raw / 4.9M-row pickle are far too large for git and
   are freely re-downloadable from the public BSEE API. This script
   regenerates that data on demand (auto-downloads the ZIP if the pickle is
   missing); you can also run ``make data``. Do not commit anything under that
   directory.

Data sources (all public BSEE):
  * Directional surveys: ``dsptsdelimit.ZIP`` (~140 MB) ->
    ``data/modules/bsee/bin/dsptsdelimit/dsptsdelimit.{ZIP,bin}`` (OFF-REPO,
    gitignored — see note above).
    The headerless raw file is parsed with the 13 documented column names
    (see ``well_data.py:_get_column_names_for_dsptsdelimit_file``).
  * Well metadata: ``data/modules/bsee/current/wells/well_data.csv`` (curated
    Lower-Tertiary working set), which names the Julia wells present in this
    catalog: ``JU101`` and ``JU105``.

Julia-well identification
-------------------------
This demo renders the Julia wells PRESENT IN THE CURATED WELL CATALOG
(``well_data.csv``), selected by the "JU" ``WELL_NAME`` prefix: API12s
608124009400 (JU101) and 608124011101 (JU105). This is NOT the full Julia /
G20351 field -- the field also includes JU102/JU103/JU104/JU106 (see
``tests/unit/bsee/analysis/legacy/results/Data/WR_584.csv``), which are simply
absent from the curated catalog. A surface lat/long box was *not* used as the
filter because the survey file's SURF_LAT/LON columns carry per-station (not
surface) coordinates, so a Walker-Ridge box mis-classifies these wells.

Usage::

    uv run python scripts/bsee/demo_well_path_julia.py

Assumes the pickle/zip is already present; downloads the ZIP if missing.
"""

from __future__ import annotations

import math
import os
import pickle
import sys
import urllib.request
import zipfile

import pandas as pd

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "src"))

# OFF-REPO data location: this tree is gitignored (see module note + .gitignore).
# Nothing under DSPTS_DIR is tracked; the pickle is regenerated, never committed.
DSPTS_DIR = os.path.join(REPO, "data", "modules", "bsee", "bin", "dsptsdelimit")
DSPTS_ZIP = os.path.join(DSPTS_DIR, "dsptsdelimit.ZIP")
DSPTS_BIN = os.path.join(DSPTS_DIR, "dsptsdelimit.bin")
DSPTS_TXT_MEMBER = "dsptsdelimit.txt"
DSPTS_URL = "https://www.data.bsee.gov/Well/Files/dsptsdelimit.ZIP"

WELL_DATA_CSV = os.path.join(
    REPO, "data", "modules", "bsee", "current", "wells", "well_data.csv"
)

REPORTS_DIR = os.path.join(REPO, "reports", "bsee")
PLOTLY_OUT = os.path.join(REPORTS_DIR, "julia_well_path_plotly.html")
THREEJS_OUT = os.path.join(REPORTS_DIR, "julia_well_path_threejs.html")

FIELD_NAME = "Julia (Walker Ridge, lease G20351)"

# 13 documented columns of the headerless dsptsdelimit raw file, in order.
DSPTS_COLS = [
    "API_WELL_NUMBER",
    "INCL_ANG_DEG_VAL",
    "INCL_ANG_MIN_VAL",
    "SURVEY_POINT_MD",
    "WELL_N_S_CODE",
    "DIR_DEG_VAL",
    "DIR_MINS_VAL",
    "WELL_E_W_CODE",
    "SURVEY_POINT_TVD",
    "DELTA_X",
    "DELTA_Y",
    "SURF_LONGITUDE",
    "SURF_LATITUDE",
]

# Deg -> feet conversion (standard local-tangent approximation).
FT_PER_DEG_LAT = 364000.0
FT_PER_DEG_LON_AT_EQ = 365000.0


# ---------------------------------------------------------------------------
# Step 1: download (if missing) + verify
# ---------------------------------------------------------------------------
def ensure_zip() -> None:
    if os.path.exists(DSPTS_ZIP) and os.path.getsize(DSPTS_ZIP) > 130_000_000:
        return
    os.makedirs(DSPTS_DIR, exist_ok=True)
    print(f"Downloading {DSPTS_URL} ...")
    urllib.request.urlretrieve(DSPTS_URL, DSPTS_ZIP)
    size = os.path.getsize(DSPTS_ZIP)
    with open(DSPTS_ZIP, "rb") as fh:
        magic = fh.read(4)
    if magic[:2] != b"PK":
        raise RuntimeError(
            f"Downloaded file is not a ZIP (magic={magic!r}); "
            "BSEE likely returned an HTML error page."
        )
    print(f"  downloaded {size:,} bytes; PK magic OK")


# ---------------------------------------------------------------------------
# Step 2: parse -> pickle (or load existing pickle)
# ---------------------------------------------------------------------------
def load_surveys() -> pd.DataFrame:
    """Return the full directional-survey DataFrame with proper headers.

    Prefers an already-built pickle; rebuilds it from the ZIP otherwise. The
    raw file is headerless, so the 13 documented column names are applied in
    order (a prior loader bug consumed the first data row as a header).
    """

    def _good_pickle(df: pd.DataFrame) -> bool:
        return "API_WELL_NUMBER" in df.columns

    if os.path.exists(DSPTS_BIN):
        with open(DSPTS_BIN, "rb") as fh:
            df = pickle.load(fh)
        if _good_pickle(df):
            print(f"Loaded existing pickle: {df.shape[0]:,} rows")
            return _normalize(df)
        print("Existing pickle lacks named columns; rebuilding from ZIP ...")

    ensure_zip()
    print("Parsing dsptsdelimit.txt from ZIP ...")
    with zipfile.ZipFile(DSPTS_ZIP) as zf:
        with zf.open(DSPTS_TXT_MEMBER) as raw:
            df = pd.read_csv(
                raw,
                header=None,
                names=DSPTS_COLS,
                dtype={
                    "API_WELL_NUMBER": str,
                    "WELL_N_S_CODE": str,
                    "WELL_E_W_CODE": str,
                },
            )
    df = _normalize(df)
    with open(DSPTS_BIN, "wb") as out:
        pickle.dump(df, out)
    print(f"Parsed + pickled: {df.shape[0]:,} rows")
    return df


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in ("API_WELL_NUMBER", "WELL_N_S_CODE", "WELL_E_W_CODE"):
        df[c] = df[c].astype(str).str.strip()
    return df


# ---------------------------------------------------------------------------
# Step 3: identify Julia wells (API cross-reference with well_data.csv)
# ---------------------------------------------------------------------------
def julia_well_metadata() -> pd.DataFrame:
    """Return the well_data.csv rows for Julia wells (WELL_NAME starts 'JU')."""
    wd = pd.read_csv(WELL_DATA_CSV, dtype=str)
    wd["API_WELL_NUMBER"] = (
        wd["API_WELL_NUMBER"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    )
    julia = wd[wd["WELL_NAME"].astype(str).str.upper().str.startswith("JU")].copy()
    return julia


# ---------------------------------------------------------------------------
# Step 4: build pipeline inputs
# ---------------------------------------------------------------------------
def build_inputs(
    surveys_all: pd.DataFrame, julia_meta: pd.DataFrame
) -> tuple[pd.DataFrame, dict]:
    julia_apis = list(julia_meta["API_WELL_NUMBER"].unique())
    ds = surveys_all[surveys_all["API_WELL_NUMBER"].isin(julia_apis)].copy()
    if ds.empty:
        raise RuntimeError(f"No survey rows for Julia APIs {julia_apis}")

    # Critical geometry inputs: coerce then FAIL CLOSED. Silently filling NaN
    # with 0.0 on these columns would fabricate well geometry (a 0-md / 0-inc /
    # 0-az station looks like a vertical surface point), so any residual NaN
    # after coercion is a hard error reported per-well/per-column.
    critical_cols = (
        "SURVEY_POINT_MD",
        "INCL_ANG_DEG_VAL",
        "INCL_ANG_MIN_VAL",
        "DIR_DEG_VAL",
        "DIR_MINS_VAL",
    )
    for c in critical_cols:
        ds[c] = pd.to_numeric(ds[c], errors="coerce")
        bad = ds[c].isna()
        if bad.any():
            counts = (
                ds.loc[bad, "API_WELL_NUMBER"].value_counts().to_dict()
            )
            for api, n in counts.items():
                print(
                    f"ERROR: column {c!r} has {n} non-numeric/NaN row(s) "
                    f"for API12 {api}"
                )
            raise ValueError(
                f"Critical survey column {c!r} has {int(bad.sum())} invalid "
                "row(s) after coercion; refusing to fill geometry inputs with 0."
            )

    # Non-critical / optional columns may default to 0.0 (only used for an
    # informational lat/lon box, not the minimum-curvature geometry).
    for c in ("SURF_LONGITUDE", "SURF_LATITUDE"):
        ds[c] = pd.to_numeric(ds[c], errors="coerce").fillna(0.0)

    ds = ds.rename(columns={"API_WELL_NUMBER": "API12"})
    ds["API12"] = ds["API12"].astype("int64")

    # Data hygiene (input shaping only -- the pipeline now owns the
    # positional-index fix internally via its own reset_index):
    #  (1) The raw survey carries a trailing record with SURVEY_POINT_MD == 0
    #      per well (a sentinel/footer row). Left in place it (a) corrupts the
    #      payload's ``total_md`` (which reads the last point's md) and
    #      (b) duplicates the surface md. Keep only the first md==0 row per well.
    #  (2) Sort by (API12, md) so the per-well slices the pipeline builds are in
    #      depth order; reset to a clean RangeIndex before the dedup below.
    ds = ds.sort_values(["API12", "SURVEY_POINT_MD"]).reset_index(drop=True)
    is_zero = ds["SURVEY_POINT_MD"] == 0
    # within each well, keep the FIRST zero-md row, drop any later zero-md rows
    dup_zero = is_zero & ds.duplicated(subset=["API12", "SURVEY_POINT_MD"], keep="first")
    ds = ds[~dup_zero].reset_index(drop=True)

    # Surface coords for the relative-WH offset come from well_data.csv
    # (authoritative surface lat/long), converted to field-relative feet.
    julia_meta = julia_meta.copy()
    julia_meta["lat"] = pd.to_numeric(julia_meta["SURF_LATITUDE"], errors="coerce")
    julia_meta["lon"] = pd.to_numeric(julia_meta["SURF_LONGITUDE"], errors="coerce")
    lat0 = julia_meta["lat"].mean()
    lon0 = julia_meta["lon"].mean()
    cos_lat0 = math.cos(math.radians(lat0))

    rows = []
    for _, m in julia_meta.iterrows():
        api12 = int(m["API_WELL_NUMBER"])
        api10 = int(str(api12)[:10])
        # Pipeline coordinate convention (well_api12.py:process_survey_xyz +
        # add_relative_WH_positions): x_coor = NORTH component
        # (delta_x = sin(inc)*cos(az), azimuth from north), y_coor = EAST
        # component (delta_y = sin(inc)*sin(az)). The relative wellhead offset is
        # added to those same axes, so SURF_x_rel MUST be the NORTH offset and
        # SURF_y_rel MUST be the EAST offset (both feet). Do NOT swap these.
        surf_x = (m["lat"] - lat0) * FT_PER_DEG_LAT  # NORTH offset (x axis)
        surf_y = (m["lon"] - lon0) * cos_lat0 * FT_PER_DEG_LON_AT_EQ  # EAST offset (y axis)
        rows.append(
            {
                "API12": api12,
                "API10": api10,
                "Well Name": str(m.get("WELL_NAME") or api12),
                "Sidetrack and Bypass": str(m.get("WELL_NAME_SUFFIX") or ""),
                "SURF_x_rel": round(surf_x, 2),
                "SURF_y_rel": round(surf_y, 2),
                "Water Depth (feet)": pd.to_numeric(
                    m.get("WATER_DEPTH"), errors="coerce"
                ),
                "Total Measured Depth": pd.to_numeric(
                    m.get("BH_TOTAL_MD"), errors="coerce"
                ),
                "Total Depth Date": m.get("TOTAL_DEPTH_DATE"),
                "Spud Date": m.get("WELL_SPUD_DATE"),
            }
        )
    merged = pd.DataFrame(rows)
    well_data = {"merged_api12_df": merged}
    return ds, well_data


# ---------------------------------------------------------------------------
# Step 5-6: run pipeline + render
# ---------------------------------------------------------------------------
def main() -> int:
    from worldenergydata.bsee.analysis.well_api12 import WellAPI12
    from worldenergydata.bsee.visualization import (
        render_well_paths_plotly,
        render_well_paths_threejs,
    )

    surveys_all = load_surveys()
    julia_meta = julia_well_metadata()
    selected_apis = sorted(julia_meta["API_WELL_NUMBER"].unique())
    assert selected_apis, (
        'No wells selected: no "JU"-prefixed WELL_NAME rows found in '
        f"{WELL_DATA_CSV}"
    )
    print(
        f"\nSelected {len(selected_apis)} Julia well(s) from the curated "
        f"catalog (API12s): {selected_apis}"
    )
    print("\nJulia wells (from well_data.csv):")
    print(
        julia_meta[
            ["API_WELL_NUMBER", "WELL_NAME", "WELL_NAME_SUFFIX",
             "SURF_LATITUDE", "SURF_LONGITUDE"]
        ].to_string(index=False)
    )

    ds, well_data = build_inputs(surveys_all, julia_meta)

    # Run the FIXED pipeline ONCE with ALL Julia wells. prepare_well_paths now
    # does .reset_index(drop=True) on each per-API survey slice (well_api12.py
    # ~line 538), so its positional-read / label-write alignment holds for every
    # well, not just the first. Passing all wells in a single call exercises the
    # multi-well path end-to-end on real data (the prior one-well-per-call
    # workaround is no longer needed).
    pipe = WellAPI12()
    pipe.prepare_well_paths(ds, well_data)
    payload = pipe.export_well_paths(field_name=FIELD_NAME)
    if not payload or payload["well_count"] == 0:
        print("ERROR: no well paths produced")
        return 1

    os.makedirs(REPORTS_DIR, exist_ok=True)
    render_well_paths_plotly(payload, PLOTLY_OUT, title=FIELD_NAME)
    render_well_paths_threejs(payload, THREEJS_OUT, title=FIELD_NAME)

    # ---- self-verification ----
    print(f"\nField: {payload['field']['name']}")
    print(f"Well count: {payload['well_count']}")
    print(f"Bounds (ft): {payload['bounds']}")
    for w in payload["wells"]:
        npts = len(w["points"])
        print(
            f"  {w['api12']}  {w['label']:<20} "
            f"pts={npts:<4} total_md={w['total_md']:.0f} "
            f"max_tvd={w['max_tvd']:.0f} "
            f"surf=({w['surface']['x']:.0f},{w['surface']['y']:.0f})"
        )
    for p in (PLOTLY_OUT, THREEJS_OUT):
        print(f"  wrote {p} ({os.path.getsize(p):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
