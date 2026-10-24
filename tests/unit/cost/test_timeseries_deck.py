"""Exact-year deck tests; monetary values below are synthetic hand calculations.

Arithmetic mean source: NIST/SEMATECH e-Handbook (2003), section 1.3.5.1,
https://www.itl.nist.gov/div898/handbook/eda/section3/eda351.htm.
No fixture is a measured cost or an engineering acceptance limit.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from worldenergydata.cost.timeseries.deck import (
    CostBasisQuery,
    build_cost_deck,
    lookup_annual_cost,
)
from worldenergydata.cost.timeseries.schema import (
    CostComponent,
    CostObservation,
    DevelopmentSystemBand,
    FigureType,
    PriceBasis,
    Provenance,
)


def query(**changes):
    """Explicit synthetic comparison basis, without field-economics defaults."""
    return CostBasisQuery(
        **(
            {
                "component": CostComponent.OPEX_VARIABLE,
                "band": DevelopmentSystemBand.TIEBACK,
                "currency": "USD",
                "unit": "usd_per_bbl",
                "region": "global",
                "segment": None,
                "figure_type": FigureType.DISCLOSED_TOTAL,
                "price_basis": PriceBasis.NOMINAL,
                "basis_year": None,
            }
            | changes
        )
    )


def observation(value=10.0, year=2020, **changes):
    """Synthetic evidence; dates identify fixture years, not cost assumptions."""
    return CostObservation(
        **(
            {
                **query().model_dump(),
                "year": year,
                "value": value,
                "provenance": Provenance.SOURCED,
                "source_title": "Synthetic arithmetic fixture",
                "source_url": "https://example.org/synthetic-cost",
                "quoted_text": f"Synthetic value {value}",
                "accessed_date": date(2026, 10, 19),
            }
            | changes
        )
    )


def test_annual_mean_preserves_source_evidence():
    """Hand calculation: (10 + 30) / 2 = 20 usd/bbl in 2020."""
    rows = [observation(10), observation(30)]
    result = lookup_annual_cost(rows, year=2020, query=query())
    assert result.status == "EVALUATED"
    assert result.value == 20
    assert result.year == 2020
    assert result.query == query()
    assert result.observations == tuple(rows)
    assert result.reason is None
    assert "eda351" in result.method_source


@pytest.mark.parametrize(
    "changes",
    [
        {"year": 2021},
        {"component": CostComponent.OPEX_FIXED},
        {"band": DevelopmentSystemBand.SUBSEA_20},
        {"currency": "GBP"},
        {"unit": "usd_per_year"},
        {"region": "regional"},
        {"segment": "deepwater"},
        {"figure_type": FigureType.SINGLE_FIXTURE},
        {"price_basis": PriceBasis.REAL, "basis_year": 2020},
        {"provenance": Provenance.FITTED, "notes": "Synthetic fitted row"},
        {"provenance": Provenance.ASSUMED, "notes": "Synthetic assumed row"},
        {"provenance": Provenance.ALLOCATED, "notes": "Synthetic allocated row"},
        {"provenance": Provenance.TODO, "value": None},
    ],
)
def test_incomparable_rows_cannot_change_mean(changes):
    """Hand calculation: one matching value, 10 / 1 = 10; others excluded."""
    rows = [observation(), observation(**({"value": 90} | changes))]
    result = lookup_annual_cost(rows, year=2020, query=query())
    assert result.value == 10
    assert result.observations == (rows[0],)


def test_missing_year_is_not_evaluated_without_carry_forward():
    """Only 2020 is observed; there is no independent 2021 value."""
    result = lookup_annual_cost([observation()], year=2021, query=query())
    assert result.status == "NOT_EVALUATED"
    assert result.value is None
    assert result.observations == ()
    assert result.reason


def test_real_basis_years_are_separate():
    """2020-base value 10 is excluded; only 2021-base value 30 remains."""
    rows = [
        observation(10, price_basis=PriceBasis.REAL, basis_year=2020),
        observation(30, price_basis=PriceBasis.REAL, basis_year=2021),
    ]
    result = lookup_annual_cost(
        rows, year=2020, query=query(price_basis=PriceBasis.REAL, basis_year=2021)
    )
    assert result.value == 30


@pytest.mark.parametrize(
    "changes",
    [
        {"price_basis": PriceBasis.REAL},
        {"basis_year": 2020},
        {"unit": " "},
        {"region": " "},
    ],
)
def test_invalid_comparison_basis_is_rejected(changes):
    with pytest.raises(ValidationError):
        query(**changes)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_evidence_is_not_evaluated(value):
    result = lookup_annual_cost([observation(value)], year=2020, query=query())
    assert result.status == "NOT_EVALUATED"
    assert result.value is None
    assert "finite" in result.reason


def test_duplicate_evidence_requires_resolution():
    """Repeating 10 would bias (10 + 30)/2 = 20 to (10 + 10 + 30)/3."""
    row = observation()
    result = lookup_annual_cost([row, row, observation(30)], year=2020, query=query())
    assert result.status == "NOT_EVALUATED"
    assert result.value is None
    assert "Duplicate" in result.reason


def test_zero_is_an_observation_not_a_gap():
    """Hand calculation: a sourced zero has mean 0 / 1 = 0."""
    result = lookup_annual_cost([observation(0)], year=2020, query=query())
    assert result.status == "EVALUATED"
    assert result.value == 0


def test_multi_year_deck_retains_requested_gaps_and_consumes_generator_once():
    """2020 mean (10+30)/2=20; 2021 missing; 2022 mean 40/1=40."""
    rows = (row for row in [observation(10), observation(30), observation(40, 2022)])
    deck = build_cost_deck(rows, years=[2022, 2020, 2021, 2020], query=query())
    assert [result.year for result in deck] == [2020, 2021, 2022]
    assert [result.value for result in deck] == [20, None, 40]
    assert deck[1].status == "NOT_EVALUATED"


def test_empty_deck_request_has_no_results():
    assert build_cost_deck([], years=[], query=query()) == ()


def test_csv_round_trip_deck(tmp_path):
    """CSV round trip: synthetic (10 + 30) / 2 = 20; next year remains absent."""
    from worldenergydata.cost.timeseries.dataset import (
        read_timeseries_csv,
        write_timeseries_csv,
    )

    path = tmp_path / "cost.csv"
    write_timeseries_csv([observation(10), observation(30)], path)
    deck = build_cost_deck(read_timeseries_csv(path), years=[2020, 2021], query=query())
    assert [result.value for result in deck] == [20, None]
    assert all(row.source_url for row in deck[0].observations)


def test_query_currency_matches_observation_normalization():
    """Currency case does not alter a unit: synthetic 10 / 1 = 10 USD/bbl."""
    result = lookup_annual_cost([observation()], year=2020, query=query(currency="usd"))
    assert result.value == 10


@pytest.mark.parametrize("name", list(CostBasisQuery.model_fields))
def test_all_comparison_dimensions_are_required(name):
    dimensions = query().model_dump()
    del dimensions[name]
    with pytest.raises(ValidationError):
        CostBasisQuery(**dimensions)


def test_mean_of_large_finite_values_remains_finite():
    """Synthetic (1e308 + 1e308) / 2 = 1e308 in real arithmetic."""
    rows = [observation(1e308), observation(1e308, source_title="Other synthetic row")]
    result = lookup_annual_cost(rows, year=2020, query=query())
    assert result.value == 1e308
