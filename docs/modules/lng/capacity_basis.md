# LNG collector capacity basis

Empty refreshes retain the last successful cache and its metadata. GIE capacity
is evaluated only when its unit and mass conversion basis are known; otherwise
the terminal remains available with `capacity_mtpa=None`.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| A | 2026-10-21 | Document explicit units and required conversion inputs to prevent silent capacity errors. |

## Input contract

The collector accepts these throughput fields:

| Input | Unit | Basis |
| --- | --- | --- |
| `maxCapacity` with `maxCapacityUnit` | Exactly `mcm/d` or `GWh/d` | Explicit adapter contract; no inferred default |
| `dtrs`, when `maxCapacity` is absent | `GWh/d` | GIE API User Manual v007 (2022), section 2.4, page 8 |
| `dtmi` | Storage volume, never throughput | Same manual and section |

An explicit `maxCapacity` takes precedence even when invalid. No fallback hides
an unknown unit. Unknown or missing units, invalid rates, absent conversion
bases and absent factors produce a `NOT_EVALUATED` warning and no capacity.
Rates and factors must be finite and positive. Zero send-out *capacity* is not
treated as a nameplate rating; operating flow belongs in a different field.

`GIECapacityBasis` requires `days_per_year` and a nonblank `reference`. Supply
`tonnes_per_mcm` for volume rates or `tonnes_per_gwh` for energy rates. These are
required conversion inputs, with no default gas density, calorific value or
annual operating basis. For production, reference a supporting source and match
the source gas, reference conditions and energy basis. A declared assumption
must be labelled as such. The collector records that reference as a capacity
citation; it does not validate the supporting document or gas properties.

By dimensional cancellation:

```text
MTPA = rate [mcm/d] * factor [tonnes/mcm] * days [d/year] / 1,000,000
MTPA = rate [GWh/d] * factor [tonnes/GWh] * days [d/year] / 1,000,000
```

The decimal divisor is from NIST SP 811 (2008), section 4.3, table 5
(mega = ten to the sixth power). It is a unit scale, not a gas-property factor.
Results retain floating-point precision; display rounding belongs downstream.

## Worked example

All inputs below are synthetic arithmetic inputs, not recommended gas
properties: 360 days/year, 700 tonnes/mcm and 70 tonnes/GWh. The independent
hand calculations are `10 * 700 * 360 = 2,520,000` tonnes/year and
`100 * 70 * 360 = 2,520,000` tonnes/year. Both give **2.52 MTPA**.

```python
from worldenergydata.lng_terminals.collectors.gie_collector import (
    GIECapacityBasis,
    GIECollector,
)

basis = GIECapacityBasis(
    days_per_year=360,
    tonnes_per_mcm=700,
    tonnes_per_gwh=70,
    reference="Synthetic hand calculation in the capacity basis guide",
)
records = [
    dict(name="Synthetic Volume Terminal", country="GB",
         maxCapacity="10", maxCapacityUnit="mcm/d"),
    dict(name="Synthetic Energy Terminal", country="GB", dtrs="100"),
]
with GIECollector(capacity_basis=basis) as collector:
    terminals = collector.parse_records(records)
assert [terminal.capacity_mtpa for terminal in terminals] == [2.52, 2.52]
print([terminal.capacity_mtpa for terminal in terminals])
```

This example parses local inputs and makes no network request or cache write.
The default constructor has no conversion basis and therefore does not publish
an assumed mass throughput. Capacity is excluded from source field coverage
when it cannot be evaluated. Existing caches are not migrated; an explicit
refresh is needed to replace previously converted values.

## Cache behavior and limits

The shared persistence boundary rejects an empty collection, including empty
parsing and all-invalid validation. It logs a warning and leaves both cache
data and success metadata unchanged. An empty first collection creates neither
file. A successful non-empty collection can still replace an earlier cache.
Collection returns the empty fresh result on an outage; it does not silently
return expired records. Existing TTL rules still apply when reading the cache.

No live refresh or recovery of previously emptied caches is included. Configure
a supported conversion basis before relying on mass-capacity output. Scheduler
enablement and upstream adapter schema changes are outside this change.

## Sources

- [GIE API User Manual v007 (4 October 2022)](https://www.gie.eu/transparency-platform/GIE_API_documentation_v007.pdf),
  section 2.4, Facility Report listing, page 8: `dtrs` versus `dtmi`.
- [NIST Special Publication 811 (2008)](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication811e2008.pdf),
  section 4.3, table 5: decimal SI prefixes.

Both source documents were opened successfully on 2026-10-21. Regression tests
state their independent expected calculations in their docstrings.
