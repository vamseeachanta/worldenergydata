# Public drilling and completion refresh

The refresh checks public WAR source structure before computing descriptive
statistics for the configured bore population. Row defects are reported per
bore. Missing date or phase evidence remains unevaluated and is never converted
to a measured zero. Retained exports and their source receipts are in `quality/`.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-22 | Add reproducible retrieval, offline tests and a source-quality receipt; withhold statistics where source evidence fails QA. |
| 2 | 2026-10-22 | Add checked exclusion accounting and explanations generated from quality counts; preserve the source-quality gate. |
| 3 | 2026-10-22 | Separate structural failures from per-bore diagnostics, retain signed report identifiers and rebuild population exports. Remove the unsupported exclusion-accounting claim. |

## Run a new vintage

Install the package with its existing dependencies. From the repository root,
use a new data directory and an empty output directory:

```sh
python -m worldenergydata.bsee.analysis.drilling_refresh \
  config/analysis/bsee/drilling_refresh.json \
  --fetch --data-dir <download-directory> --output-dir <new-output-directory>
```

Configuration names the archive members, source keys, required columns, units,
date bounds and historical API12 population CSV. Relative paths resolve from the
working directory. The population CSV selects bores only; its old duration
values are not used. Each export records its digest.

The row-count floor of `1` is an empty-table guard, not evidence of corpus
completeness. No stable public completeness threshold is available. Every table
is counted in the QA receipt so changes between vintages remain visible. Date
bounds are inclusive: `1900-01-01` is a broad historical sanity bound rather
than a claim about the earliest record; `2026-10-22` is this evaluation's cutoff.
Update that cutoff explicitly when evaluating a later vintage. Missing,
malformed or out-of-range dates leave the affected quantity unevaluated.

The downloader writes `manifest.json` beside the archive, recording public URL,
observed HTTP status, UTC retrieval time, byte size and SHA-256. Completed
files resume only after size and digest validation. HTTP protocol errors and
Content-Length mismatches report `BLOCKED-NETWORK`; incomplete files do not
enter the manifest. Unrecorded partial files are preserved and require a new
directory. Raw downloads remain outside version control.

Omit `--fetch` to analyse previously downloaded, manifest-backed bytes offline.
For curl retrievals, `record_download` accepts the observed status and UTC time
and validates the ZIP and destination. It never infers retrieval time from a
file modification time. ZIP members are read in memory; source text retains
its published encoding. Generated report text uses UTF-8 and LF.

## QA and output contract

Whole-table schema, provenance, key-format and duplicate-key failures block all
statistics. Empty tables, invalid configured units and an unsupported basis
also fail the structural contract. A failed run retains `qa.json` with
`status: not-evaluated`; row quality files are written when identifiers can be
published safely. No arbitrary row is selected from duplicate keys.

Row diagnostics do not block the population rebuild. The QA receipt contains
whole-table counts, `population_tables` counts and `bore_quality` entries for
every selected API12. Each bore entry records date and activity defects plus
missing joins. Whole-table legacy defects remain visible without entering the
population's statistics. Activity rows without matching WAR rows cannot be
assigned to a bore and are reported in the whole-table join count.

The canonical `war_rig_days` implementation supplies all rig-day arithmetic:
reversed intervals are rejected and counted per bore; implausible spans are
retained and flagged; unattributed weeks remain coverage without contributing
to a coded activity total. The refresh imports `MAX_PLAUSIBLE_SPAN_DAYS` and
compares the exclusive span with that bound. Inclusive endpoint counting still
applies when computing usable WAR interval unions.

`data_quality.csv`, `data_quality.json` and `public_data_quality.txt` report
detected occurrences reconciled against QA counts. They do not claim that all
reported occurrences were excluded or corrected. The columns are `defect`,
`count`, `example_id`, `rule`, `reason`; `rule` is `reported`. Examples use the
original signed decimal SN_WAR for report/activity records and API12 for
borehole or population records. A malformed report key never falls back to a
bore identifier. Free text is never published as an example.

Missing dates count fields, duplicate keys count excess copies, and missing
joins count distinct keys. Population coverage counts missing borehole and WAR
joins separately. These overlapping counts cannot be summed as distinct bores.
The public quality explanation is generated from the same rows and reasons.

Successful runs emit paired CSV and JSON products:

| Product | Quantity and basis |
| --- | --- |
| `calendar` | Per-bore spud-to-TD elapsed days; missing or unusable milestones give a blank value and `NOT_EVALUATED`. |
| `completion` | Per-bore inclusive COM interval-union days and phase status. |
| `drilldown` | API12 drilling, completion and separate PND days, coverage status, rejected, implausible and unattributed week counts. |
| `rig_day_basis` | API10 interval unions across sidetracks, compared with overlapping API12 sums. |
| `activity` | Annual raw code-bearing record counts for the selected population and usable start dates. |

JSON products repeat source provenance, population digest, basis, quality
explanation and limits. `headlines.json` collects the same headlines;
`run_config.json` records criteria without local directories. Calendar medians
use only evaluated bores. Missing phase values stay null with their coverage
status. A passing structural receipt does not assert complete phase coverage.

Calendar elapsed days do not establish learning, utilisation or efficiency.
Code-bearing records do not establish intervention counts or service durations.
Unknown activity tokens retain their raw meaning. No independent validation of
the rig-day interpretation is claimed. The fixed historical population does
not discover additional bores from the new vintage. Existing HTML builders and
chart adapters remain unchanged.

## Retained source evaluation

The original `manifest.json` and `qa.json` retain the earlier whole-table gate
result and original workflow digest. The current rebuild, its manifest, QA,
quality explanation and population products are retained under `quality/`.
The current receipt identifies the implementation by its exact LF byte digest.
The archive and temporary computations remain outside version control.

The [current headlines](quality/headlines.json) report a calendar median of
47.0 days, a drilling bore sum and API10 union of 11,484.0 days each, a completion
bore sum of 5,522.0 days and 4,041 code-bearing activity records. These are
descriptive values on the stated population and available evidence. The
[QA receipt](quality/qa.json) supplies whole-table and population counts plus
each bore's diagnostics; the [calendar export](quality/calendar.csv) identifies
every unevaluated calendar value. These exports are not independent validation
of the activity interpretation.

## Offline verification

The fixture in `tests/unit/bsee/analysis/fixtures/drilling_refresh/` is synthetic.
Hand-worked literals assert calendar durations of 13 and 6 days (median 9.5),
a DRL bore sum of 21 days, an API10 union of 14 days and a COM sum of 7 days.
Those are fixture expectations, not public-source measurements. Separate tests
cover negative report keys, legacy rows outside the population, missing dates,
unattributed coverage, span boundaries, partial HTTP responses, provenance,
schema, duplicate keys, invalid keys and count disagreement. No test downloads
data or starts a browser.

Run `test_drilling_refresh*.py` and `test_war_rig_days*.py` in
`tests/unit/bsee/analysis/`. The CI selector routes source and test changes to
the BSEE shard and configuration changes to its analysis tests; selector
regressions assert those routes.
