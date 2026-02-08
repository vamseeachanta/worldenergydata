"""
ABOUTME: Tests for well-test vs commercial production classification
ABOUTME: Covers OGOR code-based rules, first_oil boundary, and priority ordering
"""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.lower_tertiary.production_classifier import (
    ProductionClass,
    classify_production,
    summarize_classification,
)

# ---------------------------------------------------------------------------
# Unit tests with synthetic DataFrames
# ---------------------------------------------------------------------------


def _make_df(rows: list[dict]) -> pd.DataFrame:
    """Build a test DataFrame with required columns and sensible defaults."""
    defaults = {
        "development": "TestDev",
        "date": pd.Timestamp("2020-01-01"),
        "oil_bbl": 100.0,
        "PRODUCT_CODE": "O",
        "WELL_STAT_CD": "4",
    }
    records = [{**defaults, **r} for r in rows]
    return pd.DataFrame(records)


def test_product_code_t_is_well_test():
    df = _make_df([{"PRODUCT_CODE": "T", "oil_bbl": 500}])
    result = classify_production(df)
    assert result["production_class"].iloc[0] == ProductionClass.WELL_TEST


def test_well_stat_cd_1_with_oil_is_well_test():
    df = _make_df([{"WELL_STAT_CD": "1", "oil_bbl": 200}])
    result = classify_production(df)
    assert result["production_class"].iloc[0] == ProductionClass.WELL_TEST


def test_well_stat_cd_1_no_oil_is_non_producing():
    df = _make_df([{"WELL_STAT_CD": "1", "oil_bbl": 0}])
    result = classify_production(df)
    assert result["production_class"].iloc[0] == ProductionClass.NON_PRODUCING


def test_pre_first_oil_is_well_test():
    first_oil_map = {"TestDev": pd.Timestamp("2020-06-01")}
    df = _make_df([{"date": pd.Timestamp("2020-03-01"), "oil_bbl": 50}])
    result = classify_production(df, first_oil_map=first_oil_map)
    assert result["production_class"].iloc[0] == ProductionClass.WELL_TEST


def test_post_first_oil_is_commercial():
    first_oil_map = {"TestDev": pd.Timestamp("2020-06-01")}
    df = _make_df([{"date": pd.Timestamp("2020-07-01"), "oil_bbl": 1000}])
    result = classify_production(df, first_oil_map=first_oil_map)
    assert result["production_class"].iloc[0] == ProductionClass.COMMERCIAL


def test_classification_priority_t_overrides_date():
    """PRODUCT_CODE='T' should be well_test even if date is after first_oil."""
    first_oil_map = {"TestDev": pd.Timestamp("2020-01-01")}
    df = _make_df(
        [
            {"date": pd.Timestamp("2020-06-01"), "PRODUCT_CODE": "T", "oil_bbl": 300},
        ]
    )
    result = classify_production(df, first_oil_map=first_oil_map)
    assert result["production_class"].iloc[0] == ProductionClass.WELL_TEST


def test_no_first_oil_map_code_only():
    """Without first_oil_map, only code-based rules (PRODUCT_CODE, WELL_STAT_CD) apply."""
    df = _make_df(
        [
            {"PRODUCT_CODE": "T", "oil_bbl": 100},
            {"PRODUCT_CODE": "O", "WELL_STAT_CD": "4", "oil_bbl": 200},
            {"PRODUCT_CODE": "O", "WELL_STAT_CD": "4", "oil_bbl": 0},
        ]
    )
    result = classify_production(df)
    classes = result["production_class"].tolist()
    assert classes[0] == ProductionClass.WELL_TEST
    assert classes[1] == ProductionClass.COMMERCIAL
    assert classes[2] == ProductionClass.NON_PRODUCING


def test_parse_strips_whitespace():
    """Raw quoted/whitespace values in PRODUCT_CODE should be cleaned before classifying."""
    df = _make_df([{"PRODUCT_CODE": ' "T" ', "oil_bbl": 100}])
    result = classify_production(df)
    assert result["production_class"].iloc[0] == ProductionClass.WELL_TEST


def test_summarize_classification():
    first_oil_map = {"DevA": pd.Timestamp("2020-06-01")}
    df = _make_df(
        [
            {"development": "DevA", "date": pd.Timestamp("2020-03-01"), "oil_bbl": 100},
            {"development": "DevA", "date": pd.Timestamp("2020-07-01"), "oil_bbl": 500},
            {"development": "DevA", "date": pd.Timestamp("2020-08-01"), "oil_bbl": 0},
        ]
    )
    classified = classify_production(df, first_oil_map=first_oil_map)
    summary = summarize_classification(classified)
    assert "DevA" in summary
    assert summary["DevA"]["commercial_oil_bbl"] == 500
    assert summary["DevA"]["well_test_oil_bbl"] == 100
    assert summary["DevA"]["commercial_count"] == 1
    assert summary["DevA"]["well_test_count"] == 1
    assert summary["DevA"]["non_producing_count"] == 1


# ---------------------------------------------------------------------------
# Integration tests with real OGOR data
# ---------------------------------------------------------------------------

try:
    from worldenergydata.lower_tertiary.v30_reproducer import (
        aggregate_production_by_development,
        load_ogor_production,
        load_v30_leases,
    )

    OGOR_AVAILABLE = True
except ImportError:
    OGOR_AVAILABLE = False

skip_no_ogor = pytest.mark.skipif(
    not OGOR_AVAILABLE, reason="OGOR data or v30_reproducer not available"
)


@skip_no_ogor
def test_jack_st_malo_well_test_records_found():
    """Jack St Malo should have well-test records (PRODUCT_CODE='T' or WELL_STAT_CD='1')."""
    leases_df = load_v30_leases()
    ogor_df = load_ogor_production(start_year=2000, end_year=2025)

    # Filter for JSM leases
    jsm_leases = set(leases_df[leases_df["DEV_NAME"] == "Jack St Malo"]["LEASE_NUM"])
    jsm_ogor = ogor_df[ogor_df["LEASE_NUMBER"].isin(jsm_leases)].copy()

    # Clean PRODUCT_CODE and WELL_STAT_CD
    for col in ("PRODUCT_CODE", "WELL_STAT_CD"):
        jsm_ogor[col] = (
            jsm_ogor[col]
            .astype(str)
            .str.strip()
            .str.replace('"', "", regex=False)
            .str.upper()
        )

    # Check for PRODUCT_CODE='T'
    t_records = jsm_ogor[jsm_ogor["PRODUCT_CODE"] == "T"]
    # Check for WELL_STAT_CD='1' (Exploratory)
    exploratory_records = jsm_ogor[jsm_ogor["WELL_STAT_CD"] == "1"]

    well_test_count = len(t_records) + len(
        exploratory_records[~exploratory_records.index.isin(t_records.index)]
    )
    assert (
        well_test_count >= 2
    ), f"Expected at least 2 well-test records for JSM, got {well_test_count}"


@skip_no_ogor
def test_cascade_chinook_corrected_first_oil_gains_production():
    """Corrected first_oil=2012-09-01 should add ~3.26M bbl vs golden baseline 2014-01-01."""
    leases_df = load_v30_leases()
    ogor_df = load_ogor_production(start_year=2000, end_year=2025)
    ogor_df = ogor_df[
        (ogor_df["date"] >= "2000-09-01") & (ogor_df["date"] <= "2025-05-31")
    ]

    dev_production = aggregate_production_by_development(ogor_df, leases_df)
    cc_monthly = dev_production.get("Cascade Chinook")
    assert cc_monthly is not None, "Cascade Chinook not found in development production"

    cc_monthly = cc_monthly[cc_monthly["oil_bbl"] > 0]

    # Production with golden baseline first_oil (2014-01-01)
    golden_oil = cc_monthly[cc_monthly["date"] >= "2014-01-01"]["oil_bbl"].sum()

    # Production with corrected first_oil (2012-09-01)
    corrected_oil = cc_monthly[cc_monthly["date"] >= "2012-09-01"]["oil_bbl"].sum()

    gained = corrected_oil - golden_oil
    assert (
        gained > 2_000_000
    ), f"Expected >2M bbl gain from first_oil correction, got {gained:,.0f}"
    assert (
        gained < 5_000_000
    ), f"Gain seems too large ({gained:,.0f}), expected ~3.26M bbl"
