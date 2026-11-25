# Gulf of America well completions, by year and water depth

Part 3 of 7 in the series "Life of a Gulf of America well". This folder counts completions from the public raw
data of the Bureau of Safety and Environmental Enforcement (BSEE) and holds the
code, the small result tables, the charts and the checks. It uses the
definitions of the interventions study in
[`../interventions_by_depth`](../interventions_by_depth) (part 5 of the series),
so that the completion counted here is the event that study sets aside.

Counts are records in public files: approved permits and filed reports. They
are not a census of completed wells, and no cause is claimed for any change
over time.

## Data

BSEE Data Center, [raw data downloads](https://www.data.bsee.gov/Main/RawData.aspx),
files dated 23 Nov 2026 by BSEE and downloaded in one sitting on 23 Nov 2026,
18:54:37 to 18:56:12 UTC. This is the single data basis of the series.

| File | BSEE file date | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| BoreholeRawData.zip | 11/23/2026 4:31:21 AM | 3,488,947 | `72fa55e55fd28db26c59e52b3a43c7d053f9d12a6d06b0a0f6a46ef541c66a5c` |
| eWellAPMRawData.zip | 11/23/2026 4:36:24 AM | 35,824,667 | `1a38ed6cf9eab1f8079bf65d8e5b389cb41cc343cde4ce679e2b6e057fd7da50` |
| eWellEORRawData.zip | 11/23/2026 4:36:30 AM | 4,501,468 | `b67c61826ea90aa51d7e1f01c2df94bba6e869665a7992cd5438ea538ee603bc` |

The archives are not stored in this repository (they are public and
re-downloadable; BSEE refreshes them daily, so a later download gives other
digests and slightly different recent counts). [`series_basis.json`](series_basis.json)
records the digests, and a run stops when a file does not match.

Tables read: `mv_boreholes_all`; `mv_apm_main`, `mv_apm_suboperations`,
`mv_apm_main_prop` (narratives, for the new-hole screen only, never written
out) and `mv_apm_suboperation_codes`; `mv_eor_mainquery`, `mv_eor_completions`
and `mv_eor_perf_intervals`. `mv_eor_completionsprop` (reservoir and interval
names, coordinates) and `mv_eor_compstatcodes` (status labels) were read to
understand the tables and are not tabulated.

## What BSEE says the fields mean

Quoted from BSEE's own pages, read 23 Nov 2026:

- Both electronic feeds begin in April 2004. The End of Operations Report query
  "contains only End of Operations Reports that were submitted via eWell since
  April 2004", and the permit query "contains only Applications for Permit to
  Modify that were submitted via eWell since April 2004"
  ([EOR query](https://www.data.bsee.gov/Well/eWellEOR/Default.aspx),
  [APM query](https://www.data.bsee.gov/Well/eWellAPM/Default.aspx)).
- `BOREHOLE_STAT_CD`: "Indicates the conditions relating to a borehole."
- `BOREHOLE_STAT_DT`: "The date the borehole status becomes effective."
- `SUBSEA_COMPLETION_FLAG`: "A flag to indicate whether a subsea completion exists."
  ([EOR field definitions](https://www.data.bsee.gov/Well/eWellEOR/FieldDefinitions.aspx))
- `WATER_DEPTH`: "The depth of the water at a well/platform location from the
  water level to the mud line."
- `TOTAL_DEPTH_DATE`: "The date drilling on a well reached the final total depth."
- `WELL_TYPE_CODE`: "Indicates the final classification of a borehole denoting
  the purpose of the drilling."
  ([Borehole field definitions](https://www.data.bsee.gov/Well/Borehole/FieldDefinitions.aspx))

The code tables inside the archives give the labels used below: permit type
`COMP` is "Completion"; sub-operations `INITCOMP` "Initial Completion", `ZONE`
"Change Zone", `PERF` "Modify Perforations", `REPERF` "Reperforation",
`OTHRCOMP` "Other Completion", `FRAC` "Hydraulic Fracking"; report operation
code `C` is "COMPLETION"; completion status codes such as `POW` "PRODUCING OIL
WELL", `PGW` "PRODUCING GAS WELL", `OSI` "OIL SHUT IN", `GSI` "GAS SHUT IN",
`GLO` "GAS LIFT OIL", `WIW` "WATER INJECTION WELL".

**Not defined by BSEE on those pages:** the fields of the completion tables
(`INTERVAL`, `COMP_STATUS_CD`, the perforation depths) and `EOR_OPERATION_CD`.
The interval labels (S1, S2, D1 and so on) are therefore reported as observed
labels; what the letter and the number mean is not established here, and no
count rests on that meaning. Perforation depths carry no stated unit and are
not used; only the number of perforated intervals is counted.

## Definitions

A completion leaves two public records. Both are counted, and kept apart.

1. **Completion approval** (permit file). One approved permit to modify of a
   Gulf well, counted once by its permit key, whose type is `COMP` and which the
   interventions study classifies as "initial completion excluded": no `ZONE`
   sub-operation (a change of zone is a recompletion, which that study counts
   as an intervention), no plug-back and no new hole. The rule is imported from
   that study's code, not copied. Year is the approval year; 2005 is the first
   full year of the feed and 2026 runs to 23 Nov.
   - *Initial completion*: the approval carries the sub-operation `INITCOMP`.
   - *Other completion work*: it does not (perforation changes, other
     completion). These approvals are in the group the interventions study
     excludes, and they are not initial completions by the regulator's own
     sub-operation label.
2. **Completion report** (End of Operations Report file). One report of a Gulf
   well whose operation code is `C`. Its year is the borehole status date. A
   bore can have more than one such report, and for 1,741 of the 1,878 bores
   that do, every report carries the same status date, so the status date is
   read as the date of the bore's completion status, not the date of each
   report (`summary.json`). What each later report covers is not classified
   here. The file holds no filing date.
3. **First completion record of a bore.** A bore is one twelve-digit API number; a well is
   its first ten digits. By the approval record: the bore's earliest initial
   completion approval. By the report record: the earliest status date among its
   completion reports. The earliest record is taken over the whole file and then
   the years 2005 to 2026 are kept, so a bore first approved in 2004 is not
   counted in 2005. A first completion record is the first record in the
   electronic files, not a statement that the work was done; the table and key
   names (`bores_first_completed_...`) keep the shorter wording. A
   bore completed on paper before April 2004 and approved or reported again
   later would be counted at its first electronic record, on either basis; the
   files cannot show how many there are. The reports are every report of code
   `C`, not only reports of an initial completion.
4. **Water depth bands**, as in the interventions study: under 100 m, 100 to
   500 m, 500 to 1,500 m, 1,500 m and deeper (feet times 0.3048), from the
   bore's water depth, or the single depth shared by every bore of the well.
   Every counted record has a depth.
5. **Fluid** of a bore: from the status codes of the completion intervals on its
   completion reports. Oil: `POW`, `GLO`, `OSI`. Gas: `PGW`, `GSI`. Oil and gas:
   both. Injection or source: `WIW`, `GIW`, `LIW`, `WSW`. This grouping is this
   study's reading of the regulator's labels. A status code is the status at the
   time of the report (producing or shut in), not a production record.
6. **Wells drilled** and well type follow the interventions study: one well is
   one ten-digit API number with a non-cancelled bore and a spud date;
   development or exploration is the type of the original hole.

## Results

Years 2005 to 2026 (2026 to 23 Nov). Every number is in a table in
[`output/`](output).

| Count | Value | Table |
| --- | ---: | --- |
| Completion approvals (the group the interventions study excludes) | 8,472 | `completion_approvals_by_year_band.csv` |
| of which initial completion (`INITCOMP`) | 6,841 (80.7 %) | same |
| of which other completion work, no change of zone | 1,631 | same |
| Bores with a first initial completion approval | 3,216 (2,921 wells) | `bores_first_completed_by_year_band.csv` |
| Bores with a first completion report | 3,238 (3,005 wells) | same |
| Completion reports, status date 2005 to 2026 | 5,276 | `completion_reports_by_year_band.csv` |
| Completion reports, all status years | 8,446 | `summary.json` |

By water depth, 2005 to 2026:

| Water depth | Completion approvals | Bores with a first initial completion approval | Bores with a first completion report |
| --- | ---: | ---: | ---: |
| Under 100 m | 4,460 | 1,959 | 2,013 |
| 100 to 500 m | 641 | 239 | 243 |
| 500 to 1,500 m | 1,676 | 561 | 553 |
| 1,500 m and deeper | 1,695 | 457 | 429 |
| All | 8,472 | 3,216 | 3,238 |

- Approvals: 657 in 2006, the highest year, and 331 in 2025. Under 100 m: 531
  and 51. At 1,500 m and deeper: 30 and 173.
- Bores with a first initial completion approval: 395 in 2006 and 73 in 2025; with a first completion report:
  394 and 72.
- The two records name largely the same bores: 3,043 of the 3,216 bores first
  approved have a completion report (94.6 %), and 3,048 of the 3,238 bores first
  reported have an initial completion approval (94.1 %). The status date falls
  a median 23 days after the first approval (middle half 12 to 43 days); for
  157 matched bores it falls before it (`approval_report_match.csv`).
- A bore first approved for initial completion carries a mean 2.13 initial completion approvals
  (median 1; 1,677 bores carry one).
- Other completion work (`completion_approval_suboperations.csv`, which counts
  each sub-operation over all approvals and over each kind): of the 1,631
  approvals, 1,020 carry Modify Perforations (62.5 %) and 381 Reperforation
  (23.4 %). One approval can carry several sub-operations. The interventions
  study names the whole group of 8,472 "initial completion excluded"; here
  only the 6,841 with the sub-operation `INITCOMP` are called initial
  completions.
- What the reports of the 3,238 bores record (`bore_attributes_by_band.csv`,
  `bore_attributes_all_depths.csv`, `fluid_by_year.csv`): oil 1,746, gas 1,125,
  oil and gas 231, injection or source 86, no interval reported 50. Under 100 m
  gas 46.4 % and oil 40.2 %; at 1,500 m and deeper oil 85.5 %. The subsea
  completion flag is YES for 1.6 % of bores under 100 m and 89.7 % at 1,500 m
  and deeper; it is not stated for 67 bores (2.1 %). 1,038 bores (32.1 %) have
  more than one completion interval label reported.
- Perforated intervals (`perforated_intervals_by_band.csv`): of 5,143 completion
  intervals read, 82.7 % record one perforated interval and 0.9 % none.
- Hydraulic fracturing sub-operation (`fracturing_by_year.csv`,
  `fracturing_by_band.csv`): the code `FRAC` first appears on a permit in 2015.
  Of the 805 bores first approved for initial completion from 2016 to 23 Nov
  2026, 538 (66.8 %) carry it. Before 2015
  the code is absent, which is a change in coding; whether practice changed is
  not established, and no trend is drawn across 2015.
- Drilling to completion (`drilled_to_completed.csv`): of the wells first
  drilled 2005 to 2025, 1,023 of 1,235 development wells (82.8 %) and 792 of
  1,655 exploration wells (47.9 %) have an initial completion approval.
- Timing (`timing_by_band.csv`), for the bores first approved for initial
  completion from 2005 to 23 Nov 2026, not the drilled-well group above: the
  first initial completion approval falls a median 9 days after the total
  depth date (middle half 4 to 34; 3,213 bores with a total depth date), and
  the completion status date a median 35 days after it: 24 days under 100 m
  and 85 days at 1,500 m and deeper (3,043 bores that also have a completion
  report).

Charts: [`01_completion_approvals`](output/01_completion_approvals.svg),
[`02_bores_first_completed`](output/02_bores_first_completed.svg),
[`03_fluid_by_year`](output/03_fluid_by_year.svg),
[`04_drilled_to_completed`](output/04_drilled_to_completed.svg), each as SVG
and PNG.

### Half decade figures

The [figure index](output/figures.json) gives the four body figures, their CSVs,
and the row, column and display precision behind each bullet. The first two
figures show approvals per calendar year for initial versus other completion
work, then for recompletions and perforation work. Recompletion requires a
`COMP` permit with `ZONE` that passes the interventions screen. The two
perforation flags apply to other completion work. A permit can carry both
flags, so the panels cannot be added. Only permits with an approval date in
the plotted window contribute to the figures.

The third figure divides completion approvals by the sum of the annual
1 January standing well inventories in each depth band. It measures approval
intensity across the Gulf and includes approvals on wells drilled later in the
year. Permit depth follows the bore or its unique well depth (definition 4).
Inventory depth follows the original hole or its unique well depth. A well
enters on its first dated Gulf spud among noncancelled bores. It leaves when
all nonsuperseded bores are permanently abandoned with known status dates,
at the latest of those dates. January observations of unknown depth are
excluded from the four curves. The [interventions inventory method](../interventions_by_depth/README.md#method)
gives the bore status and region rules.

The [shared chart module](../../../packages/worldenergydata-bsee/src/worldenergydata/bsee/half_decade.py)
sums tidy year, band and count rows, optionally by group. It supports counts,
counts per calendar year and rates from pooled exposure. An empty rate cell
means zero exposure. The four complete periods contain five years each. The
2025 to 2026 point uses two calendar years and includes the records available
in the 23 November 2026 snapshot, with 38 calendar days left in 2026.
The plot leaves this point detached and makes no projection for those days.
Figure 4 retains the 2005 to 2025 spud cohort and displays exploratory wells
first. Later spuds had less time to receive an initial approval by the snapshot.

## Checks

Tests: [`tests/unit/bsee/test_completions_by_depth.py`](../../../tests/unit/bsee/test_completions_by_depth.py),
written and committed before the counting code. Tolerances were fixed before
the first run: every count comparison is exact; a percentage stored to one
decimal equals its counts within 0.05 point.

| Check | Comparator class | Result |
| --- | --- | --- |
| Band counts sum to the total; year counts sum to the total; the year by band grid is complete, without repeats | conservation | pass, approvals and reports |
| Each approval and each report is counted once, by its key; a repeated raw row adds nothing; a conflicting repeat stops the run | conservation | pass (207 repeated permit rows in the feed) |
| The approvals equal the interventions study's "initial completion excluded" group, computed by that study's own code on the same archives | cross-solver (independent reading, joining and tallying; shared classification rule) | 8,472 on both sides; 110 year by band cells compared, none different |
| The completion reports equal that study's report count | cross-solver | 5,276 on both sides; 110 cells, none different |
| Two samples counted by hand from the extracted text | hand count | match (below) |
| A recount from the raw archives reproduces every delivered table byte for byte | archived-run (a guard against drift, not evidence of correctness) | pass |

What the cross-check cannot see: the classification rule itself is shared with
the interventions study by import, so an error in that rule would appear in
both counts. The hand counts and the regulator's `INITCOMP` label are the
comparators outside it.

### Hand counts

Taken from a plain listing of the extracted text, before any counting code
existed.

- Permits of type `COMP` approved in March 2025: 30 listed; 3 carry `ZONE`;
  27 completion approvals remain: 8 under 100 m, 0 at 100 to 500 m, 5 at 500 to
  1,500 m, 14 at 1,500 m and deeper. 25 carry `INITCOMP` (7, 0, 5, 13), on 14
  bores.
- Completion reports with a status date in January to March 2025: 18 reports
  (4, 2, 5, 7 by the same bands), on 17 bores.

The run recomputes both and writes them to `output/verification.json`, where
the tests compare them with the hand values.

### Run record

`output/verification.json` records the code commit, the command, the Python
and pandas versions and the UTC time of the run that wrote the tables, with the
archive digests.

## Limits

- Approvals are permits, not completed jobs; one completion can carry several
  approvals, and an approved job may not be done.
- The status date on a completion report is "the date the borehole status
  becomes effective". For 98.0 % of the reports in the window the status is
  `COM`; for the rest it is the date of another status (temporarily abandoned,
  sidetracked, bypassed).
- Records begin in April 2004. Completions approved or reported on paper before
  that are not in the files.
- Water depth, well type and status are the values in the 23 Nov 2026 borehole
  file, not values at the time of the work.
- Recent years are incomplete in a specific way: a bore approved in late 2026
  may not have its report yet.
- Completion design (sand control, tubing size, tree type, intelligent
  completions) is not in these tables.

## Run it

```text
uv run python -I examples/bsee/completions_by_depth/count_completions.py \
  --data-dir <folder holding the three archives> \
  --out examples/bsee/completions_by_depth/output
python3 examples/bsee/completions_by_depth/plot_charts.py
bash examples/bsee/completions_by_depth/render_png.sh      # needs google-chrome
BSEE_SERIES_BASIS_DIR=<that folder> uv run pytest \
  tests/unit/bsee/test_completions_by_depth.py
```

Without `BSEE_SERIES_BASIS_DIR` the three tests that read the raw archives are
skipped; the synthetic and delivered-table tests always run.

To adapt the counts to a field, lease or depth range, see the
[reusable prompt](reusable-prompt.md).
