# Well-access calibration analysis

The adapter estimates intervention demand from evidenced dry-tree well analogs
and reports production availability from normalized BSEE WAR and OGOR exports.
The saved example is synthetic. It establishes arithmetic and repeatability;
it is not an empirical calibration of any field or play.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Add evidence requirements, equations and a hand-calculated example. |
| 1 | 2026-10-20 | Reject conflicting report identities and malformed APIs before selection to prevent contradictory event rates. |

## Inputs and invocation

Run `uv run python -m worldenergydata config/input/well_access_calibration.yml`
from the repository root. The engine stores the result in
`cfg['bsee']['well_access_calibration']`. For smaller applications, call
`run_calibration(mapping)` or `build_calibration(wells, war, production, parameters)`.
Configure `outputs.calibration_yml` and `outputs.report_html` to retain results
outside the checkout. The HTML contains no external assets.

The example CSVs under `examples/well_access_calibration/` define the input
columns. API identifiers must be read as strings containing 12 ASCII digits
(wellbore) or 14 ASCII digits (wellbore and completion suffix). Surrounding
whitespace is stripped; missing values, nonnumeric suffixes and other lengths
are rejected in all three tables before cohort selection or wellbore truncation.
The well manifest supplies
`API_WELL_NUMBER`, `LEASE_NUMBER`, `tree_type`, and `first_production`, with optional
`last_observed` (exclusive). First production must be independently evidenced;
the first record in an incomplete production extract is not sufficient.
Observation end is exclusive. Observation start and end, first production,
report dates and optional last observation must use the same time basis.

Only verified well-level SPAR, TLP or MTLP tree evidence qualifies a well for the
cohort. This code policy follows the issue #510 implementation plan (2026).
Merely sharing a lease with a qualifying structure does not establish a dry-tree
well. `analog_basis` records the evidence supporting the manifest. No unchecked
platform-to-lease join is attempted. Subsea wells are excluded; subsea access
multipliers are not estimated here.

WAR requires `SN_WAR`, `API_WELL_NUMBER`, `WELL_ACTIVITY_CD`, `WAR_START_DT` and
`WAR_END_DT`. An optional `war_properties_csv` supplies the raw activity column
by a validated many-to-one `SN_WAR` join instead. Raw activity tokens are retained
as opaque source data. Report IDs must be nonempty after whitespace is stripped.
Repeated `SN_WAR` values must agree on the full normalized API, parsed start and
end dates, and explicit intervention label, together with any supplied
classification evidence, activity code and rig name. Conflicts are rejected
before cohort selection or inferred classification, including conflicts with
excluded wells. Exact duplicates and differences in unrelated metadata do not
add events or duration. The canonical
`bsee/analysis/data/war_activity_codes.yml` (2026, data vintage 2026-02-19)
records that no published WELL_ACTIVITY_CD domain was found, and that `WO` and
`REC` have unknown meanings. Legacy display strings in `ops_timeline.py` are
explicitly not definitions. They must not be used as calibration evidence.

Independently reviewed rows can supply `INTERVENTION_TYPE` (workover,
recompletion or light_well_intervention) together with a nonempty
`CLASSIFICATION_BASIS` evidence reference. These are normalized analyst inputs,
not claimed BSEE code meanings. The saved example supplies synthetic labels.
Absent explicit labels, raw `WO`, `REC` and `ST` tokens produce no demand rates.
A new nonzero completion suffix is inferred as recompletion only after a prior
suffix has been observed; explicit event labels take precedence. The API
wellbore convention follows `ops_timeline.py:detect_reentries` (2026). Optional
`RIG_NAME` uses the existing `classify_rig_type` heuristic for wireline, coil,
liftboat and snubbing signals. Recompletion and light-intervention estimates
always carry low confidence because these heuristic signals are not a validated
record of demanded interventions.

Production requires `API_WELL_NUMBER`, `LEASE_NUMBER`, `PRODUCTION_DATE` in YYYYMM
form and `DAYS_ON_PROD`. The column basis is the repository's
`lower_tertiary/ops_timeline.py:OGOR_COLUMNS` and
`bsee/analysis/production_api12.py` (2026). Exact duplicate rows are removed.
Conflicting well-month observations, including multiple completions, are
rejected instead of silently summing production days above a calendar month.

## Method and sources

For age band `[a, b)`, well first production `f`, evidenced follow-up end `l`,
WAR observation window `[s, e)` and user-selected days per model year `Y`:

```text
exposure_days = max(0, min(e, l, f + b*Y) - max(s, f, f + a*Y))
exposure_years = sum(exposure_days) / Y
lambda(type, band) = event_starts(type, band) / exposure_years
```

The rate equation adapts observed person-time incidence to recurrent well events:
[CDC, Principles of Epidemiology, third edition (2012), lesson 3, section 2,
“Incidence rate or person-time rate”](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/lesson3/section2.html).
Interval intersection is the direct hand derivation of observed time within an
age band. The issue #510 specification (2026) requires clipping exposure to WAR
coverage. `coverage_basis` must establish completeness during that interval and
per-well follow-up; earliest/latest records alone do not establish completeness.
The historical feed has limited coverage, described as approximately 2014 onward
in `ops_timeline.py:derive_spud_milestones`; the adapter embeds no fixed start year.

Same-well, same-type report windows form one event when the next window begins
within the supplied `event_gap_days` of the cluster end. Duration is the union
of covered report spans; gaps are excluded and overlapping days counted once.
This is an explicit observation definition, following the issue #510 clustering
requirement with overlap correction. It is not a measured resource occupancy
model. The median of complete positive event durations supplies `duration_days`;
linear empirical quartiles and the range describe the distribution. Events
starting before the observation window are excluded as left censored. Events
starting inside it count toward rates, but incomplete durations are excluded.

For fully observed well-months only:

```text
monthly_availability = DAYS_ON_PROD / calendar_days_in_month
suggested_availability = sum(DAYS_ON_PROD) / sum(calendar_days_in_month)
```

These ratios define the production-day proxy required by issue #510 (2026),
using the OGOR column basis above. Calendar lengths come from each actual month,
including leap years. Monthly quantiles and lease summaries are unweighted;
the suggested scalar is day weighted. Missing months are counted explicitly and never filled as zero;
partial months are omitted because monthly totals cannot resolve daily timing.
Production downtime does not identify facility-caused downtime. Review the proxy
before copying it into the consumer's `input.yml` under
`well_program.facility_availability`; the consumer ignores `uptime` in calibration.

No empirical coefficients or acceptance limits are embedded. `days_per_year`,
`band_edges_yr`, `event_gap_days`, `min_events` and `min_exposure_years` are required
policy inputs. Low confidence follows a type's total event count, any band's
exposure floor, censored durations or heuristic recompletion/light-intervention signals.
Unlabelled reports are counted and also force low confidence; their absence
from a type must not imply that no intervention occurred. Classification
evidence references accompany the aggregate output. Sparse Lower-Tertiary
evidence remains a caveat on every output. Unexposed bands
are omitted. A type without positive complete duration evidence is
`NOT_EVALUATED` and omitted from `base_rates`. This prevents an unsupported zero
duration from appearing as a valid engine calibration. Omitted types must not
be interpreted as evidence of zero demand.

The consumer contract was read at digitalmodel revision
`84aa1f618eccd06a21b4d79d8c47fd99166c6a8f` (2026),
`src/digitalmodel/well_access/intervention_rates.py:build_intervention_types`.
Evaluated entries use its `duration_days`, `resource_class`, `low_confidence` and
`age_curve` fields. Only its supported type names are emitted: workover,
recompletion and light_well_intervention. Extra diagnostics, uptime, caveats and
input digests remain outside `base_rates`. No consumer package is imported.

## Worked example: inputs, method and answer

Every number here is a selected synthetic test input, not a field estimate.
The model year has 100 days for transparent arithmetic. The observation window
contains 200 days. One verified dry-tree well contributes 100 days to each of
`[0, 1)` and `[1, 2)` years, or 1.0 well-year per band. A second, subsea well
contributes no demand exposure.

Workover windows `[10, 20)` and `[15, 25)` days after first production overlap.
They form one event with `25 - 10 = 15.0` covered days. The first band's rate is
`1 / 1 = 1.0` event per well-year; the second is `0 / 1 = 0.0`. The event-count
threshold is the synthetic input 2, so the workover result is low confidence.
No recompletion or light-intervention duration was observed; those types are
`NOT_EVALUATED`, without invented demand rates or resource days.

February 2020 has 29 days, all on production. March has 31 days, none on
production. The suggested proxy is `29 / (29 + 31)`, or 48.3 %. The two monthly
fractions are 1.0 and 0.0. Tests compare the unrounded ratio to an independent
hand calculation; reporting rounds percentages to one decimal place.

Repeated runs on identical input bytes produce identical YAML. SHA-256 digests
identify each normalized input file; the original exports remain unchanged.
No wall-clock run time or absolute input path is included in the output.

## Real-data validation and later slices

Set `WED_DATA_ROOT` to the available data root. To enable the real-data smoke
test, supply `modules/bsee/well_access_calibration/parameters.yml` and reviewed
`wells.csv`, `war.csv`, `production.csv` there. The parameters mapping has the
same required policies as the saved example, with independently evidenced
coverage and well-tree identity. Binary presence alone cannot establish these
facts. The smoke test skips explicitly when those reviewed exports are absent.

The delivered slices cover the pure calculations, durable engine workflow,
deterministic YAML and offline evidence report. A real-data dated snapshot,
platform/well join qualification, independent spot checks on a real BSEE subset
and play-specific calibration remain pending reviewed local data. The source
catalog metadata was unavailable during implementation, and no alternate catalog
was created. These limits prevent claiming completion of the empirical snapshot
requirement. Refs #510; the issue remains open for these evidence tasks.
