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
are loaded fail-closed via `get_fiscal_terms(country)`. v1 ships three:
`us_gom`, `norway`, `uk`. **Brazil is deferred to #718** (its sliding-scale
royalty needs a production-rate seam `calculate_royalty` does not yet expose;
the loader rejects `model: sliding_scale` with a pointer to #718).

### Consumed vs. declarative (v1)

Only the **royalty** layer is consumed by the cashflow engine in v1. Every other
field is declarative provenance/metadata — readable, validated, but **not** yet
wired into revenue/NPV (that seam is #716). This is what makes exact parity with
the pre-carve BSEE path provable: the `us_gom` deck overrides royalty only.

| Field | Status | Notes |
|---|---|---|
| `royalty.model` (`flat` \| `none`) | **Consumed** | `flat` → per-dev-system rate; `none` → 0.0 |
| `royalty.rate_by_dev_system` | **Consumed** | exact keys `{dry, subsea15, subsea20, default}`, each in `[0,1]` |
| `country` | **Consumed** | deck identity / lookup key |
| `price_marker` (`wti`/`brent`/`gas_hh`/`gas_ttf`) | Declarative | revenue seam → #716 |
| `currency` | Declarative | engine is USD-denominated in v1 |
| `discount_rate` | Declarative | NPV discount seam → #716 |
| `income_tax` (CIT/SPT/EPL/…) | Declarative | after-tax seam → #716 (e.g. Norway 78%) |
| `source_url`, `source_ref`, `revision`, `effective_date`, `schema_version` | Provenance | required, machine-verifiable, non-empty |

### Royalty-rate resolution precedence

`CashflowEngine.calculate_royalty` resolves the rate as: explicit `royalty_rate`
argument → `fiscal_terms` deck → legacy `AssumptionsManager` ROYALTY_RATE. With
no deck (`fiscal_terms=None`) the behavior is **byte-identical** to the
pre-carve engine.

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
