# Article revisions

## Revision 4

Revision 4 is `gom-well-interventions-r4.html`. It applies no new owner
comment. It rebuilds the page after the code review of revision 3 found three
defects in the data steps; those are fixed in the data change that the page now
pins to. It replaces the revision 3 page, which this change does not carry.

- Raw archives are read only after their size and SHA-256 match the manifest.
  This applies to the end-of-operations archive, which supplies the subsea
  flags, and to the life-cycle step, which earlier compared two manifests but
  not the archives themselves. On the retained files of 13 November 2026 no
  output changes.
- Sidetrack and bypass ages now use the window of the permit events, 2005 to
  2026. Revision 3 mixed 13,898 sidetracks spudded from 1948 to 2004 with
  permits from 2005 on, while Figure 2 and the text describe events from 2005.
  The age table states the window in a new `event_window` column.
- The data tables, the chart and the reusable prompt are pinned to their own
  commits: data links to the data change, chart links, the study link and the
  prompt to the commit that also holds the charts and scripts.
- Appendix A, "Permits", states the assumption that the README already marks
  as assumed: BSEE's permit table has no separate approval-status field, so
  every row is taken to be an approved permit and `ACC_STATUS_DATE` is read as
  its approval date, both to be confirmed. No number changes with it.

### Numbers that changed from revision 3

Only the sidetrack or bypass ages. Every other output table is byte-identical,
and every other number on the page is unchanged.

| Where | Revision 3 | Revision 4 |
| :-- | :-- | :-- |
| Section 2, life story: development sidetrack, median years after spud | 1.6 | 14.4 |
| Figure 2, right: development sidetrack, median (middle half), years | 1.6 (0.1 to 16.0) | 14.4 (1.2 to 28.6) |
| Figure 2, right: exploration sidetrack, median (middle half), years | 0.2 (0.1 to 0.7) | 0.5 (0.2 to 7.2) |
| `life_cycle_event_ages.csv`: sidetrack events, all wells | 17,284 | 3,386 |

The life story sentence changes with the number. Revision 3 said development
wells were sidetracked "usually early (median 1.6 years after spud)", with heavy
work "next" at 13.3 years. With one window, sidetracks and heavy work come at
similar ages (medians of 14.4 and 13.3 years), and the page now says so; the
build stops if those two medians move more than two years apart or if light
work no longer follows them.

Figures 1 and 3 to 6 are unchanged: their input tables are byte-identical.

## Revision 3

Owner comments received 13 November 2026 on revision 2. Each comment is quoted
as received; the lines below it say where revision 3 applies it. The page is
`gom-well-interventions-r3.html`, built by `../build_article.py` from the
tables in `../output/`. Revision 2 was prepared outside this repository; its
text is not carried over except where a comment refers to it.

### Comment 1 (opening paragraph, "In 2025, three quarters of the approved abandonment permits...")

> Introduce the key. significance of intervention for. following this. we can always proceed further. to the greater details

- New section 1, "Why interventions matter", opens the article. It says what
  an intervention is, light against heavy, why an operator does one, and what
  it costs and saves, each with its source page: BOEM EIS 2016-018, section
  3.1.3.5, pp. 3-37 and 3-38 (purpose, 7-day median, "seven workovers or other
  well activities during its lifetime"); BSEE TAP-738 pp. 5-21, 6-9, 8-12 and
  8-18 (intervention vessels against rigs, 12 to 15 rig days against 8 to 10,
  day rates). The cost range comes from `output/cost_table.csv`.
- The details follow: the well life cycle (section 2), then the counts by
  water depth (section 3). The revision 2 opening fact is kept in section 3:
  three quarters of the 2025 abandonment approvals (1,963 of 2,610) were for
  wells in less than 100 m of water.

### Comment 2 (before Figure 1, the stacked bars of approved permits)

> Before coming to this. can we add? a chart of the key life cycle? of the wells that we are seeing. [...] life story. Life story life story. That is the secret

(The full comment is long; it asks for the lifetime of a well in years, the
counts of drilling and sidetrack work, interventions split heavy and light,
temporary and permanent abandonment, for all wells, as a life story; then the
interventions; abandonment in the next article.)

- New section 2, "The life of a Gulf of Mexico well", before the permit
  charts, from the same BSEE borehole and permit-to-modify archives (files of
  13 November 2026), built by `../well_life_cycle.py`:
  - Figure 1 (`05_well_life`): life in years of every Gulf well with a spud
    date (37,512), development and exploration, abandoned and still standing.
  - Figure 2 (`06_well_life_stages`): share of wells reaching each stage
    (drilling, sidetrack or bypass, light, heavy and unclassified
    intervention, temporary and permanent abandonment), and the well's age
    at each event.
  - Table 1: per-well counts for wells first drilled 2005 to 2025.
  - "The life story of a development well", a paragraph told from those
    numbers.
- Light and heavy follow the unit type the permit names, which the branch
  already maps (`unit_type_mapping.csv`): light is wireline, coiled tubing,
  intervention vessel, liftboat or recorded non-rig operation; heavy is a
  hydraulic workover or snubbing unit, platform rig, jack-up rig, drillship or
  semisubmersible. The branch's combined "liftboat / jack-up" category is
  divided by its two source codes (LB light, JU heavy). The rule is in
  Appendix A and `output/intervention_weight_mapping.csv`.
- Abandonment stays light: section 5 says the next article covers it.

### Comment 3 (on "Figure 2 divides each year's approvals by its opening well stock.")

> This sounds like a decent matrix, but we would like to understand what this means. [...] it kind of helps us to understand, you know, how many wells are being being modified [...] maybe similar charm in the in the life cycle. of the gulf of Mexico Wells will be very helpful.

- Section 3, "What the rate means", under the rate chart (now Figure 4):
  approvals per standing well per year in plain words; whether intervention is
  going up or down (11.9 to 14.8 approvals per 100 standing wells a year from
  2006 to 2019, 9.4 to 10.5 from 2023 to 2025, part of it the 2021 coding
  change); light against heavy by year (new table
  `output/intervention_weight_by_year.csv`); depth; and abandonment.
- The life-cycle view the comment asks for is Figure 2 in section 2.

### General comment

> We'll have to do these enhancements in a holistic manner across all. the all the articles relevant to such similar analysis and also raise a story to actually assess how we are going to do the worldwide wells as well at some point.

- Not part of this revision. Applying the life-cycle view to the related
  articles and planning a worldwide-wells assessment are passed on for
  planning; no issue is raised from this revision.

### Figure numbers

Revision 3 adds two figures at the front. The existing charts follow as
Figure 3 (approvals by depth, revision 2 Figure 1), Figure 4 (rate per 100
standing wells, revision 2 Figure 2), Figure 5 (unit types) and Figure 6
(cost per event). Their files and contents are unchanged.

### Numbers

- No existing number changed. The 21 existing output tables were regenerated
  from the retained archives after a refactor of `count_interventions.py`
  (permit classification moved into `classified_permits`, unchanged) and are
  byte-identical to the committed ones. The four existing charts are not
  regenerated.
- The README changes are additions (the "Well life cycle" section, two chart
  entries, three run steps) and the test result line (78 to 104 passed).
- New numbers are only in section 2, the "What the rate means" bullets and
  the new tables: `life_cycle_*.csv`, `life_cycle_summary.json`,
  `intervention_weight_by_year.csv`, `intervention_weight_mapping.csv`.
- The life-cycle permits reconcile with the published counts over 2005 to
  2026: 31,932 intervention, 29,470 temporary, 24,572 permanent and 1,866
  unstated-type abandonment approvals; 21 name a well with no spud date.
  In 2025, light 414 + heavy 214 + not established 137 = 765 interventions,
  the headline.
