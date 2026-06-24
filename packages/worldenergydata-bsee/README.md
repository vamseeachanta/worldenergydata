# worldenergydata-bsee

BSEE Gulf-of-Mexico data cluster — a uv workspace member of the
[`worldenergydata`](https://github.com/vamseeachanta/worldenergydata) namespace
(ADR 0001 Phase 2, domain split batch 3, #529).

## Why one member ships five subpackages

These five subpackages are mutually coupled and cannot be carved into separate
distributions:

```
bsee  <-->  lower_tertiary     (import cycle)
bsee  <-->  fdas               (import cycle)
hse    -->  bsee
well_production_dashboard --> bsee
```

A uv workspace member may not contain an import cycle that crosses member
boundaries, so the strongly-connected core (`bsee`/`lower_tertiary`/`fdas`) plus
its in-cluster dependents (`hse`, `well_production_dashboard`) ship together as
this single distribution.

Provides:

- `worldenergydata.bsee` — Bureau of Safety and Environmental Enforcement data
- `worldenergydata.lower_tertiary` — Lower Tertiary geological / portfolio analysis
- `worldenergydata.fdas` — facility / field development economic analysis
- `worldenergydata.hse` — Health, Safety & Environment incident data
- `worldenergydata.well_production_dashboard` — well production dashboards

## Cross-member dependencies

Depends on the carved members `worldenergydata-core`, `worldenergydata-sodir`,
`worldenergydata-reporting`, `worldenergydata-texas_rrc`, and
`worldenergydata-cost`. The root-resident `worldenergydata.engine`,
`worldenergydata.validation` and `worldenergydata.analysis` resolve via the
`pkgutil.extend_path` namespace at runtime (the root distribution depends on
this member, not the reverse).
