# WAR duration methodology and publication limits

WAR-derived durations require a declared basis, a depth convention when
normalized, and a coverage statement. The weekly reporting cadence limits
inference from status rows. It does not turn a calendar interval into active
rig time. This note describes publication metadata; it changes no day count.

## Revision history

| Revision | Date | Change and reason |
|---|---|---|
| 1 | 2026-10-22 | Documented the capability export and a synthetic calculation so consumers can retain the duration limits. |

## Source limits

- **Weekly boundary quantization.** The official annual CFR, 2025 edition,
  [30 CFR 250.743(a)](https://www.govinfo.gov/content/pkg/CFR-2025-title30-vol2/xml/CFR-2025-title30-vol2-sec250-743.xml),
  requires Gulf of Mexico weekly WAR periods from Sunday midnight through
  Saturday 23:59. A period is at most seven days; first and last periods may
  be shorter, and more frequent reporting may be required. Inferring a phase
  transition only from weekly statuses introduces roughly a week of boundary
  ambiguity. This is an inference from reporting cadence, not a statistical
  confidence interval or a guaranteed error bound on narrative-derived dates.
- **Reported April 2004 coverage floor.** The repository Makefile comment above
  the data target records this electronic-submission date. The
  [BSEE bulk-file listing](https://www.data.bsee.gov/Main/RawData.aspx),
  [field definitions](https://www.data.bsee.gov/Well/eWellWAR/FieldDefinitions.aspx)
  and [online query](https://www.data.bsee.gov/Well/eWellWAR/Default.aspx)
  examined on 2026-10-22 do not establish a hard bulk-file floor or completeness
  of earlier paper reports. Historical completeness remains `NOT_EVALUATED`.
  Earlier report dates in a local feed do not establish complete coverage.
  Missing reports cannot be interpreted as zero days.
- **MD versus TVD.** Measured depth (`MAX_BH_TOTAL_MD`) and true vertical depth
  (`MAX_WELL_BORE_TVD`) are distinct denominators. The existing legacy ratio
  uses MD minus water depth, with a lower bound in
  `scripts/extract_all_well_data.py`; the learning-series convention differs.
  `bsee.analysis.drilling_intensity` requires an explicit denominator and uses
  the selected full depth. Its ratio must not be silently substituted for a
  legacy below-mudline ratio.
- **Publisher-declared duration basis.** No official active drilling-days
  definition was found in the cited agency pages. The
  [superseding basis decision](https://api.github.com/repositories/574746314/issues/comments/6132640847)
  selects drilling days = TD date minus spud date, and completion days =
  distinct reported days from TD onward across all activity codes, excluding
  unreported gaps. Activity-code days and the earlier interim rule remain
  separate columns. Wider-population confirmation precedes replacement of
  published figures. The activity comparison page retains its activity basis.

The public publisher-deposited abstract of **SPE-87117-MS (2004), Deepwater
Success Through Predictable and Distinctive Drilling and Completion
Performance**, [paragraph 4](https://api.crossref.org/works/10.2118/87117-MS),
reports a deepwater reference range of **20–23 days per 10,000 ft**. Its abstract
does not establish MD versus TVD or equivalence to milestone calendar days.
Reference comparability remains `NOT_EVALUATED`; this range is a plausibility
reference, not an acceptance threshold or evidence that a well is efficient.

## Capability and dataset consumers

`scripts/build_pages.py --domains lower_tertiary` emits `war-methodology.json`
beside the duration pages. `methodology_metadata()` in
`scripts/lower_tertiary/war_methodology.py` supplies the same content directly.
The export contains:

| Field | Consumer meaning |
|---|---|
| `data_limits` | Shared Markdown disclosure to display alongside day counts. |
| `basis_decision_url` | Superseding duration decision. |
| `coverage_floor_status` | `NOT_EVALUATED`: agency confirmation is absent. |
| `reference_comparability_status` | `NOT_EVALUATED`: depth and duration bases are not established as comparable. |
| `depth_denominator_policy` | Explicit MD or TVD selection is required. |

Capability consumers can copy `data_limits` into their capability metadata.
The dataset-card builder already uses the same shared note. This change
prepares the local export; it does not publish a remote dataset card or update
an external website. The statuses describe missing evidence, not a true zero
or a failed operational result.

## Worked example: declared calendar basis and depth

The following inputs are synthetic arithmetic examples, not a measured well,
operating assumptions, or acceptance limits:

| Input | Value |
|---|---|
| Spud date | 2025-01-01 |
| TD date | 2025-02-12 |
| Selected duration basis | Milestone calendar, exclusive date difference |
| Full MD | 20,000 ft |
| Full TVD | 15,000 ft |

Under the superseding decision's drilling equation, elapsed days are
31 days in January plus 11 days in February = **42 days**. No inclusive
endpoint adjustment is added. The normalization is the dimensional conversion
from days/ft to days per 10,000 ft, using the reporting scale in the cited
SPE abstract. The selected depth remains an explicit input:

```text
MD ratio  = 42 / 20,000 × 10,000 = 21.0 days per 10,000 ft MD
TVD ratio = 42 / 15,000 × 10,000 = 28.0 days per 10,000 ft TVD
```

The MD result lies numerically in the published range; this does not establish
comparability because milestone days include waiting and suspension, and the
abstract's denominator is undeclared. Both ratios retain the supplied basis.
The regression example in `test_war_methodology_metadata.py` writes out this
independent hand calculation and exercises both denominator selections.

## Remaining evidence and publication work

Agency confirmation of historical completeness, comparable depth and duration
definitions for the reference range, external capability integration and live
dataset-card publication remain outstanding. No source data or financial
result is restated by this documentation change.
