"""Unit tests for the per-field deep-dive report generator.

Synthetic only: a header-corrupted OGOR-A pickle fixture (reusing the
corruption pattern from ``test_ogor_production_loader.py``) plus hand-built
atlas field rows.  No real data, no network — deterministic everywhere.
"""

import pickle
from pathlib import Path

import pandas as pd
import pytest

from tests.test_markers import unit
from worldenergydata.bsee.data.sources.bin.ogor_production_loader import (
    OGOR_COLUMN_NAMES,
)
from worldenergydata.bsee.reports.field_deepdive import (
    build_field_timeline,
    render_field_deepdive,
)


def _row(yyyymm, oil, gas, wtr, api, field):
    """One canonical OGOR-A record (19 cols) for the given field/period."""
    return [
        "G12345",  # LEASE_NUMBER
        "E001",  # COMPLETION_NAME
        yyyymm,  # PRODUCTION_DATE (YYYYMM)
        30,  # DAYS_ON_PROD
        "O",  # PRODUCT_CODE
        oil,  # MON_O_PROD_VOL
        gas,  # MON_G_PROD_VOL
        wtr,  # MON_WTR_PROD_VOL
        api,  # API_WELL_NUMBER
        "PR",  # WELL_STAT_CD
        "MC0807",  # AREA_CODE_BLOCK_NUM
        "03151",  # OPERATOR_NUM
        "OPER",  # SORT_NAME
        field,  # BOEM_FIELD
        0.0,  # INJECTION_VOLUME
        "Q01",  # PROD_INTERVAL_CD
        20100101,  # FIRST_PROD_DATE
        "",  # UNIT_AGT_NUMBER
        "",  # UNIT_ALOC_SUFFIX
    ]


def _write_corrupted_bin(path: Path, rows) -> None:
    """Write a header-corrupted OGOR pickle (first record consumed as header).

    Matches the real on-disk artefact: the first physical row is lost and the
    columns are that first record's values.  We therefore prepend a sacrificial
    row so every row we care about survives.
    """
    sacrificial = _row(190001, 0.0, 0.0, 0.0, "000000000000", "ZZZ")
    full = pd.DataFrame([sacrificial] + rows, columns=OGOR_COLUMN_NAMES)
    corrupted = pd.DataFrame(full.iloc[1:].values, columns=list(full.iloc[0].values))
    with open(path, "wb") as f:
        pickle.dump(corrupted, f)


def _make_two_field_years(data_dir: Path) -> None:
    """Write 2023 + 2024 bins with two fields (MC807, GC640) and 2 wells each."""
    _write_corrupted_bin(
        data_dir / "ogora2023delimit.bin",
        [
            # MC807, year 2023: 2 wells, 2 months -> oil 3_000_000, gas 11_000
            _row(202301, 1_000_000.0, 5_000.0, 200.0, "API_A", "MC807"),
            _row(202302, 2_000_000.0, 6_000.0, 250.0, "API_B", "MC807"),
            # GC640, year 2023: 1 well
            _row(202303, 500_000.0, 1_000.0, 50.0, "API_C", "GC640"),
        ],
    )
    _write_corrupted_bin(
        data_dir / "ogora2024delimit.bin",
        [
            # MC807, year 2024: same 2 wells again -> distinct well count = 2
            _row(202401, 4_000_000.0, 7_000.0, 300.0, "API_A", "MC807"),
            _row(202402, 1_000_000.0, 3_000.0, 100.0, "API_B", "MC807"),
        ],
    )


@unit
def test_build_field_timeline_filters_and_aggregates(tmp_path):
    _make_two_field_years(tmp_path)

    tl = build_field_timeline(
        "MC807", data_dir=tmp_path, start_year=2023, end_year=2024
    )

    assert list(tl.columns) == ["YEAR", "OIL_MMBBL", "GAS_BCF", "WATER_MMBBL", "WELLS"]
    assert tl["YEAR"].tolist() == [2023, 2024]  # sorted by year

    y2023 = tl[tl["YEAR"] == 2023].iloc[0]
    assert y2023["OIL_MMBBL"] == pytest.approx(3.0)  # 3_000_000 / 1e6
    assert y2023["GAS_BCF"] == pytest.approx(0.011)  # 11_000 / 1e6
    assert y2023["WATER_MMBBL"] == pytest.approx(0.00045)
    assert int(y2023["WELLS"]) == 2  # API_A, API_B

    y2024 = tl[tl["YEAR"] == 2024].iloc[0]
    assert y2024["OIL_MMBBL"] == pytest.approx(5.0)
    assert int(y2024["WELLS"]) == 2


@unit
def test_build_field_timeline_unknown_field_is_empty(tmp_path):
    _make_two_field_years(tmp_path)
    tl = build_field_timeline("NOPE", data_dir=tmp_path, start_year=2023, end_year=2024)
    assert tl.empty
    assert list(tl.columns) == ["YEAR", "OIL_MMBBL", "GAS_BCF", "WATER_MMBBL", "WELLS"]


@unit
def test_build_field_timeline_strips_whitespace(tmp_path):
    _write_corrupted_bin(
        tmp_path / "ogora2024delimit.bin",
        [_row(202401, 1_000_000.0, 0.0, 0.0, "API_A", " MC807 ")],
    )
    tl = build_field_timeline(
        "MC807", data_dir=tmp_path, start_year=2024, end_year=2024
    )
    assert len(tl) == 1
    assert tl.iloc[0]["OIL_MMBBL"] == pytest.approx(1.0)


def _timeline():
    return pd.DataFrame(
        {
            "YEAR": [2004, 2005],
            "OIL_MMBBL": [10.0, 25.0],
            "GAS_BCF": [1.0, 2.0],
            "WATER_MMBBL": [0.5, 1.5],
            "WELLS": [3, 5],
        }
    )


def _field_row_full():
    return {
        "FIELD_CODE": "MC807",
        "FIELD_NAME": "Mars-Ursa",
        "WELL_COUNT": 230,
        "CUM_OIL_MMBBL": 1855.06,
        "CUM_GAS_BCF": 2349.44,
        "PEAK_OIL_BOPD": 272638.0,
        "REC_PER_WELL_MMBBL": 8.07,
        "WATER_DEPTH_AVG": 3000.0,
        "GEOLOGICAL_ERA": "Miocene",
        "N_OPERATORS": 2,
        "DOMINANT_OPERATOR": "OperatorCo",
        "GROSS_OIL_REVENUE_MM_USD": 120000.0,
        "DECOM_P50_MM_USD": 800.0,
        "DECOM_P90_MM_USD": 1200.0,
    }


@unit
def test_render_contains_name_metrics_chart_footnote():
    html = render_field_deepdive(_field_row_full(), _timeline())

    assert "Mars-Ursa" in html  # title / field name
    # metric labels present
    assert "Cumulative Oil" in html
    assert "Water Depth" in html
    assert "Dominant Operator" in html
    # economics metric present
    assert "Decommissioning" in html or "Decom" in html
    # timeline chart title
    assert "Production Timeline" in html
    # footnote with data vintage
    assert "OGOR-A" in html
    assert "1996" in html and "2025" in html


@unit
def test_render_omits_absent_economics_columns():
    row = {
        "FIELD_CODE": "GC640",
        "FIELD_NAME": "SomeField",
        "WELL_COUNT": 5,
        "CUM_OIL_MMBBL": 11.0,
    }
    html = render_field_deepdive(row, _timeline())

    assert "SomeField" in html
    assert "Cumulative Oil" in html
    # economics columns absent -> their labels must NOT appear
    assert "Decommissioning" not in html
    assert "Gross Oil Revenue" not in html
    assert "Netback" not in html


@unit
def test_render_includes_netback_when_present():
    row = dict(_field_row_full())
    row["NETBACK_BASE_MM_USD"] = 45000.0
    row["BREAKEVEN_OPEX_USD_BBL"] = 22.5
    html = render_field_deepdive(row, _timeline())
    assert "Netback" in html
    assert "Breakeven" in html


@unit
def test_render_empty_timeline_does_not_crash():
    empty = pd.DataFrame(
        columns=["YEAR", "OIL_MMBBL", "GAS_BCF", "WATER_MMBBL", "WELLS"]
    )
    html = render_field_deepdive(_field_row_full(), empty)
    assert "Mars-Ursa" in html
    assert "no production timeline" in html.lower()
    # metrics still rendered
    assert "Cumulative Oil" in html


@unit
def test_render_skips_nan_metric_values():
    row = dict(_field_row_full())
    row["WATER_DEPTH_AVG"] = float("nan")
    html = render_field_deepdive(row, _timeline())
    # NaN known column should not render a fake number; label omitted.
    assert "Water Depth" not in html
