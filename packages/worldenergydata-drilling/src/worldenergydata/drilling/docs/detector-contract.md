# Detector reconciliation and parsing contract

The detector groups unique, normalized spud events and estimates a descriptive
learning factor from observed individual well durations. The report APIs expose
every row disposition and every fallback or clipping decision. These contracts
address #1343; they do not establish empirical drilling calibration.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-19 | Define parsing, reconciliation, time windows and fit policies so omitted records and substituted results are observable. |

## Input contracts

`BSEEBatchDetector.detect_batches_with_report(frame, time_window_months=...)`
requires `well_id`, `rig_name`, `field_name`, `spud_date`. Schema errors, duplicate
column names and invalid window arguments raise `ValueError`, including on empty
frames. Extra columns are ignored. Inputs are copied; indices need not be unique.

- Identifiers must be nonempty strings. Surrounding whitespace is stripped;
  case is preserved. Numeric identifiers must be explicitly normalized upstream.
- Dates accept `date`, `datetime`, `Timestamp`, `datetime64`, or ISO-shaped text:
  `YYYY-MM-DD`, optionally followed by `T` or a space and `HH:MM`, optional
  seconds and fractional seconds, and optional `Z` or signed `HH:MM` offset.
  Fractional seconds have at most nine digits, matching nanosecond precision.
  Locale dates, numeric epochs, relative dates and impossible dates are rejected.
- Naive dates assume UTC; offsets convert to UTC before sorting and grouping.
  This is an explicit ingestion convention, not evidence of the source timezone.
  Dates must fit the pandas nanosecond timestamp range. Local civil-time windows
  and daylight-saving interpretations are not inferred.
- The window is a positive integer number of **calendar months**. The default
  remains twelve months for compatibility with the pinned detector cited below.
  Calendar offsets replace the previous approximate month-length coefficient.
  Month-end dates clamp to the last valid day of the destination month.
- Within each rig/field, sort by UTC spud instant, preserving input order on
  ties. Anchor a window at the earliest unassigned event and include its end
  instant. The next event outside that window starts a new batch. This is not
  a transitive sliding-gap rule. Single-event batches are retained.
- `span_days = (last_spud - first_spud) / Timedelta(days=1)` retains fractional
  elapsed days. This span is not drilling duration or a sum of well durations.
  A window beyond the supported date range raises `ValueError`.

`fit_learning_curve_with_report(frame, default_factor=None, clip_bounds=None)`
requires `well_position`, `days_to_drill`, including on empty frames.

- Numbers accept finite real numeric scalars or stripped ASCII decimal text,
  including a sign, decimal point and scientific exponent. Thousands separators,
  decimal commas, underscores, unit suffixes and Boolean values are rejected.
  No locale, unit or missing-value sentinel is guessed.
- Null scalars and blank strings are missing. Nonfinite text and infinities are
  invalid. Both dispositions are rejected, with distinct reasons.
- Positions must be positive integers after float parsing. Durations must be
  positive elapsed days supplied by the caller. No completion-date subtraction
  or partial-day rounding is performed. Nonpositive values are excluded;
  fractional positions are rejected. Very large integer text can lose float
  precision; distinctness is checked after parsing and again in log space.
- Repeated positions represent independent, equally weighted observations;
  they are not deduplicated. At least two distinct usable positions identify the
  straight-line intercept and slope. A fit with no residual degrees of freedom
  is arithmetic only; uncertainty and goodness of fit are not evaluated.

## Reconciliation

Both results contain `reconciliation.rows` with `row_number` (zero-based input
position), `status` and `reason`. `reconciliation.counts` always includes
`accepted`, `rejected`, `excluded`, including zero counts. Their sum equals input
length. The reports contain no original row payload; retain the input separately
to map positional numbers to source records.

Each row has one primary reason. Activity precedence is missing/invalid
`well_id`, then `rig_name`, then `field_name`, then `spud_date`. Among otherwise
valid rows, all records sharing a well identifier but differing in normalized
rig, field or spud instant are rejected as `conflicting_well_id`. An exact
normalized duplicate retains its first row as accepted; subsequent rows are
excluded as `duplicate_record`. An invalid row does not invalidate a separate
valid event for that identifier. Accepted rows appear in exactly one batch, so
the sum of batch sizes equals the accepted count.

Fit precedence is `well_position` then `days_to_drill`; for each column, missing,
invalid, nonpositive, then noninteger position. Reasons use these prefixes plus
the column name. Accepted pairs remain accepted even when the overall dataset
cannot identify a fit. Empty and all-rejected inputs are thus distinguishable.

## Method and explicit policy

With `x = log(position)` and `y = log(days_to_drill)`, ordinary least squares gives
`b = sum((x-x_mean)*(y-y_mean)) / sum((x-x_mean)**2)`.
The descriptive power law is `T(N) = A*N**b`, so the doubling ratio is
`LC = T(2N)/T(N) = 2**b`. The base two comes from doubling, not calibration.
The straight-line equation and centered slope are from
[NIST/SEMATECH e-Handbook of Statistical Methods (2012), section 4.4.3.1,
LS for Straight Line](https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd431.htm).
This algebra does not qualify the duration-law interpretation tracked in #1342.

| Status | Meaning |
| --- | --- |
| `FITTED` | Finite positive raw factor; no boundary substitution. |
| `CLIPPED` | Raw factor lies outside caller-supplied inclusive bounds; `factor` is substituted, `raw_factor` and `slope` remain available. |
| `DEFAULTED` | Insufficient usable rows or indistinct positions; the caller explicitly supplied `default_factor`; raw factor and slope are absent. |
| `NOT_EVALUATED` | No caller default for insufficient/indistinct data, or numerical failure; `factor` is absent. |

Reasons are `fit`, `outside_clip_bounds`, `insufficient_data`,
`indistinct_positions` and `nonfinite_fit`. A zero/nonfinite log-space denominator
or an underflowed/overflowed doubling ratio is `nonfinite_fit`, without fallback.
No positive numerical conditioning threshold is assumed.
Defaults and bounds must be finite positive real scalars; bounds must be ordered,
and a default supplied with bounds must lie inside them. Clipping is optional,
and factors above unity can describe increasing durations. Caller policy values
require a campaign-specific basis; this API supplies no empirical acceptance
limits. Calibration, goodness of fit and uncertainty remain **NOT_EVALUATED**.

## Compatibility and sources

`detect_batches` still returns a DataFrame; `fit_learning_curve` still returns a
float. Both log aggregate rejected/excluded counts. The scalar wrapper also logs
`DEFAULTED`, `CLIPPED` or `NOT_EVALUATED`; numerical failure raises `ValueError`.
Use the report APIs when row-level evidence is required. No mutable last-result
state or DataFrame metadata is used to hide the report.

The legacy scalar fallback `0.85` and inclusive bounds `[0.5, 1.0]` are retained
only for compatibility: **assumed, based on previous experience**, without
campaign calibration. Their source is the repository detector at code revision
`b1394197a66f95d78615425b4e1ad4ff78bd9de2`, lines 138–140 and 159–160;
the twelve-month window is from lines 38–41. These are provenance references,
not published engineering limits. The report API requires explicit policy inputs
to substitute them. Calendar windows, UTC outputs, duplicate rejection,
malformed-row reporting and fractional spans intentionally change the former
implicit behavior; downstream consumers relying on it must review this contract.

The [knowledge pack](agent-pack.md) preserves its historical code pin and digest
table. Its detector failure inventory describes that pin. This contract and
`tests/unit/drilling/test_detector_contracts.py` cover the current behavior.

## Worked example

Run `examples/drilling_detector_contract.py` with the drilling package on
`PYTHONPATH`. It prints its input records and the following independently
checkable results. The same example executes in the contract tests.

The synthetic activity inputs are two distinct wells spudded on January 31 and
February 29 in a leap year, a missing-rig row and an exact duplicate of the first
well. With one calendar month, January 31 plus one month is February 29: both
valid wells form one batch with a 29.0-day span. Four input rows reconcile to two
accepted, one rejected (`missing_rig_name`) and one excluded (`duplicate_record`).

The synthetic fit inputs are `(N, days) = (1, 8), (2, 4), (4, 2), (0, 8)`.
The zero-position pair is excluded. Doubling position halves duration, giving
`b = -1`, `LC = 0.5`. With explicit synthetic bounds `[0.5, 1.0]`, the raw
factor is exactly on the lower boundary: status `FITTED`, without clipping.
These chosen inputs and policy bounds test arithmetic; they are not field data.

Slices covered: row reconciliation; parsing and time conventions; fit filtering,
explicit fallback/clipping policy and observable results. Later qualification of
duration laws (#1342), model contracts (#1344), economic semantics (#1345),
implementation enrollment (#1346), distribution (#1347) and independent
clearance (#1348) remains separate work.
