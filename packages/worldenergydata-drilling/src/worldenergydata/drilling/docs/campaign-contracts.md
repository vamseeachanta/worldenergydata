# Drilling campaign contracts and duration assumptions

Campaign costs require finite, typed inputs, a complete well sequence and at
least one well. Learning and first-well duration assumptions are supplied by the
caller. The retained cost law uses individual-well durations. The mathematical
form is sourced; drilling calibration and applicability are **NOT_EVALUATED**.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-22 | Define input and completeness contracts, remove unqualified numeric defaults and distinguish duration interpretations with independent hand calculations. |

## Input and completeness contracts

The table in `batch_economics/models.py` is the field, unit, sign and finiteness
contract for both models and calculator calls. Counts require integers; real
numbers reject Boolean values, numeric strings, NaN and either infinity.
Missing required numeric inputs raise errors rather than receiving defaults.
Nonblank identifiers/categories and Boolean `mpd_required` are also enforced.
Water depth and mobilization may be zero; measured depth, duration and day rate
must be positive. Coordinates are finite signed latitude/longitude values in
decimal degrees; geographic bounds and datum remain unqualified.

`ValidationError.errors()` provides named locations, error types and messages.
Positional direct-call errors also name the parameter. Nested failures retain
the campaign, well index and field. Models reject extra fields. Calculation
entry points and `ordered_wells()` revalidate models, including mutable lists.

A campaign contains unique well IDs. An absent or empty sequence explicitly
selects insertion order. A nonempty sequence must contain every well exactly
once. Duplicates, unknown IDs and omitted IDs raise errors naming the identifier
at the `sequence` field. Duplicate well definitions fail at `wells`. Rejection
is chosen because dropping rows would change both the learning position and the
cost denominator without warning. A zero-well campaign raises
`wells must contain at least one well`; filtering every well out is the same
case. There is no economics-layer exclusion mechanism or partial-cost result.

Metadata defaults remain documented: `bore_design="standard"`,
`mpd_required=False`, and an empty sequence meaning insertion order. These are
representation conventions, not calibrated engineering assumptions.

## Duration law and sources

The public primary source opened for this change is NASA's
[Guidelines for Application of Learning/Cost Improvement Curves (1975)](https://ntrs.nasa.gov/api/citations/19760006882/downloads/19760006882.pdf).
Section IV.A-B, printed pages 6-7, distinguishes cumulative-average and
individual-unit observations. Section VII.B, printed page 15, numbered formulas
1-2, gives the power-law form and slope relation. The NASA repository copy was
retrieved successfully on 2026-10-22. Its mathematical form is used here; no
claim is made to have inspected the original historical papers.

Define the supplied factor `L` as the ratio when quantity doubles. The equations
below normalize the source's slope notation into a signed exponent `e`:

```text
D1: 2**e = L, so e = log(L)/log(2).
D2 (individual duration): t(n) = T1 * n**e.
D3 (individual total): S(N) = sum(t(n), n=1..N).
A1 (average duration): A(N) = T1 * N**e.
A2 (average-reading total): C(N) = N*A(N) = T1*N**(1+e).
A3 (marginal duration): C(n)-C(n-1), with C(0)=0.
```

D1-D2 and A1 follow the NASA formulas and the ordinate definitions in IV.A-B.
D3, A2 and A3 are summation, average-times-count and differencing identities,
respectively. `T1` and all durations are in days; `n` is a one-based count;
`L` and `e` are dimensionless. The API domain `0 < L <= 1` expresses a
nonincreasing individual-time law, not an empirically established calibration
range. For a positive marginal-time interpretation of A3, `1+e > 0` is required.

`learning_curve_time` returns D2; cost methods apply D3. This retains the
previous individual-duration arithmetic and corrects the cumulative-average
label. A1 has the same ordinate but A2 is a different total. The cost API does
not offer a cumulative-average mode. A factor fitted to individual durations
cannot be assumed transferable to average-duration data. The detector's fit
provenance/default status must be assessed separately before supplying a factor.

### Coefficient basis and retained limits

| Quantity | Previous basis in repository | Current handling |
| --- | --- | --- |
| Learning factor | Default fraction 0.85 in the former model and calculator signatures | Required input; drilling calibration **NOT_EVALUATED** |
| First-well days | Automatic depth heuristic, with empty-list fallback 60 days | Explicit `base_days_per_well` required by comparison; empty campaigns rejected |
| Depth coefficients | Former helper used MD/400 + WD/2000 + 10, floored at 30 days | Every coefficient required when the helper is called; empirical basis **NOT_EVALUATED** |
| Annual discount fraction | Former default 0.10, unused | Optional `None`, no assumed rate; supplied values validated but still unused |

The previous values are recorded by the knowledge pack's historical section 3
and the pre-change `_estimate_base_well_days` definition. They are provenance
for the migration, not recommendations. No public source examined establishes
these drilling coefficients, their calibration population or their applicable
depth/duration range. They are neither silently substituted nor presented as
qualified defaults. No field-measured duration reference is established.

The optional depth arithmetic is explicitly
`max(mean_MD/a + mean_WD/b + c, d)`, where `a` and `b` are ft/day and `c` and
`d` are days. Water depth contributes a separate additive term; it does not
multiply measured depth. The former implementation added 10 fixed days while
its prose said 20; the expression is retained with caller-supplied `c` and
corrected prose. The comparison no longer invokes it automatically. The helper
only evaluates assumptions; it does not validate their engineering basis.

The legacy NPV names still return undiscounted positive costs and their
difference. `n_wells_standalone` is validated but remains unused in allocation.
Break-even search/fallback semantics remain as before. These limits remain
tracked separately in #1345. Finite inputs alone do not establish numerical
conditioning or prevent overflow for extreme magnitudes. No upper-magnitude
engineering limit is introduced without calibration.

## Worked synthetic three-well example

Source for the formulas: NASA (1975), sections IV.A-B and VII.B.1-2 above.
Every input here is deliberately synthetic, not a field benchmark. Expected
values are hand calculations reproduced in executable test docstrings.

Inputs: wells `W1`, `W2`, `W3`, each with MD 8000 ft and water depth 2000 ft;
finite coordinates `(0.0, 0.0)`; 100 USD/day rig rate; one 300 USD mobilization;
first-well duration 12 days; learning factor `1/sqrt(2)`; sequence
`W3, W1, W2` (a complete permutation). Stored depths do not determine the
explicitly assumed 12-day base.

D1 gives `e=-1/2`. Under the individual-duration reading, the durations are
`12`, `6*sqrt(2)` and `4*sqrt(3)` days. Their sum is
`12+6*sqrt(2)+4*sqrt(3)` days. Under the average reading the cumulative total is
`12*sqrt(3)` days; marginal durations are `12`, `12*(sqrt(2)-1)` and
`12*(sqrt(3)-sqrt(2))` days.

| Result | Individual-duration reading (API) | Cumulative-average reading (comparison only) |
| --- | --- | --- |
| Three-well duration | 27.4 days | 20.8 days |
| Batch cost, 300 + 100 times duration | 3041.3 USD | 2378.5 USD |
| Standalone cost, 3 times (300 + 100 times 12) | 4500.0 USD | 4500.0 USD |
| Savings relative to standalone | 1458.7 USD | 2121.5 USD |

Displayed values are rounded to one decimal; tests compare unrounded radical
expressions. Absolute tolerances are 1e-12 days and 1e-8 USD, relative tolerance
zero. These are arithmetic roundoff allowances, not engineering acceptance
limits. They separate the two totals and cannot validate field predictions.

A separate depth-arithmetic example deliberately supplies the old coefficients
as assumptions: `a=400`, `b=2000` ft/day, `c=10`, `d=30` days. The hand result is
`max(8000/400+2000/2000+10,30)=31` days; increasing only `d` to 40 gives 40 days.
These exact integer results require no tolerance and do not calibrate the model.

A rejected input: `planned_md_ft=float("nan")` fails with field
`planned_md_ft` and error type `finite_number`. A sequence `W1, W2` fails with
`sequence omitted identifiers: W3`; `W1, W1, W3` names the duplicate `W1`.
An unknown identifier is rejected rather than silently excluded.

## Executable evidence and migration

- `tests/unit/drilling/test_campaign_contracts.py`: finite/type/sign/required
  field classes, complete/duplicate/unknown/omitted three-well sequences, empty
  and all-excluded campaigns, and revalidation after mutation.
- `tests/unit/drilling/test_duration_qualification.py::test_individual_duration_reference`:
  D1-D3, independent radical expressions and exact campaign cost identity.
- `tests/unit/drilling/test_duration_qualification.py::test_cumulative_average_reference`:
  A1-A3 and the independent alternative total; this is a mathematical reference,
  not an additional cost mode.
- `tests/unit/drilling/test_duration_qualification.py::test_depth_arithmetic_reference`:
  explicit coefficients, fixed-term correction and floor behavior.
- Remaining tests in that file require factor/base/coefficient inputs and check
  structured errors, invalid coefficients and the unused discount argument.

Migration: supply `learning_curve_factor` in every campaign; supply `lc_factor`
to direct learning and break-even calls; supply `base_days_per_well` as a keyword
to `batch_vs_standalone_npv`. `campaign_total_cost` already requires the base.
If using the depth helper explicitly, provide all four coefficients and retain
external calibration evidence. Do not substitute detector fallbacks without
reviewing their diagnostic status. A failed contract must be corrected before
calculating a complete campaign total.
