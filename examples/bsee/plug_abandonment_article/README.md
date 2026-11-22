# Plugging-and-abandonment article: parked inputs

This folder holds material for the plugging-and-abandonment article of the series "Life of a Gulf of America
well". It is parked here, not published.

## Section 3 of the Issue 2 public data article

Revision 10 of the Issue 2 public data article ("Gulf of Mexico well permits: a public US data file",
`../issue2_public_data_r10/`) had a section 3, "Days from drilling to abandonment". Revision 11 moves it out of
that article, because the days at each stage of a well's life, and abandonment above all, fit the
plugging-and-abandonment article better. Nothing is deleted:

- `section3-days.md`: the section as revision 10 gave it (observations, counting rules, Figures 6 and 7 with
  their notes), with the values read from `data/`.
- `days_charts.py`: the section's code, copied unchanged from `../issue2_public_data_r10/build_r10.py`
  (commit 70c73f65). It draws Figures 6 and 7, writes the observations and Table B1.
- `days_charts.js`: the interactive versions of the same charts (Plotly), copied from the revision 10 page
  template.
- `data/days-summary.csv`: the day statistics (records, exclusions, quartiles and medians by stage and water
  depth), derived by `../issue2_public_data_r9/build_r9.py` from the BSEE borehole and Application for Permit to
  Modify files of 12 November 2026. `data/days-overview.csv`: the Figure 6 medians and N.
- The full counting rules and record counts (the revision 10 Appendix B, Table B1 included) are in
  `../issue2_public_data_r11/counting-rules.md`, section 4.

## Rebuild the charts

From the repository root:

```sh
uv run --no-project --with pandas --with matplotlib --with pytest python examples/bsee/plug_abandonment_article/days_charts.py --output-dir <folder outside this one>
uv run --no-project --with pandas --with matplotlib --with pytest python -m pytest --noconftest -o addopts='' examples/bsee/plug_abandonment_article/tests -q
```

## Before it goes into the article

- Abandonment days are operator estimates on permits to modify, not measured durations; drilling days are
  recorded intervals. The article keeps them apart, as revision 10 did.
- The medians describe 2005 to 2025 as a whole. Medians by calendar year need a recount of the files by year.
