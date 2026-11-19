# Article revisions

## What changed since revision 2

`../build_article.py` shows the list below in a panel at the top of the page
(hidden in print). Each item names an owner ask on revision 2 and where it went.

- **Opening graphic** (road map note, 13 November: "add the deckhand opening
  graphic to each of the newsletters"): the shared Deckhand opening graphic
  heads the page; its slot carries this article's title, with no chart.
- **Why interventions matter, first** (comment 1): section 1 opens the article;
  its cost detail is in Appendix B.
- **The life story of a well, before the interventions** (comment 2): section
  2, with Figures 1 and 2 and Table 1, comes before Figure 3.
- **What the rate means** (comment 3): section 3, "What the rate means", under
  Figure 4; the light and heavy detail is in Appendix C.
- **Abandonment in the next article** (comment 2): counted and rated here;
  section 5 says the next article covers it.
- **Across all articles and worldwide wells** (general comment): not in this
  article; passed on for planning.

## Revision 4, review fix-up 3 (built 14 November 2026)

The second-provider review of fix-up 2 found that the reproduction prompt
named the chart commit, whose builder predates the fix-up 2 wording: run as
published, it gave back "wells abandoned under approvals". The cause is in the
design: one pin served both the charts and the code. The page now carries
three pins, each for what it names. Data links pin to the commit of the data
tables, as before. Chart links pin to the commit of the charts, as before. The
study link and the reusable prompt pin to the commit that holds the builder
and scripts that made this page (`--code-commit`; on the command line it
defaults to the last commit that changed the scripts, this file or the opening
graphic, and the build stops if any of them has uncommitted changes). A test
reads the pins from the committed page, checks that nothing the builder runs
or reads changed after the code pin, and runs the builder from the code pin on
the tables there: it must give back the committed page byte for byte. Same
data and chart pins and build date; no chart changes.

- Takeaway: "The data hold 16,860 development wells abandoned so far, of which
  16,858 have an established life; the 23.0-year median is over those 16,858."
  Two abandoned wells have an abandonment date before spud, so their life is
  not established. The populations sentence calls the first value "the life of
  those abandoned wells". Both counts are read from
  `life_cycle_life_years.csv`.

## Revision 4, review fix-up 2 (built 14 November 2026)

The second-provider review of the fix-up found that the takeaway called the
33.0-year value an age of wells "abandoned under approvals". It is the median
age of the well at 17,904 permanent-abandonment approvals from 2005 to 2026:
`life_cycle_event_ages.csv` has one row per approved permit, so repeated
approvals on one well each count and a well that still stands can count. The
page is rebuilt with the same pins and build date. No number changes and no
chart changes.

- Takeaway: "the 33.0-year median age at permanent-abandonment approval",
  "the age of the well at 17,904 permanent-abandonment approvals from 2005 to
  2026, and counts approvals, not wells: a well approved twice counts twice,
  and a well still standing can count". The 23.0-year value stays "the life of
  the 16,860 development wells abandoned so far". The approval count is read
  from the age table.
- Section 2, life story: "temporary-abandonment approval at 32.3 and
  permanent-abandonment approval at 33.0, ages that count approvals, not
  wells". Sections 1 to 5 are now 796 words.
- Opening graphic: the slot of `assets/opening.svg` no longer carries the
  revision 2 chart picture or title. It now shows the label "ENERGY STREET ·
  WELL INTERVENTIONS" under the teal rule and this page's title, "Gulf of
  Mexico well interventions: the life of a well, then the work by water
  depth", with no chart. The frame, hand mark, rope, bollard, wordmark and
  type are unchanged. `assets/opening.png` is rendered from the SVG at
  1200 x 627 and `assets/opening-alt.txt` describes the new slot.

## Revision 4, review copy fix-up (built 14 November 2026)

The review copy of revision 4 failed the pre-review gate. The page is rebuilt
from the same tables (data files of 13 November 2026). No number in a table
changes, and every number of the earlier page is still on the page; some move
from the sections to Appendix B or the new Appendix C.

- Opening graphic: `assets/opening.svg`, `assets/opening.png` and
  `assets/opening-alt.txt` are the shared Deckhand opening graphic of revision
  2. The page embeds the PNG with its alt text in the opening slot, as revision
  2 did. The graphic still shows the revision 2 title and chart in its slot.
- Section 1: the costs are "our scenarios, built from TAP-738 day rates and
  BOEM durations", not the study's cost cases. The day rates move to
  Appendix B, where USD 64,530 a day is "derived from a TAP-738 P&A spread
  (Table 8-2: USD 225,856 over 84 hours)". The 1-day-to-several-months range
  also moves there. "Traditionally" is dropped from the BOEM quote line; it is
  not the source's word.
- Appendix B and the Figure 6 note state that rig mobilisation is excluded
  from the drillship or semisubmersible rows (README: "Rig mobilisation is
  excluded"). Mobilisation is added only for the platform spreads: the rigless
  case (TAP-738 Table 8-2), and the casing-jack case, which borrows it in
  `cost_basis.yml`. Appendix B previously said every spread adds mobilisation.
- Version line: the revision date is the build date (`--build-date`,
  14 November 2026); the data date stays "files of 13 November 2026".
- Takeaway: heavy work (a rig or a hydraulic workover unit) at a median 13.3
  years after spud, light work later at 24.1 years, in place of "heavy,
  rig-based work comes early". A new sentence separates the 23.0-year life
  (every development well abandoned so far) from the 33.0-year median age at
  permanent-abandonment approvals from 2005 to 2026. The band is named
  "1,500 m and deeper", and the shelf is defined at first use (under 100 m
  water depth).
- Article corrections go to the maintainers. The references that follow include
  BOEM 2016-018, BSEE TAP-738 (July
  2015), the BOEM MAG-PLAN Alaska update (2012), the BSEE Pacific cost update
  (February 2015, the rigless durations behind Figure 6) and the BSEE raw data
  and permit query pages.
- Figures 1, 2, 3 and 5 each have a one-sentence lead-in.
- Length: sections 1 to 5, without figures and Table 1, are 790 words (1,214
  before). Moved, not deleted: the day rates and duration range to Appendix B;
  the 2025 interventions by depth, the 2006-to-2025 count, the light and heavy
  rates, the share of wells with heavy work, the age of standing wells, the
  exploration abandonment share and the per-job duration estimates to the new
  Appendix C, before the reusable prompt, which becomes Appendix D and
  stays last. Dropped as repetition: the paragraph listing sections 2 to 4 and
  BOEM's list of other uses of a reentry. The build stops above 800 words.
- Charts: the figure titles that repeated the page captions (Figures 1, 2, 5
  and 6) are removed, and the panel titles of Figures 3 and 4 are shortened to
  "Well work" and "Abandonment". The notes and source lines inside the PNGs
  stay, so a downloaded chart still carries its source. All six charts are
  regenerated from the unchanged tables with matplotlib 3.11.2, the version
  the verification receipt records (Figures 3 to 6 were last drawn with
  3.10.6).
- A "What changed since revision 2" panel, from the section above, heads the
  page and is hidden in print.

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
