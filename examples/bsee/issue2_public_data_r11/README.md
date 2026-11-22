# Issue 2 public data, revision 11

This local review copy applies the five maintainer comments of 18 November 2026 on revision 10 (see
`changes.md`). It has not been published.

Revision 11 keeps the revision 9 permit counts (pinned by SHA-256 in `inputs/manifest.json` and copied byte for
byte). Figure 1 adds the new wells of every year from 2005 to 2025, derived by `derive_r11.py` from the same
borehole file as revision 9, and the annual WTI oil price from the repository snapshot `data/wti-monthly.csv`.
Section 3 of revision 10 (days from drilling to abandonment) is parked in `../plug_abandonment_article/`.

## Files

- `issue2-public-data-r11.html`: the page, built from `inputs/page-template.html`.
- `counting-rules.md`: the full Appendix B (built from `inputs/counting-rules-template.md`).
- `prompts/README.md`: the full Appendix A (built from `inputs/prompts-template.md`).
- `data/`, `figures/`: a CSV for every chart and table; PNG and SVG exports of the six charts.
- `derive_r11.py`: writes the three Figure 1 data files from the pinned borehole file; run once.
- `tests/test_build_r11.py`: offline tests; `tests/browser_check.mjs`: headless browser check of Figure 1
  (exits 1 on any false check, console error or exception).

## Rebuild

From the repository root:

```sh
uv run --no-project --with pandas --with matplotlib python examples/bsee/issue2_public_data_r11/derive_r11.py --data-dir <folder holding BoreholeRawData.zip>
uv run --no-project --with pandas --with matplotlib --with pillow python examples/bsee/issue2_public_data_r11/build_r11.py --build-commit "$(git rev-parse HEAD)"
uv run --no-project --with pandas --with matplotlib --with pillow --with pytest python -m pytest --noconftest -o addopts='' examples/bsee/issue2_public_data_r11/tests examples/bsee/plug_abandonment_article/tests -q
node examples/bsee/issue2_public_data_r11/tests/browser_check.mjs <Chromium-based browser> examples/bsee/issue2_public_data_r11/issue2-public-data-r11.html <output folder>
```

`derive_r11.py` needs BoreholeRawData.zip with the revision 9 pin; it is not needed to rebuild the page.
`--build-commit` is the full SHA of a commit that already holds `build_r11.py`, `counting-rules.md` and
`prompts/`; the appendices link them at that commit. The build downloads Plotly 2.35.2 and the Natural Earth land
outline when absent from the ignored `cache/` folder, under the pins in `inputs/source-pins.json`.

## Figure 1

- The map steps through the seventeen five-year windows every 1.3 s from when it scrolls into view, until the
  reader clicks the map, the slider or a year in panel b. Reduced-motion readers get the slider only.
- Panel b: yearly counts (dots), three-year trailing rolling average (lines, from 2007) and the WTI annual mean
  (dashed, right axis). The shaded years are the map window.
- Colours: the revision 10 water-depth palette (light to dark as the water deepens); the oil price is Okabe-Ito
  vermilion, apart from every depth colour.
