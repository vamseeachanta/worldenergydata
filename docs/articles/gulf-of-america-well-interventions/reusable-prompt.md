# Reusable prompt

Article: "Public Data for Gulf of America: well interventions", The Deckhand Chronicles, revision 6 of 19 Nov 2026. This page holds in full what Appendix B of the article summarises.

This prompt rebuilds the life of every Gulf of America well and the intervention counts from BSEE's public raw data, and adapts them to your own field or depth range.

## What you need to run this

- Data required: BSEE raw data, BoreholeRawData.zip and eWellAPMRawData.zip (and eWellEORRawData.zip and eWellWARRawData.zip for the cross-checks), from data.bsee.gov.
- Data required to adapt: a list of API numbers, or a lease, area or depth range.
- Paid or behind an account: nothing.
- Changes over time: BSEE refreshes the files daily, so a new download gives slightly different recent counts.

## Reproduce the published result

```text
Using the worldenergydata repository at commit 24744b528298f26c51bfce4cb3b66fa4f676eb02, folder examples/bsee/interventions_by_depth:
download the four BSEE archives with download_data.py --snapshot 2026-11-13
(or use a later snapshot and expect small changes in recent years), then run
count_interventions.py, well_life_cycle.py, build_cost_basis.py, estimate_costs.py,
plot_charts.py, plot_life_cycle.py and build_article.py. Check that
output/life_cycle_reconciliation.csv shows the same published and counted totals,
and that 2025 gives 765 intervention and 2,610 abandonment approvals.
```

## Adapt it to your project

```text
Filter the borehole and permit tables to your wells before the life-cycle step.
Report, per well: life in years, bores drilled, light and heavy interventions,
temporary and permanent abandonment approvals, with the counting rules of counting-rules.md.
Keep approvals separate from completed jobs, and state the unit rule you use.
```

Data set: BSEE Data Center raw well data (public), files of 13 November 2026.
