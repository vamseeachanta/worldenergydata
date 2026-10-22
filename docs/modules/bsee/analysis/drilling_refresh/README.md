# Public drilling and completion refresh

The refresh workflow downloads public WAR archives, records their provenance,
and checks source quality before computing descriptive statistics. The retained
public vintage is **not evaluated**: the source failed QA, so no new chart values,
headline statistics or public HTML were generated. Existing pages retain their
historical basis and must not be presented as refreshed results.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-22 | Add reproducible retrieval, offline tests and a source-quality receipt; withhold statistics where source evidence fails QA. |
| 2 | 2026-10-22 | Add checked exclusion accounting and explanations generated from quality counts; preserve the source-quality gate. |

## Run a new vintage

Install the package with its existing dependencies. From the repository root,
run the following with a new data directory and a new output directory:

```sh
python -m worldenergydata.bsee.analysis.drilling_refresh \
  config/analysis/bsee/drilling_refresh.json \
  --fetch --data-dir <download-directory> --output-dir <new-output-directory>
```

The JSON configuration names the data folder, output folder, archive members,
required columns, keys, row-count floor, units, date columns and historical
API12 population CSV. Relative paths resolve from the working directory.
The population file selects bores only; its old duration values are never used.
Its digest is recorded in the QA receipt and successful headline exports.

The downloader uses the standard library, reads one source at a time and writes
`manifest.json` beside the archive. Each entry records the public URL, observed
HTTP status, UTC download time, byte size and SHA-256 of the original bytes.
Raw downloads remain outside version control. HTTP failures report
`BLOCKED-NETWORK` with the required URL; an HTML response cannot become a data
archive. Completed files resume only after digest validation. To re-pull a new
vintage, use a new data directory. An interrupted, unrecorded file is preserved
and requires a new directory rather than an automatic overwrite.

Omit `--fetch` to analyse previously downloaded, manifest-backed bytes offline.
For downloads made with curl, `record_download` accepts the observed HTTP status
and retrieval time after validating the configured destination and ZIP format.
It does not infer a retrieval time from a file modification time.

## QA and output contract

QA covers all supplied rows before population selection. It records row counts,
date ranges, duplicate keys, missing keys, API12 validity, missing or malformed
dates, reversed intervals, implausible WAR spans, unit contracts, activity joins
and population coverage. Calendar dates support both the date-only and timestamp
forms supplied by BSEE. The configured WAR span bound follows the existing
canonical rig-day implementation's plausibility bound; it is a rejection rule,
not a measured operating limit.

Any failed check produces `qa.json` with `status: not-evaluated`, the criterion,
basis, reasons and source digests. It returns a nonzero exit status and withholds
every statistic and chart value, including those for otherwise valid records.
A passing subset is not inferred from incomplete source evidence. A run requires
an empty output directory, preventing old statistics from appearing beside a new
failed QA receipt. Import digest mismatches also fail closed. The workflow digest
identifies the implementation that evaluated the recorded source vintage.

When source records can be evaluated, the refresh also writes `data_quality.csv`,
`data_quality.json` and `public_data_quality.txt`, even when source checks fail.
CSV columns and the JSON `columns` array are `defect`, `count`, `example_id`,
`rule`, `reason`. Each defect class has one row, one numeric public report or bore
key, and its exclusion criterion. Free-text source values are never examples.
JSON includes the excluded and corrected occurrence counts for each class, the
synthetic-fixture label and the whole-table evaluation basis. No supported
correction is currently applied: every detected occurrence is `excluded`, with
zero corrected occurrences. Raw source bytes are retained without alteration.

Accounting compares the full detected and excluded key multisets, including
repeated occurrences, before writing the table. It also reconciles detected
occurrences against every source QA count. Missing dispositions, extra classes,
unpublishable examples or unmatched counts fail closed with a QA receipt and no
statistics. Schema or provenance failures before record evaluation may prevent
the table from being written; no example identifier is invented.

Counts retain the QA basis: missing dates count blank fields, duplicate keys count
excess copies, and missing joins count distinct source keys. Population coverage
adds missing borehole joins and missing WAR joins separately, so a bore can count
twice. Defect classes can overlap and their sum is not a distinct-bore count.
All copies of an ambiguous record remain outside every statistic under the gate.
The `Public data quality` text is generated from the table rows and their reasons;
its numbers are never maintained separately. Passing exports repeat the text in
each product JSON, beside the statistics basis and limits.

After QA passes, the workflow emits the following paired CSV and JSON products:

| Product | Quantity and basis |
| --- | --- |
| `calendar` | Per-bore spud-to-TD elapsed calendar days, excluding the endpoint adjustment. |
| `completion` | Per-bore inclusive WAR-union days attributed to COM, with phase coverage status. |
| `drilldown` | API12 drilling and completion WAR-union days; PND stays separate. |
| `rig_day_basis` | API10 interval unions across sidetracks, for comparison with overlapping API12 sums. |
| `activity` | Annual raw activity-code record counts for the whole supplied WAR table. |

CSV headers name quantity and unit. Each JSON repeats source URLs, download
dates, byte digests, population digest, basis and limits. `headlines.json`
collects the same headline values. `run_config.json` records the criteria without
machine-specific directories. Missing phase evidence is null, never zero.
The existing `war_rig_days` functions supply all rig-day arithmetic.

Calendar cycle times do not establish learning, rig utilisation or efficiency.
Code-bearing record counts do not establish intervention counts or service
durations. Undocumented activity tokens are preserved without assigning meanings.
No independent external validation of the rig-day basis is claimed. The fixed
historical population does not discover additional wells from the new vintage.

## Retained public source evaluation

`manifest.json` records the fresh public WAR retrieval. `qa.json` records the
evaluation of those bytes. The source failed because of reversed dates,
implausible spans, blank activity keys, missing borehole milestone dates,
unattributed reports and missing population joins. Counts and date ranges are
available in that machine-readable receipt; no analysis figures are published.

The rebuild command returned `1` with `QA not-evaluated: see qa.json`.
Existing drilling, completion, D&C and intervention HTML builders were therefore
not run against this vintage. The new exports do not yet replace the existing
dashboard chart adapters. A maintainer must resolve the source-quality and
coverage gaps before those builders can publish refreshed statistics; missing
evidence must not be converted to zero or removed silently.

The subsequent public rebuild also returned `1` with the same source-quality
rejection. Its generated [quality table](quality/data_quality.csv),
[accounting](quality/data_quality.json) and
[Public data quality explanation](quality/public_data_quality.txt) are retained
under `quality/`, beside the new manifest and QA receipt. The response was HTTP
200; archive bytes and temporary computation outputs remain outside version
control. The original receipt above remains unchanged. No chart adapter or HTML
builder was run because the source gate did not pass.

## Offline verification

The committed fixture in
`tests/unit/bsee/analysis/fixtures/drilling_refresh/` is **synthetic**. It includes
overlapping sidetrack weeks so that bore sums and well unions differ. Tests
regenerate headline values, preserve missing phase evidence, check timestamp
parsing and exercise each QA rejection, download provenance, resume behaviour,
network failure, invalid archives, source schema and digest mismatches.
The combined synthetic quality fixture covers every retained defect type, checks
the CSV/JSON columns and generated text, and proves excluded records never reach
the statistics computation. Separate cases reject mismatched exclusion accounting
and free-text examples before any table is written. The retained historical QA
receipt keeps its original workflow digest; fresh receipts are checked against
the current implementation digest.

Run `tests/unit/bsee/analysis/test_drilling_refresh.py` together with the existing
`test_war_rig_days*.py` regression files using pytest. No test downloads data.
No test starts a browser or uses a licensed solver.
