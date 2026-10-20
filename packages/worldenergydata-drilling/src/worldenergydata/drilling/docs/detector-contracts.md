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
numbers and finite integral floats, normalized with `str(int(value))`. Numeric
and text forms of the same well ID share duplicate identity. Fractional or
nonfinite numeric well IDs are rejected; rig and field keys still require text. No case folding, identity inference or
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
2 denotes doubling, not an empirical coefficient. The least-squares criterion
and linear model are described in the [NumPy `lstsq` reference, Examples
(2026)](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html).
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
is not established here. [Duration-law qualification remains tracked separately](https://github.com/vamseeachanta/worldenergydata/issues/1342).

## Worked example

The following inputs are synthetic and are not field measurements. The example
also appears as executable arithmetic assertions in
`tests/unit/drilling/test_detector_contracts.py`.

```python
import pandas as pd
from worldenergydata.drilling import BSEEBatchDetector

detector = BSEEBatchDetector()
events = pd.DataFrame({
    "well_id": ["A", "B", "C", "D"],
    "rig_name": ["R"] * 4,
    "field_name": ["F"] * 4,
    "spud_date": [
        "2024-01-31T12:00:00Z", "2024-02-29T12:00:00Z",
        "2024-02-29T12:00:01Z", "2024-02-29T18:00:01Z",
    ],
})
batches = detector.detect_batches_with_diagnostics(events, time_window_months=1)
assert batches.counts == {"accepted": 4, "rejected": 0, "excluded": 0}
assert batches.batches.batch_size.tolist() == [2, 2]
assert batches.batches.span_days.tolist() == [29.0, 0.25]

fit = detector.fit_learning_curve_with_diagnostics(pd.DataFrame({
    "well_position": ["1", "2", "3"],
    "days_to_drill": ["8", "2", "bad"],
}))
assert fit.counts == {"accepted": 2, "rejected": 1, "excluded": 0}
assert abs(fit.raw_factor - 0.25) < 1e-12  # Numerical roundoff assertion only.
assert fit.factor == 0.5
assert fit.status == "clipped_lower"
assert fit.qualification == "NOT_EVALUATED"
```

Calendar method and answer: January 31 noon plus one calendar month is February
29 noon in the selected leap year. That endpoint is included; the next second
starts another batch. The spans are 29 days and six hours (one quarter day).

Learning method and answer: the valid two-point observations give
`b = log(2/8)/log(2/1) = -2`, hence `LC = 2**(-2) = 0.25`. The third duration is
rejected. The legacy lower bound changes the reported factor to 0.5; both the
raw factor and clipping disposition remain visible. This result is a hand
calculation of a synthetic numerical case, not engineering validation.


## Limits

Knowledge pack revision 2 describes the earlier detector. Its approximate month,
integer-span and missing-check descriptions do not govern this contract; only
its legacy policy values are retained here. The pack revision, code pin, digests
and resolved failure rows will be refreshed in the
[knowledge-pack follow-up](https://github.com/vamseeachanta/worldenergydata/issues/1549).
Physical duration-law qualification remains separate from this parser fix.
