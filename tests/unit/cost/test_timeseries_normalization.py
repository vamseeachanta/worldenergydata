"""Currency and price-basis contracts for normalization (issue #1261).

Method reference: OpenStax, Principles of Economics, 3rd edition (2022),
section 19.2, "Adjusting Nominal Values to Real Values": divide nominal money
by its price index, expressed relative to the selected base year.
https://openstax.org/books/principles-economics-3e/pages/19-2-adjusting-nominal-values-to-real-values

All numbers below are synthetic test inputs, not empirical index levels.
Hand calculation: for 2000 and 2002 indices of 100 and 125, respectively,
200 nominal currency units in 2000 become 200 * 125 / 100 = 250 in 2002.
The reverse conversion is 200 * 100 / 125 = 160. Same-year conversion is
200 * 100 / 100 = 200. These integer results need no numerical tolerance.
"""

from dataclasses import asdict

import pytest

from worldenergydata.cost.timeseries.normalization import (
    Deflator,
    DeflatorBasis,
    build_deflator,
    deflate_series,
)
from worldenergydata.cost.timeseries.schema import (
    CostComponent,
    CostObservation,
    PriceBasis,
    Provenance,
)


def _observation(**overrides) -> CostObservation:
    """Synthetic nominal money; years and amounts follow the module example."""
    fields = {
        "year": 2000,
        "component": CostComponent.OPEX_FIXED,
        "value": 200.0,
        "unit": "currency_units",
        "provenance": Provenance.ASSUMED,
        "notes": "Synthetic input for independent arithmetic in the test docstring.",
    }
    fields.update(overrides)
    return CostObservation(**fields)


def _deflator(basis: DeflatorBasis = DeflatorBasis.CPI) -> Deflator:
    """Synthetic indices from the module's hand calculation."""
    return Deflator(
        basis=basis,
        values={2000: 100.0, 2002: 125.0},
        interpolated_years=frozenset(),
        source_note="Synthetic test indices; not measured CPI or UCCI.",
    )


@pytest.mark.parametrize("basis", list(DeflatorBasis))
@pytest.mark.parametrize(
    "year,basis_year,expected", [(2000, 2002, 250.0), (2002, 2000, 160.0)]
)
def test_nominal_conversion_retains_money_semantics(basis, year, basis_year, expected):
    """Forward/reverse expected values are hand-calculated in the module example."""
    row = _observation(year=year)
    [point] = deflate_series([row], _deflator(basis), basis_year)

    assert point.nominal == row.value
    assert point.real == expected
    assert point.currency == "USD"
    assert point.price_basis is PriceBasis.REAL
    assert point.basis is basis
    assert point.basis_year == basis_year
    assert point.year == row.year
    assert point.component is row.component
    assert point.band == row.band.value
    assert point.unit == row.unit
    assert not point.deflator_is_interpolated
    assert asdict(point)["currency"] == "USD"
    assert asdict(point)["price_basis"] == "real"


@pytest.mark.parametrize("basis_year", [2000, 2002])
def test_real_rows_raise_even_when_already_in_target_year(basis_year):
    """REAL 2002 money cannot be treated as nominal 2000 money or re-deflated."""
    row = _observation(price_basis=PriceBasis.REAL, basis_year=2002)
    with pytest.raises(ValueError, match="price_basis.*real.*nominal"):
        deflate_series([row], _deflator(), basis_year)


@pytest.mark.parametrize("currency", ["GBP", "EUR"])
def test_foreign_currency_raises(currency):
    """Synthetic amount is incompatible with a USD index regardless of its size."""
    with pytest.raises(ValueError, match=f"currency.*{currency}.*USD"):
        deflate_series([_observation(currency=currency)], _deflator(), 2002)


@pytest.mark.parametrize("currency", ["GBP", "gbp", "Gbp"])
def test_explicit_currency_is_used_instead_of_assuming_usd(currency):
    """Same synthetic ratio: 200 GBP * 125 / 100 = 250 GBP; no FX conversion."""
    deflator = Deflator(
        basis=DeflatorBasis.CPI,
        values={2000: 100.0, 2002: 125.0},
        interpolated_years=frozenset(),
        source_note="Synthetic GBP index supplied explicitly by the caller.",
        currency=currency,
    )
    assert deflator.currency == "GBP"
    [point] = deflate_series([_observation(currency="gbp")], deflator, 2002)
    assert point.currency == "GBP"
    assert point.real == 250.0
    with pytest.raises(ValueError, match="currency.*USD.*GBP"):
        deflate_series([_observation()], deflator, 2002)


@pytest.mark.parametrize("basis", list(DeflatorBasis))
def test_builder_to_series_preserves_real_output_contract(basis):
    """Synthetic anchors: 200 * 125 / 100 = 250; 200 * 125 / 125 = 200.

    Inputs follow the module's OpenStax-based hand calculation. Neither
    the expected numbers nor the metadata are obtained from another API.
    """
    component = (
        CostComponent.INDEX_CPI
        if basis is DeflatorBasis.CPI
        else CostComponent.INDEX_UCCI
    )
    anchors = [
        _observation(component=component, value=100.0),
        _observation(component=component, year=2002, value=125.0),
    ]
    rows = [_observation(), _observation(year=2002)]
    deflator = build_deflator(anchors, basis)
    points = deflate_series(rows, deflator, 2002)

    assert [point.real for point in points] == [250.0, 200.0]
    for point in points:
        serialized = asdict(point)
        assert serialized["currency"] == "USD"
        assert serialized["price_basis"] == "real"
        assert serialized["basis"] == basis.value
        assert serialized["basis_year"] == 2002


@pytest.mark.parametrize("basis", list(DeflatorBasis))
def test_incompatible_rows_raise_before_coverage_is_considered(basis):
    """Missing coverage must not hide a REAL or foreign-currency input."""
    for incompatible in [
        {"price_basis": PriceBasis.REAL, "basis_year": 2002},
        {"currency": "GBP"},
    ]:
        with pytest.raises(ValueError, match="price_basis|currency"):
            deflate_series([_observation(**incompatible)], _deflator(basis), 2001)


@pytest.mark.parametrize("year,basis_year", [(2001, 2002), (2000, 2001)])
def test_uncovered_year_keeps_point_and_target_metadata(year, basis_year):
    """2001 has no supplied index: retain the row and declare the missing result."""
    [point] = deflate_series([_observation(year=year)], _deflator(), basis_year)
    assert point.real is None
    assert point.currency == "USD"
    assert point.price_basis is PriceBasis.REAL
    assert point.basis_year == basis_year


@pytest.mark.parametrize("interpolated_year", [2000, 2002])
def test_interpolation_flag_covers_both_ends(interpolated_year):
    """The supplied synthetic ratio still gives 250; either inferred end is flagged."""
    deflator = Deflator(
        basis=DeflatorBasis.UCCI,
        values={2000: 100.0, 2002: 125.0},
        interpolated_years=frozenset({interpolated_year}),
        source_note="Synthetic inferred endpoint, not measured UCCI.",
    )
    [point] = deflate_series([_observation()], deflator, 2002)
    assert point.real == 250.0
    assert point.deflator_is_interpolated


def test_excluded_and_missing_rows_do_not_raise():
    """Only selected valued rows enter conversion; identity gives 200 unchanged."""
    missing = _observation(value=None, provenance=Provenance.TODO, currency="GBP")
    excluded = _observation(
        component=CostComponent.HOST_CAPEX,
        currency="GBP",
        price_basis=PriceBasis.REAL,
        basis_year=2002,
    )
    [point] = deflate_series(
        [missing, excluded, _observation()],
        _deflator(),
        2000,
        components={CostComponent.OPEX_FIXED},
    )
    assert point.real == 200.0
    assert deflate_series([excluded], _deflator(), 2002, components=set()) == []
    assert deflate_series([], _deflator(), 2002) == []


def test_mixed_selected_series_raises_instead_of_returning_partial_results():
    """A valid first row must not conceal a later incompatible currency."""
    with pytest.raises(ValueError, match="currency.*GBP.*USD"):
        deflate_series(
            [_observation(), _observation(currency="GBP")], _deflator(), 2002
        )


@pytest.mark.parametrize(
    "basis,component",
    [
        (DeflatorBasis.CPI, CostComponent.INDEX_CPI),
        (DeflatorBasis.UCCI, CostComponent.INDEX_UCCI),
    ],
)
@pytest.mark.parametrize(
    "incompatible",
    [
        {"currency": "GBP"},
        {"price_basis": PriceBasis.REAL, "basis_year": 2002},
    ],
)
def test_builder_rejects_incompatible_reference_rows(basis, component, incompatible):
    """A selected index anchor must retain the built-in nominal USD contract."""
    rows = [
        _observation(component=component),
        _observation(component=component, **incompatible),
    ]
    with pytest.raises(ValueError, match="currency|price_basis"):
        build_deflator(rows, basis)


@pytest.mark.parametrize(
    "basis,component",
    [
        (DeflatorBasis.CPI, CostComponent.INDEX_CPI),
        (DeflatorBasis.UCCI, CostComponent.INDEX_UCCI),
    ],
)
def test_builder_ignores_unselected_or_missing_reference_rows(basis, component):
    """Only the selected valued reference matters; synthetic anchor stays 100."""
    rows = [
        _observation(component=component, value=100.0),
        _observation(currency="GBP", price_basis=PriceBasis.REAL, basis_year=2002),
        _observation(
            component=component, value=None, provenance=Provenance.TODO, currency="GBP"
        ),
    ]
    deflator = build_deflator(rows, basis)
    assert deflator.currency == "USD"
    assert deflator.values == {2000: 100.0}
