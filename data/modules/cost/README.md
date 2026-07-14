# `cost` data module

**Issue:** [#844](https://github.com/vamseeachanta/worldenergydata/issues/844) — living cost-basis time-series for field-development economics.

The cost components used in offshore field economics, traced **through time**, with
a source citation on every figure. Built to supersede the single-point cost deck in
`docs/modules/bsee/analysis/production/FDAS_V30/lease_assumptions.xlsx`, which is a
frozen assumption set rather than a sourced, time-varying basis.

## Datasets

| File | What it is |
|---|---|
| `curated/cost_component_timeseries.csv` | `year × cost-component × band` — rig and vessel day rates, SURF lump-sum awards, and the CPI/PPI/oil reference series. One row per (year, component, source). |
| `curated/sanctioned_projects.csv` | Deepwater projects with disclosed FID CAPEX and scope — the **top-down anchor** the bottom-up component series is cross-checked against. |
| `curated/COST_COMPONENT_TIMESERIES.md` | Provenance doc for the component series. |
| `curated/SANCTIONED_PROJECTS.md` | Provenance doc for the project table. |

## The one rule

> **A figure without a source is a TODO row, not a guess.**

This is enforced by the schema (`worldenergydata.cost.timeseries.schema.CostObservation`),
not by discipline. A `todo` row **cannot** carry a value; a `sourced` row **cannot**
lack a citation. The CSVs are re-validated on read, so they can safely be hand-edited
in a spreadsheet — a row with a number but no source will fail loudly on the next build
rather than quietly entering the deck.

## Columns you must not ignore

**`PROVENANCE`** — `sourced` / `fitted` / `allocated` / `assumed` / `todo`. Only
`sourced` rows were read off a citable page. Everything else is derived, and says so.

**`FIGURE_TYPE`** — the difference between a contractor's backlog-weighted
`fleet_average` and a market-clearing `single_fixture`. These diverge violently in a
downturn: Transocean's ultra-deepwater fleet average read **$484k in Q1-2016 while its
own new fixtures were signing at $170k**, because stacked rigs are excluded from the
average and legacy contracts persist for years. **Never average across figure types.**

**`CURRENCY`** — mostly USD, but the Seabrokers North Sea spot rates are **GBP** and are
stored unconverted (no source states an FX rate; inventing one would inject an unsourced
number). Filter on this column before aggregating.

**`PRICE_BASIS` / `BASIS_YEAR`** — `nominal` (money-of-the-day) vs `real` (deflated).
A `real` figure without a basis year is meaningless, so the schema forbids it.

## Refresh

This is a **living** dataset. See
[`docs/modules/cost/REFRESH_PROCEDURE.md`](../../../docs/modules/cost/REFRESH_PROCEDURE.md)
for sources, cadence and the re-run command.

```bash
uv run python scripts/cost/seed_cost_timeseries.py       # re-pull reference series, rewrite CSVs
uv run python scripts/cost/build_cost_basis_report.py    # rebuild the report
```

## Report

`reports/cost/cost_basis_timeseries.html` — single-file, no external fetches, with the
trend charts, the inflation-normalization and back-allocation formula cards, and
colour-coded provenance.
