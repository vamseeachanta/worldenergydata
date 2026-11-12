# Project unit-cost benchmarks

The analysis groups disclosed project CAPEX intensities in constant 2026 USD.
Each group gives empirical P10/P50/P90, the independent project count and the
project IDs behind the statistics. A group with fewer than five projects carries
`indicative_only=true`. That threshold is a reporting rule, not a confidence test.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-11-12 | Define project intensities, source lineage and fail-closed input requirements. |

Table 1. Method edition history.

## Run and required inputs

Run from the repository root in the installed workspace environment:

```bash
uv run python -m worldenergydata.cost.benchmarks benchmarks \
  --data-dir data/modules/cost/curated \
  --output-dir reports/cost --report-date 2026-11-12
```

The command writes `unit_cost_benchmarks.csv` and `unit_cost_benchmarks.html`.
It validates the inputs and renders the HTML before creating either output.
An input error exits nonzero and preserves any earlier reports. No nominal mode
or silent nominal fallback is implemented.

The owning dataset remains the curated cost register. No cost is researched,
imputed or invented by this module. The input files are:

- `sanctioned_projects.csv`: the existing sanctioned-project schema plus
  `CAPEX_USD_MM_2026`, `INDEX_USED`, `INDEX_BASE_YEAR`, `ESCALATION_FACTOR`.
  A missing escalation column prevents report generation. An individual missing
  or invalid cost or lineage value excludes that project with a reason.
- `cost_project_identity.csv`: active project IDs and exact
  `sanctioned_projects.csv` locators of the form `PROJECT=<project>`.
  An explicit `PROJECT_ID` on the project row takes precedence and must agree
  with the registry when both are present. Unregistered projects are listed by
  name with an exclusion reason. Duplicate identities are rejected; project
  names are never matched fuzzily.
- `project_field_crosswalk.csv`: `PROJECT_ID`, `CATALOG_FIELD_IDS`,
  `MATCH_METHOD`, `CONFIDENCE`, `EVIDENCE`. Headers are case-insensitive.
  `CATALOG_FIELD_ID`, `FIELD_IDS` and `FIELD_ID` are explicit aliases for the field
  ID column. One row per project is required; multiple field IDs may be carried
  in that row. Duplicate rows are rejected as ambiguous. Missing field matching
  or evidence excludes the affected project. The crosswalk file itself is
  mandatory; its absence prevents output creation.
- `project_asset_requirements.csv`: a tree count uses one disclosed row per
  project, with `ASSET_TYPE` equal to `subsea tree` or `wet tree`,
  `QUANTITY_UNIT=tree`, positive `QUANTITY`, `SOURCE_URL` and `SOURCE_LOCATOR`.
  Multiple candidate rows are excluded as ambiguous rather than summed. Dry
  trees, estimated quantities and well counts never substitute for subsea trees.

The base revision lacks `CAPEX_USD_MM_2026` and
`project_field_crosswalk.csv`. Real output is therefore not established.
After [the escalation input](https://github.com/vamseeachanta/worldenergydata/issues/1896)
and [the field crosswalk](https://github.com/vamseeachanta/worldenergydata/issues/1898)
are merged, the command above will exercise their actual interface. Those
upstream files and their methods are outside this implementation's scope.

## Quantities, units and grouping

| Metric | Quantity column | Calculation | Output unit |
| --- | --- | --- | --- |
| `capex_per_well` | `sanctioned_projects.WELL_COUNT` | CAPEX / wells | `USD_MM_2026/well` |
| `capex_per_tree` | `project_asset_requirements.QUANTITY` | CAPEX / disclosed subsea trees | `USD_MM_2026/tree` |
| `capex_per_surf_km` | `sanctioned_projects.SURF_KM` | CAPEX / SURF length | `USD_MM_2026/km` |
| `capex_per_kboed` | `sanctioned_projects.PEAK_PRODUCTION_BOEPD` | CAPEX / (boe/d / 1000) | `USD_MM_2026/kboe/d` |
| `capex_per_boe` | `sanctioned_projects.RECOVERABLE_RESOURCE_MMBOE` | CAPEX / resource in MMboe | `USD_2026/boe` |

Table 2. CAPEX is supplied in USD million at the 2026 price basis; the two
million multipliers cancel for the resource intensity.

Every group has the exact key `(water_depth_band, region, development_type,
host_type)`. Region and development/host types are retained as supplied; absent
values become `unknown`. No aliases or inferred host types are applied.
Water depth follows the existing `WaterDepthBand` categories: shallow at
0–300 m, mid above 300 through 1000 m, deep above 1000 through 2000 m and
ultra-deep above 2000 m. Missing, invalid or negative depths are `unknown`.

A project contributes at most once to each metric. Missing, nonpositive or
non-finite quantities exclude only that metric, with the reason retained in the
HTML. Missing source, escalation or crosswalk lineage excludes all its metrics.
Missing source values remain missing; zero is not a replacement.

## Percentiles and reporting precision

For ascending values `x`, the interpolation position is `h = (n - 1) * p`.
P10, P50 and P90 interpolate between the surrounding ranks at `p=0.1`, `0.5`
and `0.9`. The shared reporting helper uses Python `statistics.quantiles` with
`method="inclusive"`. A singleton has three equal percentiles; an empty sample
has no statistic. These are ascending empirical cost percentiles, not resource
exceedance probabilities or model uncertainty bounds.

The invented test fixture has per-well values `[10, 20, 30, 40, 100]`.
Its P10/P50/P90 are `14.0`, `30.0` and `76.0`. No fixture value is engineering
input. Each project has equal weight. Percentiles are calculated before rounding;
CSV and HTML figures are published to one decimal place, with scientific
notation for positive figures that would otherwise round to zero. Source quantity and
index metadata remain identified separately for traceability.

The CSV columns are exactly:

```text
metric,unit,water_depth_band,region,development_type,host_type,n,p10,p50,p90,indicative_only,comparables,cost_basis
```

`comparables` contains sorted project IDs separated by semicolons;
`cost_basis=USD_2026`. The HTML lists every observation's numerator,
denominator column, quantity, index metadata, field linkage, accounting basis
and cost/quantity sources. It includes exclusion reasons, raw-input SHA-256
digests, and a facts digest. An edition date or hash does not establish source
freshness or upstream correctness.

## Reuse and limits

The implementation extends `reporting.benchmark_report` with
`percentile_summary` and reuses it in the existing `_cohort_summary` and the new
unit-cost grouping. Existing `_table`, `_source_links` and `facts_digest` handle
escaped tables, cited links and reproducible facts. `timeseries.dataset` supplies
`read_sanctioned_csv`, including its existing CAPEX-basis validation.

`calibration.observed_benchmark.benchmark_observed_costs` compares observations
with supplied proxies using mean, bias and RMSE. It does not calculate project
intensity percentiles and is not duplicated or changed by this module.

These ratios divide total project CAPEX by a scope quantity. They do not
represent the purchase price of a well, tree or SURF component. Exact statistical
groups do not establish accounting equivalence: gross/net ownership, phase
boundaries, leased facilities, integrated onshore costs, disclosure dates and
resource definitions may differ. The supplied accounting and offshore-only
bases remain visible per comparable; no allocation or ownership conversion is
performed. Grouping is descriptive and does not qualify a project estimate.

Upstream index selection, escalation arithmetic, field matching and underlying
source contents are not independently verified here. Acceptance of a particular
engineering estimate requires those inputs and comparable accounting/scope
bases to be established.
