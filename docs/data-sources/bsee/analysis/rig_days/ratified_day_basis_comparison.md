# Ratified day basis comparison

## Purpose and decision compared

The repository owner's decision of 2026-10-12 on the day basis is compared with the domain owner's published tables and the repository summary. Drilling is DRL only; completion is COM only; suspended and temporarily abandoned time are separate. This is the comparison requested before replacing published figures (decision comment on issue 1064). No existing figure or calculation is changed.

## Inputs found

The inventory is repository-only. API12 wellbores are the comparison grain; API10 QA rollups are excluded. Existing openpyxl dependency is declared at pyproject.toml:111.

| Path | Contents | Wells covered | Columns used | Size (bytes) |
| --- | --- | --- | --- | --- |
| docs/data-sources/bsee/analysis/rig_days/rig_days_summary.md | activity breakdown and formulas | test well via milestone note | COM,DRL,PND,TA; lines18,25,33 | 2182 |
| docs/data-sources/bsee/analysis/rig_days/rig_days_by_WAR.md | interval method | no IDs | WAR_START_DT,WAR_END_DT,WELL_ACTIVITY_CD; lines3-11 | 484 |
| docs/data-sources/bsee/analysis/rig_days/rig_days_by_milestone.md | calendar/remark anchors | 608124009500 | API,spud,TD,drilling line16; completion line41 | 9010 |
| docs/data-sources/bsee/data/WELL_ACTIVITY_CD/well_activity_cd_description.md | code provenance correction | not a well table | canonical code-list reference | 4220 |
| docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.xlsx | published workbook | 217 API12 | Sheet1 D=API,F=spud,G=TD,H=drilling,I=completion | 36744 |
| docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days_v21_kc.csv | published export | 253 API12 | API_WELL_NUMBER,DRILLING_DAYS,COMPLETION_DAYS,WELL_SPUD_DATE,TOTAL_DEPTH_DATE | 20834 |
| reports/lower_tertiary/data/roy_rig_days_qa.csv | previous computed QA | 22 API12 bore rows; API10 rollups excluded | grain,api12,drilling_days,completion_days,pnd_days,ta_days | 3596 |
| reports/lower_tertiary/lt_well_benchmark_lower_tertiary_2010_latest.csv | calendar benchmark | 56 API12 | api12,spud,drilling_days,completion_days | 7501 |
| docs/modules/bsee/analysis/rig_days/war_data_608124003301.csv | weekly history | 608124003301;32 records | API_WELL_NUMBER,WAR_START_DT,WAR_END_DT,WELL_ACTIVITY_CD | 9072 |
| docs/modules/bsee/analysis/rig_days/war_data_608124009500.csv | weekly history | 608124009500;45 records | same weekly columns | 12281 |
| data/modules/bsee/current/operations/well_activity_summary.csv | sparse operational sample | 69 API12;100 records;2 matching IDs | same weekly columns | 9431 |
| data/modules/bsee/current/operations/well_activity_remarks.csv | remarks; no code or end bound | 84 API12;100 rows | API_WELL_NUMBER,WAR_START_DT,SN_WAR;not counted | 68237 |
| reports/lower_tertiary/data/war_activity_code_frequency.csv | code frequencies; no per-week rows | no well IDs | code,rows,pct;not counted | 492 |
| docs/modules/bsee/analysis/rig_days/attachments/api_608124003301_remarks.xlsx | original/parsed remarks | 608124003301;32 rows | SN_WAR,TEXT_REMARK | 46222 |
| docs/modules/bsee/analysis/rig_days/attachments/api_608124003301_remarks_parsed.xlsx | original/parsed remarks | 608124003301;32 rows | SN_WAR,DATE,TEXT_REMARK | 41653 |
| docs/modules/bsee/analysis/rig_days/attachments/stones_producing_wells.csv | producing-well membership | 22 API12 | API_WELL_NUMBER,WELL_NAME,SURF_BLOCK_NUM | 529 |

Table 1. Inputs opened; byte sizes apply to the inspected revision.

The workbook folder identifies V30; its Sheet1 and Diagnostics have no in-file date or basis. Diagnostics repeats every Sheet1 day figure and is not counted twice. The export filename identifies v21, with no in-file vintage or basis. Current extractor code uses activity codes (docs/modules/bsee/analysis/production/FDAS_V30/extract_drilling_completion_days.py:388-400), which does not establish the retained tables' basis. These two sources are compared separately, including disagreements. QA is a cached recomputation, not independent validation (scripts/lower_tertiary/build_roy_rig_days_qa.py:33-35); bore rows have no stated vintage. The benchmark filename identifies a 2010/latest population, not an observation vintage. Its generator measures calendar spud-to-completion and completion-to-first-oil (packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/well_benchmark.py:272-288). The notes are last updated 2025-07-24; the summary communication is dated 2025-06-02. These dates are in the respective files.

The remarks workbooks have no complete coded weekly duration table. The producing-well table is membership only. The tracked fleet parquet is a rig aggregate with first/last WAR dates, not per-well weekly records. Filename and day-column searches also locate historical test outputs; these are not treated as independent domain-owner published tables.

## Rule and conventions

The new count_ratified_days function wraps war_rig_days.rig_days_by_bore with BASIS_DRL_COM. Existing union_days is reused. No existing function changes. The wrapper adds categories and gap/duplicate diagnostics.

| Code | Treatment | Source in packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/data/war_activity_codes.yml |
| --- | --- | --- |
| DRL | drilling only | lines71-78 |
| COM | completion only | lines80-87 |
| DSI | suspended; excluded from drilling/completion | lines116-123 |
| TA | temporarily abandoned; excluded from drilling/completion | lines89-96 |
| PND | undefined; other-coded, separately visible | lines135-160;null label,unknown role |
| remaining codes | other-coded by actual token | lines98-114,126-133,162-191 |

Table 2. Documented labels are from the borehole-status domain; reuse in activity codes remains inferred (docs/data-sources/bsee/data/WELL_ACTIVITY_CD/well_activity_cd_description.md:43-51). Unknown codes are not given meanings.

A record's own WAR_START_DT and WAR_END_DT are normalized to midnight and counted inclusively. Adjacent, overlapping and duplicate intervals merge within each code and for the overall union (war_rig_days.py:178-211,501-526). The full package path is packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/. Each week retains its one recorded code; milestone or remark dates do not split it. A within-week code change is not resolved by this schema. Different code buckets may overlap; their sum need not equal total. The CSV exposes cross_code_excess_days and unattributed_days. The four matched wellbores have no cross-code excess, exact duplicate, uncoded record, rejected or implausible span. Gap boundaries are in the CSV; gaps add no activity days and do not establish inactivity or missing regulator submissions. Preparation excludes missing endpoints and counts reversed spans as rejected (war_rig_days.py:243-309).

Absent DRL or COM remains null (war_rig_days.py:418-428); diagnostic categories may be zero within held records. Missing repository records leave computed values blank. Percent differences are blank for missing or zero published values.

Interim drilling is inclusive (TD minus spud) plus one; completion uses preferred method 3, (last WAR end minus TD) plus one (rig_days_summary.md:7,25,30-33). These formulas count TD in both phases. Workbook/export dates come from each row. QA dates come explicitly from the export at the same API12 key. Benchmark spud comes from its row and TD from the export. Both note comparisons use milestone line16. The CSV identifies milestone_source. Null/reversed milestones remain unavailable; first WAR start and WELL_ACTV_START_DT are never substituted for spud.

## Wells compared and wells not computed

The published inputs contain 253 distinct API12 wellbores; 4 match committed weekly records and 249 do not. There are 550 source/well rows, 13 with computed activity fields. Two wellbores have per-well extracts and two only sparse samples. Step 3 proceeds to the available-well comparison of step 4, with sparse samples separated. Whole-population closeness is not established.

| API12 | Coverage | Records | First date | Last date | Gaps |
| --- | --- | --- | --- | --- | --- |
| 608114077400 | sparse operational sample | 2 | 2024-05-05 | 2024-11-02 | 1 |
| 608124003301 | per-well history | 32 | 2015-01-18 | 2016-04-03 | 1 |
| 608124009500 | per-well history | 45 | 2014-07-23 | 2016-01-16 | 1 |
| 608124014001 | sparse operational sample | 1 | 2023-12-03 | 2023-12-09 | 0 |

Table 3. A per-well extract is not a complete-history certificate. Every absent source/well row is listed in the CSV as "not computed: records not in the repository".

## Per-well table

All computed rows are below. The [CSV](ratified_day_basis_comparison.csv) holds the full population, exact input row keys/cell locators, all category counts, dates, record counts and both day/percent differences. None below means unavailable, not zero. Source aliases refer to Table 1.

| API12 | Source | Published D/C (days) | Ratified D/C (days) | D delta (days) | C delta (days) | Interim D/C (days) |
| --- | --- | --- | --- | --- | --- | --- |
| 608124009500 | milestone | 155/93 | 151/91 | -4 | -2 | 156/387 |
| 608124009500 | summary | 151/87 | 151/91 | 0 | 4 | 156/387 |
| 608114077400 | workbook | 171.0/276.0 | None/7 |  | -269.0 | 172/172 |
| 608124003301 | workbook | 37.0/173.0 | 35/142 | -2.0 | -31.0 | 38/403 |
| 608124009500 | workbook | 155.0/152.0 | 151/91 | -4.0 | -61.0 | 156/387 |
| 608124014001 | workbook | 0.0/0.0 | 7/None | 7.0 |  | None/None |
| 608114077400 | export | 171.0/276.0 | None/7 |  | -269.0 | 172/172 |
| 608124003301 | export | 37.0/173.0 | 35/142 | -2.0 | -31.0 | 38/403 |
| 608124009500 | export | 155.0/152.0 | 151/91 | -4.0 | -61.0 | 156/387 |
| 608124014001 | export | 2.0/22.0 | 7/None | 5.0 |  | 3/8 |
| 608124009500 | QA | 151.0/91.0 | 151/91 | 0.0 | 0.0 | 156/387 |
| 608124003301 | benchmark | 75.0/331.0 | 35/142 | -40.0 | -189.0 | 38/403 |
| 608124009500 | benchmark | 451.0/318.0 | 151/91 | -300.0 | -227.0 | 156/387 |

Table 4. The workbook/export disagreement for 608124014001 is preserved separately.

## Summary statistics

Statistics use the same numeric well/metric pairs for both rules, grouped by source and coverage. Sources are not pooled or averaged; nulls are not zeros. Undefined percentage denominators are excluded.

| Source | Coverage | Metric | Rule | Wells | Median absolute (days) | Maximum absolute (days) | Within 5 days | Within 5 percent | Mean signed (days) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| milestone | history | drilling | ratified | 1 | 4 | 4 | 1 | 1 | -4 |
| milestone | history | drilling | interim | 1 | 1 | 1 | 1 | 1 | 1 |
| milestone | history | completion | ratified | 1 | 2 | 2 | 1 | 1 | -2 |
| milestone | history | completion | interim | 1 | 294 | 294 | 0 | 0 | 294 |
| summary | history | drilling | ratified | 1 | 0 | 0 | 1 | 1 | 0 |
| summary | history | drilling | interim | 1 | 5 | 5 | 1 | 1 | 5 |
| summary | history | completion | ratified | 1 | 4 | 4 | 1 | 1 | 4 |
| summary | history | completion | interim | 1 | 300 | 300 | 0 | 0 | 300 |
| workbook | history | drilling | ratified | 2 | 3.0 | 4.0 | 2 | 1 | -3.0 |
| workbook | history | drilling | interim | 2 | 1.0 | 1.0 | 2 | 2 | 1.0 |
| workbook | history | completion | ratified | 2 | 46.0 | 61.0 | 0 | 0 | -46.0 |
| workbook | history | completion | interim | 2 | 232.5 | 235.0 | 0 | 0 | 232.5 |
| workbook | sample | completion | ratified | 1 | 269.0 | 269.0 | 0 | 0 | -269.0 |
| workbook | sample | completion | interim | 1 | 104.0 | 104.0 | 0 | 0 | -104.0 |
| export | history | drilling | ratified | 2 | 3.0 | 4.0 | 2 | 1 | -3.0 |
| export | history | drilling | interim | 2 | 1.0 | 1.0 | 2 | 2 | 1.0 |
| export | history | completion | ratified | 2 | 46.0 | 61.0 | 0 | 0 | -46.0 |
| export | history | completion | interim | 2 | 232.5 | 235.0 | 0 | 0 | 232.5 |
| export | sample | drilling | ratified | 1 | 5.0 | 5.0 | 1 | 0 | 5.0 |
| export | sample | drilling | interim | 1 | 1.0 | 1.0 | 1 | 0 | 1.0 |
| export | sample | completion | ratified | 1 | 269.0 | 269.0 | 0 | 0 | -269.0 |
| export | sample | completion | interim | 1 | 104.0 | 104.0 | 0 | 0 | -104.0 |
| QA | history | drilling | ratified | 1 | 0.0 | 0.0 | 1 | 1 | 0.0 |
| QA | history | drilling | interim | 1 | 5.0 | 5.0 | 1 | 1 | 5.0 |
| QA | history | completion | ratified | 1 | 0.0 | 0.0 | 1 | 1 | 0.0 |
| QA | history | completion | interim | 1 | 296.0 | 296.0 | 0 | 0 | 296.0 |
| benchmark | history | drilling | ratified | 2 | 170.0 | 300.0 | 0 | 0 | -170.0 |
| benchmark | history | drilling | interim | 2 | 166.0 | 295.0 | 0 | 0 | -166.0 |
| benchmark | history | completion | ratified | 2 | 208.0 | 227.0 | 0 | 0 | -208.0 |
| benchmark | history | completion | interim | 2 | 70.5 | 72.0 | 0 | 0 | 70.5 |

Table 5. Paired statistics. One paired well does not establish a population trend.

## Largest ten differences with causes

| API12 | Source | Metric | Delta (days) | Evidence / cause |
| --- | --- | --- | --- | --- |
| 608124009500 | benchmark | drilling | -300.0 | Published calendar cycle basis, not coded rig time. Held dates 2014-07-23 to 2016-01-16; gap boundaries [('2015-02-21', '2015-10-15')]. Full attribution not shown by the records. |
| 608114077400 | workbook | completion | -269.0 | Sparse sample 2024-05-05 to 2024-11-02; prior whole-well history absent; cause not shown by the records. |
| 608114077400 | export | completion | -269.0 | Sparse sample 2024-05-05 to 2024-11-02; prior whole-well history absent; cause not shown by the records. |
| 608124009500 | benchmark | completion | -227.0 | Published calendar cycle basis, not coded rig time. Held dates 2014-07-23 to 2016-01-16; gap boundaries [('2015-02-21', '2015-10-15')]. Full attribution not shown by the records. |
| 608124003301 | benchmark | completion | -189.0 | Published calendar cycle basis, not coded rig time. Held dates 2015-01-18 to 2016-04-03; gap boundaries [('2015-07-12', '2016-02-28')]. Full attribution not shown by the records. |
| 608124009500 | workbook | completion | -61.0 | Held dates 2014-07-23 to 2016-01-16; PND 49 days and TA 17 days excluded; gaps [('2015-02-21', '2015-10-15')]. Published basis unstated; cause not shown by the records. |
| 608124009500 | export | completion | -61.0 | Held dates 2014-07-23 to 2016-01-16; PND 49 days and TA 17 days excluded; gaps [('2015-02-21', '2015-10-15')]. Published basis unstated; cause not shown by the records. |
| 608124003301 | benchmark | drilling | -40.0 | Published calendar cycle basis, not coded rig time. Held dates 2015-01-18 to 2016-04-03; gap boundaries [('2015-07-12', '2016-02-28')]. Full attribution not shown by the records. |
| 608124003301 | workbook | completion | -31.0 | Held dates 2015-01-18 to 2016-04-03; PND 35 days and TA 0 days excluded; gaps [('2015-07-12', '2016-02-28')]. Published basis unstated; cause not shown by the records. |
| 608124003301 | export | completion | -31.0 | Held dates 2015-01-18 to 2016-04-03; PND 35 days and TA 0 days excluded; gaps [('2015-07-12', '2016-02-28')]. Published basis unstated; cause not shown by the records. |

Table 6. Ranked absolute differences across both metrics; published tables remain independent.

## Is the ratified rule closer than the interim rule

For the two histories against workbook/export, drilling is **no** by median absolute difference: ratified 3 days versus interim 1; within-5-days ties at 2 versus 2. Signed means are -3 versus +1. Whole-week codes differ from calendar milestones. For 608124009500 the week containing TD is PND, 2014-12-21 to 2014-12-27; TD is 2014-12-26 (weekly CSV row24; milestone line16). No allocation within the week is inferred.

Completion is **mixed by the requested criteria**: median absolute difference improves to 46 versus 232.5 days, while within-5-days ties at 0 versus 0. Signed means are -46 versus +232.5. PND, TA and gaps are excluded by the ratified rule and included in the interim calendar span; the retained tables do not declare their exact basis, so the residual gap is not fully explained.

Across the remaining sources the result is mixed. Milestone drilling favors interim (1 versus 4 days; within5 ties at1), while completion favors ratified (2 versus294; within5:1 versus0). Summary drilling medians are0 versus5 with counts1 versus1; completion medians4 versus300 with counts1 versus0. QA agreement is reproducibility only. Against the calendar benchmark, ratified is farther for drilling (170 versus166 days; counts0 versus0) and completion (208 versus70.5; counts0 versus0). Sparse samples cannot establish whole-well accuracy. No recommendation to change the decision follows.

## Test well

Summary line18 records DRL151, COM87, PND49, TA21, summing to308. Repository records compute DRL151, COM91, PND49, TA17, total308. Drilling, PND and total agree; COM differs+4 and TA-4. The requested 49-day pin reproduces PND, not suspension: DSI-coded suspension is0. PND is undefined in the code list, so calling it suspended is not established.

The hand calculation from war_data_608124009500.csv is DRL4+21 times7=151 (rows2-23), PND7 times7=49 (rows24-30), TA7+7+3=17 (rows31-33), COM13 times7=91 (rows34-46). TA covers 2015-02-08 to2015-02-21 and2015-10-15 to2015-10-17; COM resumes2015-10-18. The note gives no daily allocation behind COM87/TA21. The precise cause of the compensating four-day difference is not shown by the records. Tests pin the computed values and expose the discrepancy.

## Records needed

Missing API12 identifiers are enumerated below and in every corresponding CSV source row. Complete histories are also needed for sparse matches 608114077400 and608124014001 (two and one records). Further coverage verification is needed even for per-well extracts.

608074030500 608074030501 608074030502 608074031400 608074031500 608074031501 608074031502 608074032000
608074032001 608074032002 608074032003 608074032800 608074033000 608074033100 608074033200 608074033300
608074033400 608074033500 608074033600 608074033700 608074034100 608074034300 608074034400 608084001100
608084001101 608084001102 608084001103 608084001104 608084001500 608084001600 608084001601 608084002100
608084002700 608084002701 608084003100 608084003101 608084003102 608084003103 608084003104 608084003105
608084003106 608084004700 608084004701 608084005500 608084006000 608084006001 608084006100 608084006101
608084006700 608084006701 608084006702 608084007000 608084007200 608084007300 608084007301 608084007700
608084007701 608114062100 608114062101 608114063500 608114063501 608114063502 608114066100 608114066101
608114067300 608114067301 608114072800 608114075000 608114075100 608114076100 608114076101 608114076900
608114079600 608124000400 608124000401 608124000402 608124000800 608124000801 608124001000 608124001100
608124001300 608124001301 608124001500 608124001600 608124001601 608124001700 608124001701 608124001900
608124002000 608124002001 608124002002 608124002003 608124002004 608124002005 608124002200 608124002300
608124002301 608124002302 608124002700 608124002701 608124002702 608124002703 608124002900 608124003100
608124003101 608124003300 608124003400 608124003401 608124003402 608124003800 608124004400 608124004600
608124004601 608124004602 608124004700 608124004701 608124005000 608124005100 608124005101 608124005102
608124005103 608124005200 608124005201 608124005202 608124005203 608124005300 608124005400 608124005500
608124005600 608124005700 608124005800 608124005900 608124006000 608124006001 608124006200 608124006300
608124006301 608124006302 608124006400 608124006401 608124006402 608124006403 608124006404 608124006500
608124006600 608124006601 608124006602 608124006603 608124006700 608124006800 608124006900 608124007000
608124007100 608124007101 608124007102 608124007103 608124007200 608124007300 608124007400 608124007500
608124007700 608124007900 608124008200 608124008300 608124008700 608124009200 608124009201 608124009300
608124009301 608124009400 608124009700 608124009900 608124010100 608124010101 608124010102 608124010103
608124010200 608124010300 608124010400 608124010500 608124010700 608124010701 608124010800 608124010900
608124011000 608124011001 608124011100 608124011101 608124011200 608124011300 608124011301 608124011302
608124011400 608124011500 608124011501 608124011502 608124011503 608124011504 608124011600 608124011601
608124011602 608124011603 608124011604 608124011605 608124011606 608124011700 608124011800 608124011801
608124012200 608124012300 608124012500 608124012600 608124012601 608124012602 608124012700 608124012701
608124012800 608124012801 608124012802 608124012803 608124012804 608124012900 608124013200 608124013201
608124013202 608124013300 608124013400 608124013500 608124013600 608124013700 608124013701 608124013900
608124014000 608124014002 608124014003 608124014100 608124014300 608124014301 608124014400 608124014600
608124015100 608124015200 608124015300 608124015400 608124015500 608124015501 608124015502 608124015503
608124015504

Required regulator tables: mv_war_main (SN_WAR,API_WELL_NUMBER,WAR_START_DT,WAR_END_DT), joined to mv_war_main_prop (SN_WAR,WELL_ACTIVITY_CD) on SN_WAR, for the listed API12s. Borehole WELL_SPUD_DATE and TOTAL_DEPTH_DATE are needed where retained dates are blank. Daily code allocation is needed for the unresolved COM/TA discrepancy.

The block loader expects the configured war_main directory plus mv_war_main.bin (packages/worldenergydata-bsee/src/worldenergydata/bsee/data/loaders/block/war_data.py:38-47). The QA builder expects data/modules/bsee/bin/war/mv_war_main.bin and mv_war_main_prop.bin (scripts/lower_tertiary/build_roy_rig_days_qa.py:362-376). The lower-tertiary extractor reads a configured ZIP (packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/lower_tertiary/war_extractor.py:16,34-35); config/input/world_oil_lower_tertiary.yaml:187 names data/modules/bsee/.local/war/eWellWARRawData.zip. Its main member is eWellWARRawData/mv_war_main.txt (packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/buckskin/extractor.py:28-37). These are expected input locations, not data opened by this comparison.

Repository manifest/cold/fetch filename and content searches find **no manifest entry found** for missing weekly records in a cold-data store. No cold-data mount or external download is used.

## Limits

Retained-file comparison is not independent validation or regulator completeness certification. Current extractor behavior does not retrospectively establish published-table basis. Summary authorship is not established. Unknown codes remain undefined. Sparse samples and missing histories prevent whole-population acceptance; independently unioned code buckets are not necessarily additive.

## How to regenerate

From the repository root with existing dependencies:

    PYTHONPATH=src:packages/worldenergydata-core/src:packages/worldenergydata-bsee/src python -m worldenergydata.bsee.analysis.ratified_day_basis_comparison

The command regenerates only the new CSV and prints paired statistics. Report prose is reviewed against that output; no existing table or report is regenerated.
