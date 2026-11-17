# Revision 10 changes

Maintainer comments received 17 November 2026 on revision 9. Each comment is
quoted as received; the lines below it say where revision 10 applies it.

## Comment 1 (title)

> Can we add the infographic And based on the new data, we did change based on the new newsletter design. We did change the way we are going to release this. by category by the day. So can you tell me which which day and ....ravel up on my mind? What is going on

- Infographic: after the title and the newsletter's masthead line, a figure
  built from the article's objective: a scene of the four water-depth bands
  as water over a stepped seabed in the depth colours, with the stages of a well's life
  in order, and five panels (objective, starting point, what we did, what we
  found, what you can do). The "What we found" sentence is generated from
  `map-summary.csv` and `days-summary.csv` and fails closed if either trend
  reverses.
- Introduction: three short parts (what we did, why it matters, what is
  inside) with a one-line prompt linked to this folder. The revision 9
  takeaway quote is replaced; its content is in the "What we found" panel.
- The release-day question concerns the publishing schedule, not this page;
  it is answered with the review copy.

## Comment 2 (Figure 4)

> Carson figure. Two and three are so bright Why can't we use them consistently in this one? in this one. unless you want to keep the water. deep water has darker. has darker color, but we can. just do the same thing with I don't know. You tell me why you chose these colors

- Revision 9 used four light-to-dark blues for water depth, a palette of its
  own. Revision 10 takes the water-depth colours from the same family as
  Figures 2 and 3 (the two brand colours and the Okabe-Ito set) and keeps
  darker for deeper: yellow, teal, blue, navy. Water depth is an ordered
  quantity, so lightness carries the order; rig type has no order, so its
  colours differ by hue only.
- The same four colours now mark the bands in Figures 1, 4, 5, 6 and 7. A
  note under Figure 4 says so. Validation is described in `README.md`.

## Comment 3 (section 3.3)

> Can we add additional pie chart? on the bar chart to show the medians for each of the water dutts. That way people will understand. So we will have one chart for water depth and show all the stages drilling completion, Etcetera. So that the pie charts will look good and good and it will give a comparison of, you know, how things are progressed for each depth overtime also. tell you know like for each depth what was oh yeah try with time and with depth let us see

- New Figure 6, "Median days of each stage, by water depth", with two
  panels: (a) by stage in the order of a well's life, four bars per stage, one
  per water-depth band; (b) by water depth, the five stages of each band in
  life order. Every bar carries its median; hover gives N.
- Pies are not used for these medians. A pie shows parts of one whole; the
  medians come from different records (recorded drilling intervals and
  operator estimates on separate permits), are not paired and do not add up to
  a well's life, so a pie would show a share that does not exist. The notes
  under Figure 6 say the medians are not added up.
- "With time" is read as the order of a well's life (panel a) and "with depth"
  as panel b. Medians by calendar year need a recount of the files by year and
  are not in this revision.
- The five stage charts follow as Figure 7.

## Comment 4 (stage chart a, drilling)

> I like the way the number of samples are shown now Also provide the median. and also define below the chart that what N means and median means, you know, not everybody knows it. So use the footnotes to do that.

- Each band on every stage chart is labelled "Median 21 d · N = 1,507"
  (counts above four significant figures read "N ≈ 23,220", as before).
- The notes under Figures 6 and 7 define median (the middle value: half of the
  records take fewer days and half take more) and N (the number of records
  behind a median, with what counts as a record and what is left out), and the
  quartile bars.

## Comment 5 (Figure 6 title)

> Can we bring the chart title below the footnote so that people will read the footnotes?

- Every figure and table now gives its numbered notes first and its title
  below them: Figures 1 to 7, Table 1 and Table B1.

## Other changes

- Chart backgrounds stay white in dark mode, so the navy series stay visible.
- Pie slice labels use dark text on light fills (yellow, teal, orange, sky
  blue) and white text on dark fills.
- Map markers and depth bars carry a thin dark edge, so the yellow band reads
  on white and on the pale sea.
- Appendix A links `build_r10.py` at its commit and `build_r9.py` at commit
  6b2dbc38, which derived the counts and day statistics; the piece date is
  17 November 2026.

## Data

- Counts in Figures 1 to 5 and Table 1, and every day statistic in Figures 6
  and 7 and Table B1, are unchanged from revision 9: the build reads the
  revision 9 data files and the tests compare them byte for byte.
- No source file was downloaded again for the counts. The permit counts stay
  on the APD file of 2 November 2026; the day statistics and the map on the APM
  and borehole files of 12 November 2026.

## Build and tests

- Built with `--build-commit 4505a2f854dcd0998fb59fee1138b2b1369440b9`, the
  commit that holds the current `build_r10.py`.
- Verified environment: Windows 11, Python 3.14.3, pandas 3.1.1, matplotlib
  3.11.2, pytest 9.2.0, Node.js 26.13.0. `tests/test_build_r10.py`: 26 passed.
- Not run: the revision 9 tests (revision 9 is unchanged) and a rerun of
  `build_r9.py` (it needs the pinned BSEE archives).

## Review-gate round 1 fixes

- Appendix A: the permit counting script at commit f5af5b6d is now described
  as merged into the main branch on 16 November 2026 (pull request 1844);
  the pin stays at f5af5b6d.
- Infographic "What we found": shortened to "New wells moved to deep water:
  68.8 % were in less than 100 m in 2005 to 2009, 13.4 % in 2021 to 2025.
  Median drilling days rise with depth, from 21 d to 67 d." It is still
  generated from the data and still stops the build if either trend reverses.
- Page description: now names the water-depth counts, the map and the days
  at each stage of a well's life.
