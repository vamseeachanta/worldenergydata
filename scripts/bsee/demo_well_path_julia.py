#!/usr/bin/env python3
"""Render 3D well paths for the Julia field (BSEE lease G20351, Walker Ridge).

Drives the existing BSEE well-path pipeline + the two shared 3D renderers
(Plotly and Three.js) against REAL BSEE directional-survey data.

.. note::

   **The directional-survey data is NOT in this git repo.** It lives at an
   OFF-REPO data location: ``data/modules/bsee/bin/dsptsdelimit/`` is excluded
   by ``.gitignore`` (``/data/modules/bsee/bin`` + ``**/*.bin``) per the
   local data pattern (``docs/data/LOCAL_DATA_PATTERN.md``).
   The archive and its text member remain local data. This script downloads
   the ZIP only when missing and verifies it against a required SHA-256 pin
   before parsing. Legacy binary caches are ignored and left untouched.

Data sources (all public BSEE):
  * Directional surveys: ``dsptsdelimit.ZIP`` ->
    ``data/modules/bsee/bin/dsptsdelimit/dsptsdelimit.ZIP`` (OFF-REPO,
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

    uv run python scripts/bsee/demo_well_path_julia.py --survey-sha256 "$SURVEY_SHA256"

The digest must come from an independently reviewed, trusted archive version.
See ``docs/modules/bsee/survey-archive-integrity.md`` for the trust boundary and
an offline worked example. No digest is inferred from a fresh download.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import math
import os
import string
import sys
import zipfile

import httpx
import pandas as pd

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "src"))

# OFF-REPO data location: this tree is gitignored (see module note + .gitignore).
# Nothing under DSPTS_DIR is tracked; only the text archive is read.
DSPTS_DIR = os.path.join(REPO, "data", "modules", "bsee", "bin", "dsptsdelimit")
DSPTS_ZIP = os.path.join(DSPTS_DIR, "dsptsdelimit.ZIP")
DSPTS_TXT_MEMBER = "dsptsdelimit.txt"
DSPTS_URL = "https://www.data.bsee.gov/Well/Files/dsptsdelimit.ZIP"

WELL_DATA_CSV = os.path.join(
    REPO, "data", "modules", "bsee", "current", "wells", "well_data.csv"
)

REPORTS_DIR = os.path.join(REPO, "reports", "bsee")
PLOTLY_OUT = os.path.join(REPORTS_DIR, "julia_well_path_plotly.html")
THREEJS_OUT = os.path.join(REPORTS_DIR, "julia_well_path_threejs.html")

FIELD_NAME = "Julia (Walker Ridge, lease G20351)"

# Schema source: WellData._get_column_names_for_dsptsdelimit_file in
# packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/zip/well_data.py.
# Preserve that documented headerless column order.
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
    """Download the fixed HTTPS source only when the local archive is absent.

    Download success is not evidence of integrity; load_surveys verifies the
    required digest before interpreting any archive contents. Redirects are
    refused so an unexpected endpoint requires explicit investigation.
    """
    if os.path.exists(DSPTS_ZIP):
        return
    os.makedirs(DSPTS_DIR, exist_ok=True)
    print(f"Downloading {DSPTS_URL} ...")
    with httpx.stream("GET", DSPTS_URL, follow_redirects=False) as response:
        response.raise_for_status()
        with open(DSPTS_ZIP, "xb") as output:
            output.writelines(response.iter_bytes())


def _validate_digest(expected_sha256: str) -> str:
    """Require a SHA-256 hexadecimal pin, never an observed-download default."""
    # Python hashlib documentation, hash.digest_size and hash.hexdigest:
    # https://docs.python.org/3/library/hashlib.html#hash-objects
    # Each digest byte has two hexadecimal digits.
    if (
        not isinstance(expected_sha256, str)
        or len(expected_sha256) != hashlib.sha256().digest_size * 2
        or any(character not in string.hexdigits for character in expected_sha256)
    ):
        raise ValueError("A complete hexadecimal SHA-256 pin is required")
    return expected_sha256.lower()


# ---------------------------------------------------------------------------
# Step 2: verify archive bytes, then parse data-only text with the pinned schema
# ---------------------------------------------------------------------------
def load_surveys(expected_sha256: str) -> pd.DataFrame:
    """Verify the archive against a trusted pin before reading its text member.

    There is no binary-cache fallback. Cached ZIPs are reverified on every call.
    Hashing and ZIP parsing use the same open file to avoid reopening a changed
    path between verification and parsing. Invalid files are left for inspection.
    """
    expected_sha256 = _validate_digest(expected_sha256)
    ensure_zip()
    with open(DSPTS_ZIP, "rb") as archive:
        digest = hashlib.sha256()
        for chunk in iter(lambda: archive.read(io.DEFAULT_BUFFER_SIZE), b""):
            digest.update(chunk)
        if digest.hexdigest() != expected_sha256:
            raise ValueError("Survey archive SHA-256 mismatch; refusing to parse")
        archive.seek(0)
        with zipfile.ZipFile(archive) as zf:
            if zf.namelist().count(DSPTS_TXT_MEMBER) != 1:
                raise ValueError("Archive must contain exactly one dsptsdelimit.txt")
            with zf.open(DSPTS_TXT_MEMBER) as raw:
                try:
                    # Infer field count before assigning names: supplying names
                    # to read_csv can silently turn extra fields into an index.
                    df = pd.read_csv(raw, header=None, dtype=str, keep_default_na=False)
                    if df.empty or len(df.columns) != len(DSPTS_COLS):
                        raise ValueError("Unexpected survey field count")
                    df.columns = DSPTS_COLS
                    df = _normalize(df)
                    if not df["API_WELL_NUMBER"].str.fullmatch(r"[0-9]+").all():
                        raise ValueError("Invalid survey identifier")
                    for column, codes in (
                        ("WELL_N_S_CODE", ("N", "S")),
                        ("WELL_E_W_CODE", ("E", "W")),
                    ):
                        if not df[column].isin(codes).all():
                            raise ValueError("Invalid survey direction code")
                    for column in DSPTS_COLS:
                        if column not in (
                            "API_WELL_NUMBER",
                            "WELL_N_S_CODE",
                            "WELL_E_W_CODE",
                        ):
                            df[column] = pd.to_numeric(df[column], errors="raise")
                except (ValueError, pd.errors.ParserError) as error:
                    raise ValueError(
                        "Text does not match the documented survey schema"
                    ) from error
    print(f"Verified + parsed: {df.shape[0]:,} rows")
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
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render verified survey text")
    parser.add_argument(
        "--survey-sha256",
        required=True,
        type=_validate_digest,
        help="Trusted SHA-256 pin for the exact survey ZIP version",
    )
    args = parser.parse_args(argv)
    surveys_all = load_surveys(args.survey_sha256)

    from worldenergydata.bsee.analysis.well_api12 import WellAPI12
    from worldenergydata.bsee.visualization import (
        render_well_paths_plotly,
        render_well_paths_threejs,
    )

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
