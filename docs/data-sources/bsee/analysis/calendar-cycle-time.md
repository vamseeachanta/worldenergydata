# Well calendar cycle time

The well benchmark reports elapsed calendar components. Calendar spans include
waiting, suspension and overlapping well activity; their sum cannot establish
active drilling time, rig occupancy or a learning effect.

## Revision history

| Revision | Date | Change and reason |
|---|---|---|
| 1 | 2026-10-19 | Define calendar intervals and migration to prevent rig-time interpretation. |

## Inputs and method

Source: issue #1077 (2026), benchmark definition; date arithmetic follows
[Python 3.13 (2024), date objects](https://docs.python.org/3.13/library/datetime.html#date-objects).
No engineering coefficient or acceptance threshold is required.

- Benchmark `spud_to_completion_calendar_days` = earliest completion marker minus
  spud, in elapsed days. The former `drilling_days` alias is removed.
- Benchmark `completion_days` = first oil minus earliest completion marker,
  also in elapsed calendar days. It does not establish active completion time.
- Insight `spud_to_td_calendar_days` = TD date minus spud date. Its download
  carries `basis=calendar_elapsed_spud_to_td`.
- Missing endpoints and reversed intervals produce null components. Equal dates
  give zero elapsed days. Neither endpoint is counted inclusively.

The benchmark retains its producing-well population and configured spud-year
window. The insight uses every named workbook row, with valid chronological
spud/TD dates required for statistics. Blank lease names, including totals rows,
are excluded. The download retains missing intervals and source metadata.
`legacy_reported_completion_days` preserves the workbook's reported completion
values without validating their basis; it is excluded from calendar statistics.

## Worked example

Synthetic inputs: spud 2020-01-01, TD 2020-01-08, first completion 2020-03-01,
first oil 2020-06-09. Independent hand calculation:

- Spud to TD: 8 minus 1 = 7 calendar days.
- Spud to completion: January 31 + February 29 = 60 calendar days (leap year).
- Completion to first oil: March 31 + April 30 + May 31 + June 8 = 100 days.
- Whole spud-to-first-oil span: 60 + 100 = 160 calendar days.

The first interval and the benchmark's first component have different endpoints.
Neither represents active rig time.

## Population reconciliation and limits

Issues #1077 and #1062 (2026) record a former 184-wellbore, 11,124-day claim versus
an article's 211-well, 21,944-day claim. The former selected positive legacy
workbook durations. The revised insight selects chronological dated intervals.
The count difference is 211 minus 184 = 27, but the populations and definitions
differ. It does not establish 27 missing drilling records or a performance gap.
Exact paired membership, the article's operational day basis and active rig time
are **NOT_EVALUATED** from these inputs. The saved benchmark is a separate
producing-well cohort. Its per-well values are preserved during schema migration.

## Reproduction and migration

For checkouts with raw inputs, regenerate the benchmark normally:

```bash
python scripts/lower_tertiary/build_well_benchmark.py --config config/input/lt_well_benchmark.yml
python scripts/lower_tertiary/build_drilling_insights.py
```

For a saved benchmark without raw production inputs, rename its column with the
repository's schema migration, which preserves all source cells:

```bash
python scripts/lower_tertiary/build_well_benchmark.py --migrate-saved-csv reports/lower_tertiary/lt_well_benchmark_lower_tertiary_2010_latest.csv
```

Consumers requesting the removed alias must use the explicit calendar name.
The presentation consumers use production, economics or well counts; the
Markdown renderer and saved configuration now use the calendar field. The
historical day-basis comparison reads the explicit calendar column while
preserving its diagnostic schema and frozen comparison values. Its historical
`published_drilling_days` key is a comparison container, not a rig-time assertion.
The historical insight URL remains available, with a revised CSV schema and an
explicit download. Legacy learning classifications are no longer published by
this page; the separate analytical helper is not a rig-time authority.

The schema migration does not recompute economics, production or activity-coded
D&C datasets. Recomputing raw production inputs and validating paired article
membership require separate evidence.
