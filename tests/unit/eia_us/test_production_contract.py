"""Synthetic production contracts with independently worked arithmetic.

Unit factors: NIST SP 811 (2008), section 4, Table 5 (kilo = 1000).
Rate times duration: quantity-equation reasoning, section 7.11 of that guide.
Calendar: Python calendar documentation (2026), monthrange and isleap.
All rates, years and amounts below are selected synthetic inputs, not estimates.
"""

import math

import numpy as np
import pandas as pd
import pytest

from worldenergydata.eia_us.international.country_production import (
    MOCK_COUNTRY_PRODUCTION,
    CountryProductionLoader,
)
from worldenergydata.eia_us.production.alaska_production import AlaskaProductionLoader
from worldenergydata.eia_us.production.basin_production import BasinProductionLoader
from worldenergydata.eia_us.production.drilling_productivity import (
    DrillingProductivityReport,
)
from worldenergydata.eia_us.production.state_production import StateProductionLoader


@pytest.mark.parametrize(
    "unit,value,expected",
    [
        ("Barrels", 100, 100),
        ("Thousand Barrels", 2, 2000),
        ("Barrels per Day", 100, 2900),
        ("Thousand Barrels per Day", 2, 58000),
    ],
)
def test_state_declared_units(unit, value, expected):
    """February 2024: 29 days; 100*29=2900, 2*1000*29=58000 bbl.

    Period volumes stay 100 bbl or 2*1000=2000 bbl; no days factor.
    """
    df = StateProductionLoader().load(
        [{"period": "2024-02", "value": value, "unit": unit}], "TX"
    )
    assert df.loc[0, "crude_bbl"] == expected
    assert df.loc[0, "unit"] == "bbl"
    assert df.loc[0, "basis"] == "volume_per_period"
    assert df.loc[0, "input_unit"] == unit


@pytest.mark.parametrize("unit", [None, "", "Mbbl", "bananas", "Bcf"])
def test_state_unknown_unit_rejected_even_if_value_missing(unit):
    """An unspecified or ambiguous scale cannot define a barrel amount."""
    with pytest.raises(ValueError, match="unit"):
        StateProductionLoader().load(
            [{"period": "2024-01", "value": None, "unit": unit}], "TX"
        )


@pytest.mark.parametrize(
    "period", ["2024-00", "2024-13", "2024-1", "2024-01x", "", None]
)
def test_invalid_month_is_rejected(period):
    """The monthly contract requires YYYY-MM in the Gregorian calendar."""
    with pytest.raises(ValueError, match="period"):
        StateProductionLoader().load(
            [{"period": period, "value": 1, "unit": "Barrels"}], "TX"
        )


def test_inconsistent_basis_rejected():
    """A daily rate cannot declare the volume-per-period basis."""
    with pytest.raises(ValueError, match="basis"):
        StateProductionLoader().load(
            [
                {
                    "period": "2024-01",
                    "value": 1,
                    "unit": "Barrels per Day",
                    "basis": "volume_per_period",
                }
            ],
            "TX",
        )


@pytest.mark.parametrize(
    "loader,record,columns",
    [
        (
            AlaskaProductionLoader(),
            {"period": "2024-01", "field": "synthetic"},
            ["crude_bopd", "ngl_bopd"],
        ),
        (
            BasinProductionLoader(),
            {"period": "2024-01", "basin": "synthetic"},
            [
                "rig_count",
                "new_well_ip_bopd",
                "legacy_decline_bopd",
                "total_production_bopd",
            ],
        ),
        (
            CountryProductionLoader(),
            {"year": 2024, "country": "synthetic"},
            ["production_kbd"],
        ),
    ],
)
def test_missing_is_distinct_from_zero(loader, record, columns):
    """Absent numbers are NaN; explicitly reported zero remains numerical zero."""
    missing = loader.load([record])
    zero = loader.load([{**record, **dict.fromkeys(columns, 0)}])
    for column in columns:
        assert pd.isna(missing.loc[0, column])
        assert missing.loc[0, f"{column}_missing"]
        assert zero.loc[0, column] == 0
        assert not zero.loc[0, f"{column}_missing"]


@pytest.mark.parametrize(
    "loader,record",
    [
        (AlaskaProductionLoader(), {"period": "2024-01", "field": "synthetic"}),
        (BasinProductionLoader(), {"period": "2024-01", "basin": "synthetic"}),
        (CountryProductionLoader(), {"year": 2024, "country": "synthetic"}),
    ],
)
def test_named_rate_schema_rejects_conflicting_units(loader, record):
    """A typed rate field cannot be reinterpreted as period barrels."""
    with pytest.raises(ValueError, match="unit"):
        loader.load([{**record, "unit": "Barrels"}])
    with pytest.raises(ValueError, match="basis"):
        loader.load([{**record, "basis": "volume_per_period"}])


@pytest.mark.parametrize(
    "year,expected", [(2023, 36500), (2024, 36600), (2100, 36500), (2000, 36600)]
)
def test_annual_daily_rates(year, expected):
    """Hand sum: seven*31 + four*30 + February = 337+28/29=365/366.

    100 bbl/day * 365/366 = 36500/36600 bbl. Gregorian century rules
    make 2100 common and 2000 leap (calendar.isleap documentation).
    """
    loader = StateProductionLoader()
    raw = [
        {"period": f"{year}-{month:02d}", "value": 100, "unit": "Barrels per Day"}
        for month in range(1, 13)
    ]
    annual = loader.annual_total(loader.load(raw, "TX"))
    assert annual.loc[0, "crude_bbl"] == expected
    assert annual.loc[0, "reported_crude_bbl"] == expected
    assert annual.loc[0, "crude_missing_months"] == ()
    assert annual.loc[0, "status"] == "COMPLETE"


def test_mixed_units_missing_month_worked_example():
    """2024 hand answer: Jan 100*31=3100; Feb 2*1000=2000;

    Mar 1*1000*31=31000; Apr zero bbl; May absent; Jun-Dec 10 bbl
    each = 7*10=70. Reported subtotal = 3100+2000+31000+0+70=36170.
    Annual total is unknown, never 36170 with May silently replaced by zero.
    """
    loader = StateProductionLoader()
    raw = [
        {"period": "2024-01", "value": 100, "unit": "Barrels per Day"},
        {"period": "2024-02", "value": 2, "unit": "Thousand Barrels"},
        {"period": "2024-03", "value": 1, "unit": "Thousand Barrels per Day"},
        {"period": "2024-04", "value": 0, "unit": "Barrels"},
    ] + [
        {"period": f"2024-{month:02d}", "value": 10, "unit": "Barrels"}
        for month in range(6, 13)
    ]
    annual = loader.annual_total(loader.load(raw, "TX"))
    assert pd.isna(annual.loc[0, "crude_bbl"])
    assert annual.loc[0, "reported_crude_bbl"] == 36170
    assert annual.loc[0, "crude_missing_months"] == (5,)
    assert annual.loc[0, "status"] == "MISSING"


def test_null_month_and_all_null_year():
    """Twelve absent values have no reported subtotal; none is a true zero."""
    loader = StateProductionLoader()
    raw = [{"period": f"2024-{month:02d}", "unit": "Barrels"} for month in range(1, 13)]
    frame = loader.load(raw, "TX")
    assert frame["value_missing"].all()
    annual = loader.annual_total(frame)
    assert pd.isna(annual.loc[0, "crude_bbl"])
    assert pd.isna(annual.loc[0, "reported_crude_bbl"])
    assert annual.loc[0, "crude_missing_months"] == tuple(range(1, 13))


def test_alaska_annual_volumes_and_partial_component():
    """2024: crude 100*366=36600; NGL zero except absent February.

    NGL's reported subtotal is zero, but the annual NGL volume is unknown.
    """
    loader = AlaskaProductionLoader()
    raw = [
        {
            "period": f"2024-{month:02d}",
            "field": "synthetic",
            "crude_bopd": 100,
            "ngl_bopd": None if month == 2 else 0,
        }
        for month in range(1, 13)
    ]
    frame = loader.load(raw)
    before = frame.copy(deep=True)
    annual = loader.annual_total(frame)
    assert annual.loc[0, "crude_bbl"] == 36600
    assert pd.isna(annual.loc[0, "ngl_bbl"])
    assert annual.loc[0, "reported_ngl_bbl"] == 0
    assert annual.loc[0, "ngl_missing_months"] == (2,)
    assert "crude_bopd" not in annual.columns
    pd.testing.assert_frame_equal(frame, before)
    assert math.isnan(loader.to_records(frame)[1].total_liquids_bopd)


def test_duplicate_months_rejected():
    """Two identical monthly rows must not double a volume."""
    loader = StateProductionLoader()
    row = {"period": "2024-01", "unit": "Barrels", "value": 1}
    with pytest.raises(ValueError, match="Duplicate"):
        loader.annual_total(loader.load([row, row], "TX"))


def test_missing_dpr_component_propagates_through_summary():
    """Missing new-well input plus a reported zero is still missing.

    Extends the signed-net-change cases in the independent crosscheck work.
    """
    report = DrillingProductivityReport()
    frame = report.load_all_basins(
        [{"period": "2024-01", "basin": "synthetic", "legacy_decline_bopd": 0}]
    )
    assert pd.isna(report.net_change_summary(frame).loc[0, "net_change_bopd"])


def test_country_synthetic_provenance_survives_ranking():
    """No revision-qualified source means no engineering qualification.

    Reuses the synthetic/live distinction from the adapter provenance work.
    """
    loader = CountryProductionLoader()
    frame = loader.load(MOCK_COUNTRY_PRODUCTION)
    for result in (frame, loader.top_producers(frame)):
        assert set(result["source"]) == {"synthetic"}
        assert set(result["engineering_status"]) == {"NOT_EVALUATED"}
        assert result["source_revision"].isna().all()
        assert set(result["unit"]) == {"kbd"}
        assert set(result["basis"]) == {"rate_per_day"}


@pytest.mark.parametrize("value", [None, float("nan"), pd.NA])
@pytest.mark.parametrize(
    "unit",
    ["Barrels", "Thousand Barrels", "Barrels per Day", "Thousand Barrels per Day"],
)
def test_state_explicit_missing_markers(value, unit):
    """None, NaN and nullable scalar mean unreported; never substitute zero."""
    frame = StateProductionLoader().load(
        [{"period": "2024-01", "value": value, "unit": unit}], "TX"
    )
    assert frame.loc[0, "value_missing"]
    assert pd.isna(frame.loc[0, "crude_bbl"])


@pytest.mark.parametrize(
    "value",
    [
        -1,
        float("inf"),
        float("-inf"),
        "invalid",
        True,
        False,
        np.bool_(True),
        np.bool_(False),
    ],
)
@pytest.mark.parametrize("kind", ["state", "alaska", "basin", "country"])
def test_invalid_production_is_rejected(kind, value):
    """Unsigned physical amounts cannot be negative, infinite or nonnumeric.

    These are structural rejection cases; -1 is a selected invalid input,
    not a measured value or an engineering acceptance threshold.
    """
    with pytest.raises((TypeError, ValueError)):
        if kind == "state":
            StateProductionLoader().load(
                [{"period": "2024-01", "unit": "Barrels", "value": value}], "TX"
            )
        elif kind == "alaska":
            AlaskaProductionLoader().load(
                [{"period": "2024-01", "field": "synthetic", "crude_bopd": value}]
            )
        elif kind == "basin":
            BasinProductionLoader().load(
                [
                    {
                        "period": "2024-01",
                        "basin": "synthetic",
                        "total_production_bopd": value,
                    }
                ]
            )
        else:
            CountryProductionLoader().load(
                [{"year": 2024, "country": "synthetic", "production_kbd": value}]
            )


def test_zero_year_is_complete():
    """Twelve reported zero volumes sum to zero, with no missing month."""
    loader = StateProductionLoader()
    frame = loader.load(
        [
            {"period": f"2024-{month:02d}", "value": 0, "unit": "Barrels"}
            for month in range(1, 13)
        ],
        "TX",
    )
    annual = loader.annual_total(frame)
    assert annual.loc[0, "crude_bbl"] == 0
    assert annual.loc[0, "status"] == "COMPLETE"


@pytest.mark.parametrize(
    "loader,args",
    [
        (StateProductionLoader(), ([], "TX")),
        (AlaskaProductionLoader(), ([],)),
    ],
)
def test_empty_annual_schema(loader, args):
    """No input means no inferred entity/year, but a stable volume schema."""
    empty = loader.annual_total(loader.load(*args))
    assert empty.empty
    assert {"crude_bbl", "reported_crude_bbl", "crude_missing_months", "status"} <= set(
        empty.columns
    )


def test_country_source_revision_is_evidence_only():
    """A supplied source revision survives ranking without asserting qualification."""
    loader = CountryProductionLoader()
    frame = loader.load(
        [
            {
                "country": "synthetic",
                "year": 2024,
                "production_kbd": 1,
                "source": "synthetic",
                "source_revision": "fixture-r1",
            },
            {
                "country": "synthetic",
                "year": 2023,
                "production_kbd": 0,
                "source": "synthetic",
                "source_revision": "fixture-r0",
            },
            {"country": "missing", "year": 2024},
        ]
    )
    top = loader.top_producers(frame)
    assert top.loc[0, "source_revision"] == "fixture-r1"
    assert top.loc[0, "engineering_status"] == "NOT_EVALUATED"
    assert top.loc[1, "production_kbd_missing"]
    assert pd.isna(top.loc[1, "production_kbd"])


def test_aliases_are_explicit_and_scale_preserving():
    """January: 1*31=31 bbl; kilo aliases give 1*1000*31=31000 bbl."""
    loader = StateProductionLoader()
    for unit, expected in [
        ("bbl", 1),
        ("kbbl", 1000),
        ("bbl/day", 31),
        ("bopd", 31),
        ("kbd", 31000),
    ]:
        frame = loader.load([{"period": "2024-01", "unit": unit, "value": 1}], "TX")
        assert frame.loc[0, "crude_bbl"] == expected


def test_dpr_declares_each_columns_measurement_schema():
    """Rates and rig counts have different units; metadata must identify each.

    Retain the numeric-column contract in the related direct DPR tests.
    """
    loader = BasinProductionLoader()
    for frame in (
        loader.load([]),
        loader.load([{"period": "2024-01", "basin": "synthetic", "rig_count": 0}]),
    ):
        assert frame.attrs["measurements"]["rig_count"] == {
            "unit": "rigs",
            "basis": "count",
        }
        for column in [
            "new_well_ip_bopd",
            "legacy_decline_bopd",
            "total_production_bopd",
        ]:
            assert frame.attrs["measurements"][column] == {
                "unit": "bopd",
                "basis": "rate_per_day",
            }


@pytest.mark.parametrize("year", [2024, "2024"])
def test_country_year_accepts_integer_and_numeric_string(year):
    """Both representations identify the same selected synthetic calendar year."""
    frame = CountryProductionLoader().load(
        [{"country": "synthetic", "year": year, "production_kbd": 0}]
    )
    assert frame.loc[0, "year"] == 2024


@pytest.mark.parametrize("year", [None, 0, 2024.5, True, "2024x", 10000])
def test_country_year_rejects_invalid_calendar_year(year):
    """Missing, non-integral and out-of-calendar years cannot identify a period."""
    with pytest.raises((TypeError, ValueError), match="year|period"):
        CountryProductionLoader().load([{"country": "synthetic", "year": year}])


@pytest.mark.parametrize(
    "unit", ["Thousand Barrels", "Barrels per Day", "Thousand Barrels per Day"]
)
def test_state_monthly_volume_overflow_rejected(unit):
    """Finite synthetic input must not become infinite after scaling or integration."""
    with pytest.raises(ValueError, match="finite"):
        StateProductionLoader().load(
            [{"period": "2024-01", "value": 1e308, "unit": unit}], "TX"
        )


@pytest.mark.parametrize("kind", ["state", "alaska"])
@pytest.mark.parametrize("month_count", [11, 12])
def test_annual_volume_overflow_rejected(kind, month_count):
    """Finite monthly volumes cannot yield infinite totals or partial subtotals.

    Synthetic state months each report 1e308 bbl. Alaska months integrate
    1e306 bbl/day over 31, 29 or 30 days; every monthly volume is finite,
    but even January-November totals 335*1e306 = 3.35e308 bbl, above float range.
    """
    if kind == "state":
        loader = StateProductionLoader()
        frame = loader.load(
            [
                {"period": f"2024-{month:02d}", "value": 1e308, "unit": "Barrels"}
                for month in range(1, month_count + 1)
            ],
            "TX",
        )
    else:
        loader = AlaskaProductionLoader()
        frame = loader.load(
            [
                {
                    "period": f"2024-{month:02d}",
                    "field": "synthetic",
                    "crude_bopd": 1e306,
                    "ngl_bopd": None,
                }
                for month in range(1, month_count + 1)
            ]
        )
    with pytest.raises(ValueError, match="finite"):
        loader.annual_total(frame)


@pytest.mark.parametrize("column", ["crude_bopd", "ngl_bopd"])
def test_alaska_monthly_integration_overflow_rejected(column):
    """The existing annual boundary also rejects overflow in either rate component."""
    loader = AlaskaProductionLoader()
    frame = loader.load([{"period": "2024-01", "field": "synthetic", column: 1e308}])
    with pytest.raises(ValueError, match="finite"):
        loader.annual_total(frame)


def test_large_finite_volume_is_retained():
    """Synthetic 1e300 kbbl/day: January 1e300*1000*31 = 3.1e304 bbl.

    Annual leap-year volume is 1e300*1000*366 = 3.66e305 bbl; both are finite.
    """
    loader = StateProductionLoader()
    frame = loader.load(
        [
            {"period": f"2024-{month:02d}", "value": 1e300, "unit": "kbd"}
            for month in range(1, 13)
        ],
        "TX",
    )
    assert frame.loc[0, "crude_bbl"] == pytest.approx(3.1e304)
    annual = loader.annual_total(frame)
    assert annual.loc[0, "crude_bbl"] == pytest.approx(3.66e305)
    assert annual.loc[0, "reported_crude_bbl"] == pytest.approx(3.66e305)
    assert annual.loc[0, "status"] == "COMPLETE"
