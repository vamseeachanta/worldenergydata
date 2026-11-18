# Revision 11 changes

Maintainer comments received 18 November 2026 on revision 10. Comments 1 and 2 are quoted in full; comments 3, 4
and 5 are quoted in part, as marked, with "..." where words are left out. The lines below each comment say where
revision 11 applies it.

## Comment 1 (infographic below the opening picture)

> Can we not make the infographic below use? the left empty space a bit more.

- The scene's shallow-water columns were mostly empty seabed. Each water-depth band now carries its new wells
  started, 2005 to 2009 then 2021 to 2025, and their share of all new wells (for example 1,089 to 33, 68.8 % to
  13.4 % under 100 m): on the seabed under the shallow bands, in the water itself for the deep bands. The numbers
  come from `map-summary.csv`.
- The stage strip marks drilling (new wells) as this article's stage, solid; the later stages, dashed, follow in
  the series.

## Comment 2 (Figure 1)

> Until the user clicks, can we not make it a transition? infographic. until the user clicks on a certain ear also. can we add in more? granularity like a decade or something? Yeah, just think how we can make this better.
>
> Is it ever 5 years? or? or something like that? Following that, can you make some rolling averages to understand things were influenced by oil rises and stuff that will be a good follow up. So yeah, keep going at it. You know, let us see what we can do. We want to release this this morning.

- Figure 1a plays through every five-year window, 2005 to 2009, 2006 to 2010, ... 2021 to 2025, one step every
  1.3 s, from when the map scrolls into view, until the reader clicks the map, the slider or a year in panel b.
  Play and the slider then choose a window. Readers who ask for reduced motion get the slider without autoplay.
  Five-year windows are used rather than decades: each window holds 246 or more wells, enough to read on the map.
- New Figure 1b: the new wells started each year in each band (dots), the three-year rolling average (lines) and
  the annual mean WTI oil price (dashed, right axis). The years of the map window are shaded; clicking a year moves
  the map to the window that ends in it.
- The oil price is the repository's existing snapshot `data/wti-monthly.csv` (US Energy Information
  Administration, Cushing WTI spot price; added in pull request 1185 with its provenance file). It is cited under
  Figure 1 and in `prompts/README.md`.
- A new observation reads the rolling averages beside the price: from 2014 to 2015 the WTI annual mean fell from
  USD 93.26 to 48.69 a barrel; the three-year average of new wells under 100 m fell from about 62 a year (2012 to
  2014) to about 12 (2015 to 2017), in 500 m or more from about 76 to about 59. The exact values (62.0, 12.3, 75.7,
  59.3) are in the Figure 1 notes. The text is generated from the data and stops the build if the reading no
  longer holds. An open point in section 3 says that no cause is fitted.
- Data: `derive_r11.py` applies the revision 9 borehole rule (`build_r9.map_wells`) one year at a time to the
  same pinned borehole file (12 November 2026). 2005 to 2009 and 2021 to 2025 equal the revision 9 map well for
  well; the test checks it.
- The page uses Plotly 2.35.2 as before; the animation is inline script, no new library.

## Comment 3 (section 3, days from drilling to abandonment; quoted in part)

> Can we roll this into the next series article? ... You make a judgment and move on. ... Make sure other articles are reviewed. to ensure we do have. a well rounded answer and usage of all this data. Some of this data may be better fitting in other articles, whatever you judge

- Judgement: the section moves to the series' plugging-and-abandonment article. A one-line pointer stays at the
  end of section 2; old section 4 is now section 3.
- The section's text, code and data are parked in `../plug_abandonment_article/` (`section3-days.md`,
  `days_charts.py`, `days_charts.js`, `data/`), with a test that rebuilds its charts. The full day-statistics
  rules and Table B1 are in `counting-rules.md`, section 4.
- Other articles checked: the four planned parts of the series on the life of a Gulf of America well (part 1 this
  article; part 2 well interventions; part 3 well abandonment by water depth; part 4 worldwide wells) and the
  planned jack-up, rig and costing articles.
- Where each data set goes:
  - Permit counts by rig type and water depth (Figures 2 to 5, Table 1), the yearly new wells and the WTI price
    (Figure 1): stay in this article.
  - Days at each stage (`days-summary.csv`, `days-overview.csv`, revision 10 Figures 6 and 7): part 3, well
    abandonment, which carries the drilling and abandonment days and the side-by-side stage chart.
  - Completion and intervention days (rows of the same files): also part 2, well interventions.
  - Rig-type counts and shares (Figures 2 and 3, Table 1): the jack-up and rig articles, with the jack-up shift
    from new wells to plugging and abandonment also in part 3.
  - Yearly well counts by depth with the day statistics: activity inputs for the costing article.
  - Part 4, worldwide wells: takes none of these files (US federal Gulf waters only).
  - Open: which article carries the completion days on their own.

## Comment 4 (Appendix A; quoted in part)

> I need this short and sweet one to two lines. for this section. with a link to our key repo repository. ...

- Appendix A is two purpose bullets and a link to `prompts/` in this folder, which holds the full prompt, the
  files, the check values and the sources.

## Comment 5 (Appendix B; quoted in part)

> Put the counting rules in the ecosystem. If somebody wants more details, they can look at it. Use a link. Use a github link. Provide a brief summary. ...

- Appendix B is two purpose bullets and a GitHub link to `counting-rules.md` in this folder, which holds the full
  rules for the permits, the map and the rolling averages, and the full revision 10 Appendix B (day-statistics
  rules, selection counts and Table B1).

## Review gate run 1 (18 November 2026)

- Sign-off line: "Approved: awaiting the maintainer's review of revision 11" in place of the 3 November
  approval, which belonged to an earlier revision; a test keeps the old date out of it. The release build takes
  the date of the maintainer's approval of revision 11.
- Section 3.1 keeps two hypotheses. The third (shallow-water wells follow the oil price more closely) is removed:
  it had no source, and Figure 1b cuts against it (shallow-water wells fell from 2005 to 2011 while the price
  rose). The section 1 observation and the open point in section 3.2 carry the price reading.
- Section 1 names the public data set: two BSEE raw data files (permits to drill, boreholes) and the EIA WTI spot
  price.
- The rolling-average observation gives whole wells (about 62 to about 12 a year); the exact values are in the
  Figure 1 notes.
- Infographic source line: "Sources: BSEE raw data files; EIA WTI spot price (section 1, Figure 1)".
- Section 3.3 has the maintainer's line as he wrote it: "To try it out or adapt the analysis, see reusable
  prompt."
- The review panel lists the other articles checked and where each data set goes (comment 3 above).
- `tests/browser_check.mjs` exits 1 when any check is false and checks a click on the slider while playing.

## Data

- Permit counts (Figures 2 to 5, Table 1) are unchanged: the build reads the revision 9 data files and the tests
  compare them byte for byte. No source file was downloaded again.
- New files: `map-wells-by-year.csv`, `new-wells-by-year.csv` and `wti-annual.csv` (written by `derive_r11.py`,
  pinned in `inputs/manifest.json`); `map-windows.csv` and `new-wells-trend.csv` (written by the build).

## Build and tests

- Built with `--build-commit 0aeea0aa460b1799539a98a3f955934b273ca56e`, the commit that holds `build_r11.py`,
  `counting-rules.md` and `prompts/`; page 518 KB.
- Verified environment: Windows 11, Python 3.14.3, pandas 3.1.1, matplotlib 3.11.2, pytest 9.2.0, Node.js 26.13.0.
- `tests/test_build_r11.py` and `../plug_abandonment_article/tests`: 33 passed; `../issue2_public_data_r10/tests`
  (unchanged): 26 passed.
- `tests/browser_check.mjs` in headless Microsoft Edge: Plotly loaded, six charts drawn, the map moved from
  2005 to 2009 to 2008 to 2012 in 4.2 s, a click on the map stopped it (Play shown, window unchanged 3 s later),
  a click on 2015 in panel b moved the map to 2011 to 2015 and shaded 2011 to 2015; no console errors or
  exceptions.
