# Legacy field-development component retirement

The unused `ONGFDComponents` coordinator and its drilling helpers are retired
together. Their useful WAR capabilities already live in
`worldenergydata.bsee.analysis.war_rig_days`: per-rig credits, maximum reported
drilling-fluid weight, and separate sidetrack, temporary abandonment and
permanent abandonment activity buckets. Reporting gaps do not establish NPT.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Retire the unused component after checking the retained capabilities; document inputs, arithmetic, provenance and limits. |

## Scope and caller evidence

The source tree is split into distribution members. The retired files were
under `packages/worldenergydata-core/src/worldenergydata/common/legacy/`:

- `ong_fd_components.py`: superseded implementation, with no importers.
- `ong_fd_components_refactored.py`: coordinator exported as `ONGFDComponents`.
- `ong_fd_drilling.py`: called by that coordinator, so it could not be removed
  on its own.

The package initializer no longer imports those modules or exports
`ONGFDComponents`, `get_rig_days_and_drilling_wt` or `assign_st_bp_tree_info`.
The remaining exports, including `calculate_drilling_completion_summary`,
are retained. `common.legacy.data` is unaffected.

Before removal, the following search found definitions, exports and internal
calls in the connected component. Outside it, Python matches were historical
comments/docstrings, including the already ported WAR module and its tests:

```sh
rg -n 'ONGFDComponents|ong_fd_components|ong_fd_drilling|get_rig_days_and_drilling_wt|assign_st_bp_tree_info' packages src scripts tests --glob '*.py'
```

The retirement regression test also checks import edges in `packages/`,
`src/` and `scripts/`, checks that the deleted modules cannot be found, and
imports the remaining legacy exports and data utilities. Repository searches
cannot establish whether an external consumer exists. Future users of these
removed import paths must migrate to the modern analysis API.

The sidetrack/bypass suffix and subsea-tree elevation lookup had no caller
outside the retired coordinator. It is therefore not ported. The modern
`bore_suffix` is an API12 suffix, not a substitute for the separate end-of-well
metadata fields. No tree elevation or bypass value is synthesized.

## Replacement and provenance

```python
from worldenergydata.bsee.analysis.war_rig_days import (
    rig_days_by_bore,
    rig_days_by_well,
)

bores = rig_days_by_bore(joined_war)
wells = rig_days_by_well(joined_war)
```

Supply WAR main records joined to their activity/property records on `SN_WAR`.
Preserve source records and join provenance upstream; the summary is not a
row-level audit ledger. Required input fields are `API_WELL_NUMBER`,
`WAR_START_DT`, `WAR_END_DT` and `WELL_ACTIVITY_CD`. Optional fields are
`RIG_NAME` and `DRILL_FLUID_WGT`.

| Capability | Output | Basis and limits |
| --- | --- | --- |
| Per-rig credits | `rig_days_by_rig` | Union of valid intervals for each stripped, case-folded identity. First spelling is displayed. Missing/blank identities use `None`. Overlaps between different rigs credit each rig; the credits are not a partition of total coverage. |
| Fluid weight | `max_drill_fluid_wgt` | Maximum valid `DRILL_FLUID_WGT` supplied by the caller, in ppg. Null if no valid value exists. See the input contract below. |
| Additional phases | `sidetrack_days`, `temp_abandonment_days`, `perm_abandonment_days` | Separate unions of ST, TA and PA intervals, with companion status fields. Names are inferred interpretations, not published WAR activity definitions. |
| Well coverage | `war_days_total` at API10 | Union across bores; additive bore totals are reported separately. |

The emitted `basis` records the drilling/completion code selection and
inclusive counting convention. Phase membership is configurable at bore grain.
The canonical [activity-code provenance file](../../../../packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/data/war_activity_codes.yml)
(retrieved 2026-07-28) records that ST, TA and PA reuse tokens published for
`BOREHOLE_STAT_CD`; their reuse as WAR activity meanings remains inferred.
The reporting rule does not establish that code mapping. In particular, a
phase name is not a validated interpretation of every operation during a week.

### Interval method

For calendar dates $s_i$ and $e_i$, retain valid intervals with

$$
I_i = \{s_i, s_i+1\text{ day}, \ldots, e_i\},\qquad e_i\ge s_i.
$$

The measured coverage is the cardinality of their union:

$$
D = \left|\bigcup_i I_i\right|
  = \sum_{j\in\text{merged spans}} ((e_j-s_j).\mathrm{days}+1).
$$

The endpoint convention follows [30 CFR 250.743(b), 2024 edition](https://www.govinfo.gov/content/pkg/CFR-2024-title30-vol2/pdf/CFR-2024-title30-vol2-sec250-743.pdf):
the reporting week runs Sunday through Saturday and covers at most seven
calendar days. Inclusive counting makes a complete reporting week seven days.
Unioning overlapping intervals is the analysis method, not a regulatory
equation. Adjacent intervals can be merged without changing the set of days.
It measures reported calendar coverage, not operating hours or rig utilization.

For each rig, apply the same union to its own records. A rig change with
overlapping returns credits both rigs for the overlap because the feed does
not allocate hours between them. At API10, union the underlying bore intervals
instead of adding per-bore totals. No equation adds reporting gaps to activity.
Under a basis that includes TA in completion, the TA phase and completion
overlap; adding those columns would double-count.

### Fluid-weight contract

The caller must supply `DRILL_FLUID_WGT` in ppg. [Form BSEE-0133, expiration 2024](https://www.bsee.gov/sites/bsee.gov/files/form-0133-exp-2024.pdf),
item 10, labels the mud-weight entry MW / PPG. No unit conversion or unit
detection is attempted. The field's mapping to that entry is an input contract,
not something the summary can verify from an unlabelled number.

For rows with usable intervals, coerce weight entries to numeric values and
retain the finite positive set $V$. Then

$$
W_{\max}=\max V\quad\text{if }V\ne\varnothing;
\qquad W_{\max}=\mathrm{null}\quad\text{otherwise}.
$$

Finite and positive are input validity rules, not a sourced engineering
acceptance range. Zero continues to mean unreported under the existing port's
contract (#1119); negative, nonnumeric, missing and infinite values are excluded.
No upper physical limit, formation-pressure model or design acceptance limit
is introduced. Engineering suitability is **NOT_EVALUATED**: it requires
qualified source data and application-specific criteria. Weight values on
rejected reversed-date rows cannot affect this maximum; rows without usable
endpoints also do not contribute. The maximum spans all activity codes in the
usable records, not just DRL.

## Worked example

Run `uv run python examples/bsee/war_rig_days.py` in the repository environment.
The example prints inputs, bore results, rig credits, fluid units, basis and
well results. All values are synthetic inputs for arithmetic checks; none are
field measurements or acceptance limits. API12 `120000000100` and
`120000000101` denote two bores of the same synthetic well.

| Bore | Start | End | Activity token | Rig identity | Weight input, ppg |
| --- | --- | --- | --- | --- | --- |
| 00 | 2024-01-07 | 2024-01-13 | DRL | Unit A | 12.0 |
| 00 | 2024-01-10 | 2024-01-16 | DRL | ` unit a ` | 14.0 |
| 00 | 2024-01-14 | 2024-01-20 | ST | Unit B | 13.5 |
| 00 | 2024-01-21 | 2024-01-27 | TA | missing | 0.0, unreported |
| 00 | 2024-02-04 | 2024-02-10 | PA | Unit B | missing |
| 00 | 2024-02-11 | 2024-02-17 | COM | Unit B | infinity, invalid |
| 01 | 2024-01-14 | 2024-01-20 | DRL | Unit A | 11.5 |

Independent hand calculation:

- Bore 00 drilling: Jan 7–13 union Jan 10–16 = Jan 7–16 = **10 days**.
- ST, TA, PA and COM each occupy a separate seven-day span.
- Bore 00 total: Jan 7–27 plus Feb 4–17 = 21 + 14 = **35 days**.
- Rig credits: Unit A = 10; Unit B = 7 + 14 = 21; no identity = 7.
  Their sum is 38 because Jan 14–16 credits both rigs for three days.
- Bore 00 valid weights are 12.0, 14.0 and 13.5; the maximum is **14.0 ppg**.
- Bore 01 drilling and total are seven days. At well grain, drilling is
  Jan 7–20 = **14 days**, rather than the additive bore total 10 + 7 = 17.
  Overall well coverage remains **35 days**, rather than 35 + 7 = 42.
- Jan 28–Feb 3 has no reported interval. Its seven days contribute no measured
  activity; neither downtime nor NPT is inferred.

`test_war_rig_days_retirement.py` checks these answers independently and covers
invalid weights and rejected intervals. Existing WAR tests cover uncovered
populations, same-day intervals, duplicates, phase configuration and nulls.

## Defects and heuristics retained only as history

The retired implementations mixed incompatible measurement bases and contained
these defects, recorded in #1112 and confirmed in the removed source:

- Conditional day counting added an endpoint only to positive elapsed spans:
  same-day records counted as zero and reversed records could reduce totals.
- Chained pandas assignments depended on copy-on-write behavior.
- The metadata lookup discarded `sort_values` and read an arbitrary first row.
- A flag switched drilling from the spud-to-TD calendar span to WAR-derived
  time, with no basis recorded beside the result.
- Summing interval lengths double-counted overlapping reports and bore weeks.
- Unsorted consecutive-report gaps were attributed to activity statuses as NPT;
  errors and missing evidence could become zero.

The historical 90-day ceiling came from the removed `max_allowed_npt` default
and its gap branch (#1112). A larger pre-TD gap triggered the assumption that
the well was suspended and that the calendar span should be replaced. The
250-day calendar switch recorded in #1068 addressed the same underlying
suspended-well problem. These are historical heuristics, not accepted limits
or evidence of NPT. Neither is introduced into the replacement. Existing WAR
span-quality diagnostics are separate from any interpretation of reporting gaps.

## Known limits and later work

No gap-derived NPT, branch/tree metadata API or engineering fluid-weight
acceptance check is provided. Actual NPT requires an affirmative operational
source. Confirming WAR activity definitions remains the source-provenance work
tracked in #1065. This retirement does not revalidate previously published
datasets or change the existing well-pipeline adapter.
