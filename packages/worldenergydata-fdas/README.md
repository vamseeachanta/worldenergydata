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
are loaded fail-closed via `get_fiscal_terms(country)`. Available decks include
`us_gom`, `norway`, `uk` and the scoped `australia` screening deck.
**Brazil is deferred to #718** (its sliding-scale
royalty needs a production-rate seam `calculate_royalty` does not yet expose;
the loader rejects `model: sliding_scale` with a pointer to #718).

### Consumed vs. declarative (v1)

The cashflow engine consumes the **royalty** layer. The `gas_au` price marker
also requires an explicit gas deck; other markers remain declarative. Other
fields are provenance/metadata, with revenue/NPV integration tracked in #716.
This is what makes exact parity with the pre-carve BSEE path provable: the `us_gom` deck overrides royalty only.

| Field | Status | Notes |
|---|---|---|
| `royalty.model` (`flat` \| `none`) | **Consumed** | `flat` → per-dev-system rate; `none` → 0.0 |
| `royalty.rate_by_dev_system` | **Consumed** | exact keys `{dry, subsea15, subsea20, default}`, each in `[0,1]` |
| `country` | **Consumed** | deck identity / lookup key |
| `price_marker` | `gas_au` requires explicit gas pricing | Other markers remain declarative |
| `currency` | Declarative | engine is USD-denominated in v1 |
| `discount_rate` | Declarative | NPV discount seam → #716 |
| `income_tax` (CIT/SPT/EPL/…) | Declarative | after-tax seam → #716 (e.g. Norway 78%) |
| `source_url`, `source_ref`, `revision`, `effective_date`, `schema_version` | Provenance | required, machine-verifiable, non-empty |

### Royalty-rate resolution precedence

`CashflowEngine.calculate_royalty` resolves the rate as: explicit `royalty_rate`
argument → `fiscal_terms` deck → legacy `AssumptionsManager` ROYALTY_RATE. With
no deck (`fiscal_terms=None`) the behavior is **byte-identical** to the
pre-carve engine.

## Australian gas marker

`get_fiscal_terms("australia")` selects `gas_au`. Monthly cashflow requires an
explicit gas deck in USD/Mcf, independently of the oil deck. To normalize a
supplied Australian marker quoted in AUD/GJ:

```python
from worldenergydata.fdas.fiscal.gas_prices import au_gas_prices_usd_per_mcf

# All mappings use identical YYYY-MM keys and caller-supplied observations.
gas_prices = au_gas_prices_usd_per_mcf(
    monthly_marker_aud_per_gj,
    gj_per_mcf=monthly_heating_value_gj_per_mcf,
    usd_per_aud=monthly_fx_usd_per_aud,
)
terms = get_fiscal_terms("australia")
engine = CashflowEngine(AssumptionsManager(), "dry", fiscal_terms=terms)
# Pass gas_prices=gas_prices to engine.generate_monthly_cashflow(...).
```

The equation is `(AUD/GJ) * (GJ/Mcf) * (USD/AUD) = USD/Mcf`, applying quantity
calculus from the [BIPM SI Brochure, ninth edition (2019), section 5.4.1](https://www.bipm.org/documents/20126/41483022/SI-Brochure-9.pdf).
No heat-content factor, exchange rate, market quotation or escalation is
embedded. The caller selects the delivery market and compatible heat-content
and volume bases; the helper validates finite inputs and matching months.

The deck is a screening assumption for Commonwealth offshore permits without
a royalty obligation, with state waters and royalty-bearing permits excluded.
Historical context is the [Treasury PRRT Review, Final Report (2017), sections
6.1-6.3 and 6.5](https://treasury.gov.au/review/review-of-the-petroleum-resource-rent-tax/final-report).
The no-royalty scope is **assumed, based on previous experience**. Current
permit applicability, PRRT and company tax are **NOT_EVALUATED**. No discount
rate is supplied. The deck date records its review, not a legislative effective
date. Mixed streams continue to price oil separately. The Australian reference
chain still has no production source; this change does not add market-data or
production ingestion.

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
