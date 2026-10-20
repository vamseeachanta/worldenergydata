# Operator opportunity one-pager

The generator turns a public registry and ranked screen snapshot into standalone
HTML and, with Chrome and `pdfinfo` installed, a PDF accepted only after readback
confirms exactly one page. Figures retain source identifiers and reporting
periods. Missing figures say `not captured`; missing conclusions say
`NOT_EVALUATED`. No uplift or ownership is inferred.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-20 | Add the snapshot contract, build targets and worked example for repeatable sourced pages. |

## Build

Run from the repository root, with Python available:

```sh
make onepager OPERATOR=001 INPUT=registry-screen.json OUTPUT=artifacts
```

`INPUT` is a JSON snapshot; `OUTPUT` is an explicit artifact directory. Keep
generated production pages and PDFs outside the repository. `onepager.html` and
`onepager.pdf` are written there. Use a distinct output directory for each
operator. The operator ID is matched exactly as text, including leading zeros;
the report uses the ID, without a prospect name or outreach copy.

For HTML without PDF validation:

```sh
make onepager-html OPERATOR=001 \
  INPUT=tests/fixtures/operator_onepager/worked_example.json OUTPUT=artifacts
```

The equivalent module entry point accepts `--chrome`, `--pdfinfo` and
`--candidate-limit`. The default executable names are `google-chrome` and
`pdfinfo`. The HTML-only option makes no page-count claim. Chrome is run with
`--headless=new --disable-gpu --no-pdf-header-footer`; the last flag suppresses
the date and local file address. The browser sandbox remains enabled.

Chrome writes a candidate PDF first; `pdfinfo` must report `Pages: 1` before
that file replaces the destination PDF. A failed build returns a nonzero status
and preserves any previous destination PDF. Inspect the command status before
distributing an artifact: a previous PDF is not the result of a failed build.
Rejected candidates and isolated browser profiles remain available for diagnosis.
Set the usual temporary-directory environment variable to the artifact disk.
Content is never clipped, hidden, or silently shrunk to force acceptance.

## Snapshot contract

The sibling registry and screening work defines the production roll-up and
ranking. This generator introduces an explicit handoff format; it does not
claim an existing parquet adapter. Convert upstream rows into this contract
without redistributing lease production to wells or replacing missing values.
The compact, executable example is
[`worked_example.json`](../../../tests/fixtures/operator_onepager/worked_example.json).

- `schema_version`: integer `1`, the initial contract revision.
- `data_status`: `public` or `synthetic`. Synthetic pages carry a visible banner.
- `sources`: map of stable source identifiers to `dataset`, `vintage` (ISO
  calendar date), `period` and `reference` (public dataset address or documented
  derivation). Preserve catalog-issued identifiers when adapting real data.
- `registry_source`: source identifier for registry membership and counts.
- `operators`: registry list with unique text `operator_no` values, optional
  `summary`, and optional `screen`. A registered operator with no screen still
  gets a page that explicitly reports the missing analysis.

Every non-null measurement is an object with numeric `value` and `source`.
Null or an absent optional measurement means `not captured`; numeric zero is
displayed as zero. Non-finite, boolean or text figures are rejected. Summary
figures and peer-chart rates must be non-negative; signed screen evidence such
as a reported rate change retains its sign. Counts additionally require integers.
No units are converted.

Summary keys match the registry issue: `well_count_total`,
`well_count_producing`, `well_count_inactive`, `field_count`, `oil_bbl_last12`,
`gas_mcf_last12` and `water_bbl_last12`. Units are wells, fields, bbl and Mcf.
The source period for the production totals must describe the actual reporting
window; the generator cannot establish source completeness or independently
audit the roll-up. If it is unavailable, supply a gap rather than an estimate.

The optional `screen` contains:

- `source`: provenance of ranks and selection, and `method`: the upstream
  ranking method and sensitivity qualification, displayed verbatim as text.
- `candidates`: list of `rank` (unique positive integer), `entity_id` (unique),
  `granularity` (`well` or `lease`) and a nonempty `evidence` list. Each evidence
  measurement also includes `label` and `unit`. Rows are sorted by supplied
  rank. All rows are validated even when not displayed. Lease observations
  receive an explicit warning against interpretation as well production.
- `peer_comparison`: optional object containing `metric`, `unit`, `cohort`,
  `operator` and `median`. Both measurements use the declared metric and unit;
  their source records must have identical reporting periods. The adapter must establish
  compatible field, vintage, depth and reporting windows. Missing measurements
  suppress the chart and display a gap. No median or peer group is invented.
- `false_positive_rate`: optional sourced measurement expressed as a fraction
  between zero and unity. Without validation evidence supply null; the page
  says `NOT_EVALUATED`, without claiming an error budget.

The limitations section has no suppression switch. It also identifies
reservoir-versus-mechanical uncertainty for each displayed candidate, the
distinction between operator of record and working interest, and limits on
economic or uplift claims. Statistical comparison is not a diagnosis.

## Presentation and arithmetic

No domain equation, coefficient or acceptance threshold is introduced. Supplied
figures and ranks are preserved. Counts display as integers; other observations
display to one decimal place. Source measurements retain their input precision
in the snapshot. A bar's width is `100 * value / max(operator, median)` percent;
both widths are zero when both values are zero. This is a normalized visual
scale, not an uplift percentage. Its independent hand calculation appears below
and in the test docstring.

A supplied false-positive fraction is displayed as `100 * fraction` percent to
one decimal place. The corresponding synthetic test uses the independent hand
calculation `1 / 20 = 0.05`, displayed as `5.0 %`.

The default of five candidate rows, A4 page layout, margins, font sizes and
colors are presentation choices in the template, not scientific limits. The
number of omitted candidates is disclosed and the full ranking stays in the
screen. A shorter candidate list may be requested, but it cannot suppress
limitations. Long evidence or source text may still overflow; the PDF check
rejects it. No successful HTML build alone establishes that a PDF fits.

## Worked example

All values in the fixture are invented hand-calculation inputs, labelled
synthetic in both the dataset titles and the generated page. They are not
regulator measurements, a named operator's records, or a validation case for
the upstream ranking.

Inputs: operator `001` has four reported wells, three producing and one inactive,
in two fields. Supplied period totals are 120 bbl oil and 600 Mcf gas; water is
not captured. A supplied screen places `well-alpha` at rank 1 with a rate of
2 bbl/day and peer median of 8 bbl/day; `lease-beta` is rank 2 with a prior
lease rate of 3 bbl/day. Both source periods are explicitly recorded.

Method: preserve the supplied totals and ranking, join each displayed figure to
its source, and scale the two chart bars. By independent arithmetic,
`max(2, 8) = 8`, `100 * 2 / 8 = 25.0` and `100 * 8 / 8 = 100.0`.

Answer: the page displays 120.0 bbl, 600.0 Mcf, explicit missing water,
`well-alpha` before `lease-beta`, and bars occupying 25.0 % and 100.0 % of the
chart. The lease rate remains a lease observation. No false-positive rate,
recoverable production or cause of underperformance is established. The
checked-in HTML golden file records the complete expected presentation.

## Verification and limits

The contract tests cover the golden page, zero versus missing figures,
provenance, ranking, escaping and absence of external assets, candidate omission,
registry members without screens, chart scaling, CLI and Make integration, and
PDF readback accepting one page and rejecting overflow. Browser calls in unit
tests are substituted; these tests do not establish actual Chrome pagination.
Actual rendering requires an installed browser and `pdfinfo` and must be checked
on the intended rendering environment. No production registry or screen output
was available for this example; the upstream parquet adapter remains follow-up.

## Sources

- Issue #1128, parameterized per-operator opportunity one-pager generator:
  content, missing-data and exactly-one-page requirements.
- Registry issue #1126 and screen issue #1127 in this repository:
  handoff fields, reporting granularity and inference boundaries.
- [Chrome Headless mode](https://developer.chrome.com/docs/automation-and-testing/headless),
  accessed 2026-10-20: headless execution. The PDF command and required header
  suppression flag are explicitly specified in issue #1128, Requirements.
