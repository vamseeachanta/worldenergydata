"""Invented monthly energy records in the EIA API v2 value/units layout.

EIA API Technical Documentation, January 2024 v2.1.6 patch notes, specifies
string-valued observations: https://www.eia.gov/opendata/documentation.php
All amounts here are synthetic monthly energy, not power or stock snapshots.
"""

import sys

import pytest

from worldenergydata.eia.client import EIAFeedClient
from worldenergydata.eia.monthly_energy import total_monthly_energy_mwh


def _row(period="2024-01", value="125.5", units="MWh", series="synthetic"):
    return {"period": period, "value": value, "units": units, "series": series}


def test_two_month_energy_total_after_response_parsing():
    # Hand sum in the declared unit: 125.5 MWh + 74.25 MWh = 199.75 MWh.
    rows = [_row(), _row("2024-02", "74.25")]
    client = EIAFeedClient(api_key="synthetic-test-only")
    parsed = client.parse_response({"response": {"data": rows}})
    assert total_monthly_energy_mwh(parsed) == 199.75
    assert rows[0]["value"] == "125.5"
    assert total_monthly_energy_mwh(iter(reversed(parsed))) == 199.75


def test_numeric_observation_and_reported_zero():
    assert total_monthly_energy_mwh([_row(value=0)]) == 0
    assert total_monthly_energy_mwh([_row(value=0.125)]) == 0.125


def test_empty_is_not_reported_zero():
    with pytest.raises(ValueError, match="no monthly"):
        total_monthly_energy_mwh([])


@pytest.mark.parametrize("units", ["GWh", "MW", None, ""])
def test_unit_mismatch_fails_before_summing(units):
    with pytest.raises(ValueError, match="MWh"):
        total_monthly_energy_mwh([_row(), _row("2024-02", units=units)])


@pytest.mark.parametrize(
    "value", [None, True, "", "unavailable", -1, "NaN", "Infinity", float("inf")]
)
def test_invalid_or_missing_observation_fails(value):
    with pytest.raises((TypeError, ValueError), match="value"):
        total_monthly_energy_mwh([_row(value=value)])


@pytest.mark.parametrize("period", ["0000-01", "2024-00", "2024-13", "2024-1", None])
def test_invalid_month_fails(period):
    with pytest.raises(ValueError, match="period"):
        total_monthly_energy_mwh([_row(period=period)])


def test_duplicate_month_fails():
    with pytest.raises(ValueError, match="duplicate"):
        total_monthly_energy_mwh([_row(), _row()])


@pytest.mark.parametrize("series", [None, "", "other"])
def test_missing_or_different_series_fails(series):
    with pytest.raises(ValueError, match="series"):
        total_monthly_energy_mwh([_row(), _row("2024-02", series=series)])


def test_total_overflow_fails():
    with pytest.raises(ValueError, match="finite"):
        total_monthly_energy_mwh(
            [_row(value=sys.float_info.max), _row("2024-02", sys.float_info.max)]
        )
