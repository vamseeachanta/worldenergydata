"""Tests for the Lower-Tertiary well-benchmarking analytic (worldenergydata#499).

These run on REAL BSEE data (the OGOR-A ``.bin`` DataFrames + WAR bins + V30
drilling tables). When that data is not present in a checkout they skip rather
than fail, matching the existing ``test_well_npv_stackup`` convention.

Coverage:
  * determinism — the same config produces a bit-identical table twice;
  * structure — one row per well, sorted by cumulative oil descending;
  * uptime — DAYS_ON_PROD-based fraction stays in [0, 1] and flags missing data;
  * flag-don't-fake — derivable metrics are numeric; non-derivable are None,
    never invented.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.uptime import compute_uptime
from worldenergydata.lower_tertiary.well_benchmark import (
    BenchmarkConfig,
    run_well_benchmark,
    select_play_wells,
)


def _ensure_ogor_or_skip() -> None:
    """Patch the .bin OGOR loader (as the report generator does) or skip."""
    from worldenergydata.lower_tertiary import ops_timeline

    try:
        ops_timeline.ensure_ogor_loader()
        ops_timeline.v30_reproducer.load_ogor_production(start_year=2016, end_year=2016)
    except FileNotFoundError:
        pytest.skip(
            "BSEE OGOR-A data not present (set WED_DATA_ROOT / run `make data`)"
        )


# A small, fast subset: one single-lease producing field with a fixed window so
# the run is deterministic and quick.
_SUBSET = BenchmarkConfig(
    play="lower_tertiary",
    spud_year_min=2000,
    spud_year_max=None,
    fields=["Julia"],
    end_date="2025-05-31",  # frozen window -> stable across data refreshes
)


class TestComputeUptime:
    def test_bounds_and_missing_flag(self):
        # Two wells: one full month with days, one month missing DAYS_ON_PROD.
        df = pd.DataFrame(
            {
                "API_WELL_NUMBER": ["111111111100", "111111111100", "222222222200"],
                "date": pd.to_datetime(["2020-01-01", "2020-02-01", "2020-01-01"]),
                "MON_O_PROD_VOL": [1000.0, 800.0, 500.0],
                "DAYS_ON_PROD": [31, None, 20],
            }
        )
        out = compute_uptime(df)
        assert set(out["API_WELL_NUMBER"]) == {"111111111100", "222222222200"}
        for _, r in out.iterrows():
            # uptime is a fraction; a partial month can exceed neither 1 nor < 0.
            assert 0.0 <= r["uptime"] <= 1.0
        # Well 1 has one of two months missing DAYS_ON_PROD -> flagged.
        w1 = out[out["API_WELL_NUMBER"] == "111111111100"].iloc[0]
        assert w1["missing_days_months"] == 1
        assert bool(w1["low_confidence"]) is True

    def test_empty_input(self):
        out = compute_uptime(pd.DataFrame())
        assert out.empty


class TestWellBenchmarkRealData:
    def test_runs_and_has_rows(self):
        _ensure_ogor_or_skip()
        df = run_well_benchmark(_SUBSET)
        assert not df.empty, "expected producing Julia wells"
        # One row per well; unique wellbores.
        assert df["well"].is_unique

    def test_sorted_by_cum_oil_desc(self):
        _ensure_ogor_or_skip()
        df = run_well_benchmark(_SUBSET)
        cums = list(df["cum_oil_mmbbl"])
        assert cums == sorted(cums, reverse=True)
        assert all(c >= 0 for c in cums)

    def test_determinism_same_input_same_output(self):
        _ensure_ogor_or_skip()
        a = run_well_benchmark(_SUBSET)
        b = run_well_benchmark(_SUBSET)
        # Bit-identical table on a repeated run (same config + same data).
        pd.testing.assert_frame_equal(a, b)

    def test_uptime_within_bounds(self):
        _ensure_ogor_or_skip()
        df = run_well_benchmark(_SUBSET)
        ups = df["uptime_pct"].dropna()
        assert ((ups >= 0) & (ups <= 100.0001)).all()

    def test_flag_dont_fake(self):
        _ensure_ogor_or_skip()
        df = run_well_benchmark(_SUBSET)
        # Where a numeric metric is present it must be numeric; where absent it
        # is None (not a fabricated 0 masquerading as a real value).
        for _, r in df.iterrows():
            flag = r["decline_flag"] or ""
            if flag == "insufficient_history" or flag.startswith("fit_failed"):
                assert r["decline_annual_pct"] is None or pd.isna(
                    r["decline_annual_pct"]
                )
            # cumulative oil is always real (the well is producing).
            assert r["cum_oil_mmbbl"] is not None and r["cum_oil_mmbbl"] >= 0

    def test_select_play_wells_field_filter(self):
        _ensure_ogor_or_skip()
        wells = select_play_wells(
            "lower_tertiary", fields=["Julia"], end_date="2025-05-31"
        )
        assert not wells.empty
        assert set(wells["field"].unique()) == {"Julia"}
