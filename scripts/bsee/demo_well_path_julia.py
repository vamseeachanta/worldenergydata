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
  * Lease membership and well names: the raw ``mv_war_main.txt`` table.
  * Well metadata: the raw ``mv_boreholes_all.txt`` table.
    Supply both comma-delimited tables explicitly. No curated-catalog
    fallback is used; provision the raw inputs before running this demo.

Julia-well identification
-------------------------
WAR surface-lease membership selects the field's full bore set, including
non-producers and sidetracks. Names and surface positions must agree with the
raw borehole records. The curated catalog is excluded because its metadata
conflicts with the lease-resolved economics data (issue #493, 2026). Missing
metadata, conflicting identities or missing survey coverage stop the render.
Neither a name prefix nor a survey-station latitude/longitude box establishes
field membership. This selection alone does not reconcile the curated catalog;
real-data reconciliation and regenerated figures remain separate work.

Usage::

    uv run python scripts/bsee/demo_well_path_julia.py \\
        --war-main-csv mv_war_main.txt --boreholes-csv mv_boreholes_all.txt

Assumes the pickle/zip is already present; downloads the ZIP if missing.
"""

from __future__ import annotations

import argparse
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

REPORTS_DIR = os.path.join(REPO, "reports", "bsee")
PLOTLY_OUT = os.path.join(REPORTS_DIR, "julia_well_path_plotly.html")
THREEJS_OUT = os.path.join(REPORTS_DIR, "julia_well_path_threejs.html")

FIELD_NAME = "Julia (Walker Ridge, lease G20351)"
# Lease basis: docs/data-sources/bsee/analysis/julia_api12_resolution.md
# (2025-07-24), "Way forward": select APIs from downloaded WAR records.
FIELD_LEASE = "G20351"

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
# Step 3: identify Julia wells from WAR surface-lease membership
# ---------------------------------------------------------------------------
def _clean_text(values: pd.Series) -> pd.Series:
    """Normalize quoted BSEE text while preserving missing values."""
    return values.astype("string").str.replace('"', "", regex=False).str.strip()


def _api_keys(values: pd.Series) -> pd.Series:
    """Match string/integer/float API spellings without truncating bore IDs."""
    return _clean_text(values).str.replace(r"\.0$", "", regex=True)


def julia_well_metadata(
    war_main: pd.DataFrame,
    boreholes: pd.DataFrame,
) -> pd.DataFrame:
    """Join lease-selected WAR APIs to raw borehole metadata, failing closed.

    Input schemas follow bsee/data/loaders/api/well.py
    (get_eWellWARRawData_mv_war_main_from_bin and get_BoreholeRawData_from_bin).
    The caller supplies decoded raw tables. Repeated WAR activities
    and identical borehole records are allowed; ambiguous identities are not.
    """
    war_columns = ["API_WELL_NUMBER", "SURF_LEASE_NUM", "WELL_NAME"]
    bore_columns = ["API_WELL_NUMBER", "WELL_NAME", "SURF_LATITUDE", "SURF_LONGITUDE"]
    for label, frame, required in (
        ("WAR", war_main, war_columns),
        ("borehole", boreholes, bore_columns),
    ):
        missing = sorted(set(required) - set(frame.columns))
        if missing:
            raise ValueError(f"Missing {label} columns: {missing}")

    # Match the economics resolver's _norm_lease in lower_tertiary/ops_timeline.py.
    lease = (
        _clean_text(war_main["SURF_LEASE_NUM"])
        .str.upper()
        .str.replace(" ", "", regex=False)
    )
    selected = war_main.loc[lease == FIELD_LEASE, war_columns].copy()
    if selected.empty:
        raise ValueError(f"No WAR wells for surface lease {FIELD_LEASE}")
    selected["SURF_LEASE_NUM"] = FIELD_LEASE
    selected["API_WELL_NUMBER"] = _api_keys(selected["API_WELL_NUMBER"])
    # API12 format basis: issue #493 (2026), API12 evidence table; do not
    # truncate a longer identifier into a potentially different bore.
    if not selected["API_WELL_NUMBER"].str.fullmatch(r"[0-9]{12}").fillna(False).all():
        raise ValueError("Invalid WAR API: expected complete API12 identifiers")
    selected["WELL_NAME"] = _clean_text(selected["WELL_NAME"]).str.upper()
    if selected["WELL_NAME"].isna().any() or selected["WELL_NAME"].eq("").any():
        raise ValueError("Missing WAR well name")
    selected = selected.drop_duplicates()
    if selected["API_WELL_NUMBER"].duplicated().any():
        raise ValueError("Conflicting WAR names for the same API")

    optional = [
        "WELL_NAME_SUFFIX",
        "WATER_DEPTH",
        "BH_TOTAL_MD",
        "TOTAL_DEPTH_DATE",
        "WELL_SPUD_DATE",
    ]
    metadata = boreholes.reindex(columns=bore_columns + optional).copy()
    metadata["API_WELL_NUMBER"] = _api_keys(metadata["API_WELL_NUMBER"])
    metadata = metadata[metadata["API_WELL_NUMBER"].isin(selected["API_WELL_NUMBER"])]
    for column in metadata.columns:
        if column != "API_WELL_NUMBER":
            metadata[column] = _clean_text(metadata[column])
    metadata["WELL_NAME"] = metadata["WELL_NAME"].str.upper()
    metadata = metadata.drop_duplicates()
    if metadata["API_WELL_NUMBER"].duplicated().any():
        raise ValueError("Conflicting borehole metadata for the same API")
    missing_apis = sorted(
        set(selected["API_WELL_NUMBER"]) - set(metadata["API_WELL_NUMBER"])
    )
    if missing_apis:
        raise ValueError(f"Missing borehole metadata for APIs: {missing_apis}")
    result = selected.merge(
        metadata,
        on="API_WELL_NUMBER",
        suffixes=("", "_BOREHOLE"),
        validate="one_to_one",
    )
    disagrees = result["WELL_NAME_BOREHOLE"].isna() | (
        result["WELL_NAME"] != result["WELL_NAME_BOREHOLE"]
    )
    if disagrees.any():
        apis = result.loc[disagrees, "API_WELL_NUMBER"].tolist()
        raise ValueError(f"Conflicting well names between WAR and boreholes: {apis}")
    for column, limit in (("SURF_LATITUDE", 90), ("SURF_LONGITUDE", 180)):
        result[column] = pd.to_numeric(result[column], errors="coerce")
        if (
            not result[column]
            .map(lambda value: pd.notna(value) and math.isfinite(value))
            .all()
            or not result[column].between(-limit, limit).all()
        ):
            raise ValueError(f"Invalid borehole surface coordinates: {column}")
    # A missing suffix is optional, but pd.NA must not reach boolean fallback
    # expressions in build_inputs. Missing engineering quantities stay unknown.
    result["WELL_NAME_SUFFIX"] = result["WELL_NAME_SUFFIX"].fillna("")
    return (
        result.drop(columns="WELL_NAME_BOREHOLE")
        .sort_values("API_WELL_NUMBER")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Step 4: build pipeline inputs
# ---------------------------------------------------------------------------
def build_inputs(
    surveys_all: pd.DataFrame, julia_meta: pd.DataFrame
) -> tuple[pd.DataFrame, dict]:
    julia_apis = list(julia_meta["API_WELL_NUMBER"].unique())
    survey_apis = _api_keys(surveys_all["API_WELL_NUMBER"])
    missing_apis = sorted(set(julia_apis) - set(survey_apis.dropna()))
    if missing_apis:
        raise ValueError(f"Missing survey rows for lease-selected APIs: {missing_apis}")
    ds = surveys_all[survey_apis.isin(julia_apis)].copy()
    ds["API_WELL_NUMBER"] = survey_apis.loc[ds.index]
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

    # Surface coords for the relative-WH offset come from the matched raw
    # borehole records, converted to field-relative feet.
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
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--war-main-csv",
        required=True,
        help="Raw comma-delimited WAR main table with surface-lease membership",
    )
    parser.add_argument(
        "--boreholes-csv",
        required=True,
        help="Raw comma-delimited borehole table with names and surface coordinates",
    )
    args = parser.parse_args(argv)
    # Validate the lease inputs before importing the pipeline or downloading
    # the much larger survey dataset. Missing raw inputs have no fallback.
    julia_meta = julia_well_metadata(
        pd.read_csv(args.war_main_csv, dtype=str),
        pd.read_csv(args.boreholes_csv, dtype=str),
    )
    surveys_all = load_surveys()

    from worldenergydata.bsee.analysis.well_api12 import WellAPI12
    from worldenergydata.bsee.visualization import (
        render_well_paths_plotly,
        render_well_paths_threejs,
    )

    selected_apis = sorted(julia_meta["API_WELL_NUMBER"].unique())
    print(
        f"\nSelected {len(selected_apis)} well(s) from WAR surface lease "
        f"{FIELD_LEASE} (API12s): {selected_apis}"
    )
    print("\nLease-selected wells (WAR names, raw borehole metadata):")
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
