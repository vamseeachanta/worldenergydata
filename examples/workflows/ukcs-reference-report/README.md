# UKCS reference-chain analysis

The offline example runs raw NSTA-shaped synthetic inputs through the existing
production loader, unified adapter, FDAS production conversion, concept screen
and pre-tax cashflow chain. The HTML is self-contained; production charts are
inline SVG. No HTTP request is made by the CSV workflow.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Add a reproducible fixture example and an explicit live-cache template. |

Table 1. Example revision history.

## Inputs, method and answer

The CSV is invented, with one synthetic field and twelve monthly rows in 2024.
Each row supplies 100 tonnes of oil, 10 thousand standard cubic metres of
associated gas, 2 thousand standard cubic metres of dry gas and 20 cubic metres
of water. The scenario supplies a water depth of 100 metres and an oil price of
75 USD/bbl. These are example inputs, not measured field data or forecasts.

The existing loader uses the repository conversion registry in
`packages/worldenergydata-core/src/worldenergydata/common/units.py`, revision
`d867ba1e`, classes `OilUnits`, `GasUnits` and `WaterUnits`. Its generic oil mass
factor is an approximation, not a measured field density. No new engineering
coefficient or acceptance limit is introduced by this report.

Independent hand calculation for the worked example:

- Monthly oil: 100 tonnes × 7.33 bbl/tonne = 733.0 bbl.
- Annual oil: 12 × 733.0 = 8,796.0 bbl.
- Gross oil revenue: 8,796.0 × 75 = 659,700.0 USD, pre-tax.
- Monthly gas: (10 + 2) × 35.3147 = 423.8 Mcf, displayed to one decimal.
- Monthly water: 20 × 6.2898 = 125.8 bbl, displayed to one decimal.

The conversion-factor basis is the repository registry cited above. These checks
verify arithmetic against that existing convention; they do not independently
validate the physical conversion factors. The raw schema and units are described
by the [NSTA PPRS service metadata](https://services-eu1.arcgis.com/OZMfUznmLTnWccBc/arcgis/rest/services/UKCS_hydrocarbon_field_production_reports_PPRS_points_(WGS84)/FeatureServer/0?f=pjson)
and its [dataset description](https://www.arcgis.com/sharing/rest/content/items/dd38204275a04618ab7ddd00f87224e3?f=pjson),
observed on 2026-10-20. Oil is reported there in tonnes, gas in thousand standard
cubic metres, and water in cubic metres.

Monthly reporting-unit rows are summed by period. Selected rows, selected
months, first/last period, source row/field counts and the raw-input SHA-256
remain in the facts JSON. The example is always labelled `fixture` even though
the adapter uses the tag `nsta` for normalized rows.

## Regeneration

From the repository root with the workspace dependencies available:

```sh
uv run --frozen python -m worldenergydata examples/workflows/ukcs-reference-report/input.yml
uv run --frozen python -m worldenergydata.ukcs.report
```

The first command regenerates the example HTML and facts JSON in `outputs/`.
The second regenerates `reports/ukcs_reference/index.html` and `_facts.json`.
UTC generation timestamps change; the input digest and calculated values remain
reproducible. Output paths are taken from the engine's configured result root.
Programmatic embedding requires the engine's normal `default` configuration and
an explicit result root; the router does not write outside that result root.

## Opt-in live source

`input_live.yml` is a template, excluded from the offline workflow registry.
Replace `REPLACE_WITH_FIELD` with a field present in the bounded source extract,
choose the reporting year and scenario price, and supply field metadata only
where evidence is available. Missing water depth stays missing; inherited
screening and cost assumptions remain unqualified.

```sh
uv run --frozen python -m worldenergydata examples/workflows/ukcs-reference-report/input_live.yml
```

The live configuration requires an explicit cache directory, a positive record
bound per year, a year or unique year list, and an explicit field selection.
`force_refresh: true` invokes the existing NSTA client refresh seam; `false`
reuses its cache. Cache filenames follow the client's monthly convention.
Raw CSV and parquet files are ignored and are not report deliverables. Exact raw
bytes are retained in digest-named CSV snapshots inside the cache directory;
these support repeatable analysis after the mutable year cache is refreshed.

The report reads the retained cache back, records its SHA-256 and modification
time in UTC, and requires the cache evidence plus normalized source tags before
showing `nsta_live`. Cache modification time is a local cache-write timestamp,
not a regulator publication date. For multiple years, the oldest cache timestamp
bounds freshness. A cached bounded extract remains partial even when a larger
bound is later requested; use forced refresh when changing the bound.
Full field or UKCS coverage is never inferred from these extracts.

A bounded current-year source request was opened on 2026-10-20. The retained
24-row response passed the existing client's cache-read path and the full
report chain for a selected seven-month history. This verifies a freshly
collected cache-to-report path, not the client's network pagination. No live
source payload or derived live report is included in this example.

## Sources and limitations

The source licence is identified in the issue as **NSTA Open User Licence**.
The proposed official open-data licence page returned HTTP 404 at the time of
inspection, and the ArcGIS dataset description contained no licence terms.
Current reuse rights are therefore not independently established here. The
committed data and reports contain synthetic example inputs only. Confirm the
current terms with [NSTA](https://www.nstauthority.co.uk/) before redistributing
live extracts. The shared source catalogs were unavailable in this checkout;
no catalog source identifier or engineering readiness is claimed.

The concept screen is a sparse-metadata wiring demonstration, not a field
recommendation. Its heuristic weights and inherited cashflow costs are assumed,
based on previous experience; applicability is `NOT_EVALUATED`. The chain has no
drilling capital schedule. Gas revenue, after-tax fiscal treatment and UK
investment economics are `NOT_EVALUATED`. The pre-tax net cashflow is incomplete.
After-tax treatment remains tracked by issue 736; citation sidecar adoption
remains tracked by issue 361.

## Tests

The report tests cover aggregation, strict JSON, missing values, HTML escaping,
provenance rejection and self-containment. Workflow tests prohibit HTTP and use
a fake NSTA client to check cache readback, required inputs, empty selections,
invalid production, output containment and embedded engine execution. The two
registry tests exercise the offline engine and module command.
