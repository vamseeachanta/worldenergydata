# Issue 2 public data, revision 8

This local review copy applies the five owner comments of 12 November 2026,
21:50 UTC. It has not been published. The inherited page byline describes the
earlier approval; it does not approve r8.
Before publication, the approval byline needs an owner-confirmed update;
removing the review panel alone does not establish approval of this revision.

## Rebuild

From the repository root:

```sh
uv run --no-project --with pandas --with matplotlib --with pytest python examples/bsee/issue2_public_data_r8/build_r8.py --build-commit "$(git rev-parse HEAD)"
uv run --no-project --with pandas --with matplotlib --with pytest python examples/bsee/issue2_public_data_r8/build_r8.py --offline --build-commit "$(git rev-parse HEAD)"
uv run --no-project --with pandas --with matplotlib --with pytest python -m pytest --noconftest -o addopts='' examples/bsee/issue2_public_data_r8/tests/test_build_r8.py -q
```

`--build-commit` is required: the full 40-character SHA of a commit that already
holds this `build_r8.py`. Appendix A links the script at that commit, so a
branch name or short SHA is refused. Commit the script first, then build the
page from that checkout. `--bundle PATH` also writes an offline interactive copy
with the pinned Plotly bytes inlined; the path must lie outside this example
folder, and the copy is not committed.

`--data-dir` selects the raw download cache; the default is the ignored `cache/`
directory beside the script. `--output-dir` selects a separate artifact folder.
Network access uses a standard-library `urllib` opener with an HTTPS handler
only, only for missing files; any other scheme, and any redirect to one, is refused. Each
cached file needs its adjacent `.receipt.json`. The receipt records the URL,
retrieval time in UTC and SHA-256. Existing files with absent or mismatched
receipts fail closed; their retrieval date is never guessed. All four sources
also have issued SHA-256 pins in `inputs/source-pins.json`; a self-consistent
substitute receipt cannot authorize different bytes. Offline mode
requires all four cached files and receipts, including Plotly. Raw zips and the
cached library are not committed. A fresh cache downloads the current BSEE
files only when absent, and rejects any bytes that differ from the issued pins.
It cannot recover historical duration results after upstream changes unless the
original cache and receipts are retained. A source refresh requires a separately
reviewed revision of the pins, input manifest and narrative; no refresh bypass
flag is provided. Treat outputs of a failed build as incomplete and rebuild
successfully before using them.

No archival replica has been published or backed up by this task. If the local
cache is lost after BSEE replaces the source files, these duration results cannot
be reproduced from the repository alone. Raw zip publication is outside this
task's authority.

The `inputs/` CSVs preserve the supplied r7 aggregates. `inputs/table1.csv` is
transcribed mechanically from the r7 HTML table. `inputs/page-template.html`
preserves its CSS and retained prose. `inputs/manifest.json` pins these inputs.
The r7 raw APD zip was not supplied; its digest and retrieval date are inherited
from the supplied r7 receipt, not independently recalculated here. The script
does not replace the r7 counts with counts from today's APD file.

The script prints every inspected data-member header and writes
`data/source_columns.csv`. APM `EST_OPERATION_DAYS` supplies permit estimates.
Borehole `TOTAL_DEPTH_DATE - WELL_SPUD_DATE` supplies recorded calendar intervals,
without an inclusive extra day. APD has no estimated-days field in either
inspected table. The page and `changes.md` define the cohorts and exclusions.

Each of the nine figures has PNG and SVG exports. Six are individual pies.
The page embeds the static PNGs and loads the pinned Plotly 2.35.2 release from
its release address with a SHA-384 integrity hash of the pinned bytes, which keeps
the tracked page under the 1,000 KiB commit limit. Eight charts have interactive
views; Figure 3 uses the static export. Without network access, or if the
library fails its integrity check, every chart shows its static PNG. Pie legends
do not hide slices, so the printed shares stay true. The `--bundle` copy retains
the library's upstream license notice. The body tables, Appendix B table and every
figure have CSV data. Display values use at most four significant figures;
pie shares use one decimal place. Zero-permit types are omitted from pie labels and legends, but retained in CSVs. Approximate count displays carry an ≈ mark. CSVs retain exact counts and higher precision quartiles
for checking; dates, years, identifiers and digests are not rounded.

Determinism uses fixed input receipts, sorted identities, fixed figure sizes,
DejaVu Sans, fixed colours, `svg.hashsalt` and no SVG metadata dates. Identical
bytes are expected with the same Python, pandas and matplotlib versions. Font
and renderer version changes can alter exported bytes. The verified environment
uses Python 3.14.6, pandas 3.1.1, matplotlib 3.11.2 and pytest 9.2.0.

## Sources

Source ID: `bsee-data-center`. The authoritative public-source collection owner
is `worldenergydata`; this example owns only the r8 derivatives.

- [BSEE raw-data index](https://www.data.bsee.gov/Main/RawData.aspx), inspected
  13 November 2026 UTC.
- [APDRawData.zip](https://www.data.bsee.gov/Well/Files/APDRawData.zip): r7
  snapshot dated 2 November, retrieved 3 November 2026; fresh schema-inspection
  copy retrieved 13 November 2026 UTC.
- [eWellAPMRawData.zip](https://www.data.bsee.gov/Well/Files/eWellAPMRawData.zip),
  retrieved 13 November 2026 UTC.
- [BoreholeRawData.zip](https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip),
  retrieved 13 November 2026 UTC.
- [Plotly 2.35.2](https://cdn.plot.ly/plotly-2.35.2.min.js), retrieved
  13 November 2026 UTC; chart library, not engineering data.
- [Published r7 counter](https://github.com/vamseeachanta/worldenergydata/tree/f5af5b6da87710bb395552f9cda5e34d1f324479/examples/bsee/rawdata_fact_check).
- [Prior duration method](https://github.com/vamseeachanta/worldenergydata/tree/b26eb928ea88e397e11a0d237fbff3d4f1f0a26d/examples/bsee/interventions_by_depth),
  inspected with `git show`. Reused ideas: one APM submission per observation,
  joined subtype sets, abandonment precedence, finite positive estimates and
  explicit missing-depth handling. No checkout or mutation of that branch.

Full source receipts are in `data/sources.csv`. Classification source labels
and analysis rules are in `data/code_mapping.csv`. Exact selection counts are in
`data/exclusions.csv`; per-band duration exclusions are in `data/days-summary.csv`.
`data/subtype-activity.csv` provides an activity/primary/subtype cross-tab.
Each subtype set is counted once per submission; totals across subtype rows are
not additive. The repeat API/operation/year diagnostic counts extra submissions
sharing that key, not proven duplicate jobs.
`data/repeat-key-sensitivity.csv` compares those medians with an alternative
that retains the latest status date per API/primary operation/status year,
breaking ties by text-order SN_APM. It is a sensitivity cohort, not a claim that
all shared keys are revisions. The main results remain permit-based.
`data/source-members.csv` records every archive member. Date-quality diagnostics
split nonblank invalid dates from blank total-depth dates, and zero intervals
from negative intervals. Both zero and negative intervals remain excluded under
the owner's nonpositive-day rule.

Section 3.1 observations are generated by reading `data/days-summary.csv`.
Section 3.2 gives five plain rules; section 3.3 gives Figure 3, the day medians
and quartiles by water depth; the page has no Table 2. Appendix B retains the detailed rules, sensitivity result,
selection counts and full Table B1, including all five zero-count missing-depth
rows and day-exclusion columns. The source receipts retain ISO timestamps;
the page presents retrieval dates as day, month name and year.

The template is the authored page source; the HTML is generated. There is no
review-plan file. The render profile and probe pages are disposable and are
not required for an offline rebuild; source archives and receipts are required.
