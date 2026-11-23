# FDAS country adapter onboarding checklist (F2, #715)

Governance steps for wiring a new country into the FDAS field-development chain.
The F2 contract bridges the existing per-country production adapters
(`worldenergydata.production.unified`) into the schema the FDAS cashflow engine
consumes, plus a metadata→`FieldConcept` mapping for concept screening. Work
through the steps in order; each has a machine-checkable landing spot.

## Steps (per country)

### (a) Production adapter — `AbstractProductionAdapter` subclass
Implement or verify a subclass in `production/unified/adapters/` that emits the
unified `STANDARD_COLUMNS` (`region, field_name, year, month, oil_bbl, gas_mcf,
water_bbl, condensate_bbl, source, ...`). It must declare a non-empty `region`
class attribute (the region key, e.g. `"ncs"`, `"gom"`, `"brazil"`) — that key
is how `ProductionQuery(regions=[...])` routes to the adapter and how the
conformance fixtures tie to it. Cover it in
`tests/unit/production/unified/test_adapters.py` (`_ALL_ADAPTERS`).

### (b) Field metadata mapping — `FieldMetaMapping`
Define the country's regulator-metadata → `FieldConcept` map in
`fdas/adapters/field_concept_normalizer.py` terms: a `FieldMetaMapping` of
`{fieldconcept_field: FieldMapEntry(source_key, transform)}`. Reuse the ported
callable transforms rather than hand-rolling logic:
- `number_from` — comma-stripped float coercion,
- `year_from` — 4-digit year regex from free text,
- `fluid_from_reserve_type` — reserve-type string → `FluidType` (oil-primary for
  mixed),
- `reduce_concept_type` — many-facilities → one concept by priority.

Targets are validated against `FieldConcept` fields at construction (a typo'd
target raises), so only `name` is strictly required; unmapped/`None` values are
dropped.

### (c) Confirm the production transform
Assert `to_fdas_production(unified_df)` yields a valid FDAS production frame:
columns exactly `FDAS_PRODUCTION_COLUMNS`
(`YEAR_MONTH, DEV_NAME, MONTHLY_OIL_BBL, MONTHLY_WATER_BBL, MONTHLY_GAS_MCF`),
`YEAR_MONTH` parseable as a monthly period, `DEV_NAME` carried from `field_name`,
and non-negative oil/gas. (Note the canonical `_BBL`/`_MCF` columns — not the
legacy `bsee_adapter` `MONTHLY_*_VOLUME`.)

### (d) Scheduler refresh job — `AbstractJob` + `_LAZY_EXPORTS`
Add a `<Country>RefreshJob` implementing
`worldenergydata.scheduler.jobs.base.AbstractJob` (`run(config) -> JobResult`,
`name`, `default_output_dir`) and register it in the `_LAZY_EXPORTS` dict of
`scheduler/jobs/__init__.py` (alongside `SodirRefreshJob`, `BseeRefreshJob`,
`BrazilAnpRefreshJob`, `EiaUsRefreshJob`, `UkcsRefreshJob`, …).

### (e) Source-refresh contract (#462)
Add the new source to the data-completeness governance contract
(`scripts/audit/validate_source_refresh_contract.py`). This is orthogonal to
`AbstractJob` — it governs freshness/completeness of the refreshed data, not the
job wiring.

### (f) Conformance registry
Add the country to `tests/unit/fdas/adapters/test_conformance.py`
`_REGION_FIXTURES` (a representative `(field_name, year, oil, gas)` tuple keyed by
region). The suite then deterministically validates the transform contract for
the new country against a committed synthetic fixture (no live fetch / no repo
data). `tests/unit/fdas/adapters/test_registration_checklist.py` (Suite E) then
guards that the region keys and adapter `region` attributes stay consistent.

## Consumed vs. deferred
Production is consumed now (drives monthly cashflow). Wells / drilling-timeline
inputs are **deferred to #783** — `STANDARD_COLUMNS` cannot carry them. When a
drilling timeline is absent, the cashflow engine's honesty guard emits a WARNING
("drilling CAPEX is 0") so the silent-zero case is visible rather than hidden;
the number is still `0`.
