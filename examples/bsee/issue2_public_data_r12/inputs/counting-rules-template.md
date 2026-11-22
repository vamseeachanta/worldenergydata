# Counting rules and record counts

Issue 2 public data article ("Gulf of Mexico well permits: a public US data file"), revision 12. This file holds
in full what Appendix B of the article summarises. `build_r12.py` writes it from
`inputs/counting-rules-template.md` and the data files in `data/`.

Purpose:

- Say how each number in the article is counted, so anyone can rerun it and get the same result.
- Give the record counts and exclusions behind each number, so a rerun can be checked line by line.

## 1 New-well permits (Figures 2 to 5, Table 1)

- Source: BSEE Application for Permit to Drill raw data (APDRawData.zip), file of 2 November 2026, retrieved
  3 November 2026.
- Count each well once, at its first New Well permit in the Gulf of Mexico region.
- Use the requested spud year and the rig type named on that permit.
- From 2005 to 2026, 2,895 wells are counted this way. The rule leaves out each well's later permits, and the
  10 wells whose first New Well permit gives no requested spud date. The year 2026 runs only to the file of
  2 November 2026.
- Rig types: jack-up, drillship, semisubmersible, DP semisubmersible (dynamically positioned), platform rig and
  submersible. Barge, barge rig and well intervention vessel (19 permits) are grouped as other.
- Counting script: [rawdata_fact_check](https://github.com/vamseeachanta/worldenergydata/tree/f5af5b6da87710bb395552f9cda5e34d1f324479/examples/bsee/rawdata_fact_check)
  at commit f5af5b6d (merged 16 November 2026).

## 2 Water-depth bands (every figure)

- The files give water depth in feet. Convert at 1 ft = 0.3048 m exactly (NIST SP 811, Appendix B.8).
- Bands: under 100 m, 100 to 500 m, 500 to 1,500 m, and 1,500 m and deeper. A depth on a band edge goes to the
  deeper band.

## 3 New wells by year and the map (Figure 1)

- Source: BSEE borehole raw data (BoreholeRawData.zip), file of @@BORE_FILE@@, retrieved @@BORE_DATE@@.
- Count one `API_WELL_NUMBER` with `REGION_CODE=G`, original-hole suffix `ST00BP00` and status other than `CNL`,
  by the year of `WELL_SPUD_DATE`, 2005 to 2025, at `SURF_LATITUDE` and `SURF_LONGITUDE`, in the band of the
  borehole `WATER_DEPTH`. Every selected well has coordinates in the map area.
- `derive_r12.py` applies the revision 9 rule (`build_r9.map_wells`) one year at a time and checks that
  2005 to 2009 and 2021 to 2025 give the revision 9 map wells, well for well. Data:
  [map-wells-by-year.csv](data/map-wells-by-year.csv) and [new-wells-by-year.csv](data/new-wells-by-year.csv).
- Map windows: every five-year window from 2005 to 2009 up to 2021 to 2025, one year apart; a window counts each
  well once. Counts per window: [map-windows.csv](data/map-windows.csv).
- Rolling average: the mean of the year and the two years before it, shown from 2007, when the first full
  three-year window ends. Data: [new-wells-trend.csv](data/new-wells-trend.csv).
- Oil price: the calendar-year mean of the twelve monthly Cushing WTI spot prices (US Energy Information
  Administration), from the repository snapshot `data/wti-monthly.csv`. Data: [wti-annual.csv](data/wti-annual.csv).
  The price is shown beside the counts; the article does not fit or claim a cause.

## 4 Day statistics (moved with section 3 to the plugging-and-abandonment article)

Revision 10 gave the days from drilling to abandonment in section 3. In revision 11 that section moves to the
series' plugging-and-abandonment article; its text and code are kept in
[../plug_abandonment_article/](../plug_abandonment_article/). The rules and counts below are the full revision 10
Appendix B, kept here unchanged.

### 4.1 Recorded intervals and estimates

- Borehole: `TOTAL_DEPTH_DATE` minus `WELL_SPUD_DATE` gives a recorded spud-to-total-depth calendar interval.
- APM: `EST_OPERATION_DAYS` is the operator's estimate on the permit.
- APD: in the permit file retrieved @@SCHEMA_DATE@@, neither inspected APDRawData table has an estimated-days
  field. No drilling estimate is calculated from that file.

The day statistics use full cohort years 2005 to 2025. Sources: BSEE BoreholeRawData.zip, file of @@BORE_FILE@@,
retrieved @@BORE_DATE@@, and eWellAPMRawData.zip, file of @@APM_FILE@@, retrieved @@APM_DATE@@.

### 4.2 Detailed counting rules and exclusions

- Borehole: count one `API_WELL_NUMBER` with `REGION_CODE=G`, original-hole suffix `ST00BP00` and status other
  than `CNL`. Select by spud year, 2005 to 2025. Use borehole `WATER_DEPTH`. The map uses the same boreholes at
  `SURF_LATITUDE` and `SURF_LONGITUDE`; the [map selection counts](data/map-selection.csv) give the wells
  without coordinates in the map area.
- Subtract dates without adding a day. A recorded total-depth date after 2025 remains in the spud-year cohort.
  Missing total-depth dates exclude unfinished or unreported intervals; results describe recorded completed
  intervals. Zero-day intervals may represent work within one day; they are excluded under the nonpositive-day
  rule. The audit separates zero, negative, blank-date and invalid-date cases.
- APM: count each `SN_APM` once. Duplicate rows must agree on API, status date, operation code, days and depth.
  Conflicts stop the build. Separate submissions for the same well remain separate observations; repeat API,
  operation and year keys are counted as a diagnostic below.
- Match the APM `API_WELL_NUMBER` exactly to an unambiguous borehole `REGION_CODE=G`. Exclude unmatched or
  conflicting regions. Use APM `WATER_DEPTH`.
- Select APM `ACC_STATUS_DATE` years 2005 to 2025. The file has no separate approval-status field;
  approved-only coverage is not established.
- Completion: `COMP` without `ZONE`. Intervention: `WORKOVER`, `ENHANCE`, or `COMP` with `ZONE`. This groups
  workover, production enhancement and recompletion. Completion does not mean initial completion only. ZONE takes
  precedence even when INITCOMP also occurs.
- Abandonment: `ABANDON` with `PERMABAN` or `TEMPABAN`. Permanent takes precedence if both occur. The estimate
  covers the whole submission, not an isolated subtype.
- Exclude any `PLUGBACK` subtype as new-hole work. Exclude unspecified abandonment and `OTHER`, `INFORM` and
  `UTIL`; their physical scope is unresolved. Unknown primary codes stop the build.
- The [code mapping](data/code_mapping.csv) retains the source descriptions and analysis rules. Subtypes join
  through `SN_APM_FK`; they do not multiply observations. Classification uses codes, not free-text narratives.
  The [subtype cross-tab](data/subtype-activity.csv) shows the assigned activity. A submission can have several
  subtypes, so its rows are not additive.
- Convert feet to metres at 1 ft = 0.3048 m exactly (NIST SP 811, Appendix B.8). Use under 100 m, 100 to 500 m,
  500 to 1,500 m, and 1,500 m and deeper. Band edges go to the deeper band.
- Exclude missing, invalid, infinite and nonpositive days from each median. Count those exclusions in Table B1
  and days-summary.csv. Missing or invalid depth remains a separate row outside the four depth bands.
- Use linear interpolation for the 25th and 75th percentiles. Pool the full period without trimming large
  positive intervals. A missing median means no usable observations, not zero days.

No cost data is used.

The [repeat-key sensitivity check](data/repeat-key-sensitivity.csv) also keeps only the latest status date per
API, primary operation and status year. A date tie uses the last SN_APM in text order. It reports counts and
medians beside the full-cohort values. @@SENSITIVITY_RESULT@@ Shared keys do not prove revisions; distinct jobs
can share them. This alternative does not replace the permit-based results.

Selection counts before day exclusions (exact counts: [exclusions.csv](data/exclusions.csv); activity totals
partition the selected APM records; other lines describe selection steps or named repeat-key and zero-depth
diagnostics):

@@AUDIT@@

### 4.3 Records and day exclusions by water depth (Table B1)

@@DAYS_DETAIL_TABLE@@

- Stages in the order of a well's life, 2005 to 2025. Missing-depth rows are kept here, including zero counts.
- Used is the count behind each median; missing or invalid days and nonpositive days are left out.
- Displayed values use at most four significant figures; ≈ marks rounded counts.
- Data: [days-summary.csv](data/days-summary.csv).
