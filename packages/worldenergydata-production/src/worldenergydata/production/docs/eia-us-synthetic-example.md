# EIA US synthetic adapter example

`EiaUsAdapter` generates demonstration rows from its built-in table.
`eia_us` is a routing label; `eia_us_mock` is the provenance label on every row.
These rows are synthetic, not retrieved or measured EIA production.
A successful run establishes no retrieved production, forecast validation or
live-loader coverage. The adapter does not call or exercise the
`worldenergydata.eia_us` clients or loaders.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-26 | Add a runnable example to make the synthetic provenance boundary executable. |

## Runnable example: eia-us-synthetic-query

With the production package and its dependencies installed, run the named Python
block below. It uses the actual `ProductionQuery(regions=...)` constructor and
calls `EiaUsAdapter.fetch` directly. It prints only routing-region and source
labels; no synthetic production magnitudes serve as expected values.

<!-- example: eia-us-synthetic-query -->

```python
from worldenergydata.production.unified.adapters.eia_us_adapter import EiaUsAdapter
from worldenergydata.production.unified.query import ProductionQuery

adapter = EiaUsAdapter()
query = ProductionQuery(regions=["eia_us"])
rows = adapter.fetch(query)
assert not rows.empty

for label in sorted(rows["region"].unique()):
    print("routing-region:", label)
for label in sorted(rows["source"].unique()):
    print("source:", label)
```

Expected output:

```text
routing-region: eia_us
source: eia_us_mock
```

The smoke test in
`tests/unit/production/unified/test_eia_us_documented_example.py` executes this
exact named fence with network transports blocked and checks every returned
source label. It checks provenance and offline execution, without qualifying
production quantities or forecasting methods.

## Source basis and scope

- [Adapter implementation](../unified/adapters/eia_us_adapter.py): the routing
  label, built-in synthetic table and `source` assignment.
- [Query contract](../unified/query.py): the required `regions` argument and
  optional filters.

This example adds no evidence for other EIA US implementation families and does
not update method inventories or an external registry.
