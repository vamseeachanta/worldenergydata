# worldenergydata-fdas

Source-agnostic **Field Development Analysis System (FDAS)** economics engine
for the `worldenergydata` namespace — NPV / MIRR / IRR, monthly cashflow
modelling, and a **country fiscal-terms deck layer**.

Carved out of the `worldenergydata-bsee` cluster in #714 so that non-US data
sources can run field economics without importing the US-Gulf-of-Mexico `bsee`
cluster. The import path is unchanged: `import worldenergydata.fdas`.

```python
from worldenergydata.fdas import (
    calculate_npv, calculate_all_metrics, AssumptionsManager,
    get_fiscal_terms, FiscalTerms,
)
from worldenergydata.fdas.analysis.cashflow import CashflowEngine

# Deckless (legacy US-GoM assumptions path — unchanged behavior):
engine = CashflowEngine(AssumptionsManager(), dev_system="subsea15")

# Deck-driven (country fiscal terms):
terms = get_fiscal_terms("norway")            # royalty regime for the NCS
engine = CashflowEngine(AssumptionsManager(), dev_system="subsea15",
                        fiscal_terms=terms)
```

## Fiscal-terms decks

Decks ship as package data under `worldenergydata/fdas/fiscal/decks/*.yml` and
are loaded fail-closed via `get_fiscal_terms(country)`. Shipped decks are
`us_gom`, `norway`, `uk`, and `brazil`. The schema also accepts caller-authored
`sliding_scale` decks with validated production-rate bands.

The Brazil deck requires an explicit concession contract rate. Its daily-rate
bands are **not** taken from the illustrative Brazil analysis model. See
[the royalty-only worked example](#brazil-royalty-only-worked-example).

### Consumed vs. declarative (v1)

Only the **royalty** layer is consumed by the cashflow engine in v1. Every other
field is declarative provenance/metadata — readable, validated, but **not** yet
wired into revenue/NPV (that seam is #716). This is what makes exact parity with
the pre-carve BSEE path provable: the `us_gom` deck overrides royalty only.

| Field | Status | Notes |
|---|---|---|
| `royalty.model` | **Consumed** | `flat`: per-dev-system rate; `none`: zero; `sliding_scale`: production bands; `contractual`: required caller rate |
| `royalty.rate_by_dev_system` | **Consumed** | exact keys `{dry, subsea15, subsea20, default}`, each in `[0,1]` |
| `royalty.bands` | **Consumed** | `sliding_scale` only: ordered inclusive `max_rate_bpd` thresholds and fractional `rate`, ending with a null threshold |
| `country` | **Consumed** | deck identity / lookup key |
| `price_marker` (`wti`/`brent`/`gas_hh`/`gas_ttf`) | Declarative | revenue seam → #716 |
| `currency` | Declarative | engine is USD-denominated in v1 |
| `discount_rate` | Declarative | NPV discount seam → #716 |
| `income_tax` (CIT/SPT/EPL/…) | Declarative | after-tax seam → #716 (e.g. Norway 78%) |
| `source_url`, `source_ref`, `revision`, `effective_date`, `schema_version` | Provenance | required, machine-verifiable, non-empty |

### Royalty-rate resolution precedence

`sliding_scale` requires a finite, nonnegative `production_rate_bpd_monthly`
entry for every revenue month. The first inclusive threshold selects one rate
for the whole month's revenue, rather than marginal rates on production slices.
An explicit flat-rate argument cannot bypass the band selection. Full monthly
cashflow generation derives the rate from monthly oil barrels divided by that
month's calendar days, including leap years. Results record
`production_rate_basis = "calendar-day average per month"`.

`contractual` requires an explicit finite fractional `royalty_rate` in
`calculate_royalty` or `generate_monthly_cashflow`. A missing or invalid rate
raises even for an empty revenue mapping; no legacy assumption supplies it.
The generic fraction interval is a mathematical constraint, not validation of
a jurisdiction's contract. Callers shall establish the applicable contract rate.

For `flat`, `none`, and deckless paths, precedence is explicit `royalty_rate`
argument → deck → legacy `AssumptionsManager` ROYALTY_RATE. With no deck and
no override, the legacy behavior is preserved.

## Brazil royalty-only worked example

The source basis is [Lei 9.478/1997, art. 47](https://www.planalto.gov.br/ccivil_03/leis/l9478.htm)
and [Decreto 2.705/1998, arts. 11–12](https://www.planalto.gov.br/ccivil_03/decreto/d2705.htm).
The latter defines monthly field royalties from production and reference prices,
with the percentage specified in the concession contract. These provisions do
not prescribe the legacy model's daily production-rate bands.

The following synthetic oil-only screening example assumes a contract at the
statutory base percentage. It does not establish a particular field's terms.
Monthly volume and price are explicit demonstration inputs. Hand calculation:
29,000 bbl × 20 USD/bbl = 580,000 USD revenue; 580,000 × 0.1 = 58,000 USD
royalty. This is a royalty-only result on supplied sales value.

```python
from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.fdas.fiscal import get_fiscal_terms

# Synthetic demonstration inputs; independent arithmetic is written above.
volume_bbl = 29_000
price_usd_per_bbl = 20
# Lei 9.478/1997, art. 47, caput: statutory base, assumed contract for this example.
contract_rate = 0.1
engine = CashflowEngine(AssumptionsManager(), fiscal_terms=get_fiscal_terms("brazil"))
royalties = engine.calculate_royalty(
    {"2024-02": volume_bbl * price_usd_per_bbl}, royalty_rate=contract_rate
)
assert royalties == {"2024-02": 58_000}
print(royalties)  # {'2024-02': 58000.0}
```

For monthly projections, supply `royalty_rate=contract_rate` to
`generate_monthly_cashflow`. Its oil/gas revenues use supplied sales prices;
no statutory reference-price or currency conversion is performed. Existing
cost defaults remain screening assumptions. A sales-value example is not a
statutory payment calculation or an after-tax project valuation.

**NOT_EVALUATED:** special participation, corporate income tax, PSC profit oil,
statutory reference-price valuation and local-currency payment. Special
participation requires quarterly net revenue, fiscal production volume,
production year, location and applicable deductions under
[Decreto 2.705/1998, art. 22](https://www.planalto.gov.br/ccivil_03/decreto/d2705.htm).
These inputs and a qualified calculation are required before full fiscal
acceptance. Missing evidence is not represented as zero tax.

The existing Brazil-band parity test establishes software compatibility with
an illustrative model only. Full fiscal parity is not established and the
illustrative bands are excluded from the shipped Brazil deck. Follow-up work
belongs to [the Brazil chain](https://github.com/vamseeachanta/worldenergydata/issues/718).

## F2 country adapter contract (#715)

The source-adapter interface that feeds these decks. It bridges the repo's
existing per-country production adapters
(`worldenergydata.production.unified` — `AbstractProductionAdapter`, 8 country
implementations) into FDAS, with two entry points:

```python
from worldenergydata.fdas.adapters.contract import to_fdas_production
from worldenergydata.fdas.adapters.field_concept_normalizer import (
    FieldMapEntry, FieldMetaMapping, to_field_concept, number_from, year_from,
)
```

- **`to_fdas_production(unified_df)`** — normalizes a unified `STANDARD_COLUMNS`
  frame (`region, field_name, year, month, oil_bbl, gas_mcf, water_bbl, …`) to
  the canonical FDAS monthly-production schema the cashflow engine reads:
  `YEAR_MONTH, DEV_NAME, MONTHLY_OIL_BBL, MONTHLY_WATER_BBL, MONTHLY_GAS_MCF`
  (the `_BBL`/`_MCF` columns, **not** the legacy `bsee_adapter`
  `MONTHLY_*_VOLUME`). A pure pandas leaf — no `field_development` import.
- **`to_field_concept(meta, mapping)` / `FieldMetaMapping`** — maps a country
  regulator's field-metadata dict → a validated
  `field_development.models.FieldConcept` for concept screening. A
  `FieldMetaMapping` is `{fieldconcept_field: FieldMapEntry(source_key,
  transform)}` carrying per-field callables (`number_from`, `year_from`,
  `fluid_from_reserve_type`, `reduce_concept_type`) so no `subseaiq` logic is
  lost; targets are validated against `FieldConcept` at construction.

### Consumed vs. deferred

Production is **consumed now** — `to_fdas_production` output drives monthly
cashflow. Wells / drilling-timeline inputs are **deferred to #783**
(`STANDARD_COLUMNS` cannot carry them). When a drilling timeline is absent the
cashflow engine's empty-timeline **honesty guard** emits a WARNING
("drilling CAPEX is 0") so the silent-zero-drilling-CAPEX case is visible; the
value is still `0`.

Onboarding a new country: see
[`docs/modules/fdas/country-adapter-checklist.md`](../../docs/modules/fdas/country-adapter-checklist.md).

## Handoff

Country fiscal-terms coverage expands per the international field-development
epic (#713): per-country chains build on this deck layer. The after-tax /
price-marker seams (#716) and Brazil sliding-scale royalty (#718) are the next
consumers. See #715 for the source-adapter interface that feeds these decks.
