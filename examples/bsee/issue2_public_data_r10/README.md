# Issue 2 public data, revision 10

This local review copy applies the five maintainer comments of 17 November 2026
on revision 9 (see `changes.md`). It has not been published. The inherited page
byline describes the earlier approval; it does not approve r10. Before
publication, the approval byline needs a maintainer-confirmed update; removing
the review panel alone does not establish approval of this revision.

Revision 10 changes the presentation only. Its counts and day statistics are the
revision 9 data files, read byte for byte from `../issue2_public_data_r9/data/`
and pinned by SHA-256 in `inputs/manifest.json`. `build_r9.py` derived those
files from the BSEE raw data; it is not rerun here, so the BSEE archives are not
needed to rebuild this page.

## Rebuild

From the repository root:

```sh
uv run --no-project --with pandas --with matplotlib --with pytest python examples/bsee/issue2_public_data_r10/build_r10.py --build-commit "$(git rev-parse HEAD)"
uv run --no-project --with pandas --with matplotlib --with pytest python examples/bsee/issue2_public_data_r10/build_r10.py --offline --build-commit "$(git rev-parse HEAD)"
uv run --no-project --with pandas --with matplotlib --with pytest python -m pytest --noconftest -o addopts='' examples/bsee/issue2_public_data_r10/tests/test_build_r10.py -q
```

`--build-commit` is required: the full 40-character SHA of a commit that already
holds this `build_r10.py`. Appendix A and the prompt line link the script and
folder at that commit. `--bundle PATH` also writes an offline interactive copy
with the pinned Plotly bytes inlined, outside this folder; it is not committed.

The build downloads two files only, each when absent from the ignored `cache/`
folder, over HTTPS only, and rejects bytes that differ from the pins in
`inputs/source-pins.json`: Plotly 2.35.2 (chart library) and the Natural Earth
1:50m land outline, version 5.1.2 (map only). Each cached file needs its
`.receipt.json`. `--offline` requires both.

## What the build writes

- `data/`: the fourteen revision 9 data files the page links, copied unchanged;
  `pies-rig.csv` and `pies-depth.csv`, regenerated and equal to revision 9; and
  `days-overview.csv`, the median days and N of every stage in every
  water-depth band (Figure 6), taken from `days-summary.csv`.
- `figures/`: PNG and SVG exports of the twelve charts: the map, two bar
  charts, two pie sets, the two panels of Figure 6 and the five stage charts of
  Figure 7. The page embeds a 256-colour copy of each PNG as the static
  fallback, which keeps the tracked page under the 1,000 KiB commit limit.
- `issue2-public-data-r10.html`: the page, built from
  `inputs/page-template.html`. It loads Plotly from its release address with a
  SHA-384 integrity hash; without it, each chart shows its PNG.

## Colours

Rig types (Figures 2 and 3) keep the revision 9 colours: the two brand colours
and the Okabe-Ito set. Water depth (Figures 1, 4, 5, 6 and 7) uses one ordered
set from the same family, light to dark as the water deepens: Okabe-Ito yellow
`#F0E442`, brand teal `#2BB2A6`, Okabe-Ito blue `#0072B2` and brand navy
`#0b3d5c`. `tests/test_build_r10.py` checks that CIE L* falls band by band, and
that every pair is at least 15 CIEDE2000 apart, for normal vision and for
simulated protan, deutan and tritan vision (Machado, Oliveira and Fernandes
2009, severity 1.0). Yellow is below 3:1 on white, so yellow marks carry a dark
edge, every bar carries its value, and slice labels use dark text on light
fills. Chart backgrounds stay white in dark mode.

## Tests

`tests/test_build_r10.py` checks that the reused data files and the pie shares
equal revision 9, the Appendix A check values are unchanged, Figure 6 holds
the twenty medians of `days-summary.csv`, every stage chart shows the median
beside N, Figures 6 and 7 define N and median in their notes, every figure and
table puts its notes before its title, the palette check above, and that the
chart script draws all twelve charts in Node with a recording stand-in for
Plotly. The verified environment is listed in `changes.md`.
