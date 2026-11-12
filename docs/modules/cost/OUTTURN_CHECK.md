# Sanction estimate against stated outturn

[Issue 844](https://github.com/vamseeachanta/worldenergydata/issues/844), under
[epic 1038](https://github.com/vamseeachanta/worldenergydata/issues/1038).

`worldenergydata.cost.outturn_check` sets each held sanction estimate, carried
to the year of the final cost statement with public price indices, beside the
final cost the operator or partner stated. The output is
`reports/cost/sanction_vs_outturn.csv`. It is a calculation output, not a
source dataset.

```bash
python -m worldenergydata.cost.outturn_check --output reports/cost/sanction_vs_outturn.csv
```

## Inputs

- `data/modules/cost/curated/cost_revision_trails.csv`: dated cost statements
  per project, each with its source URL and quoted text.
- `data/modules/cost/curated/cost_component_timeseries.csv`: the held annual
  index rows, refreshed by `worldenergydata.cost.timeseries.refresh`.

## Method

A project is evaluated when the trail holds exactly one `sanction_estimate` and
at least one `final_outturn` or `final_forecast`, both in USD, and the final
statement does not precede the sanction statement. Dates are compared at the
precision both statements give (year, month or day), so a final statement dated
earlier in the sanction year is not evaluated. The latest final statement is
used. The escalation year is the year of each `STATEMENT_DATE`.

Each evaluated row carries both statement URLs with their access dates, and
`INDEX_TRACE`: the index values used, with each value's source and retrieval
date.

For sanction amount `S` in year `a` and final amount `F` in year `b`:

- `INDEX_FACTOR = CostEscalator.factor(a, b, public_only=True)`
- `ESCALATED_SANCTION_USD_MM = S * INDEX_FACTOR`
- `STATED_CHANGE = F / S - 1`
- `INDEX_CHANGE = INDEX_FACTOR - 1`
- `FINAL_OVER_ESCALATED_SANCTION = F / (S * INDEX_FACTOR) - 1`

`public_only=True` skips the UCCI anchors. The factor is then the 50:50
endpoint-ratio blend of the BLS oil-field machinery and drilling PPIs defined in
[`ESCALATION.md`](ESCALATION.md), with CPI as the last resort. The equal weights
are a declared method assumption, not measured project cost shares. The factor
accepts any pair of years the held series cover, in either direction.

## Limits

- The comparison is arithmetic on held public statements. It identifies no
  cause for a difference and is not a finding about any project.
- Scope can differ between a sanction statement and a final statement. The
  `BASIS` and `NOTES` columns of the trail record what each statement covered;
  read them before using a row.
- Annual index means are applied to statement years. Spend is not phased
  across the years between the two statements.
- The indices are United States series. Projects outside the United States
  are evaluated only when both statements are in USD; no exchange rate is
  applied and local cost movement is not represented.
- Projects with statements in other currencies, with no final statement, or
  with more than one sanction estimate are listed as `NOT_EVALUATED` with the
  reason.
- A `final_forecast` is a statement made at or near first production, not an
  audited outturn. `FINAL_KIND` records which one a row uses.

## Refresh

Re-run the command after each reference-series refresh. Index columns move
when a partial year is re-printed; statuses and statement figures change only
when the trail changes.
