# Revision 8 changes

Owner comments received 12 November 2026, 21:50 UTC.

## Comment 1

> Convert into bullet points and name them as. "some of the observations are as follows": and then convert the rest in the bullet points.

Section 1 turns the trend sentences into three observations, each linked to its figure.

## Comment 2

> Following this, can we also add. the distinction between drilling days. completion days intervention days and abandonment days, Etcetera. If we have those inside, I think we do Let us add that as another section. and let us number the sections and subsections so that people can easily follow. in this new letter

Sections 3.1 to 3.3 distinguish estimates from recorded intervals, give observation bullets, short rules, quartiles and usable counts. Appendix B holds detailed rules and exclusions. Sections and subsections are numbered; the prompt remains Appendix A.

## Comment 3

> Convert bullets where possible to keep the reading clear. and nice.

Sections 1 and 3.1 give observation bullets. Section 3.2 has five short rules, and Table 2 in section 3.3 has six columns. Detailed rules and counts are in Appendix B.

## Comment 4

> Can we also add a pie chart below? for every year? for representative decades? something like the most representative or median and Justice add them

Section 2.1 adds rig-type pies for 2005, 2015 and 2025, using the Figure 1 counts.

## Comment 5

> Can we also add a pie chart below? for every year? for representative decades? something like the most representative or median. This way people can look at the trends

Section 2.2 adds water-depth pies for the same full years, using the Figure 2 counts.


## Data choices

- Sections 2.1 to 2.3 retain the r7 snapshot: APDRawData.zip dated 2 November
  2026, retrieved 3 November 2026. Both bar charts, all six pies and Table 1
  retain its counts. The supplied counting script is referenced at its published
  revision. The original raw zip was not supplied; its digest is inherited from
  the supplied r7 receipt. The new APD download is used only to inspect schema.
- Pies use fixed full years 2005, 2015 and 2025. They are illustrative decade
  years, not medians selected by an unstated criterion. Shares are calculated
  from the exact r7 annual counts and shown with one decimal
  place. Zero-permit categories remain in the CSVs but are omitted from pie labels and legends. Year totals are in the pie titles. Partial 2026 is excluded.
- Section 3 uses APM and borehole files retrieved 13 November 2026 UTC. Each URL,
  retrieval time and SHA-256 is recorded in data/sources.csv. The HTML source
  list and Appendix A name every raw file, its URL and retrieval date.
- Neither inspected APDRawData member contains an estimated-days field. No
  drilling estimate is invented. Section 3.2 states this absence; Appendix B.1 dates the schema check.
- APM uses SN_APM, API_WELL_NUMBER, ACC_STATUS_DATE, APM_OP_CD,
  EST_OPERATION_DAYS and WATER_DEPTH. Subtypes join through SN_APM_FK and
  APM_SUBOP_CD. VALUE and DESCRIP in the primary and subtype dictionaries
  supply the code labels. data/code_mapping.csv saves the labels and rules.
- The APM cohort uses status-date years 2005 to 2025. A separate approval-status
  field is absent, so approved-only coverage is not established. Exact API joins
  to an unambiguous borehole REGION_CODE=G establish the regional selection.
  APM WATER_DEPTH is used directly; no depth is inferred from another bore.
- Duplicate APM identifiers must agree in every analysis field. The inspected
  source has 207 duplicate rows differing only in company-name text; those names
  are not exported. Conflicting estimates, depths, dates or codes stop the build.
- Completion is COMP without ZONE. Intervention is WORKOVER, ENHANCE or COMP
  with ZONE. ABANDON plus PERMABAN is permanent; TEMPABAN is temporary unless
  PERMABAN also occurs. The estimate belongs to the whole submission. PLUGBACK
  is excluded first. Unspecified abandonment, OTHER, INFORM and UTIL are excluded
  and counted. This narrower coded intervention cohort avoids treating unresolved
  or administrative scope as physical work. Unlike the prior study, free-text
  narratives are not classified. Residual mixed scopes remain a limitation.
- Boreholes use REGION_CODE=G, WELL_NAME_SUFFIX=ST00BP00 and BOREHOLE_STAT_CD
  other than CNL, one API_WELL_NUMBER each. The spud year is 2005 to 2025.
  TOTAL_DEPTH_DATE minus WELL_SPUD_DATE is a recorded calendar interval, not
  active drilling days. A later total-depth date remains in the spud-year cohort.
  Missing dates and nonpositive intervals are excluded and counted. Results are
  conditional on recorded completed intervals; no imputation is applied.
- The four depth bands use 0.3048 m/ft, lower-inclusive edges and an open upper
  band. Negative, nonnumeric and nonfinite depths are kept as missing depth,
  outside the four-band figure. Appendix B, Table B1 retains all five missing-depth rows, whose
  counts are zero. Table 2 omits these rows. Quantiles use linear interpolation. No upper-tail
  trimming, cost data or job-duration equivalence between sources is used.
- Figure 3 and Table 2 pool the retained 2005 to 2025 cohorts. Coding and coverage
  can change over that period. The medians do not establish present-day job
  durations. Table 2 reports usable counts; Table B1 reports total, usable, missing/invalid and nonpositive counts.
- Table 1, both hypothesis paragraphs, the try-it sentence, leaves-open sentence,
  closing invitation, footer and inherited byline are preserved. The review panel
  explicitly limits that earlier approval: revision 8 remains pending review.
- The page embeds Plotly 2.35.2 and the static figure images for offline use.
  PNG/SVG copies and exact CSV data accompany every figure/table. Displayed
  numbers use the significant-figure limits; machine-readable counts and source
  digests retain the precision needed for verification.

## Review corrections

- Issued hashes now pin all three raw archives and Plotly in
  `inputs/source-pins.json`. A new cache with changed upstream bytes fails;
  receipt integrity alone does not establish the issued source version.
- Counts rounded under the owner's four-significant-figure limit carry an
  approximation mark. The exact counts remain in CSVs. The suggested display
  of full five-digit counts was not adopted because it conflicts with that limit.
- Section 3 now uses the heading “Drilling intervals and permit day estimates”.
  The lead reports the two bases without implying matched comparisons.
- The borehole status column is required. US month/day date parsing rejects an
  invalid month instead of swapping its components. These changes leave the
  issued medians, quartiles and usable counts unchanged.
- Appendix B.2 links the subtype/activity cross-tab, discloses ZONE precedence
  even with INITCOMP, and distinguishes repeated submissions from unique jobs.
  Zero-depth and repeated API/operation/year diagnostics are counted.
- Appendix B.1 dates the APD schema inspection. Unresolved image placeholders and
  script-closing text fail the build. Table 1 HTML, CSV and annual aggregates
  are reconciled in tests. Pie legends also state every category's percentage,
  so small slices retain readable share labels.
- The static fallback now hides unused interactive containers. With scripts
  disabled, the figures appear without empty chart boxes. Large counts use
  rounded positional notation with thousands separators and an approximation
  mark, instead of e-notation. SVG output is normalized to LF without trailing
  whitespace; scoped Git attributes preserve the issued bytes on checkout.
- Archive-member lists and date-quality diagnostics are exported. Zero and
  negative date intervals are reported separately; both remain excluded under
  the requested nonpositive-day rule. Zero days can include work within one day.
- No archive replica is claimed. The cache must be retained locally for later
  reproduction if BSEE replaces the downloadable files. Appendix B.2 links a
  repeat-key sensitivity CSV retaining the latest status date per API, primary
  operation and status year, with text-order SN_APM as the tie-break. Shared
  keys do not establish revisions, so this alternative does not replace the
  requested permit-submission results. Counts and medians for both bases are
  retained in the CSV.

## Revision round 2

The owner's standing readability requests of 12 November 2026 (generic access
for readers, and clear reading at 21:50 UTC) apply throughout the body.

1. Section 3.2 now has five plain bullets and one link to Appendix B. Appendix
   B.1 retains the source-field definitions; B.2 retains all detailed counting,
   precedence and tie rules, the repeat-key sensitivity result and selection
   counts before day exclusions. No calculation or source selection changed.
2. Section 3.3, Table 2 now has six columns: activity and basis, water depth,
   used count, Q1, median and Q3. All five zero-count missing-depth rows are
   omitted. The page states that every selected record has a water depth; the
   build rejects that statement if missing-depth records appear. Appendix B.3,
   Table B1 and `days-summary.csv` retain all record and exclusion columns.
3. Section 3.1 starts with “Some of the observations are as follows:” and three
   bullets. The build reads `days-summary.csv` for the completion and drilling
   endpoint medians and the intervention/permanent-abandonment ranges. Tests
   compare the bullets with the CSV and change an input median to verify linkage.
4. The two hypothesis paragraphs, try-it paragraph and leaves-open paragraph
   follow Figure 3, immediately before the closing invitation. Their text is
   unchanged from the preceding commit.
5. Section 1 names APD, APM and borehole files explicitly in plain words.
6. Page retrieval dates use day, full month name and year. ISO retrieval
   timestamps remain unchanged in `sources.csv`.
7. Figure 1, Figures 1a–c, Figure 2, Figures 2a–c and Table 1 captions name BSEE
   Application for Permit to Drill raw data, the archive, file date and retrieval
   date. The redundant Table 1 footnote is removed; table values are unchanged.
8. All pie shares use one decimal place, in static images and interactive
   labels/legends. Zero-permit categories are hidden in both presentations;
   each pie caption notes this. Exact source and pie CSV values are unchanged.
9. `review-plan.html` is removed. The template contains only the concise r8
   review panel; no inherited pull-request, commit or gate-run panel remains.
10. The top panel has one bullet per original owner comment plus one section 3
    data bullet. The inherited approval byline remains qualified as earlier
    approval; revision 8 has not been published.
11. The requested render profile and two probe HTML files were removed from
    `cache/`. Source archives, Plotly and their receipts remain for offline use.

README describes the revised sections, tables and share formatting. The generated
HTML remains an output of the script and template, never an authored edit.
