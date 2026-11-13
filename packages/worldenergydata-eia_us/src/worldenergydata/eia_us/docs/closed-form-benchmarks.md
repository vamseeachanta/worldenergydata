# DPR and GoM crosscheck closed-form benchmarks

These independent exact-arithmetic cases check latest-observation selection,
production-rate addition and relative comparison. Inputs are constructed numbers,
not measured production or estimates for a field. The reference identifier is
`eia-us-closed-form-v1`; expected values do not call production helpers.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-11-04 | Record source-qualified hand calculations, units and comparison limits; extend latest-rig selection to repeated row labels. |

## Source qualification

The original source basis is
`285d65c40896b17ccf44568e59f5b789d59c943e`. Main revision
`2003360f75d8c96c16a809eee1e6f7b55a723e48` is the source-comparison baseline;
both production files matched that revision before the summary correction.
It includes the earlier zero-reference correction and direct summary tests.
Those commits identify lineage only.
The evaluated production files are identified by the following SHA-256 digests,
relative to this package's `eia_us` directory:

| File | SHA-256 of evaluated source |
| --- | --- |
| `production/drilling_productivity.py` | `31d5fcfcd494c8ef815168114b5ab46766df067eff646ab6d8221d9381ba357d` |
| `analysis/us_fiscal.py` | `239215621f3f4e0c4b2fac9da5c6c5e977f57101342a987d2cf7b335465f1362` |

Table 1. Source snapshots for this reference revision. Changes to these sources
or either cited executable test module require a fresh assessment before this
snapshot is cited as evaluation evidence.

Digests cover LF source bytes as stored in Git. For a checkout that converts line
endings, read the Git blob or normalize CRLF to LF before reproducing the digest.

## DPR reference cases

Four observations are supplied in the order below. The rig-summary cases also
reverse their order. Each basin has a unique latest period. Dates establish
order only.

| Basin | Period | Rig count (rigs) | Assumed new-well contribution (bbl/day) | Legacy change (bbl/day) | Expected net change (bbl/day) |
| --- | --- | ---: | ---: | ---: | ---: |
| B | 2024-02-01 | 2 | 40.0 | -60.0 | -20.0 |
| A | 2024-01-01 | 3 | 120.0 | -50.0 | 70.0 |
| B | 2024-01-01 | 7 | 40.0 | -60.0 | -20.0 |
| A | 2024-02-01 | 5 | 120.0 | -50.0 | 70.0 |

Table 2. Constructed inputs and independently calculated rate changes.

For A, the latest observation has 5 rigs; for B it has 2 rigs. Sorting those
latest counts in descending order gives A then B. Earlier counts of 3 and 7 rigs
cannot enter the rig summary. The same rig-summary result applies with unique labels, labels
repeated within each basin, or one label shared across all rows. Row labels do
not identify observations. The output has a fresh zero-based integer index;
the complete caller frame is preserved.

The independent rate balances are `120 + (-50) = 70 bbl/day` and
`40 + (-60) = -20 bbl/day`. The net-change case checks the four rows in the
listed order.
These integers are exactly representable, so assertions allow zero numerical
error. Rig counts use units of rigs; `new_well_ip_bopd`,
`legacy_decline_bopd` and `net_change_bopd` use bbl/day. For these constructed
cases only, `new_well_ip_bopd` is assumed to be a basin-total new-well contribution.
That assumption does not qualify the mapping from published EIA DPR fields.
For these cases, `legacy_decline_bopd` is assumed to be a signed rate, negative
for decline; this does not qualify the sign convention of published fields.
A per-rig source rate would require a separately verified conversion before
addition to a basin-total rate. No conversion to monthly volume is assumed.

A separate equal-date characterization supplies two A observations at the same
latest date, with 8 then 2 rigs and a shared row label. The expected result is
the first input observation, 8 rigs. This preserves the existing selection rule;
it does not resolve conflicting source records as an engineering policy.
Empty input retains the summary columns.

Executable cases: `tests/unit/eia_us/test_drilling_productivity_summary.py`,
including `test_latest_rig_count_and_order`,
`test_latest_period_tie_keeps_first_observation`,
`test_net_change_hand_arithmetic` and `test_empty_summary_schema`.

## GoM reference and tolerance contract

`GoMCrosscheck.compare` consumes production rates in kbd, where
`1 kbd = 1,000 bbl/day`. `difference_kbd` is signed EIA minus BSEE in kbd.
For a nonzero BSEE reference, `pct_difference` is the absolute difference
divided by the absolute BSEE reference: a dimensionless fraction.
`tolerance_pct` also uses a dimensionless fraction; its default is 5.0 %.
The comparison includes equality with that limit. Neither quantity is in
percentage points, despite the existing API names.

| EIA rate (bbl/day) | BSEE rate (bbl/day) | Independent result | Agreement criterion |
| ---: | ---: | --- | --- |
| 0.0 | 0.0 | Difference zero; relative difference zero by convention | True at a zero relative limit |
| 40.0 | 0.0 | Difference 40.0 bbl/day; relative difference undefined | Indeterminate at both 5.0 % and 100.0 % limits |
| 1,100.0 | 1,000.0 | Difference 100.0 bbl/day; relative difference 10.0 % | False at 9.0 %; true at 11.0 % |
| 1,125.0 | 1,000.0 | Difference 125.0 bbl/day; relative difference 12.5 % | True at the limit; false at the adjacent float below it |

Table 3. Exact-arithmetic comparison expectations; rate units are shown before
conversion to the API's kbd.

For the nonzero/zero case, conversion gives exactly `1/25 kbd` mathematically.
Both `pct_difference` and `within_tolerance` return `None`. No denominator or
absolute acceptance tolerance is substituted. Zero/zero returns `0.0` and
`True` by convention. An explicit absolute-tolerance API is not provided.

For the nonzero-reference decimal case, binary conversion and subtraction
introduce rounding. The test's absolute assertion allowance is four ULPs at
1.1: in kbd for the signed difference, and dimensionless for the relative
fraction against the exact 1.0 kbd reference. This is a numerical assertion
allowance, not a production acceptance tolerance. The exact binary boundary
uses the fraction `1/8` and adjacent representable floats; its boolean decision
has zero numerical allowance.

Executable cases: `tests/unit/eia_us/test_zero_reference_crosscheck.py`, including
`test_nonzero_against_zero_is_indeterminate`, `test_zero_against_zero_agrees`,
`test_nonzero_reference_hand_arithmetic` and
`test_relative_tolerance_boundary_is_inclusive`.

## Limits

This reference qualifies constructed arithmetic and the tested frame shapes.
No independent measured dataset, live EIA/BSEE agreement, matching geographic
coverage or reporting vintage, fiscal rate, or current fiscal law is qualified.
Missing basins, missing or invalid dates, and engineering resolution of duplicate
basin-period records remain unqualified. Ordering between basins with tied rig
counts is unspecified. Normalization, decline fitting and forecast accuracy
require separate evidence. These constructed numbers are not valid production
inputs for an engineering assessment.
