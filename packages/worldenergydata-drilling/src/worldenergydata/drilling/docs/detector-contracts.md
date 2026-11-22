# Drilling detector reconciliation and parsing contracts

The detector groups activity events with complete keys and dates. Diagnostic
results account for every input row and expose fitted, defaulted and clipped
learning factors. The grouping is a heuristic; engineering applicability of the
learning fit, fallback and bounds is **NOT_EVALUATED**.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-19 | Define row reconciliation, date and numeric parsing, and learning-fit dispositions to expose omitted data and substituted factors. |
| 1 | 2026-10-20 | Restore numeric well-ID ingestion, distinguish missing numeric values and document the empty-frame exception. |
| 2 | 2026-10-22 | Add complete synthetic disposition tables and boundary evidence; align the refreshed knowledge pack with the reviewed detector. |

## Record accounting

`detect_batches_with_diagnostics(frame, time_window_months=12)` returns a
`DetectionResult` with `batches`, `records` and `counts`. The existing
`detect_batches` returns only the batch table and logs disposition counts when
any input is rejected or excluded. Neither method changes the input.

Each input row has one diagnostic entry: zero-based `row_position`, original
`source_index`, `disposition` and `reason`. Positions remain unique even when
index labels repeat. Counts satisfy:

```text
input rows = accepted + rejected + excluded
sum(batch_size) = accepted
```

These are accounting identities, not statistical estimates. Accepted rows have
usable required fields. Rejected rows have invalid or missing fields; all field
reasons are joined with semicolons. Excluded rows duplicate an earlier accepted
row after normalization of the four required fields. Additional columns do not
participate in duplicate detection. The first occurrence is retained. Missing
columns or duplicate column labels raise `ValueError` rather than producing an
incomplete report. Empty frames still require the declared columns.

Identifiers (`well_id`, `rig_name`, `field_name`) accept nonblank strings;
surrounding whitespace is removed. `well_id` also accepts non-Boolean integral
numbers and finite integral Python `float` or NumPy `float64` values with
`abs(value) < 2**53`, normalized with `str(int(value))`. Other floating types
(including `float32`) are rejected because their precision may already have
lost identifier digits. Fractional or nonfinite numeric well IDs are rejected.
Numeric and text forms share duplicate identity only when their normalized
decimal strings match. Numeric inputs cannot preserve leading zeros: for example,
`423456789012` and text `"0423456789012"` remain distinct. Supply IDs as text
when leading zeros matter; no API width or zero padding is inferred.
Native and NumPy floating NaNs are reported as `missing_<column>` for identifier
columns. Rig and field keys still require text. No case folding, identity inference or
cross-field well deduplication is performed. Multiple distinct events for the
same well remain accepted. **`batch_size` counts event rows, not unique wells**;
`well_ids` can therefore contain repeated IDs.

## Time and duration

Dates accept complete extended ISO-8601 calendar text (`YYYY-MM-DD`, optionally
with time and offset) or native date/datetime objects. Partial dates and compact
numeric date strings are rejected rather than filled in. Invalid, missing,
locale-dependent date text and numeric epochs are rejected. Epoch units are
not inferred. Naive timestamps are treated as UTC; aware timestamps are
converted to UTC. Normalized timestamps are returned as UTC-aware values.
This is an explicit ingestion convention, not evidence of a source timezone.

Rows are grouped by rig and field, then sorted by date (ties retain input order).
Each batch is anchored to its first unassigned row, with an inclusive endpoint
`first_date + DateOffset(months=time_window_months)`. The next batch starts at
the first row beyond that endpoint. Windows do not chain from each new member.
Month ends follow calendar offset rules, replacing the previous approximate
fixed-day month. The window must be a positive integer; Boolean values are
rejected. The legacy default of 12 months is application policy, recorded in
[knowledge pack revision 2, section 2](agent-pack.md); no physical separation
criterion is established by that default.

`span_days = (last_date - first_date) / Timedelta(days=1)` is elapsed time,
including fractional days, without inclusive-day counting. The input duration
`days_to_drill` is likewise elapsed days; this API does not derive it from
activity codes or completion dates.

The parsing and timezone behavior follows the [pandas `to_datetime` reference,
format and utc sections (2026)](https://pandas.pydata.org/docs/reference/api/pandas.to_datetime.html).
Calendar offset behavior follows the [pandas time-series guide, date offsets
(2026)](https://pandas.pydata.org/docs/user_guide/timeseries.html#dateoffset-objects).

## Learning-fit contract

`fit_learning_curve_with_diagnostics(frame)` returns a `LearningFitResult`:

- `factor`: fitted or substituted scalar, preserving the legacy scalar API.
- `raw_factor`: the factor before clipping, or `None` when no fit is identifiable.
- `status`: `fitted`, `defaulted`, `clipped_lower` or `clipped_upper`.
- `reason`: fit method or the specific default trigger.
- `records` and `counts`: the same row-accounting schema used for detection.
- `qualification`: `NOT_EVALUATED`, including when a numerical fit succeeds.

`well_position` must be positive, integral and finite. `days_to_drill` must be
positive and finite. Decimal and scientific numeric text is accepted after
trimming. Thousands separators, locale decimal commas, units, Booleans and
nonfinite values are rejected, with explicit field reasons. Missing values are
rejected, not replaced with zero. No comma removal or unit conversion occurs.
Numeric text such as `NaN` and `inf` is invalid under the numeric grammar;
native numeric NaN is classified as `missing_<column>` and positive or negative
infinity as `nonfinite_<column>`. Repeated valid positions
are retained as observations, not deduplicated. No learning rows are excluded.

The fitted model is `log(T) = a + b log(N)`. Centered least squares gives
`b = sum((x-x_mean)*(y-y_mean)) / sum((x-x_mean)**2)` and the doubling ratio is
`LC = T(2N)/T(N) = 2**b`. This follows directly by substitution in `T=exp(a)*N**b`;
2 denotes doubling, not an empirical coefficient. The slope and intercept equations are given in the [NIST/SEMATECH
e-Handbook of Statistical Methods, section 4.4.3.1, Least Squares
(online edition accessed 2026)](https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd431.htm).
This establishes a numerical method, not the physical interpretation or
calibration of individual versus cumulative-average drilling durations.

Fewer than two usable rows, or no distinct usable log positions, produces
`defaulted` with `raw_factor=None` and reason `insufficient_data` or
`constant_position`. Two distinct positions are necessary to identify the
intercept and slope. The legacy scalar fallback is 0.85 and the legacy inclusive
bounds are [0.5, 1.0], as recorded in knowledge pack revision 2, section 2.
These are retained compatibility policies, **not sourced engineering acceptance
limits**. Values outside those bounds are clipped with explicit status. Exact
boundary equality is `fitted`; a numerical roundoff guard uses floating-point
epsilon scaled by row count and log magnitude to avoid false clipping at an
endpoint. The unrounded raw factor is retained. Extreme slopes can produce zero or infinity in
the raw floating-point doubling ratio; those values remain exposed alongside
the bounded result. The roundoff guard is not an engineering acceptance limit.

`fit_learning_curve(pd.DataFrame())` now raises `ValueError` for missing required
columns; the previous entry point returned 0.85. An empty frame declaring both
`well_position` and `days_to_drill` still returns the default with
`insufficient_data`.

`fit_learning_curve` returns only `factor` and logs when filtering, defaulting
or clipping occurs. Consumers needing disposition evidence should retain the
diagnostic result. Engineering acceptance remains conditional on a qualified
duration interpretation, calibration dataset, fallback and bounds; that evidence
is not established here. Duration-law qualification remains tracked separately in #1342.

## Worked example

All records below are synthetic; no field measurements are represented.
The regression node is
`tests/unit/drilling/test_detector_regression.py::test_worked_example_dispositions_and_learning_line`.
The table is in input order; row positions identify records even with repeated
index labels. Rig and field are `R` and `F` unless shown as missing.

| Row | Well ID input | Rig | Spud date (UTC) | Disposition | Reason |
| --- | --- | --- | --- | --- | --- |
| 0 | numeric `101` | R | 2024-01-31 12:00:00 | accepted | accepted |
| 1 | text `"101"` | R | 2024-01-31 12:00:00 | excluded | duplicate_record |
| 2 | numeric `102` | R | 2024-02-29 12:00:00 | accepted | accepted |
| 3 | numeric `103` | R | 2024-02-29 12:00:01 | accepted | accepted |
| 4 | numeric `104` | R | 2024-02-29 18:00:01 | accepted | accepted |
| 5 | numeric `105` | missing | 2024-02-29 00:00:00 | rejected | missing_rig_name |
| 6 | numeric `106` | R | `bad` | rejected | invalid_spud_date |

Hand accounting: **7 inputs = 4 accepted + 2 rejected + 1 excluded**.
Normalization makes rows 0 and 1 the same required-field record. With a
one-calendar-month window, January 31 noon ends at leap-year February 29 noon.
The endpoint is included; the next second starts a second batch. The two batches
contain rows (0, 2) and (3, 4), with sizes (2, 2) and elapsed spans 29 days and
six hours (one quarter day). These are calendar arithmetic answers, following
the pandas references above; no 30.44-day month approximation is used.

| Row | Position text | Duration text (days) | Disposition | Reason |
| --- | --- | --- | --- | --- |
| 0 | `"1"` | `"8"` | accepted | accepted |
| 1 | `"2"` | `"2"` | accepted | accepted |
| 2 | `"3"` | `"bad"` | rejected | invalid_days_to_drill |
| 3 | `"0"` | `"4"` | rejected | nonpositive_well_position |

Hand accounting: **4 training inputs = 2 accepted + 2 rejected + 0 excluded**.
For the retained two-point line, `b=log(2/8)/log(2/1)=-2`, `a=log(8)`;
therefore `log(T)=log(8)-2*log(N)`. At N=2 this gives T=8/4=2 days,
and the doubling ratio is `2**(-2)=1/4`. The compatibility lower bound gives
`factor=1/2`, `raw_factor` approximately one quarter, `status=clipped_lower`
and `qualification=NOT_EVALUATED`. The equations and hand substitution determine
the expected answers independently of the implementation.

## Boundary evidence

`tests/unit/drilling/test_detector_regression.py` checks conservation for empty,
all-rejected and mixed inputs; duplicate-column errors; nonleap, leap and
year-crossing calendar endpoints one second either side; anchoring instead of
chaining; missing and malformed durations; zero, one, two and three usable
learning rows; and repeated positions with an identifiable slope. Clipping is
checked at duration ratios 3/8, 4/8, 5/8 and 7/8, 8/8, 9/8: one synthetic day
either side of each compatibility boundary when the first duration is eight days.
The original numeric-ID and fractional-span cases remain in
`tests/unit/drilling/test_detector_contracts.py`.

## Limits

Knowledge pack revision 3 now reflects the reviewed detector and pins its source
digests. The fallback and clipping values still have only their historical
application-policy basis in revision 2; engineering qualification is
**NOT_EVALUATED**. No physical campaign-separation criterion, source-timezone
provenance or independent physical duration-law qualification is established.
The latter remains separate in #1342. The map families are proposals with
`counted: false` pending review; enrollment is not engineering clearance.
