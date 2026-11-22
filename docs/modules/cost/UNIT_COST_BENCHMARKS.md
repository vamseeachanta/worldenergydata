# Project unit-cost benchmarks

The analysis groups disclosed project CAPEX intensities in constant 2026 USD.
Each group gives empirical P10/P50/P90, the independent project count and the
project IDs behind the statistics. A group with fewer than five projects carries
`indicative_only=true`. That threshold is a reporting rule, not a confidence test.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-11-12 | Define project intensities, source lineage and fail-closed input requirements. |
| Interface update | 2026-11-12 | Reconcile upstream crosswalk and escalation tables, retain unmatched reasons, add depth marginals and preserve numeric CSV precision. |
| Bound and provenance correction | 2026-11-12 | Exclude curated lower and upper bounds anywhere in the basis and reject derived tables that disagree with an available nominal source. |
| Bound matching | 2026-11-13 | Normalise separators and match lower and upper bounds in any case and position, with negation, so separator and case variants are not treated as point costs. |

Table 1. Method edition history.

## Run and required inputs

Run from the repository root in the installed workspace environment:

```bash
uv run python -m worldenergydata.cost.benchmarks benchmarks \
  --data-dir data/modules/cost/curated \
  --projects data/modules/cost/curated/sanctioned_projects_2026.csv \
  --output-dir reports/cost --report-date 2026-11-12
```

The command writes `unit_cost_benchmarks.csv` and `unit_cost_benchmarks.html`.
It validates the inputs and renders the HTML before creating either output.
An input error exits nonzero and preserves any earlier reports. No nominal mode
or silent nominal fallback is implemented.
If no valid benchmark row remains, the command exits 2 with exclusion counts
before writing either file. An individual emptied cohort does not abort other
cohorts. Exit 2 also covers input validation and command-line usage errors.

The owning dataset remains the curated cost register. No cost is researched,
imputed or invented by this module. The input files are:

- `sanctioned_projects.csv`: the existing sanctioned-project schema plus
  `CAPEX_USD_MM_2026`, `INDEX_USED`, `INDEX_BASE_YEAR`, `ESCALATION_FACTOR`.
  A missing escalation column prevents report generation. An individual missing
  or invalid cost or lineage value excludes that project with a reason.
  `--projects` explicitly selects a complete alternative table, such as the
  upstream derived `sanctioned_projects_2026.csv`. When a separate nominal
  `sanctioned_projects.csv` is present, every selected row shall carry
  `PROJECTS_SHA256` matching its UTF-8/LF-normalized SHA-256 and
  `INPUT_DIGEST_BASIS=sha256_utf8_lf`. Missing, invalid or mismatched provenance
  stops generation before either output is written. The nominal table is read
  only for this correspondence check and input hashing; its columns and values
  never replace derived inputs. Without the nominal table, source correspondence
  cannot be checked; the selected table's own input digest still is recorded.
- `cost_project_identity.csv`: active project IDs and exact
  `sanctioned_projects.csv` locators of the form `PROJECT=<project>`.
  An explicit `PROJECT_ID` on the project row must agree with the registry and
  crosswalk cost ID when present. Without an opaque ID, an exact crosswalk
  locator supplies the comparable ID. Projects lacking both forms are listed
  with an exclusion reason. Duplicate registry locators remain fatal. Repeated
  project-table IDs exclude every affected row from both views; the alternatives
  and their supplied costs are listed, with no cost selected or averaged. A
  derived table containing both sanctioned and actual labels therefore does
  not mix those alternatives into a benchmark.
- `project_field_crosswalk.csv`: the merged schema uses `PROJECT_ID` as a
  `PROJECT:<project>` locator, optional `COST_PROJECT_ID`, `PROJECT`,
  `CATALOG_FIELD_ID`, `MATCH_METHOD`, `CONFIDENCE`, `PROVENANCE`, `EVIDENCE`
  and `REASON`. Locators match the project name exactly after stripping string
  ends; case and interior whitespace are unchanged. Conflicting IDs or competing
  name/ID joins stop the run. A row found by cost ID whose locator does not match
  the source name is excluded with that explicit reason. Legacy opaque
  `PROJECT_ID` keys remain supported. Crosswalk/quantity lineage on the project
  table cannot substitute for the authoritative evidence tables.
  Headers are case-insensitive. `CATALOG_FIELD_IDS`,
  `CATALOG_FIELD_ID`, `FIELD_IDS` and `FIELD_ID` are explicit aliases for the field
  ID column. One row per project is required; multiple field IDs may be carried
  in that row. Duplicate keys are rejected as ambiguous. An explicit `unmatched`
  method with a nonempty `REASON` and no field ID retains the sourced cost;
  its reason is shown in the comparables table. Inconsistent unmatched rows and
  missing matched-field evidence exclude the affected project. Field matching
  does not supply or alter grouping categories. The crosswalk file itself is
  mandatory; its absence prevents output creation.
- `project_asset_requirements.csv`: a tree count uses one disclosed row per
  project, with `ASSET_TYPE` equal to `subsea tree` or `wet tree`,
  `QUANTITY_UNIT=tree`, positive `QUANTITY`, `SOURCE_URL` and `SOURCE_LOCATOR`.
  Multiple candidate rows are excluded as ambiguous rather than summed. Dry
  trees, estimated quantities and well counts never substitute for subsea trees.

Escalation and crosswalk methods remain upstream inputs. An absent derived
table or its missing escalation columns stop generation; the existence of a
file alone does not establish the quality or completeness of its disclosures.

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
The HTML also provides a separate depth-only marginal view for each metric.
This view combines regions and development/host descriptions without inferring
category mappings. Missing depth remains `unknown`. Each project is counted
once per metric in each view; marginal rows are absent from the contracted CSV
and shall not be added to exact-cohort counts.

A project contributes at most once to each metric. Missing, nonpositive or
non-finite quantities exclude only that metric, with the reason retained in the
HTML. Missing source, escalation or invalid crosswalk lineage excludes all its metrics.
Missing source values remain missing; zero is not a replacement.
An explicit unmatched field is not missing cost provenance.

Disclosed lower and upper bounds are excluded from point percentiles. Before
matching, whitespace, underscores, hyphens and dashes in `CAPEX_BASIS` collapse to
one space. The declared rule then matches:

- `lower bound`, `upper bound` (also without a separator, as in `LOWERBOUND`) and
  `in excess of` anywhere in the basis, case-insensitive;
- the uppercase whole token `FLOOR` anywhere in the basis;
- a leading `floor` in any case that is followed by nothing or by a character
  other than a letter, digit, underscore, hyphen or dash, such as `Floor;`,
  `FLOOR:` or `Floor area`;
- a leading `at least`, case-insensitive.

Negation never turns this vocabulary into a point cost. `not in excess of`
states a maximum and is an upper bound. Where `not`, `not a` or `not an`
precedes `lower bound`, `upper bound` or the uppercase token `FLOOR` (for
example `NOT A FLOOR`), the basis cannot be classified from the text: the
project is excluded with that reason for source review and is not used as a
point cost. Lowercase `floor` elsewhere, lowercase `floor-mounted`, `FLOORING`
and `UPPER BOUNDARY` do not match the vocabulary. The rule also matches some
equipment wording: uppercase `FLOOR-MOUNTED` or `FLOOR_MOUNTED` normalises to
the token `FLOOR`, and a leading `floor plan` or `Floor area` matches the
leading-floor rule. Those projects are excluded with the bound reason shown,
not silently included. A bound is not converted
to a point estimate. Reasons and exclusion counts appear in the HTML. Other free-text
qualifications remain subject to source review; this vocabulary does not
establish that every bound has been identified or predict the effect of
exclusion on a percentile.

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
CSV floats retain round-trip numeric precision for downstream calculations;
only HTML figures use one decimal place, with scientific notation for positive
figures that would otherwise round to zero. Source numerators, quantities and
index metadata retain their supplied precision separately for traceability.

The CSV columns are exactly:

```text
metric,unit,water_depth_band,region,development_type,host_type,n,p10,p50,p90,indicative_only,comparables,cost_basis
```

`comparables` contains sorted project IDs separated by semicolons;
`cost_basis=USD_2026`. The HTML lists every observation's numerator,
denominator column, quantity, index metadata, field linkage, accounting basis
and cost/quantity sources, including `ESCALATION_NOTE` qualifications and
unmatched crosswalk reasons. It includes exclusion reasons, raw-input SHA-256
digests, and a facts digest. An edition date or hash does not establish source
freshness or upstream correctness.
The selected project-table basename is shown beside the input digests; an
explicit alternative table is hashed under `projects_table`.
An available separate nominal source is hashed under `nominal_projects_table`.
Its raw input digest is checked before and after calculation; the correspondence
check uses universal-newline normalization, matching the upstream escalation
table's `sha256_utf8_lf` convention.
Input-byte digests are compared before and after loading and calculation;
a detected change prevents output. This is a stability check, not an atomic
snapshot against a writer that changes and restores bytes between reads.
Identity registry locators for the canonical sanctioned table are joined to
an explicitly selected derived table by exact project name; that correspondence
remains an upstream contract rather than an independent source reconciliation.

## Reuse and limits

The implementation extends `reporting.benchmark_report` with
`percentile_summary` for unit-cost grouping. The existing `_cohort_summary`
retains `statistics.median` and its established floating-point arithmetic.
Existing `_table`, `_source_links` and `facts_digest` handle
escaped tables, cited links and reproducible facts. From `timeseries.dataset`
the module imports only `SANCTIONED_CSV_COLUMNS`; it does not call
`read_sanctioned_csv`, because that reader coerces quantities eagerly. The
module duplicates the sanctioned-table metadata validation (numeric fields,
access date, confidence, source priority and the CAPEX-basis requirement) on
raw text. A change to the typed reader's validation is not inherited and must
be repeated here; no parity test binds the two.

Rows with `SCOPE_IS_OFFSHORE_ONLY=False` are not filtered: they contribute to
the percentiles alongside offshore-only rows, and the flag is shown per
comparable in the HTML.

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
