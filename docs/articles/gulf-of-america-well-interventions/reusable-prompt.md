# Reusable prompt

Article: "Public Data for Gulf of America: well interventions", The Deckhand Chronicles, revision 6 of 19 Nov 2026. This page holds in full what Appendix B of the article summarises.

## Reproduce the published analysis

Use the study at `24744b528298f26c51bfce4cb3b66fa4f676eb02`. A historical rerun requires the four BSEE ZIP files downloaded on 13 November 2026. The repository contains the [published manifest](https://api.github.com/repositories/574746314/contents/examples/bsee/interventions_by_depth/output/manifest.json?ref=24744b528298f26c51bfce4cb3b66fa4f676eb02) and derived tables. BSEE's downloader retrieves current files, and its `--snapshot` argument only names the destination folder.

From the directory holding the four archives, check their bytes against the SHA-256 values in the published manifest. Continue only if all four files match. In PowerShell, `Get-FileHash *.zip -Algorithm SHA256` also gives the hashes for comparison by filename.

```sh
sha256sum --check <<'SUMS'
66f39baea0ef50ed97a8992dea88d7a0bee24f270b345ea20721abfc8a0ee100  BoreholeRawData.zip
6db08210b85e822b48c33002e9527d4f52baa5441f252ee79ff7937731be4050  eWellAPMRawData.zip
d1db6e6c53577ec595273768c925e3e24261be0b289fc6325151ba37fc81d127  eWellEORRawData.zip
b7a086c1fb9d270e673c5931ce3822f202ff4e6e8af5cc98e19dd3ddf03d525c  eWellWARRawData.zip
SUMS
```

Use the verified archives and the published `manifest.json` together in `data/modules/bsee/zip/2026-11-13/`. For a new analysis, run `python examples/bsee/interventions_by_depth/download_data.py` in a separate study checkout. Its default folder uses the actual download date (UTC). Retain the new manifest and report that date with the new results.

From the root of the pinned study checkout, install the dependencies listed in the [study README](https://api.github.com/repositories/574746314/contents/examples/bsee/interventions_by_depth/README.md?ref=24744b528298f26c51bfce4cb3b66fa4f676eb02). Its “Tests and reproduction” section gives these analysis commands:

```sh
(
  set -e
  study=examples/bsee/interventions_by_depth
  data=data/modules/bsee/zip/2026-11-13
  python "$study/count_interventions.py" --data-dir "$data" --out "$study/output"
  python "$study/build_cost_basis.py"
  python "$study/estimate_costs.py" --out "$study/output"
  python "$study/plot_charts.py" --out "$study/output"
  python "$study/well_life_cycle.py" --data-dir "$data"
  python "$study/plot_life_cycle.py"
)
```

The block runs in a subshell with `set -e`, so it stops at the first failing command. The pinned checkout already holds the published tables, so a replay that continued past a failure could still plot them and appear to succeed.

Check that the life-cycle event totals equal the published permit totals for each group and that 2025 has 765 well-work approvals and 2,610 abandonment approvals. This replay covers the analysis. The study's article builder generates revision 4.

Without the four matching archives, use the published [annual counts](https://api.github.com/repositories/574746314/contents/examples/bsee/interventions_by_depth/output/counts_by_year_band_group.csv?ref=78f1a9183a75e56adb7f31e88b271864f0b69d37) and [life-cycle reconciliation](https://api.github.com/repositories/574746314/contents/examples/bsee/interventions_by_depth/output/life_cycle_reconciliation.csv?ref=78f1a9183a75e56adb7f31e88b271864f0b69d37) to check the figures.

## Adapt the analysis to a field or depth range

```text
Build the well inventory first. Select API10 identifiers for the requested field,
lease, API list or inventory depth band. Retain all eligible bores and permits
for those identifiers, including bores with a different or missing depth.
Apply the counting rules to those complete well histories. For this cohort,
regenerate the permit comparison totals and opening stocks, then reconcile the
life-cycle events and calculate rates against those stocks.

Report each well's life in years, bores drilled, light and heavy interventions,
and temporary and permanent abandonment approvals. State how units are classified
and distinguish approved permits from completed jobs.
```

See the [counting rules](counting-rules.md) for depth assignment and well life.
