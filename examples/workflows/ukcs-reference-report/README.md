# UKCS reference-chain report

This workflow runs the existing UKCS adapter, FDAS production bridge, sparse
concept screening and pre-tax cashflow chain. The registered workflow uses only
a bundled synthetic CSV and requires no network, credentials or licensed solver.
The report is self-contained HTML with inline CSS and Python-generated SVG.

## Offline regeneration

Run from the repository root in the declared workspace environment:

```bash
uv run --frozen python -m worldenergydata examples/workflows/ukcs-reference-report/input.yml
uv run --frozen python -m worldenergydata.ukcs.report
```

The first command writes `outputs/ukcs_reference_report_report.html` and
`outputs/ukcs_reference_report_facts.json` beside this input. The second writes
`reports/ukcs_reference/index.html` and `_facts.json`. Both use fixture provenance;
the module command always regenerates the offline fixture report.

The 12 CSV rows are hand-derived scenario inputs, not observations from Forties:
for month `m = 1..12` in 2024, oil mass is `1000 + 50*(m-1)` tonnes, associated
gas is `25 + 2*(m-1)` thousand standard cubic metres, dry gas is 5 thousand
standard cubic metres, and water is `100 + 10*(m-1)` cubic metres. The 128 m
water depth is fixture metadata. The existing NSTA loader supplies the unit
conversions to bbl and Mcf. Missing measurements remain unknown; a true zero
is retained. These inputs are suitable for workflow verification only.

## Opt-in live lane

```bash
uv run --frozen python -m worldenergydata examples/workflows/ukcs-reference-report/input_live.yml
```

This command uses `NSTAClient.download`, an explicit ignored cache, year 2025 and
a cap of 6,000 raw records. `year` can also be a nonempty list of distinct years.
`force_refresh: true` requests fresh bytes; false permits the existing cache.
The cache directory is resolved under the configured analysis input root, which
is rebased to the injected root in embed mode. Paths outside that root are
rejected. The live input is deliberately absent from the offline registry.

The workflow reads retained CSV bytes back, records their SHA-256 digests and
cache modification timestamps, and uses the oldest cache timestamp as the
report refresh timestamp. That timestamp identifies cache retrieval, not source
publication or proof of freshness. The source identity is `uk-nsta-opendata`.
The report cites the existing client's NSTA ArcGIS URL and NSTA Open User Licence.
Live raw CSV and parquet caches are not committed.

A bounded query may omit fields or months. If Forties is absent from the returned
records, execution fails without inventing a result. The report establishes only
the selected observations, not complete annual or UKCS coverage. Live metadata
omits water depth because the production response does not establish it.

To retain a successful live report in the committed report location, copy the
live workflow's generated HTML and JSON as a pair:

```bash
cp examples/workflows/ukcs-reference-report/outputs/ukcs_reference_live_report.html reports/ukcs_reference/index.html
cp examples/workflows/ukcs-reference-report/outputs/ukcs_reference_live_facts.json reports/ukcs_reference/_facts.json
```

If live retrieval fails, retain the explicitly fixture-badged committed report.
Regenerating with the module command restores the fixture version.

## Interpretation and verification

Every monetary result is **pre-tax chain plumbing**, labelled
`chain_plumbing_pre_tax`, **not a UK investment NPV**. After-tax UK fiscal
integration remains deferred to [issue 736](https://github.com/vamseeachanta/worldenergydata/issues/736).
Sparse concept rankings demonstrate wiring, not a field-development recommendation.
Future shared citation-panel adoption is tracked in
[issue 361](https://github.com/vamseeachanta/worldenergydata/issues/361).
The separate benchmark report's `ukcs`/`nsta` source-tag mismatch is outside
[issue 797](https://github.com/vamseeachanta/worldenergydata/issues/797).

```bash
uv run --frozen python -m pytest tests/unit/ukcs tests/workflows/test_durable_workflows.py -q -m "not solver"
```

The unit tests deny HTTP, substitute only the live download boundary, and run
the actual loader, adapter, chain, renderer and engine, including embed mode.
