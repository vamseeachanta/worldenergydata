# Gulf of Mexico well interventions by water depth

## What this adds

Approved permits to modify existing wells are counted separately from new-well drilling permits. One submission is one event, not one well or evidence of completed work. In 2025, **765 well-work approvals + 2,610 abandonment approvals = 3,375 events**. Permanent-abandonment costs apply only to the **1,387 permanent approvals**, not the 1,060 temporary or 163 unspecified abandonment approvals. No expenditure is inferred from counts.

## Data

The collection owner is worldenergydata; the catalog source ID is `bsee-data-center`. The four BSEE raw archives were downloaded on 13 November 2026 (snapshot folder `2026-11-13`). Their size and SHA-256 are verified against the manifest before use. Raw archives are ignored and are not backed up by this PR. Only small derived aggregates and charts are committed.

| File                                                                            | Page updated          | Bytes       | SHA-256                                                            |
|:--------------------------------------------------------------------------------|:----------------------|:------------|:-------------------------------------------------------------------|
| [BoreholeRawData.zip](https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip) | 11/13/2026 4:31:20 AM | 3,490,322   | `66f39baea0ef50ed97a8992dea88d7a0bee24f270b345ea20721abfc8a0ee100` |
| [eWellAPMRawData.zip](https://www.data.bsee.gov/Well/Files/eWellAPMRawData.zip) | 11/13/2026 4:43:02 AM | 35,837,505  | `6db08210b85e822b48c33002e9527d4f52baa5441f252ee79ff7937731be4050` |
| [eWellEORRawData.zip](https://www.data.bsee.gov/Well/Files/eWellEORRawData.zip) | 11/13/2026 4:43:33 AM | 4,503,968   | `d1db6e6c53577ec595273768c925e3e24261be0b289fc6325151ba37fc81d127` |
| [eWellWARRawData.zip](https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip) | 11/13/2026 4:55:32 AM | 130,732,385 | `b7a086c1fb9d270e673c5931ce3822f202ff4e6e8af5cc98e19dd3ddf03d525c` |

[The manifest](output/manifest.json) retains download-start UTC timestamps and raw-page update times (timezone unspecified by BSEE). Source: [BSEE raw data](https://www.data.bsee.gov/Main/RawData.aspx).

## Method

- **ASSUMED - to be confirmed:** every APM main row represents an approved permit. `ACC_STATUS_DATE` is used as its approval date, consistent with the [query's Approved Date column](https://www.data.bsee.gov/Well/eWellAPM/Default.aspx); a separate approval-status field is absent. Counts require a valid date. Deduplication on `SN_APM` removes 207 repeated rows; conflicting API/date/primary-code identities fail. Different submission IDs remain separate, including repeated approvals for one well. Resubmittals and suboperations are not extra events.
- Gulf selection uses Borehole `REGION_CODE=G`, at API12 then API10; a G-prefixed lease is a fallback only for unmatched records. Matched non-G regions cannot be overridden. API normalisation uses the existing leaf utility and retains only 10- or 12-digit identifiers.
- Depth in feet is multiplied by exactly 0.3048. Bands are under 100 m, 100 to under 500 m, 500 to under 1,500 m, and 1,500 m and deeper; an edge enters the deeper band. Event depth uses a unique finite nonnegative API12 value then a unique API10 fallback; ambiguity remains **no depth**. Included events have 100.0% depth coverage. No-depth rows are retained in CSVs and omitted from chart legends when event counts are zero.
- WORKOVER and COMP with ZONE form workover/recompletion; ENHANCE forms production enhancement; OTHER, INFORM and UTIL form other well work. ABANDON with PERMABAN is permanent (takes precedence over TEMPABAN), otherwise TEMPABAN is temporary, otherwise unspecified. The three abandonment groups are counted together for rates, but cost applies to permanent abandonment only. Information and utility permits do not establish rig work.
- PLUGBACK (the source's Plugback To Sidetrack/Bypass), primary new-hole codes and narrow explicit new-hole narratives are excluded. Current ST/BP status is never used to exclude historical approvals. COMP without ZONE is excluded. Narrative screening does not establish exhaustive capture of drilling descriptions. [Primary mapping](output/code_mapping.csv), [suboperations](output/suboperation_mapping.csv) and [exclusion audit](output/exclusion_audit.csv) retain the classification evidence.
- **Standing stock is rebuilt per API10 over all bores**, with CNL (cancelled) bores dropped before both first-spud and status evaluation. A well enters on its first non-cancelled spud date. ST and BP bores are superseded and cannot by themselves keep a well alive. A well leaves when every non-superseded bore is PA with a known status date on or before the stock date; the removal date is the latest of those PA dates. Any live terminal bore retains the well. A well with no non-superseded bore is retained as **assumed standing**, rather than treating the empty terminal set as proof of abandonment. A missing status date on any terminal bore also retains the well and is counted as assumed standing. Spud and status cutoffs are inclusive.
- Inventory depth uses the canonical original-hole depth (ST00BP00; API12 ending 00 preferred, then earliest spud/API12); a unique depth across remaining bores is used where no usable original depth exists. This preserves a stable well-level depth without discarding other bores' statuses. Conflicting fallback depths remain no depth.
- Rates use **wells standing on 1 January**, not year-end stock: approvals during the year can concern wells removed before year end. The numerator includes approvals during the year, including wells first spudded later in that year, so this is approval intensity against opening stock, not a matched-cohort probability. [Standing wells](output/standing_wells.csv) includes stock dates and assumed counts; [year-end stock](output/standing_wells_year_end.csv) is retained separately (partial 2026 capped at the file date). Zero stock yields a missing rate, not zero.
- Full years run 2005–2025, from the first January in the feed to the year before the file date; [full-year averages](output/full_year_averages.csv) exclude partial 2026 through 13 November. The 2026 denominator remains 1 January stock and its rates are not annualised. EOR W/A/C counts use one `SN_EOR` and the borehole-status date; these are not a matched APM completion cohort. [EOR counts](output/eor_by_year_band.csv) and [same-year ratios](output/eor_permit_ratios.csv) remain descriptive.

At 1 January 2025, 136 wells are **assumed standing**: 135 have no non-superseded bore and 1 has a missing terminal status date (categories can overlap). 17 API10 wells lack any non-cancelled first-spud date and are excluded; their historical stock cannot be dated.

Primary OTHER approvals numbered 309–509 per year in 2005–2020, then 174 in 2021, 11 in 2022 and zero from 2023, while WORKOVER approvals averaged 233 per year in 2005–2020 and 439 in 2021–2025. Part of the apparent well-work decline reflects a coding change. The 2025 count should not be compared with the long-run mean without this qualification; electronic coverage also changes in the early years. The feed begins in April 2004; [monthly coverage](output/coverage_by_month.csv) retains the early ramp. Current bore statuses and dates provide a retrospective proxy, not a complete state-transition history; earlier abandonments followed by reopening cannot be reconstructed.

## Headline results

2025 approvals and distinct API10 wells are shown separately. A well can appear in both event families; the two distinct-well columns must not be added as disjoint populations. The cost cases below apply to permanent abandonment only (1,387 of 2,610 abandonment approvals).

| Depth band         | Work / abandonment approvals   | Distinct wells, work / abandonment   | Standing wells, 1 Jan   | Work / abandonment per 100   |
|:-------------------|:-------------------------------|:-------------------------------------|:------------------------|:-----------------------------|
| under 100 m        | 316 / 1,963                    | 180 / 805                            | 5,750                   | 5.5 / 34.1                   |
| 100 to 500 m       | 99 / 282                       | 44 / 101                             | 887                     | 11.2 / 31.8                  |
| 500 to 1,500 m     | 185 / 284                      | 81 / 53                              | 568                     | 32.6 / 50.0                  |
| 1,500 m and deeper | 165 / 81                       | 77 / 28                              | 426                     | 38.7 / 19.0                  |
| no depth           | 0 / 0                          | 0 / 0                                | 5                       | 0.0 / 0.0                    |

Approval-to-well ratios, from [the CSV](output/approvals_per_distinct_well.csv): approvals are not wells.

| Depth band         | Work approvals / well   | Abandonment approvals / well   |
|:-------------------|:------------------------|:-------------------------------|
| under 100 m        | 1.8                     | 2.4                            |
| 100 to 500 m       | 2.2                     | 2.8                            |
| 500 to 1,500 m     | 2.3                     | 5.4                            |
| 1,500 m and deeper | 2.1                     | 2.9                            |
| no depth           | not established         | not established                |

In 2025, deduplicated Gulf approvals number **523 WORKOVER + ENHANCE; 2,734 ABANDON; 3,833 all codes**, equal to the raw archive rows for that year. Exclusions are 127 new-hole preparations (124 ABANDON and 3 ENHANCE) and 331 COMP without ZONE. Retaining 145 COMP/ZONE and 100 OTHER/INFORM/UTIL gives 523 − 3 + 145 + 100 = 765 well work, and 2,734 − 124 = 2,610 abandonment. End-of-operations reports dated 2025 number 12 W, 891 A and 75 C.

## Unit and access evidence

The permit's `RIG_ID_NUM` joins the archive's `mv_apm_rig_view` fields `RIG_TYPE_CODE` and `RIG_NAME` with a validated many-to-one join. The type code selects the category; names are retained in [the lookup](output/unit_type_lookup.csv) but are not used to guess equipment. The mapping below is also retained in [CSV](output/unit_type_mapping.csv). NR enters **non-rig operation (recorded)**; only blank unit information enters **none named**. Of the 1,098 under-100-m permanent-abandonment approvals in 2025, 355 carry the regulator's unit type "non rig PA operation" and 14 name no unit. An unmatched nonblank ID or unmapped type enters other. SU is a submersible and is not classified as a semisubmersible. A permit's named unit need not be the unit ultimately deployed.

| source_field                          | raw_value                     | unit_category                 | rule                                                               |
|:--------------------------------------|:------------------------------|:------------------------------|:-------------------------------------------------------------------|
| RIG_TYPE_CODE                         | WL                            | wireline unit                 | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | CT                            | coiled tubing                 | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | HW                            | hydraulic workover / snubbing | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | SB                            | hydraulic workover / snubbing | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | PF                            | platform rig                  | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | LB                            | liftboat / jack-up            | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | JU                            | liftboat / jack-up            | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | WI                            | intervention vessel           | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | DS                            | drillship / semisubmersible   | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | SS                            | drillship / semisubmersible   | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | SD                            | drillship / semisubmersible   | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | NR                            | non-rig operation (recorded)  | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | BG                            | other                         | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | BR                            | other                         | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | PL                            | other                         | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_TYPE_CODE                         | SU                            | other                         | exact type code; joined via RIG_ID_NUM; no name inference          |
| RIG_ID_NUM / RIG_NAME / RIG_TYPE_CODE | all blank                     | none named                    | no unit information                                                |
| RIG_ID_NUM / RIG_TYPE_CODE            | unmatched ID or unmapped code | other                         | retained unresolved unit; SU is submersible, not a semisubmersible |

Well work — share of approvals, 2025:

| band               | Wireline        | Coiled tubing   | HW / snubbing   | Platform rig    | Liftboat / jack-up   | Intervention vessel   | Drillship / semi   | Non-rig operation (recorded)   | None named      | Other           |
|:-------------------|:----------------|:----------------|:----------------|:----------------|:---------------------|:----------------------|:-------------------|:-------------------------------|:----------------|:----------------|
| under 100 m        | 72.5%           | 3.8%            | 0.0%            | 0.0%            | 8.9%                 | 0.0%                  | 0.0%               | 2.5%                           | 12.3%           | 0.0%            |
| 100 to 500 m       | 35.4%           | 16.2%           | 0.0%            | 6.1%            | 0.0%                 | 2.0%                  | 14.1%              | 11.1%                          | 13.1%           | 2.0%            |
| 500 to 1,500 m     | 8.6%            | 5.9%            | 0.5%            | 7.6%            | 0.0%                 | 6.5%                  | 44.9%              | 7.0%                           | 17.8%           | 1.1%            |
| 1,500 m and deeper | 1.2%            | 0.0%            | 0.0%            | 18.2%           | 0.0%                 | 18.8%                 | 29.1%              | 3.6%                           | 27.9%           | 1.2%            |
| no depth           | not established | not established | not established | not established | not established      | not established       | not established    | not established                | not established | not established |
Permanent abandonment — share of approvals, 2025:

| band               | Wireline        | Coiled tubing   | HW / snubbing   | Platform rig    | Liftboat / jack-up   | Intervention vessel   | Drillship / semi   | Non-rig operation (recorded)   | None named      | Other           |
|:-------------------|:----------------|:----------------|:----------------|:----------------|:---------------------|:----------------------|:-------------------|:-------------------------------|:----------------|:----------------|
| under 100 m        | 41.4%           | 6.6%            | 1.6%            | 0.0%            | 8.4%                 | 0.0%                  | 0.0%               | 32.3%                          | 1.3%            | 8.4%            |
| 100 to 500 m       | 44.7%           | 4.3%            | 0.0%            | 0.0%            | 0.0%                 | 0.0%                  | 9.6%               | 28.7%                          | 0.0%            | 12.8%           |
| 500 to 1,500 m     | 1.9%            | 12.1%           | 24.2%           | 0.6%            | 0.0%                 | 0.0%                  | 57.3%              | 1.3%                           | 2.5%            | 0.0%            |
| 1,500 m and deeper | 0.0%            | 18.4%           | 0.0%            | 5.3%            | 0.0%                 | 0.0%                  | 73.7%              | 0.0%                           | 2.6%            | 0.0%            |
| no depth           | not established | not established | not established | not established | not established      | not established       | not established    | not established                | not established | not established |

[Unit shares](output/unit_type_shares.csv) also retain pooled 2021–2025 counts and all zero/no-depth rows. Chart 04 uses 2025 to align with the headline counts. In 500–1,500 m, only **90 of 157** permanent-abandonment approvals name a drillship or semisubmersible, and **79 of 157** have no YES subsea-completion flag. Water depth cannot select an access method.

The share with an EOR `SUBSEA_COMPLETION_FLAG=YES` follows. This is an **ever-YES flag at API10 in the retained snapshot**, not a contemporaneous access classification: any YES wins across the well's EOR bores; absent YES with a recorded NO is no, and no usable flag is unknown. Unknown records remain in the approval denominator. The complement of YES is not proof of a dry tree. [The CSV](output/subsea_completion_shares.csv) retains YES, NO and unknown counts, plus pooled 2021–2025.

| Depth band         | Flag YES, work / permanent abandonment (%)   | Unknown, work / permanent abandonment   |
|:-------------------|:---------------------------------------------|:----------------------------------------|
| under 100 m        | 0.9 / 0.0                                    | 9 / 56                                  |
| 100 to 500 m       | 21.2 / 9.6                                   | 6 / 2                                   |
| 500 to 1,500 m     | 69.2 / 49.7                                  | 14 / 14                                 |
| 1,500 m and deeper | 84.2 / 65.8                                  | 8 / 5                                   |
| no depth           | not established / not established            | 0 / 0                                   |

## Duration checks

The permit's own `EST_OPERATION_DAYS` medians are the **operator's estimate on the permit, not observed job length**. Only finite positive estimates enter a median; missing and nonpositive values remain counted in [the CSV](output/permit_duration_estimates.csv). In band order, well-work medians are **3 / 6 / 15 / 14 days**, and permanent-abandonment medians are **14 / 10 / 25 / 21 days**.

| Depth band         | Well work, median days   | Permanent abandonment, median days   | Valid estimates, work / permanent abandonment   |
|:-------------------|:-------------------------|:-------------------------------------|:------------------------------------------------|
| under 100 m        | 3                        | 14                                   | 305 / 1,093                                     |
| 100 to 500 m       | 6                        | 10                                   | 96 / 94                                         |
| 500 to 1,500 m     | 15                       | 25                                   | 167 / 152                                       |
| 1,500 m and deeper | 14                       | 21                                   | 136 / 37                                        |
| no depth           | not established          | not established                      | 0 / 0                                           |

Beside those estimates, the weekly-report check unions overlapping or adjacent inclusive intervals of 1–90 days for the same API12, named unit and raw code in 2005–2025. A gap or changed code/unit starts a new proxy episode. Missing/placeholder units are excluded. WO, REC, TA and PA are an interpreted non-drilling token subset; several meanings lack a published BSEE definition. Full-year filtering precedes union and can censor endpoints. The 24,908 episodes are neither permits nor proven complete heavy-rig jobs. [The weekly-report CSV](output/war_duration_crosscheck.csv) preserves each raw-code stratum, including the deepest WO-token median of 18 days.

| band               | episodes   | q25_days   | median_days   | q75_days   |
|:-------------------|:-----------|:-----------|:--------------|:-----------|
| 100 to 500 m       | 2,332      | 7          | 16            | 47         |
| 1,500 m and deeper | 1,202      | 7          | 11            | 21         |
| 500 to 1,500 m     | 2,324      | 6          | 11            | 21         |
| under 100 m        | 19,050     | 5          | 11            | 29         |

## Cost basis

**Access method selects the cost, with depth as source applicability only.** Values are scenario costs per well/event in **unescalated 2015 USD millions, two significant figures**. Permanent-abandonment costs apply only to the 1,387 permanent approvals out of 2,610 abandonment approvals in 2025; they do not price temporary or unspecified abandonment. No count is multiplied by a cost to claim expenditure.

| Well / access type                             | Event                 | Basis                                                        | Applicability                                                                                                                           | Low / base / high (USD million, 2015)   |
|:-----------------------------------------------|:----------------------|:-------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------|
| Platform dry-tree / rigless spread             | well work             | spread x days + mobilisation; source allowances not included | Shelf; source case 50-400 ft (15-122 m)                                                                                                 | 0.53 / 0.75 / 0.98                      |
| Platform dry-tree / rigless spread             | permanent abandonment | spread x days + mobilisation; source allowances not included | Shelf; source case 50-400 ft (15-122 m)                                                                                                 | 0.27 / 0.33 / 0.59                      |
| Platform dry-tree / casing jacks               | well work             | spread x days + mobilisation; source allowances not included | Platform-based spread; source casing-jack case above 400 ft; shelf example                                                              | 0.55 / 0.79 / 1.0                       |
| Platform dry-tree / casing jacks               | permanent abandonment | spread x days + mobilisation; source allowances not included | Platform-based spread; source casing-jack case above 400 ft; shelf example                                                              | 0.28 / 0.35 / 0.62                      |
| Subsea wet-tree / drillship or semisubmersible | well work             | spread x days + mobilisation; source allowances not included | Subsea access; duration cases 7 / 10.5 / 14 days, not depth-specific; not all wells in a depth band                                     | 4.7 / 7.1 / 9.4                         |
| Subsea wet-tree / drillship or semisubmersible | permanent abandonment | spread x days + mobilisation; source allowances not included | Subsea access; low/base durations read at 3,000 ft (914 m), high at 6,000 ft (1,829 m); not all wells in a depth band                   | 11 / 13 / 16                            |
| Subsea wet-tree / drillship or semisubmersible | permanent abandonment | spread x days + mobilisation; source allowances not included | Subsea access; low/base durations read at 6,000 ft (1,829 m), high at 9,000 ft (2,743 m); extrapolation beyond 9,000 ft not established | 14 / 16 / 18                            |
| Deepwater platform dry-tree / casing jacks     | well work             | not priced                                                   | TLP dry-tree access (source); applied to spars as an assumption; Table 8-4 anchors 1,700 / 3,000 / 5,000 ft (518 / 914 / 1,524 m)       | not priced                              |
| Deepwater platform dry-tree / casing jacks     | permanent abandonment | published total; includes source allowances                  | TLP dry-tree access (source); applied to spars as an assumption; Table 8-4 anchors 1,700 / 3,000 / 5,000 ft (518 / 914 / 1,524 m)       | 0.73 / 0.99 / 1.4                       |

- Spread scenarios are rate x days + mobilisation and **leave out the source's allowances**: TAP-738 multiplies wet-tree operations time by weather, work-provision and engineering/project-management allowances (p. 8-18) and applies similar allowances to dry-tree work (Table 8-2). The deep-platform row is a published total that includes them. The Basis column marks each row, so the step between the two platform rows is not a depth effect.
- [BSEE TAP-738](https://www.bsee.gov/sites/bsee.gov/files/tap-technical-assessment-program/738aa1.pdf), 2015: Table 8-2, printed p. 8-12 (PDF p. 143), prices rigless dry-tree wells for 50–400 ft. Its USD 225,856 P&A work charge over 84 hours implies USD 64,530/day rounded. Standalone mob and demob are USD 37,743 each. Setup, rig-down and study contingencies are outside the simple dayrate-times-duration arithmetic.
- TAP-738 Table 8-3, p. 8-14 (PDF p. 145), gives USD 68,424/day for the casing-jack spread. The study uses casing jacks above 400 ft and describes dry-tree TLP wells at about 1,500 to over 4,600 ft. The platform work durations and the shallow rigless transport charges are transferred explicitly to the shelf casing-jack scenarios.
- **Deepwater dry-tree platform permanent abandonment** uses the **published** Table 8-4, p. 8-15 (PDF p. 146), final-column totals: USD 734,356 / 987,262 / 1,374,570 per well at 1,700 / 3,000 / 5,000 ft, respectively (USD **0.73 / 0.99 / 1.4 million** at two significant figures). These are 60-well campaign totals normalised per well and include work provision, engineering, weather and shared mobilisation. They are depth anchors, not statistical low/base/high outcomes. A cited deepwater dry-tree well-work basis is not established, so that row is **not priced**. Dry-tree conductor removal is separate.
- TAP-738 section 8.3.2.3, p. 8-18 (PDF p. 149), gives the drillship/semisubmersible total spread as USD 674,600/day. **Rig mobilisation is excluded**, rather than assumed free. Subsea permanent-abandonment durations follow approximate graphic readings of Figure 8-9, p. 8-19. The 3,000-ft row uses 17 days (MODU leaving the wellhead) and 19 days (MODU) at 3,000 ft for low and base, and 23 days, the MODU reading at **6,000 ft**, for high. The deeper row uses 21 and 23 days at 6,000 ft and 27 days at 9,000 ft. These cases do not classify every approval at those depths. Beyond the 9,000-ft anchor, cost applicability is not established.
- The well-work duration labels are **median 7 days / midpoint 10.5 days / two weeks 14 days**. The [BOEM Gulf EIS 2016-018](https://www.boem.gov/sites/default/files/environmental-stewardship/Environmental-Assessment/NEPA/BOEM-EIS-2016-018-v1.pdf), section 3.1.3.5, p. 3-37 (PDF p. 163), reports a Gulf median of 7 days with a range from 1 day to several months. [BOEM MAG-PLAN Alaska update](https://espis.boem.gov/final%20reports/5179.pdf), 2012, section 3.5.5.4, p. 108 (PDF p. 117), provides one to two weeks; 10.5 days is its arithmetic midpoint. These are transferred duration scenarios, **not a spread of observed outcomes**. The midpoint retains its half day to avoid changing the arithmetic; other reported duration summaries use integer days.
- [BSEE Pacific cost update, vol. 2](https://www.bsee.gov/sites/bsee.gov/files/technology-assessment-program-tap/735ab.pdf), 2015, Appendix 2, p. A-2 (PDF p. 5), provides 3, 4, 5 and 8 trouble-free rigless days per well. The 3 / 4 / 8-day selections are scenario inputs; transfer to casing jacks is an assumption. Operator permit estimates and the weekly-report proxy above do not validate these duration scenarios.

Every numeric input and its citation are retained in [cost_basis.yml](cost_basis.yml), generated by [build_cost_basis.py](build_cost_basis.py). [Full-precision costs](output/cost_table.csv) and [published comparisons](output/published_pa_comparators.csv) retain the arithmetic. The subsea comparator for 500–1,500 m is Figure 8-10's **3,000-ft (914-m) point**, about **USD 13 million** at two significant figures; the 1,000-ft point is outside that band and is not used. The 6,000/9,000-ft comparator is about USD 16 / 19 million. The rigless published total is USD 0.34–0.42 million per well. Published totals include their stated allowances and campaign assumptions and are not equal to the simpler spread scenarios. [Citation receipts](output/cost_source_manifest.json) retain source URLs and PDF digests; a 2015 study rehosted later remains a 2015 dollar basis.

## Limits

An approval does not establish execution. Repeated IDs, administrative scopes, incomplete initial/recompletion and abandonment subcodes, daily snapshot revisions, narrow narrative screening and incomplete electronic coverage limit interpretation. The current bore-status snapshot is not a complete well-life history. Unknown flags do not establish dry-tree access, and named units do not establish deployment. Rates describe approvals against opening stock, not the proportion of wells intervened on. The coding transition limits comparisons with full-period averages.

Cost cases are neither bids nor confidence intervals. Additional materials, logistics, standby, weather and engineering are excluded unless already included in a source spread or published total. Dry-tree conductor removal, full site clearance and remediation are separate; subsea rig mobilisation remains unpriced. Dollar escalation is not applied. A light intervention vessel is not interchangeable with a heavy workover rig. Total Gulf expenditure is not established.

## Tests and reproduction

From the repository root, use the retained archives in `data/modules/bsee/zip/2026-11-13/` with the manifest digests. A new BSEE download (`download_data.py --snapshot <YYYY-MM-DD>`) is a different snapshot; the year selection and all report figures follow it. The example requires the packages in [requirements.txt](requirements.txt).

```sh
uv run --no-sync python examples/bsee/interventions_by_depth/count_interventions.py --data-dir data/modules/bsee/zip/2026-11-13 --out examples/bsee/interventions_by_depth/output
uv run --no-sync python examples/bsee/interventions_by_depth/build_cost_basis.py
uv run --no-sync python examples/bsee/interventions_by_depth/estimate_costs.py --out examples/bsee/interventions_by_depth/output
uv run --no-sync python examples/bsee/interventions_by_depth/plot_charts.py --out examples/bsee/interventions_by_depth/output
uv run --no-sync python examples/bsee/interventions_by_depth/write_results_note.py --test-result '78 passed (tests/unit/bsee/test_interventions_by_depth.py); the API-normalizer file needs the full package environment and was not collected here'
uv run --no-sync python examples/bsee/interventions_by_depth/verify_outputs.py
```

Focused example plus existing API-normalizer tests, PowerShell:

```powershell
$env:PYTHONPATH='packages/worldenergydata-bsee/src;packages/worldenergydata-core/src;../../assetutilities/src;src'
uv run --no-sync python -m pytest --noconftest -o addopts="" tests/unit/bsee/test_interventions_by_depth.py tests/unit/bsee/data/utils/test_api_well_normalizer.py -q
```

Result: **78 passed (tests/unit/bsee/test_interventions_by_depth.py); the API-normalizer file needs the full package environment and was not collected here**. Tests cover all-bore stock, date boundaries, cancelled bores, assumed standing, unit categories, three hand-worked cost literals read through YAML and published deepwater dry-tree pricing. Tests use no network or retained raw files. Aggregate reconciliation, input provenance, output digests and software versions are retained in [verification.json](output/verification.json).

## Charts

PNG width is 2,160 pixels; SVG versions are retained. Footers identify the raw files and date on activity figures and the four cost studies on the cost figure.

- [01 — Approved permits to modify by depth](output/01_approved_interventions.png) · [SVG](output/01_approved_interventions.svg)
- [02 — Approved permits to modify per 100 standing wells](output/02_rates_per_standing_well.png) · [SVG](output/02_rates_per_standing_well.svg)
- [03 — Cost scenarios by well and access type](output/03_cost_per_event.png) · [SVG](output/03_cost_per_event.svg)
- [04 — Unit types named on 2025 approvals by depth](output/04_unit_types_by_depth.png) · [SVG](output/04_unit_types_by_depth.svg)
