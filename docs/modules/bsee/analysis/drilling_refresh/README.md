# Public drilling and completion refresh

The refresh downloads public WAR archives, verifies provenance and structural
quality, and evaluates the selected historical bore population. The retained
public rebuild has **partial coverage**: missing or invalid evidence remains
not evaluated for the affected quantity, with a reason and coverage counts.
Existing dashboard adapters and HTML pages retain their historical basis.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-22 | Add reproducible retrieval, offline tests and a source-quality receipt; withhold statistics where source evidence fails QA. |
| 2 | 2026-10-22 | Add checked exclusion accounting and explanations generated from quality counts; preserve the source-quality gate. |
| 3 | 2026-10-22 | Separate structural failures from per-bore evidence gaps, preserve signed report keys, and retain a public rebuild with explicit partial coverage. |
| 4 | 2026-10-24 | Replace unsupported calendar cutoffs with cited snapshot coverage bounds and test each inclusive endpoint independently. |

## Run a new vintage

From the repository root, run the following with a new data directory and a new
output directory:

```sh
python -m worldenergydata.bsee.analysis.drilling_refresh \
  config/analysis/bsee/drilling_refresh.json \
  --fetch --data-dir <download-directory> --output-dir <new-output-directory>
```

The configuration names archive members, columns, keys, units, date bounds and
the historical API12 population CSV. Relative paths resolve from the working
directory. The population file selects bores; its historical durations are not
analysis inputs. Its digest is recorded in the receipt and product JSON.

Each table's minimum of one row rejects an empty source member. It is an
emptiness check, not evidence of population completeness. Population joins and
per-quantity evaluated counts expose missing coverage separately. The configured
inclusive date bounds follow the observed coverage of the cited archive, as
specified below. Date minima and maxima are also recorded in QA. WAR plausibility imports
`MAX_PLAUSIBLE_SPAN_DAYS` from the canonical rig-day module and rejects an
exclusive end-minus-start span above that limit. Interval-union day arithmetic
remains inclusive. The bound is a source-data heuristic, not an operating limit.

### Date-bound basis

Each configured endpoint cites the observed minimum or maximum in the retained
[source receipt](quality/qa.json), with the archive SHA-256 alongside the
criterion. The receipt's source identity agrees with the retained
[download manifest](quality/manifest.json), retrieved on 2026-10-22. These are
observations at the time of retrieval, not BSEE requirements or independently
validated limits on historical or future activity.

| Table | Inclusive minimum date | Inclusive maximum date | Evidence in the source receipt |
| --- | --- | --- | --- |
| WAR | 1988-04-07 | 2026-10-17 | `tables.war.date_min` and `tables.war.date_max` |
| Boreholes | 1947-05-10 | 2026-06-10 | `tables.boreholes.date_min` and `tables.boreholes.date_max` |

Table 1. Observed date coverage of the retained archive defines this snapshot's screening envelope.

Dates outside this evidence-supported envelope remain not evaluated for the
affected quantities. Backfilled records or a new vintage require a separately
reviewed coverage basis and updated criteria before those quantities can be
evaluated. Extrema alone do not establish the correctness of individual dates.
The retained receipt remains the historical result under its recorded criteria;
it is not represented as a rebuild under the revised configuration.

The downloader records the public URL, observed HTTP status, UTC retrieval time,
byte size and SHA-256 in `manifest.json` beside the raw archive. HTTP protocol
errors are controlled failures. When Content-Length is supplied, the received
byte count must match before provenance is recorded. An invalid or truncated ZIP
receives no manifest entry. Raw archives and partial downloads are retained
outside version control; an interrupted unrecorded download requires a new
directory. Resume requires both the recorded size and exact raw-byte digest.
The workflow downloader validates the response's resolved URL against the
configured HTTPS origin and records it. External `record_download` callers
assert the supplied retrieval observations; the retained external-download
manifest records the requested URL and does not claim a resolved-URL observation.

Omit `--fetch` to analyse manifest-backed bytes offline. For a download made with
curl, `record_download` accepts the observed status and retrieval time after
checking the configured destination and ZIP format. A file modification time
does not establish retrieval time.

## QA and output contract

Schema, provenance, row-count floors, identifier formats, duplicate keys, unit
contracts and orphan activity keys gate the entire run. Structural failure
returns a nonzero status and retains only QA and any publishable quality
inventory. A new empty output directory prevents stale statistics from being
mixed with a failed evaluation.

Row checks are recorded for both the entire source and the selected population.
Reversed, malformed, missing or out-of-range dates and implausible intervals are
reported against each affected bore. Invalid WAR evidence makes that bore's rig
quantities not evaluated; a well union is also not evaluated when any selected
sibling lacks usable WAR evidence. Missing borehole milestones make calendar
duration not evaluated independently of WAR coverage. Missing phase evidence
remains null. Missing or blank activity attribution remains visible per bore;
uncoded rows contribute no invented activity quantities.

Each product states selected, calendar-evaluated, drilling-evaluated and
completion-evaluated bore counts. A coverage status of `partial` qualifies sums
and medians over the evaluated bores. QA `pass` establishes structural eligibility
under its printed criterion; it does not establish complete population coverage.
The receipt identifies workflow source text normalized to UTF-8/LF, allowing LF
and CRLF checkouts to reproduce it. Raw archive digests remain byte exact.
Receipts remain `pending-products` while products are generated. Product failures
record `not-evaluated`; only a completed generation records `pass`. Consumers
shall require a passing receipt before using any product in an output directory.
Product JSON links to `qa.json` and carries no separate QA verdict, including
when a failed generation leaves partial files. Activity codes are stripped and
uppercased once on ingestion; `NAN` and `NONE` are treated as missing codes,
matching the canonical rig-day interpretation. Raw archive bytes are unchanged.

`data_quality.csv`, `data_quality.json` and `public_data_quality.txt` form a
whole-source detection inventory. The columns are `defect`, `count`, `example_id`,
`rule`, `reason`. Examples preserve their key type: signed decimal WAR keys or
API12 bore keys. A malformed report key cannot be replaced by a bore key.
Free-text source fields are never exported as examples.

The rule is `reported`. JSON accounting records reported occurrences, and the
separate record enumeration is reconciled against every source QA count before
writing. This inventory does not claim independently proven exclusion or source
correction. Per-bore dispositions state which quantities lack sufficient
evidence. Blank-date counts describe fields; duplicate counts describe excess
copies; missing joins describe distinct keys. Defect classes can overlap, so
their sum is not a distinct-bore count. Raw source bytes remain unchanged.
The whole-source `unattributed_reports` join count means reports with no activity
row. Per-bore `reports_without_code` includes reports whose only activity rows
have blank codes. Blank report identifiers are global format failures; blank
activity codes on valid report identifiers are attribution gaps.

After structural QA passes, paired CSV and JSON products are emitted:

| Product | Quantity and basis |
| --- | --- |
| `calendar` | Selected-bore spud-to-TD elapsed days, with null values and reasons for undated bores. |
| `completion` | Selected-bore inclusive WAR-union days attributed to COM, with phase status. |
| `drilldown` | API12 drilling and completion unions, separate PND, phase statuses and reports without a code. |
| `rig_day_basis` | API10 interval unions and phase statuses; incomplete sibling evidence stays null with a reason. |
| `activity` | Annual normalized-code record counts for eligible WAR bores in the selected population. |

CSV headers name units. Each JSON repeats source URLs, retrieval times, byte
digests, population digest, criteria, per-bore dispositions, coverage and limits.
`headlines.json` collects headline values, and `qa.json` retains the same values,
coverage, per-bore phase statuses and phase-status counts. The overlap summary
reports additive bore unions minus well unions separately for DRL and all WAR
intervals, with the selected-well and multi-bore-well counts. Zero DRL overlap
means the selected DRL intervals duplicate no days across bores; it does not
establish zero overlap across other activity codes.
`run_config.json` records criteria without local directories.
The existing `war_rig_days` functions supply all rig-day arithmetic.

Calendar durations do not establish learning, utilisation or efficiency.
Code-bearing records do not establish intervention counts or service durations.
Undocumented normalized tokens retain no assigned meaning. The fixed population does not
discover new wells. No independent external validation of the rig-day basis is
claimed.

## Retained public source evaluation

The current manifest, QA and quality inventory are retained under `quality/`.
The fresh archive was retrieved with HTTP 200. Structural checks pass; coverage
is partial. The retained QA records headline values and the counts of evaluated
bores beside the selected population. Earlier `manifest.json` and `qa.json` at
this directory's root remain historical evidence of the previous gate.

At the retained retrieval, 225 of 253 bores have calendar durations, 215 have
DRL-attributed values and 77 have COM-attributed values. Missing phase coding
accounts for 38 drilling and 176 completion values that remain not evaluated.
The 140 selected wells include 56 multi-bore wells. The retained overlap summary
records 736.0 all-WAR days and 0.0 DRL days of overlap for evaluated wells.
The overlap fields establish these values; bore sums and well unions can cover
different cohorts when a sibling is ineligible, so their difference is not a
general overlap measure.

The public rebuild generated chart CSV and JSON products outside version control.
Re-verification requires the original archive matching `quality/manifest.json`,
retained outside version control with the verification evidence. Historical
archive bytes are not distributed in this repository. Use that archive and its
manifest without `--fetch`:

```sh
python -m worldenergydata.bsee.analysis.drilling_refresh \
  config/analysis/bsee/drilling_refresh.json \
  --data-dir <retained-archive-directory> --output-dir <new-output-directory>
```

Using `--fetch` in a new directory retrieves a new vintage rather than replaying
the retained one. Existing chart adapters and HTML builders were
not run; connecting these exports to those pages remains follow-up work for
#1672. The exports must retain their partial-coverage qualifications.

## Offline verification

The existing fixture in `tests/unit/bsee/analysis/fixtures/drilling_refresh/` is
synthetic. Its two bores share an API10 and overlap by one week. Hand-worked
calendar and union values are asserted without calling the implementation as an
oracle. Tests cover structural withholding, population scoping, per-bore null
reasons, partial coverage, signed keys, the canonical span boundary, date bounds,
raw-byte download digests, portable workflow digests, HTTP failures and length
mismatches, resume behaviour and immutable output directories.

Run `tests/unit/bsee/analysis/test_drilling_refresh.py` with the existing
`test_war_rig_days*.py` regression files using pytest. These tests download no
data, start no browser and use no licensed solver. The historical receipt keeps
its original workflow digest; the current retained receipt is checked against
the normalized source digest and names the rebuild command on mismatch.
