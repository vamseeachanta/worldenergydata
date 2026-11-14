# worldenergydata-cost

`cost` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.cost` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Exact-year cost basis

`worldenergydata.cost.timeseries.deck` reads validated `CostObservation` rows
and produces annual means with the complete contributing evidence. The caller
supplies every comparison dimension explicitly. A band of `NOT_APPLICABLE` is
an exact market-wide selection, not a fallback for a missing development band.
`None` for segment or basis year also means an exact absent attribute.

```python
from pathlib import Path

from worldenergydata.cost.timeseries.dataset import read_timeseries_csv
from worldenergydata.cost.timeseries.deck import CostBasisQuery, build_cost_deck
from worldenergydata.cost.timeseries.schema import (
    CostComponent, DevelopmentSystemBand, FigureType, PriceBasis,
)

rows = read_timeseries_csv(
    Path("data/modules/cost/curated/cost_component_timeseries.csv")
)
query = CostBasisQuery(
    component=CostComponent.RIG_DAY_RATE_DRILLSHIP,
    band=DevelopmentSystemBand.NOT_APPLICABLE,
    currency="USD",
    unit="usd_per_day",
    region="global",
    segment="ultra_deepwater",
    figure_type=FigureType.FLEET_AVERAGE,
    price_basis=PriceBasis.NOMINAL,
    basis_year=None,
)
# requested_years is supplied by the consuming analysis.
deck = build_cost_deck(rows, years=requested_years, query=query)
for annual in deck:
    print(annual.year, annual.status, annual.value, annual.reason)
```

Only `SOURCED` rows are eligible. Each result retains the query, evidence rows
(including citations and retrieval dates), and arithmetic-method source. The
mean is the sum of matching observations divided by their count, following
[NIST/SEMATECH e-Handbook (2003), section 1.3.5.1, Measures of Location](https://www.itl.nist.gov/div898/handbook/eda/section3/eda351.htm).
It weights observations equally; it is not a duration-weighted rate, a
confidence interval, or a finding that a cost is applicable to a particular
field. Source freshness and overlap between different disclosures require
review by the consuming analysis.

A missing year returns `NOT_EVALUATED`, `value=None`, and a reason. Exact
repeated rows and non-finite matching values also return `NOT_EVALUATED`.
A sourced zero remains an evaluated zero. Requests are returned as unique years
in ascending order. No carry-forward, interpolation, currency conversion,
inflation adjustment, stage allocation, or FDAS assumption replacement occurs.
Real-price queries require a basis year; nominal queries require `None`.

After a curated CSV refresh, reload it with `read_timeseries_csv` and rebuild
the deck using the same explicit query. Results are not cached. Data-source
research and refresh cadence remain governed by the existing
[cost refresh procedure](../../docs/modules/cost/REFRESH_PROCEDURE.md).
