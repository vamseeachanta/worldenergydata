"""Acceptance-policy regressions using synthetic records only."""

from datetime import datetime
from types import SimpleNamespace

import pandas as pd
import pytest

from worldenergydata.bsee.pipeline_screening import estimate_wall


def test_low_pressure_is_not_evidenced_wall():
    row = estimate_wall("01", 1, {"smys_pa": {"value": 358530000}})
    assert row["wall_thickness_m"] is None
    assert row["wall_thickness_m_source"] == "UNKNOWN:no_evidenced_wall"
    assert row["hoop_yield_wall_at_assumed_smys_m"] > 0
    assert estimate_wall("01", 0, {})["maop_pa"] is None


def complete_records(years, *, latitude=27, longitude=-90):
    records = []
    for year in years:
        times = pd.date_range(
            f"{year}-01-01", f"{year+1}-01-01", freq="h", inclusive="left"
        )
        records.extend(
            SimpleNamespace(
                observation_time=t.to_pydatetime(),
                wave_height_m=1 + (year % 7) / 10 + i / len(times),
                dominant_wave_period_s=7.0,
                latitude=latitude,
                longitude=longitude,
            )
            for i, t in enumerate(times)
        )
    return records


def test_four_complete_years_stay_unknown():
    from worldenergydata.bsee.pipeline_screening import _station_record_summary

    row = _station_record_summary(complete_records(range(2022, 2026)))
    assert row["complete_annual_maxima"] == 4
    assert row["hs_10yr_m"] is row["hs_100yr_m"] is None
    assert row["hs_10yr_m_source"] == "UNKNOWN:short_record"
    assert "tp_100yr_s" not in row
    assert row["tp_at_hs_max_s"] == 7


def test_ten_years_qualify_only_hs10():
    from worldenergydata.bsee.pipeline_screening import _station_record_summary

    row = _station_record_summary(complete_records(range(2000, 2010)))
    assert row["complete_annual_maxima"] == 10
    assert row["hs_10yr_m"] > 0
    assert row["hs_10yr_lower_ci_m"] <= row["hs_10yr_m"] <= row["hs_10yr_upper_ci_m"]
    assert row["hs_10yr_distribution"] == "GEV"
    assert row["hs_100yr_m"] is None


def test_incomplete_year_and_hurricane_hours_are_not_counted():
    from worldenergydata.bsee.pipeline_screening import _station_record_summary

    observations = complete_records([2022])
    assert _station_record_summary(observations[:7000])["complete_annual_maxima"] == 0
    # More than 80% annually, but less than 80% of hurricane-season hours.
    observations = [
        r
        for r in observations
        if r.observation_time.month != 7 and r.observation_time.month != 8
    ]
    assert _station_record_summary(observations)["complete_annual_maxima"] == 0
    assert (
        _station_record_summary(observations, atlantic=False)["complete_annual_maxima"]
        == 1
    )


def test_eva_requests_95_percent_interval(monkeypatch):
    from worldenergydata.metocean.statistics.eva import ExtremeValueAnalysis, ms

    seen = []

    def uncertainty(**kwargs):
        seen.append(kwargs.get("uncertainty"))
        return pd.DataFrame(
            {
                "return_levels": [3],
                "prob_non_exceedance": [0.9],
                "ci_lower_rl": [2],
                "ci_upper_rl": [4],
            },
            index=[10],
        )

    monkeypatch.setattr(ms, "return_levels_annual_max_uncertainty", uncertainty)
    series = pd.Series(
        [1, 2, 3], index=pd.to_datetime(["2000-01-01", "2001-01-01", "2002-01-01"])
    )
    result = ExtremeValueAnalysis().fit_annual_maxima(
        series, periods=[10], confidence_level=0.95
    )
    assert seen == [0.95]
    assert result.lower_ci == {10: 2}
    assert result.upper_ci == {10: 4}
