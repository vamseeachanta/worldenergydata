# Reusable prompt: Gulf of America well completions

Article: "Public Data for Gulf of America: well completions", The Deckhand
Chronicles, part 2 of the series "Life of a Gulf of America well". This page
holds in full what the article's reusable-prompt appendix summarises. Method,
definitions and checks: [README](README.md).

## What is needed

- Data required: BSEE raw data, `BoreholeRawData.zip`, `eWellAPMRawData.zip`
  and `eWellEORRawData.zip`, from <https://www.data.bsee.gov/Main/RawData.aspx>.
- Data required to adapt: a list of API numbers, or a lease, area or
  water-depth range.
- Paid or behind an account: nothing.
- Changes over time: BSEE refreshes the files daily, so a new download gives
  other digests and slightly different recent counts. The published counts use
  the files of 23 Nov 2026, whose SHA-256 values are in `series_basis.json`.
- AI provider used: the code and counts were written with Anthropic's Claude
  and the article text was reviewed with Google's Gemini. The prompts below are
  plain text and work with any capable assistant that can run Python.

## Reproduce the published counts

```text
Using the worldenergydata repository at the commit that carries this page,
folder examples/bsee/completions_by_depth: place the three BSEE archives in one
folder. If their SHA-256 values differ from series_basis.json, say so, update
that file for the new download and expect small changes in recent years. Run
count_completions.py with --data-dir set to that folder, then plot_charts.py.
Check output/verification.json: every conservation check true, and the
comparison with the interventions study showing the same count on both sides
with no cell different. On the files of 23 Nov 2026 the totals are 8,472
completion approvals, 6,841 of them initial completions, 3,216 bores first
completed by approval and 3,238 by report.
```

## Adapt it to a field, lease or depth range

```text
Filter the borehole table to the wells of interest (by API number, lease, area
or water depth) before counting, and keep the same definitions: a completion
approval is an approved permit of type COMP without a change of zone; an
initial completion carries the sub-operation INITCOMP; a completion report is
an End of Operations Report with operation code C, dated by its borehole
status date. Report, by year and water-depth band: completion approvals, bores
first completed by each record, and how many bores appear in both. Keep
approvals apart from reports, state every field used with the regulator's
definition, give the share populated for any sparse field, and make no claim
about cause. Before reporting, check that band counts and year counts each sum
to the total and that each permit and report is counted once.
```

Data set: BSEE Data Center raw well data (public), files of 23 Nov 2026.
