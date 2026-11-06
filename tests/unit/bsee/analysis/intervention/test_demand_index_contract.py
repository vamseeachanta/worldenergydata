# ABOUTME: Synthetic demand aggregation contracts for repeated and unique row labels.
# ABOUTME: Hand-calculated durations and rates preserve start-year and FLOOR policies.

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.intervention_demand import (
    demand_by_band,
    rig_days_by_band_year,
)

_BAND = "band_500_3000"


def _records() -> pd.DataFrame:
    """Independent synthetic example; depth is inside the existing demand band."""
    return pd.DataFrame(
        {
            # Synthetic depth of 1500 ft lies between the declared band edges.
            "WATER_DEPTH": [1500.0, 1500.0],
            "API_WELL_NUMBER": ["synthetic-a", "synthetic-b"],
            # Dec 30 through Jan 1 = 3 inclusive days, assigned to start year.
            "WAR_START_DT": ["2020-12-30", "2020-06-01"],
            # June 1 through June 2 = 2 inclusive days in that same start year.
            "WAR_END_DT": ["2021-01-01", "2020-06-02"],
        }
    )


def _index_variants(frame: pd.DataFrame):
    # Labels are arbitrary metadata; distinct records may share the same label.
    for labels in (["second", "first"], ["shared", "shared"]):
        indexed = frame.set_axis(labels)
        yield indexed
        yield indexed.iloc[::-1]
    yield frame.reset_index(drop=True)
    yield frame.iloc[::-1].reset_index(drop=True)


def _aggregate_without_mutation(frame: pd.DataFrame):
    before = frame.copy(deep=True)
    by_year = rig_days_by_band_year(frame)
    pd.testing.assert_frame_equal(frame, before)
    demand = demand_by_band(frame)
    pd.testing.assert_frame_equal(frame, before)
    return by_year, demand


def test_duplicate_index_preserves_rig_day_totals():
    frame = _records()
    reference = _aggregate_without_mutation(frame.reset_index(drop=True))
    by_year, demand = reference
    # Hand calculation: 3 + 2 = 5 inclusive days, all allocated to 2020.
    assert by_year[_BAND] == {2020: 5}
    band = demand[_BAND]
    assert band["intervention_rig_days_by_year"] == {2020: 5}
    assert band["total_rig_days_floor"] == 5
    # Two records for two different wells: 2 / 2 = 1 intervention per well.
    assert band["interventions"] == 2
    assert band["distinct_wells"] == 2
    assert band["interventions_per_well"] == 1.0
    assert band["is_floor"] is True

    for variant in _index_variants(frame):
        assert _aggregate_without_mutation(variant) == reference


@pytest.mark.parametrize(
    "date_case",
    [
        "missing-start",
        "invalid-start",
        "missing-end",
        "invalid-end",
        "no-start-column",
        "no-end-column",
    ],
)
def test_missing_dates_preserve_index_contract(date_case):
    frame = _records()
    if date_case == "missing-start":
        frame.loc[0, "WAR_START_DT"] = None
    elif date_case == "invalid-start":
        frame.loc[0, "WAR_START_DT"] = "not-a-date"
    elif date_case == "missing-end":
        frame.loc[0, "WAR_END_DT"] = None
    elif date_case == "invalid-end":
        frame.loc[0, "WAR_END_DT"] = "not-a-date"
    elif date_case == "no-start-column":
        frame = frame.drop(columns="WAR_START_DT")
    else:
        frame = frame.drop(columns="WAR_END_DT")

    reference = _aggregate_without_mutation(frame.reset_index(drop=True))
    by_year, demand = reference
    if date_case in ("missing-start", "invalid-start"):
        # No usable first start: only the second record's 2 days are allocated.
        expected_years = {2020: 2}
    elif date_case == "no-start-column":
        # No start years: neither record contributes days (zero in total).
        expected_years = {}
    elif date_case == "no-end-column":
        # Both ends absent: 1 floor day per record, 1 + 1 = 2 days.
        expected_years = {2020: 2}
    else:
        # First end unusable: 1 floor day + 2 inclusive days = 3 days.
        expected_years = {2020: 3}
    assert by_year[_BAND] == expected_years
    band = demand[_BAND]
    assert band["intervention_rig_days_by_year"] == expected_years
    assert band["total_rig_days_floor"] == sum(expected_years.values())
    # Dates do not alter the two records or two wells: 2 / 2 = 1 per well.
    assert band["interventions"] == 2
    assert band["distinct_wells"] == 2
    assert band["interventions_per_well"] == 1.0
    assert band["is_floor"] is True

    for variant in _index_variants(frame):
        assert _aggregate_without_mutation(variant) == reference
