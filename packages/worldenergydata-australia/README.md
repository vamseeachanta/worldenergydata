# worldenergydata-australia

Australia source package for offshore field-development screening.

The initial #721 slice is **FieldConcept / screening-only**: Australia has no
national open per-field *offshore production* database, so this member ingests
the strong AU asset — field metadata (per-field water depth, spud date) from
**DataVic Open Data** (Resources Victoria) and **NOPTA** (Commonwealth offshore
titles/wells), both **CC-BY-4.0** — and runs the field-development concept
screening (`recommend()`) on it. Production economics are explicitly deferred
(no volumes), and the chain output is labelled `production_available=False` so
the zeroed cashflow is never mistaken for a screening result.

## Local AEMO report inspection

`worldenergydata.australia.production.aemo_gbb` reads a caller-supplied
`GasBBActualFlowStorageLast31.CSV` export. This is a feed-inspection step for
#823. It performs no download and includes no publisher data.

```python
from worldenergydata.australia.production.aemo_gbb import (
    monthly_supply,
    read_actual_flow_csv,
)

records = read_actual_flow_csv("actual-flow.csv")
summaries = monthly_supply(
    records,
    facility_id=selected_facility_id,
    location_id=selected_location_id,
)
```

Select the facility and location by their report identifiers. The reader
preserves identifiers as text and distinguishes locations within a facility.
It does not identify which facility types represent production or allocate a
facility's throughput to a field. Duplicate facility/location/gas-day keys are
rejected, even if update timestamps differ; revision precedence is unqualified.

The monthly result sums the observed `Supply` readings only, without adding
`Demand`, storage or transfers. `observed_supply_total` remains in **unqualified
report units**, with no rate integration, calorific-value assumption or gas-volume
conversion. A blank `Supply` makes the total `None`. A reported zero contributes
zero. Missing days are listed in `missing_dates`; months with no observations are
absent. `complete` means every Gregorian calendar day has a nonblank supply,
including leap days. It establishes coverage only. A partial month's numeric
total must not be presented as full-month production or extrapolated silently.

Every summary carries `unit_status`, `reuse_status` and `production_status` as
`NOT_EVALUATED`. `AustraliaAdapter` and the reference chain remain screening-only.
No engineering coefficient, price or acceptance threshold is supplied.

### Source observations and limits

The [AEMO actual-flow report](https://nemweb.com.au/Reports/Current/GBB/GasBBActualFlowStorageLast31.CSV)
and its [directory listing](https://nemweb.com.au/Reports/Current/GBB/) returned
HTTP 200 on 2026-10-19. Column names and date formats are based on that report's
header and text; all test rows are synthetic. The monthly sum is an arithmetic
inspection of readings, without asserting their physical meaning.

The [AEMO legal notices](https://www.aemo.com.au/privacy-and-legal-notices) and
[data guide page](https://www.aemo.com.au/energy-systems/gas/gas-bulletin-board-gbb/data-gbb)
returned HTTP 403 on the same date. Source-specific reuse terms, unit definitions,
revision semantics, production-facility classification and field allocation are
unqualified. Public accessibility alone does not establish reuse permission.
No source rows are redistributed by this change.

Later work requires opened source documentation for those qualifications and an
explicit conversion and gas-price basis before wiring production economics.
The PEPS-SA Excel schema and access remain unassessed by this reader; there is
no login or authenticated API integration.
