# Revision 12 changes

Maintainer comments received 18 November 2026 on revision 11. Comment 1 is quoted in part, with "..." where words
are left out; comment 2 is quoted in full. The lines below each comment say where revision 12 applies it.

## Comment 1 (Figure 1b, two y-axes; quoted in part)

> Make the right hand ... axis ... label. red. ... can we add a note ... beside the ... axis title? that you know
> the left hand axis will be solid lines on the right hand will be dashed lines. This is great actually. ... Come up
> with some more improvement like that and make sure that people will pay attention and they will go to the right
> place at the right time. ... We need to get these complicated plots reviewed a little bit more aggressively.

Figure 1b:

- The right-hand axis title, its numbers and the axis line are in the oil-price colour (Okabe-Ito vermilion,
  `#D55E00`, the colour of the dashed price line).
- A note sits beside each axis title, as a second line of the title: "left axis: solid lines and dots" and
  "right axis: dashed line". The legend title repeats it: "Solid lines: 3-year mean by water depth (left axis).
  Dashed line: oil price (right axis)."
- Two labelled key points, the readings of section 1: "Oil price fell: USD 93 to 49 (2014 to 2015)" on the
  dashed line, in the oil colour, and "Under 100 m, 3-year mean: about 62 a year (2012 to 2014) to about 12
  (2015 to 2017)" on the shallow-water line. They are generated from the same values as the section 1 text, and the
  build stops if the reading no longer holds.
- The shaded years carry a label, "Map window, panel a: 2011 to 2015", which follows the map.
- Static image: whole-year ticks (2005, 2007, ...) in place of 2007.5, 2010.0, ...

The other charts, reviewed for legend placement, axis titles, units, key points and colours:

- Figure 1a (map): the legend title reads "Water depth (light = shallow, dark = deep), new wells in the window",
  and each band's entry gives its wells in the window shown, for example "Under 100 m (1,089)" for 2005 to 2009;
  the counts follow the animation.
- Figures 2 and 4 (stacked bars): the legend title says what the colours are and that each bar stacks them in
  legend order from the bottom. A labelled key point marks 2015, the year from which drillships (Figure 2) and
  500 m or more (Figure 4) hold over half of the permits in every full year, as section 1 reads it; 2014 is below
  half in both. A second label marks 2026 as a part year, to the file of 2 November 2026, which the notes now
  also say. Both are generated from the data and checked.
- Figures 3 and 5 (pies): each pie gives its year's permits under the year (322, 83 and 47); the legend has a
  title ("Rig type", or the water-depth title above).
- Axis titles and units were checked on every chart: counts are marked (-), the price USD/bbl, the map degrees.
- Checked and kept: the rig-type colours (Figures 2 and 3) use the two brand colours, navy for jack-ups and teal
  for drillships, which are also the colours of the deepest band and of 100 to 500 m. The rig charts never show
  water depth, and their legends name every colour, so the rig palette of revisions 9 to 11 is kept.

## Comment 2 (Figure 4)

> I love the colors being consistent across for water depth. This is great.

- Kept: the four water-depth colours are the same in Figures 1a, 1b, 4 and 5 and in the infographic, light to dark
  as the water deepens. A test checks the one palette in every depth chart; the oil price stays apart from it.

## Data

- No data changed. The permit counts (Figures 2 to 5, Table 1) are the revision 9 files, compared byte for byte by
  the tests; the Figure 1 files are the revision 11 files, pinned in `inputs/manifest.json`.

## Build and tests

- Built with `--build-commit 8c18f080938d4efea28dad6f696b125aacd028d8`, the commit that holds `build_r12.py`,
  `counting-rules.md` and `prompts/`; page 568 KB.
- Verified environment: Windows 11, Python 3.14.3, pandas 3.1.1, matplotlib 3.11.2, pytest 9.2.0, Node.js 26.13.0.
- `tests/test_build_r12.py` and `../plug_abandonment_article/tests`: 39 passed (four new tests for the axis colour
  and notes, the key points, the bar readings and the legend titles); `../issue2_public_data_r11/tests` and
  `../issue2_public_data_r10/tests` (unchanged): 58 passed.
- Document rules check: prompts appendix, data set, Prepared/Checked/Approved, no Monday heading and no P.E. or
  AI-help line all pass; AI named three times (masthead line, offer box, Appendix A); no SAMPLE marks.
- `tests/browser_check.mjs` in headless Microsoft Edge, exit 0 with no false check: six charts drawn; the right
  axis title, numbers and line in `#D55E00`; both axis notes; the map legend with window counts; two key points
  on Figures 2 and 4; the map moved from 2005 to 2009 to 2008 to 2012 while playing, stopped on a click, moved to
  2011 to 2015 on a click on 2015 in panel b with the shading label following, and stopped on 2009 to 2013 on a
  slider click; no console errors or exceptions.
