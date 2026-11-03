"""Synthetic contract examples for monthly state volumes.

Independent dimensional arithmetic: one Thousand Barrels = 1000 bbl by
definition, so 2 * 1000 = 2000 bbl, 3 * 1000 = 3000 bbl, and
2000 + 3000 = 5000 bbl. Zero times 1000 remains zero.
All year/month labels below are synthetic Gregorian calendar examples;
YYYY-MM has four year digits and two month digits, January through December.
"""

from copy import deepcopy

import pandas as pd
import pytest

from worldenergydata.eia_us.client.eia_api import EIAApiClient
from worldenergydata.eia_us.production.state_production import StateProductionLoader


def monthly_record(period="2024-01", value=2):
    return {"period": period, "value": value, "unit": "Thousand Barrels"}


def test_declared_volume_unit_conversion():
    loader = StateProductionLoader()
    records = [monthly_record(value=2), monthly_record("2024-02", value=3)]
    original = deepcopy(records)

    monthly = loader.load(records, state=" tx ")
    annual = loader.annual_total(monthly)

    # Hand calculation in the module docstring, independent of the loader.
    assert monthly["crude_bbl"].tolist() == [2000.0, 3000.0]
    assert annual.to_dict("records") == [
        {"state": "TX", "year": 2024, "crude_bbl": 5000.0}
    ]
    assert records == original


@pytest.mark.parametrize(
    "series_id,state,expected_bbl",
    [
        ("PET.MCRFPTX1.M", "TX", [5200000.0, 5150000.0]),
        ("PET.MCRFPAK1.M", "AK", [450000.0, 440000.0]),
        ("PET.MCRFPUS1.M", "US", [12500000.0, 12300000.0, 12450000.0]),
    ],
)
def test_monthly_volume_series_has_loadable_mock(series_id, state, expected_bbl):
    """Synthetic mock volumes are in thousand barrels, not daily rates."""
    client = EIAApiClient(api_key="TEST_KEY")
    records = client.fetch_series(series_id, use_mock=True)

    assert records
    assert all(record["unit"] == "Thousand Barrels" for record in records)
    monthly = StateProductionLoader().load(records, state=state)
    assert monthly["crude_bbl"].tolist() == expected_bbl


def test_published_row_unit_survives_client_to_loader():
    """The published API browser reads row.unit; units names metadata.

    EIA API Technical Documentation and its linked API Query Browser,
    accessed 2026-10-29: https://www.eia.gov/opendata/documentation.php
    https://www.eia.gov/opendata/browser/
    These rows are synthetic, not an authenticated API payload.
    """
    raw = {
        "response": {
            "data": [monthly_record("2024-02", "2"), monthly_record("2024-03", "3")]
        }
    }
    original = deepcopy(raw)
    records = EIAApiClient(api_key="TEST_KEY").parse_series_response(raw)
    loader = StateProductionLoader()
    monthly = loader.load(records, state="TX")

    assert [record["unit"] for record in records] == ["Thousand Barrels"] * 2
    # 2 * 1000 = 2000 and 3 * 1000 = 3000 bbl; neither needs day weighting.
    assert monthly["crude_bbl"].tolist() == [2000.0, 3000.0]
    assert loader.annual_total(monthly)["crude_bbl"].tolist() == [5000.0]
    assert raw == original


@pytest.mark.parametrize(
    "unit_fields",
    [
        {},
        {"unit": None},
        {"unit": ""},
        {"unit": "Barrels"},
        {"unit": "Thousand Cubic Feet"},
        {"unit": "Thousand Barrels per Day"},
        {"unit": "Barrels per Day"},
        {"unit": "MBBLS"},
        {"unit": "thousand barrels"},
        {"unit": 1000},
    ],
)
def test_missing_or_rate_unit_is_rejected(unit_fields):
    loader = StateProductionLoader()
    invalid = {"period": "2024-02", "value": 3, **unit_fields}
    records = [monthly_record(), invalid, monthly_record("2024-03", value=3)]
    original = deepcopy(records)

    with pytest.raises(ValueError, match="unit") as error:
        loader.load(records, state="TX")

    assert repr(unit_fields.get("unit")) in str(error.value)
    assert records == original
    neighbors = loader.load([records[0], records[-1]], state="TX")
    assert neighbors["crude_bbl"].tolist() == [2000.0, 3000.0]


def test_missing_quantity_still_requires_declared_unit():
    with pytest.raises(ValueError, match="unit"):
        StateProductionLoader().load([{"period": "2024-01", "value": None}], state="TX")


@pytest.mark.parametrize(
    "period_fields",
    [
        {},
        {"period": None},
        {"period": 202401},
        {"period": ""},
        {"period": "2024"},
        {"period": "2024-"},
        {"period": "2024-1"},
        {"period": "2024/01"},
        {"period": "2024-00"},
        {"period": "2024-13"},
        {"period": "0000-01"},
        {"period": "-024-01"},
        {"period": "2024-011"},
        {"period": "2024-01-01"},
        {"period": "2024-01suffix"},
        {"period": " 2024-01"},
        {"period": "2024-01\n"},
        {"period": "２０２４-０１"},
    ],
)
def test_invalid_month_is_rejected(period_fields):
    loader = StateProductionLoader()
    invalid = {"value": 3, "unit": "Thousand Barrels", **period_fields}
    records = [monthly_record(), invalid, monthly_record("2024-03", value=3)]
    original = deepcopy(records)

    with pytest.raises(ValueError, match="period") as error:
        loader.load(records, state="TX")

    assert repr(period_fields.get("period")) in str(error.value)
    assert records == original
    neighbors = loader.load([records[0], records[-1]], state="TX")
    assert neighbors["month"].tolist() == [1, 3]
    assert neighbors["crude_bbl"].tolist() == [2000.0, 3000.0]


@pytest.mark.parametrize("period", ["0001-01", "2024-02", "2024-12", "9999-12"])
def test_complete_calendar_month_is_preserved(period):
    monthly = StateProductionLoader().load([monthly_record(period)], state="TX")

    assert monthly["year"].tolist() == [int(period[:4])]
    assert monthly["month"].tolist() == [int(period[5:])]
    assert monthly["crude_bbl"].tolist() == [2000.0]


@pytest.mark.parametrize(
    "quantity_fields", [{}, {"value": None}, {"value": float("nan")}]
)
def test_unknown_is_not_zero(quantity_fields):
    loader = StateProductionLoader()
    records = [
        monthly_record("2023-12", value=0),
        {"period": "2024-01", "unit": "Thousand Barrels", **quantity_fields},
        monthly_record("2024-02", value=None),
    ]
    monthly = loader.load(records, state="TX")
    annual = loader.annual_total(monthly).set_index("year")

    assert monthly["crude_bbl"].iloc[0] == 0.0
    assert monthly["crude_bbl"].iloc[1:].isna().all()
    assert annual.loc[2023, "crude_bbl"] == 0.0
    assert pd.isna(annual.loc[2024, "crude_bbl"])


@pytest.mark.parametrize("values", [[2, None], [None, 3], [0, None]])
def test_incomplete_annual_group_is_explicit(values):
    loader = StateProductionLoader()
    incomplete = loader.load(
        [monthly_record("2024-01", values[0]), monthly_record("2024-02", values[1])],
        state="TX",
    )
    known = loader.load(
        [monthly_record(value=2), monthly_record("2024-02", value=3)], state="ND"
    )
    monthly = pd.concat([incomplete, known], ignore_index=True)
    original = monthly.copy(deep=True)

    annual = loader.annual_total(monthly).set_index("state")

    assert pd.isna(annual.loc["TX", "crude_bbl"])
    assert annual.loc["ND", "crude_bbl"] == 5000.0
    pd.testing.assert_frame_equal(monthly, original)


def test_absent_months_do_not_imply_calendar_coverage():
    """Totals cover supplied rows; a missing month is not a missing-valued row."""
    loader = StateProductionLoader()
    monthly = loader.load(
        [monthly_record(value=2), monthly_record("2024-03", value=3)], state="TX"
    )

    assert loader.annual_total(monthly)["crude_bbl"].tolist() == [5000.0]
