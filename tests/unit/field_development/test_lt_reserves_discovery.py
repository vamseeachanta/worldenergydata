"""Curated LT reserves + discovery table builder (#847).

Covers: the committed dev→FIELD_NAME_CODE bridge, the Table-4 raw-grid
parser, the curated-table build (booked vs unbooked vintage caveat), and
the operator-figure discrepancy emission.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
_scripts_dir = REPO_ROOT / "scripts" / "field_development"
sys.path.insert(0, str(_scripts_dir))
from build_lt_reserves_discovery import (  # noqa: E402
    OPERATOR_ANNOUNCED_MMBOE,
    build_lt_table,
    load_bridge,
    parse_table4,
)

BRIDGE_PATH = REPO_ROOT / "config" / "input" / "lt_field_name_codes.yaml"

LT_DEVS = {
    "Anchor",
    "Big Foot",
    "Buckskin",
    "Cascade Chinook",
    "Jack St Malo",
    "Julia",
    "Kaskida",
    "North Platte",
    "Shenandoah",
    "Stones",
    "Tiber",
}


# ── bridge integrity ────────────────────────────────────────────────


def test_bridge_covers_all_lt_developments():
    bridge = load_bridge(BRIDGE_PATH)
    assert set(bridge) == LT_DEVS
    codes = [c for v in bridge.values() for c in v]
    assert len(codes) == len(set(codes)) == 13
    for code in codes:
        assert len(code) == 5 and code[:2].isalpha() and code[2:].isdigit(), code


def test_bridge_codes_resolve_in_deepqual():
    bin_path = (
        REPO_ROOT / "data/modules/bsee/bin/deepqual/mv_deep_water_field_leases.bin"
    )
    try:
        dq = pd.read_pickle(bin_path)
    except Exception:
        pytest.skip("deepqual bin not materialized (LFS stub / CI)")
    known = set(dq["FIELD_NAME_CODE"].astype(str).str.strip())
    bridge = load_bridge(BRIDGE_PATH)
    for dev, codes in bridge.items():
        for code in codes:
            assert code in known, f"{dev}: {code} not in deepqual"


# ── Table 4 parser ──────────────────────────────────────────────────


def _t4_fixture() -> pd.DataFrame:
    """Raw header=None grid shaped like the real 2023 Table 4 sheet."""
    rows = [
        [None] * 16,
        ["Table 4.  A listing..."] + [None] * 15,
        ["(Field type:  O -  Oil; G - Gas)"] + [None] * 15,
        [
            None,
            "Rank",
            "Field    name",
            None,
            "Disc          year",
            "Water  depth  (feet)",
            "Field   type",
            "Original  Reserves\n(MMBOE)",
            None,
            None,
            None,
            None,
            " Remaining Reserves\n(MMBOE",
            None,
            None,
            None,
        ],
        [
            None,
            None,
            None,
            "Field nickname",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "Cumulative Production     ",
            None,
            None,
            None,
            None,
        ],
        [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "P10",
            "P50",
            "P90",
            "MEAN",
            None,
            "P10",
            "P50",
            "P90",
            "MEAN",
        ],
        [
            None,
            1,
            "WR508",
            "STONES",
            2005,
            9556,
            "O",
            100.0,
            120.0,
            150.0,
            128.3,
            77.5,
            30.0,
            50.0,
            70.0,
            50.8,
        ],
        [
            None,
            2,
            "KC872",
            "BUCKSKIN",
            2008,
            6800,
            "O",
            400.0,
            450.0,
            500.0,
            456.6,
            51.0,
            350.0,
            400.0,
            450.0,
            405.6,
        ],
    ]
    return pd.DataFrame(rows)


def test_parse_table4_tidies_raw_grid():
    tidy = parse_table4(_t4_fixture())
    assert list(tidy["FIELD_NAME_CODE"]) == ["WR508", "KC872"]
    stones = tidy.iloc[0]
    assert stones["FIELD_NICKNAME"] == "STONES"
    assert stones["DISC_YEAR"] == 2005
    assert stones["ORIG_RESERVES_MEAN_MMBOE"] == 128.3
    assert stones["CUM_PROD_MMBOE"] == 77.5
    assert stones["REM_RESERVES_MEAN_MMBOE"] == 50.8


# ── curated build ───────────────────────────────────────────────────


def _deepqual_fixture() -> pd.DataFrame:
    # One row per LEASE (real deepqual shape). Buckskin mirrors the live
    # defect this guards: field-level FLD_FIRST_PROD says 2019 while one
    # lease's FIRST_PROD_DATE says 2026 — field level must win.
    return pd.DataFrame(
        {
            "FIELD_NAME_CODE": ["WR508", "KC872", "KC872", "GC807"],
            "FLD_NICK_NAME": ["Stones", "Buckskin", "Buckskin", "Anchor"],
            "FLD_DISCVR_DATE": [
                "2005-05-01",
                "2008-11-01",
                "2008-11-01",
                "2014-12-01",
            ],
            "FLD_FIRST_PROD": [None, "2019-06-01", "2019-06-01", None],
            "FIRST_PROD_DATE": ["2016-09-01", "2026-06-06", "2019-06-13", None],
        }
    )


def test_build_marks_unbooked_fields_with_caveat():
    bridge = {"Stones": ["WR508"], "Buckskin": ["KC872"], "Anchor": ["GC807"]}
    curated, _ = build_lt_table(
        bridge,
        parse_table4(_t4_fixture()),
        _deepqual_fixture(),
        vintage="31-Dec-2023",
        access_date="2026-07-06",
    )
    by_dev = curated.set_index("DEV_NAME")
    assert by_dev.loc["Stones", "BOEM_ORIG_RESERVES_MEAN_MMBOE"] == 128.3
    assert by_dev.loc["Stones", "RESERVES_BOOKED"] == "Y"
    # Anchor: first oil 2024 — absent from the 2023 vintage by design
    assert by_dev.loc["Anchor", "RESERVES_BOOKED"] == "N"
    assert pd.isna(by_dev.loc["Anchor", "BOEM_ORIG_RESERVES_MEAN_MMBOE"])
    assert by_dev.loc["Anchor", "DISCOVERY_DATE"] == "2014-12-01"
    # Stones has no field-level first prod → per-lease fallback
    assert by_dev.loc["Stones", "FIRST_PROD_DATE"] == "2016-09-01"
    # Buckskin: field-level 2019 wins over the 2026 lease date
    assert by_dev.loc["Buckskin", "FIRST_PROD_DATE"] == "2019-06-01"
    for col in ("SOURCE_NAME", "SOURCE_URL", "RESERVES_VINTAGE", "ACCESS_DATE"):
        assert by_dev[col].notna().all()


def test_discrepancy_emitted_above_20_percent():
    bridge = {"Stones": ["WR508"], "Buckskin": ["KC872"]}
    _, disc = build_lt_table(
        bridge,
        parse_table4(_t4_fixture()),
        _deepqual_fixture(),
        vintage="31-Dec-2023",
        access_date="2026-07-06",
    )
    # Stones: BOEM 128.3 vs operator 250 MMboe → |Δ|/250 ≈ 49% > 20%
    assert "Stones" in set(disc["DEV_NAME"])
    row = disc.set_index("DEV_NAME").loc["Stones"]
    assert row["BOEM_ORIG_RESERVES_MEAN_MMBOE"] == 128.3
    assert row["OPERATOR_ANNOUNCED_MMBOE"] == OPERATOR_ANNOUNCED_MMBOE["Stones"] == 250
    assert row["UNITS"] == "MMBOE"
    # Buckskin has no operator figure → never in the discrepancy list
    assert "Buckskin" not in set(disc["DEV_NAME"])


# ── known answer against the real pull (share/bin gated) ───────────


def test_known_answer_real_2023_vintage():
    t4_bin = (
        REPO_ROOT
        / "data/modules/bsee/bin/fieldreserves_tables"
        / "2023_tables_xlsx_public__2023_table_4_final.bin"
    )
    try:
        raw = pd.read_pickle(t4_bin)
    except Exception:
        pytest.skip("fieldreserves_tables bin not materialized (LFS stub / CI)")
    tidy = parse_table4(raw).set_index("FIELD_NAME_CODE")
    assert tidy.loc["WR508", "ORIG_RESERVES_MEAN_MMBOE"] == 128.3  # Stones
    assert tidy.loc["KC872", "ORIG_RESERVES_MEAN_MMBOE"] == 456.6  # Buckskin
