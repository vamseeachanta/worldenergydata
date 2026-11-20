# Issue 2 public data, revision 12

This local review copy applies the two maintainer comments of 18 November 2026 on revision 11 (see
`changes.md`): the right-hand axis of Figure 1b in the oil-price colour with a line-style note beside each axis
title, and the same kind of reading cue on the other charts. The water-depth colours stay the same in every figure.
It has not been published. Revision 11 is kept unchanged in `../issue2_public_data_r11/`.

Revision 12 keeps the revision 9 permit counts (pinned by SHA-256 in `inputs/manifest.json` and copied byte for
byte) and the revision 11 Figure 1 data: the new wells of every year from 2005 to 2025, derived by `derive_r12.py`
(the revision 11 script) from the same borehole file as revision 9, and the annual WTI oil price from the
repository snapshot `data/wti-monthly.csv`. Section 3 of revision 10 (days from drilling to abandonment) is parked
in `../plug_abandonment_article/`.

## Files

- `issue2-public-data-r12.html`: the page, built from `inputs/page-template.html`.
- `counting-rules.md`: the full Appendix B (built from `inputs/counting-rules-template.md`).
- `prompts/README.md`: the full Appendix A (built from `inputs/prompts-template.md`).
- `data/`, `figures/`: a CSV for every chart and table; PNG and SVG exports of the six charts.
- `derive_r12.py`: writes the three Figure 1 data files from the pinned borehole file; run once.
- `tests/test_build_r12.py`: offline tests; `tests/browser_check.mjs`: headless browser check of Figure 1 and of
  the reading cues (exits 1 on any false check, console error or exception).

## Rebuild

From the repository root:

```sh
uv run --no-project --with pandas --with matplotlib python examples/bsee/issue2_public_data_r12/derive_r12.py --data-dir <folder holding BoreholeRawData.zip>
uv run --no-project --with pandas --with matplotlib --with pillow python examples/bsee/issue2_public_data_r12/build_r12.py --build-commit "$(git rev-parse HEAD)"
uv run --no-project --with pandas --with matplotlib --with pillow --with pytest python -m pytest --noconftest -o addopts='' examples/bsee/issue2_public_data_r12/tests examples/bsee/plug_abandonment_article/tests -q
node examples/bsee/issue2_public_data_r12/tests/browser_check.mjs <Chromium-based browser> examples/bsee/issue2_public_data_r12/issue2-public-data-r12.html <output folder>
```

`derive_r12.py` needs BoreholeRawData.zip with the revision 9 pin; it is not needed to rebuild the page.
`--build-commit` is the full SHA of a commit that already holds `build_r12.py`, `counting-rules.md` and
`prompts/`; the appendices link them at that commit. The build downloads Plotly 2.35.2 and the Natural Earth land
outline when absent from the ignored `cache/` folder, under the pins in `inputs/source-pins.json`.

## Figure 1

- The map steps through the seventeen five-year windows every 1.3 s from when it scrolls into view, until the
  reader clicks the map, the slider or a year in panel b. Reduced-motion readers get the slider only. The legend
  gives the new wells of each band in the window shown.
- Panel b: yearly counts (dots) and three-year trailing rolling averages (solid lines, from 2007) on the left
  axis; the WTI annual mean (dashed line) on the right axis, whose title, numbers and line are in the oil-price
  colour. A note beside each axis title names its line style. The shaded years are the map window, labelled.
- Colours: the revision 10 water-depth palette (light to dark as the water deepens) in every figure; the oil price
  is Okabe-Ito vermilion, apart from every depth colour.

## Reading cues (all charts)

- Legend titles say how to read the colours and that each bar stacks in legend order from the bottom.
- Labelled key points are generated from the data and checked; the build stops if a reading no longer holds.
- The part year 2026 is marked in Figures 2 and 4; each pie in Figures 3 and 5 gives its year's permits.
