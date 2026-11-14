# Benchmark calendar spans

The producing-well benchmark reports elapsed calendar intervals. The column
`spud_to_completion_calendar_days` means first completion operation date minus
spud date. It includes waiting and suspension. It does not measure active
drilling time. The calendar cycle-time page separately shows TD minus spud.

## Revision history

| Revision | Date | What changed and why |
|---|---|---|
| 1 | 2026-10-22 | Define the retained calendar schema and synthetic arithmetic so spans cannot be mistaken for active rig time. |

## Inputs, method and answer

Source: issue #1077, Problem and Work; the implementation is
`benchmark_well` in `packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/well_benchmark.py`.
Date subtraction follows Python 3, `datetime`, “timedelta objects”.
This is date arithmetic; no engineering day basis or coefficient is introduced.

Synthetic input (not a real well):

| Spud | TD | First completion operation | First oil |
|---|---|---|---|
| 2020-01-01 | 2020-01-08 | 2020-03-01 | 2020-06-09 |

Independent hand calculation, using leap-year February:

- TD minus spud: January 8 minus January 1 = 7 days.
- First completion minus spud: January 31 + February 29 = 60 days.
- First oil minus first completion: March 31 + April 30 + May 31 + June 8 = 100 days.
- First oil minus spud: 31 + 29 + 31 + 30 + 31 + 8 = 160 days.

Thus `spud_to_completion_calendar_days + completion_days = first_oil - spud`:
60 + 100 = 160 days. The former `drilling_days` label represented the 60-day
component, despite TD being reached after 7 days. The column name ending in
`completion_calendar_days` is retained because its endpoint is first completion,
not first oil. No published drilling-time alias is emitted; the saved-file reader
only accepts the old header as a migration input and rejects conflicting aliases.

The synthetic test requires exact equality. The saved-data test uses the one-day
allowance specified by issue #1077, Problem; it does not alter any saved value.

## Population and page interpretation

The calendar cycle-time builder reads the workbook's positive legacy-entry count,
the committed per-well reconciliation's article total row, and the benchmark CSV
row count. Numbers in its population note come from these inputs, rather than
constants in page text. The workbook includes named lease rows with or without
production; the article has a different development population. Exact article
wellbore membership is not established by the workbook. Count differences do not
measure missing rig time. The benchmark is a third population: producing wells
selected by the configured spud window, with unknown spud dates retained by the
existing selector. The benchmark's completion endpoint also differs from TD.

## Reproducing the import check without downloading archives

After the documented workspace dependencies are installed, `make -n data` and
`make -n data-dry` expose the same split namespace `PYTHONPATH`. The regression
test runs `python -S -c "import worldenergydata.bsee"` under that recipe's actual
environment. The `-S` check verifies source discovery without installed packages;
it does not certify the refresh script's dependency installation or bulk download.
The existing source bootstrap in `scripts/refresh_bsee_all.py` is retained.

Issue #1066, Acceptance, records April 2004 as the eWell WAR bulk coverage floor.
Treat it as the issue's reported coverage limit, not proof that every bore since
that month has a complete history. Earlier wells cannot be assigned zero rig days
from absent records. The two committed per-well WAR extracts support local tests,
not a complete bulk recomputation. No archives are downloaded by these checks.

## Limits and follow-up

Missing or reversed milestones leave their applicable intervals null under the
existing guards. The `completion_days` name remains, but denotes first oil minus
first completion, including waiting and suspension. Neither interval can be used
as rig utilisation, drilling efficiency, learning, or a D&C cost input without a
separately qualified basis. Summed intervals may overlap between wells.

Issue #1064 controls adoption of the drilling/completion basis and replacement of
published totals; this change adopts no new rule. Issue #1065 controls the official
activity-code definition, particularly PND, and unblocks qualified treatment of
unknown activity. Existing provenance and republication work remains separate.

Sources: issue #1077 (calendar identity and label), issue #1066 (namespace imports
and reported bulk coverage), and the committed builder and test docstrings.
See the [calendar cycle-time report](../../../../../reports/lower_tertiary/drilling_insights.html)
and [Python date arithmetic](https://docs.python.org/3/library/datetime.html#timedelta-objects).
