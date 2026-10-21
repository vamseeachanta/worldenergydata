# Cost normalization

`deflate_series` converts selected nominal observations using an index in the
same currency. It rejects REAL observations and currency mismatches, and keeps
currency, target price basis, index basis and target year in each result.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-21 | Document currency compatibility and a reproducible conversion to prevent double deflation and currency mixing. |

## Method and source

For a nominal amount observed in year `t`, express its purchasing power in
target year `b` using:

```text
real[b] = nominal[t] * index[b] / index[t]
```

This is the nominal-to-real equation in [OpenStax, *Principles of Economics*,
third edition (2022), section 19.2, “Adjusting Nominal Values to Real
Values”](https://openstax.org/books/principles-economics-3e/pages/19-2-adjusting-nominal-values-to-real-values),
re-expressed in the selected year's purchasing power. The index ratio is
dimensionless: it changes the price basis and preserves the monetary unit.
It supplies no exchange rate.

## Worked example

All amounts, years and index levels in this example are synthetic inputs,
rather than measured CPI or UCCI data. The independent hand calculation is
`200 * 125 / 100 = 250`: nominal GBP in the observation year becomes real GBP
in the target year. The reverse ratio gives `200 * 100 / 125 = 160`, and using
the same source and target year gives `200 * 100 / 100 = 200`.

```python
from dataclasses import asdict, replace

from worldenergydata.cost.timeseries.normalization import (
    Deflator,
    DeflatorBasis,
    deflate_series,
)
from worldenergydata.cost.timeseries.schema import (
    CostComponent,
    CostObservation,
    PriceBasis,
    Provenance,
)

# Synthetic inputs; arithmetic follows the OpenStax equation cited above.
row = CostObservation(
    year=2000,
    component=CostComponent.OPEX_FIXED,
    value=200.0,
    unit="gbp_mm",
    currency="gbp",
    price_basis=PriceBasis.NOMINAL,
    provenance=Provenance.ASSUMED,
    notes="Synthetic example; not an empirical cost estimate.",
)
index = Deflator(
    basis=DeflatorBasis.CPI,
    values={2000: 100.0, 2002: 125.0},
    interpolated_years=frozenset(),
    source_note="Synthetic GBP index supplied for illustration only.",
    currency="gbp",
)
[point] = deflate_series([row], index, basis_year=2002)
assert point.nominal == 200.0
assert point.real == 250.0
assert point.currency == "GBP"
assert point.price_basis is PriceBasis.REAL
assert point.basis is DeflatorBasis.CPI
assert point.basis_year == 2002
assert asdict(point)["currency"] == "GBP"

# An uncovered target year retains the point and its target metadata.
[uncovered] = deflate_series([row], index, basis_year=2001)
assert uncovered.real is None
assert uncovered.basis_year == 2001
assert uncovered.currency == "GBP"

real_row = row.model_copy(
    update={"price_basis": PriceBasis.REAL, "basis_year": 2002}
)
usd_index = replace(index, currency="USD")
for observation, deflator in [(real_row, index), (row, usd_index)]:
    try:
        deflate_series([observation], deflator, basis_year=2002)
    except ValueError:
        pass
    else:
        raise AssertionError("Incompatible money semantics must be rejected")
```

## API contract and limits

- `Deflator.currency` defaults to USD for the built-in reference-series
  contract. Explicit currency codes are uppercased, matching observation
  normalization. A caller supplying another currency must also supply the
  corresponding index; relabelling a USD index does not convert it to GBP.
- `build_deflator` accepts nominal USD reference rows only. It checks valued
  anchors of the requested index before averaging or interpolating them.
- `deflate_series` skips missing amounts and excluded components first, then
  requires every selected valued observation to be NOMINAL and in the index's
  currency. A mismatch raises `ValueError`; no partial series is returned.
- `RealSeriesPoint.nominal` retains the input amount. `currency` applies to both
  amounts; `price_basis=REAL` and `basis_year` describe the target `real` amount.
  `basis` identifies CPI or UCCI. These fields survive dataclass serialization.
- Missing index coverage returns a point with `real=None` and the intended
  target metadata. Interpolation of either endpoint is flagged. Coverage gaps
  do not relax currency or price-basis validation.
- REAL rebasing and foreign-exchange conversion require separate explicit
  operations. `to_real` is a scalar helper without observation metadata; its
  caller must establish nominal input and compatible currency first.
