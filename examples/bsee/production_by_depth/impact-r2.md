# Round 3 impact on production by water depth

The original analysis at `396d3d4`, round 2 at `0f4ba97`, and the round 3 rebuild use the same input pins and production window, January 2005 through provisional September 2026. [Input pins](source_pins.json)

The round 3 spud rule changes the age cohort. The original analysis counted 2,514 starts, round 2 counted 1,813, and round 3 counts 1,809. Round 3 requires a first positive OGOR-A month and a dated spud on or after 1 January 2005 for every non-cancelled bore. Wells spudded before that date fall outside the cohort even when first production falls within the observation period. [Historical measurement](measure-finding3.md)

Of the original supported starts, 701 have a pre-2005 spud, including 479 under 100 m, 67 at 100 to under 500 m, 96 at 500 to under 1,500 m, and 59 at 1,500 m or deeper. A membership comparison against the original revision matched all 701 API10s and their depth bands. The age cohort under-represents long-cycle developments in the early production years. [Earlier supported starts with pre-2005 spuds](output/spud_exclusions.csv)

The round 3 spud-date ledger excludes 8 producers with an incomplete non-cancelled bore date. Four of them met the round 2 rule, which tested missing dates only on original bores. The well-by-well comparison found four removals and zero additions. All four have a blank `WELL_SPUD_DATE` on a bore with `BOREHOLE_STAT_CD = AST`. In 500 to under 1,500 m, the affected API10 and suffix are `6081140747` (`ST01BP01`), `6081741293` (`ST01BP00`) and `6081741297` (`ST01BP00`). At 1,500 m or deeper, the affected API10 is `6081240062` (`ST01BP00`). [Disposition ledger](output/record_counts.csv)

## Article headlines

| Depth band (m) | Revision | Age cohort (wells) | Producers in 2005 | Producers in 2025 | Ordered lag, median (P25 to P75), months | Month 60 oil rate, % of baseline (wells) | Year 5 WAR (%) | Year 5 approval (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Under 100 | Original | 1,554 | 5,387 | 1,097 | 1 (0 to 4) | 18.3 (714) | 66.5 | 64.1 |
| Under 100 | Round 2 | 1,075 | 5,387 | 1,097 | 1 (0 to 4) | 18.7 (499) | 69.8 | 67.3 |
| Under 100 | Round 3 | 1,075 | 5,387 | 1,097 | 1 (0 to 4) | 18.7 (499) | 69.8 | 67.3 |
| 100 to under 500 | Original | 195 | 707 | 213 | 0 (0 to 1) | 21.2 (120) | 63.6 | 56.1 |
| 100 to under 500 | Round 2 | 128 | 707 | 213 | 0 (0 to 1) | 19.9 (84) | 71.1 | 62.0 |
| 100 to under 500 | Round 3 | 128 | 707 | 213 | 0 (0 to 1) | 19.9 (84) | 71.1 | 62.0 |
| 500 to under 1,500 | Original | 396 | 314 | 358 | 1 (0 to 5) | 39.1 (217) | 63.6 | 55.6 |
| 500 to under 1,500 | Round 2 | 300 | 314 | 358 | 1 (0 to 6) | 41.2 (150) | 66.2 | 57.5 |
| 500 to under 1,500 | Round 3 | 297 | 314 | 358 | 1 (0 to 6) | 42.6 (149) | 65.9 | 57.1 |
| 1,500 and deeper | Original | 369 | 47 | 287 | 1 (0 to 6) | 43.6 (174) | 60.7 | 59.2 |
| 1,500 and deeper | Round 2 | 310 | 47 | 287 | 1 (0 to 4) | 47.7 (138) | 59.3 | 59.3 |
| 1,500 and deeper | Round 3 | 309 | 47 | 287 | 1 (0 to 4) | 48.1 (137) | 59.2 | 59.2 |
| All | Original | 2,514 | 6,455 | 1,955 | 1 (0 to 4) | 24.8 (1,225) | 65.2 | 61.7 |
| All | Round 2 | 1,813 | 6,455 | 1,955 | 1 (0 to 4) | 26.8 (871) | 68.0 | 64.5 |
| All | Round 3 | 1,809 | 6,455 | 1,955 | 1 (0 to 4) | 26.8 (869) | 68.0 | 64.4 |

*Table 1. Annual producers, age-cohort counts, ordered completion lag, observed month-60 decline and anniversary-eligible intervention shares by depth.*

| Pooled measure | Original | Round 2 | Round 3 |
| --- | ---: | ---: | ---: |
| Distinct producing wells | 9,525 | 9,525 | 9,525 |
| Producing well-months | 827,032 | 827,032 | 827,032 |
| Well-years | 85,785 | 85,785 | 85,785 |
| Signed oil volume (bbl) | 12,418,358,076 | 12,418,358,076 | 12,418,358,076 |
| Signed gas volume (Mcf) | 32,778,024,812 | 32,778,024,812 | 32,778,024,812 |
| Month 60 median oil rate, subsea flag YES (% of baseline) | 43.9 | 44.5 | 44.9 |
| Month 60 median oil rate, subsea flag NO (% of baseline) | 19.2 | 19.7 | 19.7 |
| Year 5 eligible wells | 2,306 | 1,607 | 1,604 |
| Year 5 wells with completion observed | 2,098 | 1,552 | 1,549 |
| Year 5 WAR among wells with completion observed (%) | 71.6 | 70.4 | 70.4 |
| Year 5 approval among wells with completion observed (%) | 67.8 | 66.8 | 66.7 |

*Table 2. Production totals, completion flags and year-5 sensitivity. Original completion-observed percentages use the event count divided by the observed completion count from the original intervention table.*

## Changes since round 2

The comparison to `0f4ba97` gives 280 changed, 11 added, 6 removed and 709 unchanged headline field values. For fields sourced from the production, lag, decline, intervention and article summary tables, 191 changed, 0 added, 0 removed and 610 unchanged.

The reported first-production month differs from the first positive month for 125 original starts, 120 round 2 starts and 119 round 3 starts. Among round 3 starts, 57 have no dated C report and 31 have a first C in a later month, the same counts as round 2. The original counts were 201 and 51. [Startup diagnostics](output/checks.txt)

### Article headline changes

| Headline key | Field | Round 2 | Round 3 |
| --- | ---: | ---: | ---: |
| 1500plus/Intervention approval/0 | completion_observed_wells | 298 | 297 |
| 1500plus/Intervention approval/0 | eligible_wells | 310 | 309 |
| 1500plus/Intervention approval/0 | share | 0.2129032258064516 | 0.21359223300970873 |
| 1500plus/Intervention approval/0 | share_among_completion_observed | 0.2214765100671141 | 0.2222222222222222 |
| 1500plus/Intervention approval/1 | completion_observed_wells | 285 | 284 |
| 1500plus/Intervention approval/1 | eligible_wells | 289 | 288 |
| 1500plus/Intervention approval/1 | share | 0.4186851211072664 | 0.4201388888888889 |
| 1500plus/Intervention approval/1 | share_among_completion_observed | 0.4245614035087719 | 0.426056338028169 |
| 1500plus/Intervention approval/5 | completion_observed_wells | 210 | 209 |
| 1500plus/Intervention approval/5 | eligible_wells | 214 | 213 |
| 1500plus/Intervention approval/5 | event_wells | 127 | 126 |
| 1500plus/Intervention approval/5 | share | 0.5934579439252337 | 0.5915492957746479 |
| 1500plus/Intervention approval/5 | share_among_completion_observed | 0.6047619047619047 | 0.6028708133971292 |
| 1500plus/Post-completion WAR/0 | completion_observed_wells | 298 | 297 |
| 1500plus/Post-completion WAR/0 | eligible_wells | 310 | 309 |
| 1500plus/Post-completion WAR/0 | share | 0.2709677419354839 | 0.27184466019417475 |
| 1500plus/Post-completion WAR/0 | share_among_completion_observed | 0.28187919463087246 | 0.2828282828282828 |
| 1500plus/Post-completion WAR/1 | completion_observed_wells | 285 | 284 |
| 1500plus/Post-completion WAR/1 | eligible_wells | 289 | 288 |
| 1500plus/Post-completion WAR/1 | share | 0.39100346020761245 | 0.3923611111111111 |
| 1500plus/Post-completion WAR/1 | share_among_completion_observed | 0.39649122807017545 | 0.397887323943662 |
| 1500plus/Post-completion WAR/5 | completion_observed_wells | 210 | 209 |
| 1500plus/Post-completion WAR/5 | eligible_wells | 214 | 213 |
| 1500plus/Post-completion WAR/5 | event_wells | 127 | 126 |
| 1500plus/Post-completion WAR/5 | share | 0.5934579439252337 | 0.5915492957746479 |
| 1500plus/Post-completion WAR/5 | share_among_completion_observed | 0.6047619047619047 | 0.6028708133971292 |
| 1500plus/decline/All/1 | baseline_wells | 186 | 185 |
| 1500plus/decline/All/1 | median_relative_rate | 0.6353176632965293 | 0.6396443552833256 |
| 1500plus/decline/All/1 | wells | 186 | 185 |
| 1500plus/decline/All/12 | baseline_wells | 186 | 185 |
| 1500plus/decline/All/12 | median_relative_rate | 0.8738570580097177 | 0.8686806411837238 |
| 1500plus/decline/All/12 | wells | 162 | 161 |
| 1500plus/decline/All/60 | baseline_wells | 186 | 185 |
| 1500plus/decline/All/60 | median_relative_rate | 0.47725476275618356 | 0.48087892012585004 |
| 1500plus/decline/All/60 | wells | 138 | 137 |
| 1500plus/decline/No subsea flag (NO)/1 | baseline_wells | 12 | 11 |
| 1500plus/decline/No subsea flag (NO)/1 | median_relative_rate | 0.48596036708568924 | 0.46819111772974625 |
| 1500plus/decline/No subsea flag (NO)/1 | wells | 12 | 11 |
| 1500plus/decline/No subsea flag (NO)/12 | baseline_wells | 12 | 11 |
| 1500plus/decline/No subsea flag (NO)/12 | median_relative_rate | 1.083104687328392 | 1.0254999315162308 |
| 1500plus/decline/No subsea flag (NO)/12 | wells | 12 | 11 |
| 1500plus/decline/No subsea flag (NO)/60 | baseline_wells | 12 | 11 |
| 1500plus/decline/No subsea flag (NO)/60 | median_relative_rate | 0.477127399069896 | 0.5091752428120858 |
| 1500plus/decline/No subsea flag (NO)/60 | wells | 12 | 11 |
| 1500plus/lag/ordered | same_month_wells | 106 | 105 |
| 1500plus/lag/ordered | wells | 285 | 284 |
| 1500plus/lag/signed | same_month_wells | 106 | 105 |
| 1500plus/lag/signed | wells | 294 | 293 |
| 1500plus/period_wells | permit_by_cutoff_share | 0.6451612903225806 | 0.6440129449838188 |
| 1500plus/period_wells | permit_by_cutoff_wells | 200 | 199 |
| 1500plus/period_wells | permit_signed_event_age_median_months | 4.5 | 4.0 |
| 1500plus/period_wells | supported_starts | 310 | 309 |
| 1500plus/period_wells | war_by_cutoff_share | 0.6612903225806451 | 0.6601941747572816 |
| 1500plus/period_wells | war_by_cutoff_wells | 205 | 204 |
| 1500plus/period_wells | war_signed_event_age_median_months | 5.0 | 4.5 |
| 500_1500/Intervention approval/0 | completion_observed_wells | 286 | 283 |
| 500_1500/Intervention approval/0 | eligible_wells | 300 | 297 |
| 500_1500/Intervention approval/0 | share | 0.17666666666666667 | 0.17845117845117844 |
| 500_1500/Intervention approval/0 | share_among_completion_observed | 0.1853146853146853 | 0.1872791519434629 |
| 500_1500/Intervention approval/1 | completion_observed_wells | 282 | 279 |
| 500_1500/Intervention approval/1 | eligible_wells | 289 | 286 |
| 500_1500/Intervention approval/1 | event_wells | 97 | 96 |
| 500_1500/Intervention approval/1 | share | 0.3356401384083045 | 0.3356643356643357 |
| 500_1500/Intervention approval/1 | share_among_completion_observed | 0.34397163120567376 | 0.34408602150537637 |
| 500_1500/Intervention approval/10 | completion_observed_wells | 165 | 163 |
| 500_1500/Intervention approval/10 | eligible_wells | 167 | 165 |
| 500_1500/Intervention approval/10 | event_wells | 118 | 116 |
| 500_1500/Intervention approval/10 | share | 0.7065868263473054 | 0.703030303030303 |
| 500_1500/Intervention approval/10 | share_among_completion_observed | 0.7151515151515152 | 0.7116564417177914 |
| 500_1500/Intervention approval/5 | completion_observed_wells | 224 | 222 |
| 500_1500/Intervention approval/5 | eligible_wells | 228 | 226 |
| 500_1500/Intervention approval/5 | event_wells | 131 | 129 |
| 500_1500/Intervention approval/5 | share | 0.5745614035087719 | 0.5707964601769911 |
| 500_1500/Intervention approval/5 | share_among_completion_observed | 0.5848214285714286 | 0.581081081081081 |
| 500_1500/Post-completion WAR/0 | completion_observed_wells | 286 | 283 |
| 500_1500/Post-completion WAR/0 | eligible_wells | 300 | 297 |
| 500_1500/Post-completion WAR/0 | event_wells | 90 | 89 |
| 500_1500/Post-completion WAR/0 | share | 0.3 | 0.2996632996632997 |
| 500_1500/Post-completion WAR/0 | share_among_completion_observed | 0.3146853146853147 | 0.31448763250883394 |
| 500_1500/Post-completion WAR/1 | completion_observed_wells | 282 | 279 |
| 500_1500/Post-completion WAR/1 | eligible_wells | 289 | 286 |
| 500_1500/Post-completion WAR/1 | event_wells | 131 | 129 |
| 500_1500/Post-completion WAR/1 | share | 0.4532871972318339 | 0.45104895104895104 |
| 500_1500/Post-completion WAR/1 | share_among_completion_observed | 0.4645390070921986 | 0.46236559139784944 |
| 500_1500/Post-completion WAR/10 | completion_observed_wells | 165 | 163 |
| 500_1500/Post-completion WAR/10 | eligible_wells | 167 | 165 |
| 500_1500/Post-completion WAR/10 | event_wells | 136 | 134 |
| 500_1500/Post-completion WAR/10 | share | 0.8143712574850299 | 0.8121212121212121 |
| 500_1500/Post-completion WAR/10 | share_among_completion_observed | 0.8242424242424242 | 0.8220858895705522 |
| 500_1500/Post-completion WAR/5 | completion_observed_wells | 224 | 222 |
| 500_1500/Post-completion WAR/5 | eligible_wells | 228 | 226 |
| 500_1500/Post-completion WAR/5 | event_wells | 151 | 149 |
| 500_1500/Post-completion WAR/5 | share | 0.6622807017543859 | 0.6592920353982301 |
| 500_1500/Post-completion WAR/5 | share_among_completion_observed | 0.6741071428571429 | 0.6711711711711712 |
| 500_1500/decline/All/1 | baseline_wells | 211 | 209 |
| 500_1500/decline/All/1 | wells | 211 | 209 |
| 500_1500/decline/All/12 | baseline_wells | 211 | 209 |
| 500_1500/decline/All/12 | wells | 185 | 183 |
| 500_1500/decline/All/60 | baseline_wells | 211 | 209 |
| 500_1500/decline/All/60 | median_relative_rate | 0.4119341896226457 | 0.4261019277658327 |
| 500_1500/decline/All/60 | wells | 150 | 149 |
| 500_1500/decline/Subsea/1 | baseline_wells | 179 | 177 |
| 500_1500/decline/Subsea/1 | wells | 179 | 177 |
| 500_1500/decline/Subsea/12 | baseline_wells | 179 | 177 |
| 500_1500/decline/Subsea/12 | wells | 154 | 152 |
| 500_1500/decline/Subsea/60 | baseline_wells | 179 | 177 |
| 500_1500/decline/Subsea/60 | median_relative_rate | 0.3881728208619144 | 0.39052124779410957 |
| 500_1500/decline/Subsea/60 | wells | 124 | 123 |
| 500_1500/lag/ordered | same_month_wells | 101 | 99 |
| 500_1500/lag/ordered | wells | 281 | 278 |
| 500_1500/lag/signed | p75_months | 5.0 | 5.75 |
| 500_1500/lag/signed | same_month_wells | 101 | 99 |
| 500_1500/lag/signed | wells | 289 | 286 |
| 500_1500/period_wells | permit_by_cutoff_share | 0.6866666666666666 | 0.6835016835016835 |
| 500_1500/period_wells | permit_by_cutoff_wells | 206 | 203 |
| 500_1500/period_wells | permit_signed_event_age_median_months | 14.5 | 14.0 |
| 500_1500/period_wells | supported_starts | 300 | 297 |
| 500_1500/period_wells | war_by_cutoff_share | 0.7733333333333333 | 0.7710437710437711 |
| 500_1500/period_wells | war_by_cutoff_wells | 232 | 229 |
| all/Intervention approval/0 | completion_observed_wells | 1725 | 1721 |
| all/Intervention approval/0 | eligible_wells | 1813 | 1809 |
| all/Intervention approval/0 | share | 0.20959735245449532 | 0.21006080707573244 |
| all/Intervention approval/0 | share_among_completion_observed | 0.22028985507246376 | 0.22080185938407904 |
| all/Intervention approval/1 | completion_observed_wells | 1709 | 1705 |
| all/Intervention approval/1 | eligible_wells | 1778 | 1774 |
| all/Intervention approval/1 | event_wells | 741 | 740 |
| all/Intervention approval/1 | share | 0.4167604049493813 | 0.41713641488162345 |
| all/Intervention approval/1 | share_among_completion_observed | 0.43358689291983615 | 0.4340175953079179 |
| all/Intervention approval/10 | completion_observed_wells | 1335 | 1333 |
| all/Intervention approval/10 | eligible_wells | 1387 | 1385 |
| all/Intervention approval/10 | event_wells | 1024 | 1022 |
| all/Intervention approval/10 | share | 0.738284066330209 | 0.7379061371841156 |
| all/Intervention approval/10 | share_among_completion_observed | 0.7670411985018727 | 0.7666916729182296 |
| all/Intervention approval/5 | completion_observed_wells | 1552 | 1549 |
| all/Intervention approval/5 | eligible_wells | 1607 | 1604 |
| all/Intervention approval/5 | event_wells | 1036 | 1033 |
| all/Intervention approval/5 | share | 0.6446795270690728 | 0.6440149625935162 |
| all/Intervention approval/5 | share_among_completion_observed | 0.6675257731958762 | 0.6668818592640413 |
| all/Post-completion WAR/0 | completion_observed_wells | 1725 | 1721 |
| all/Post-completion WAR/0 | eligible_wells | 1813 | 1809 |
| all/Post-completion WAR/0 | event_wells | 447 | 446 |
| all/Post-completion WAR/0 | share | 0.2465526751241037 | 0.24654505251520176 |
| all/Post-completion WAR/0 | share_among_completion_observed | 0.2591304347826087 | 0.25915165601394535 |
| all/Post-completion WAR/1 | completion_observed_wells | 1709 | 1705 |
| all/Post-completion WAR/1 | eligible_wells | 1778 | 1774 |
| all/Post-completion WAR/1 | event_wells | 719 | 717 |
| all/Post-completion WAR/1 | share | 0.4043869516310461 | 0.4041713641488162 |
| all/Post-completion WAR/1 | share_among_completion_observed | 0.42071386775892333 | 0.42052785923753666 |
| all/Post-completion WAR/10 | completion_observed_wells | 1335 | 1333 |
| all/Post-completion WAR/10 | eligible_wells | 1387 | 1385 |
| all/Post-completion WAR/10 | event_wells | 1155 | 1153 |
| all/Post-completion WAR/10 | share | 0.832732516222062 | 0.8324909747292418 |
| all/Post-completion WAR/10 | share_among_completion_observed | 0.8651685393258427 | 0.8649662415603901 |
| all/Post-completion WAR/5 | completion_observed_wells | 1552 | 1549 |
| all/Post-completion WAR/5 | eligible_wells | 1607 | 1604 |
| all/Post-completion WAR/5 | event_wells | 1093 | 1090 |
| all/Post-completion WAR/5 | share | 0.6801493466085874 | 0.6795511221945137 |
| all/Post-completion WAR/5 | share_among_completion_observed | 0.7042525773195877 | 0.7036797934151066 |
| all/decline/All/1 | baseline_wells | 1333 | 1330 |
| all/decline/All/1 | median_relative_rate | 0.6554214251128525 | 0.6554920634920636 |
| all/decline/All/1 | wells | 1328 | 1325 |
| all/decline/All/12 | baseline_wells | 1333 | 1330 |
| all/decline/All/12 | median_relative_rate | 0.6336042243560371 | 0.6301999381879562 |
| all/decline/All/12 | wells | 1130 | 1127 |
| all/decline/All/60 | baseline_wells | 1333 | 1330 |
| all/decline/All/60 | wells | 871 | 869 |
| all/decline/No subsea flag (NO)/1 | baseline_wells | 861 | 860 |
| all/decline/No subsea flag (NO)/1 | median_relative_rate | 0.6653240359073913 | 0.6656633479972216 |
| all/decline/No subsea flag (NO)/1 | wells | 856 | 855 |
| all/decline/No subsea flag (NO)/12 | baseline_wells | 861 | 860 |
| all/decline/No subsea flag (NO)/12 | median_relative_rate | 0.5282209460190219 | 0.5275552318523914 |
| all/decline/No subsea flag (NO)/12 | wells | 734 | 733 |
| all/decline/No subsea flag (NO)/60 | baseline_wells | 861 | 860 |
| all/decline/No subsea flag (NO)/60 | median_relative_rate | 0.19713709711843594 | 0.19702425436510634 |
| all/decline/No subsea flag (NO)/60 | wells | 564 | 563 |
| all/decline/Subsea/1 | baseline_wells | 379 | 377 |
| all/decline/Subsea/1 | wells | 379 | 377 |
| all/decline/Subsea/12 | baseline_wells | 379 | 377 |
| all/decline/Subsea/12 | wells | 325 | 323 |
| all/decline/Subsea/60 | baseline_wells | 379 | 377 |
| all/decline/Subsea/60 | median_relative_rate | 0.44541084957622357 | 0.4487021316321086 |
| all/decline/Subsea/60 | wells | 257 | 256 |
| all/lag/ordered | same_month_wells | 612 | 609 |
| all/lag/ordered | wells | 1704 | 1700 |
| all/lag/signed | same_month_wells | 612 | 609 |
| all/lag/signed | wells | 1735 | 1731 |
| all/period_wells | permit_by_cutoff_share | 0.7291781577495863 | 0.728579325594251 |
| all/period_wells | permit_by_cutoff_wells | 1322 | 1318 |
| all/period_wells | supported_starts | 1813 | 1809 |
| all/period_wells | war_by_cutoff_share | 0.8345284059569774 | 0.8341625207296849 |
| all/period_wells | war_by_cutoff_wells | 1513 | 1509 |

*Table 3a. 191 headline fields changed, added or removed since round 2. An absent entry has no published field for that revision.*

### Audit headline changes

| Headline key | Field | Round 2 | Round 3 |
| --- | ---: | ---: | ---: |
| audit/Article summary &#124; Gulf inventory, API10/dropped/outside eligible Gulf inventory | rows | absent | 2041 |
| audit/Article summary &#124; Gulf inventory, API10/kept/retained | rows | absent | 37529 |
| audit/Article summary &#124; Gulf inventory, API10/read/input | rows | absent | 39570 |
| audit/Article summary &#124; completion window, API10/dropped/no dated C completion | rows | 34580 | 32539 |
| audit/Article summary &#124; completion window, API10/read/input | rows | 39570 | 37529 |
| audit/Article summary &#124; permit_date by cutoff, inventory API10/dropped/no dated qualifying event | rows | 35444 | 33403 |
| audit/Article summary &#124; permit_date by cutoff, inventory API10/dropped/unsupported production start | rows | 2649 | 2653 |
| audit/Article summary &#124; permit_date by cutoff, inventory API10/kept/retained | rows | 1322 | 1318 |
| audit/Article summary &#124; permit_date by cutoff, inventory API10/read/input | rows | 39570 | 37529 |
| audit/Article summary &#124; war_date by cutoff, inventory API10/dropped/no dated qualifying event | rows | 34993 | 32952 |
| audit/Article summary &#124; war_date by cutoff, inventory API10/dropped/unsupported production start | rows | 2848 | 2852 |
| audit/Article summary &#124; war_date by cutoff, inventory API10/kept/retained | rows | 1513 | 1509 |
| audit/Article summary &#124; war_date by cutoff, inventory API10/read/input | rows | 39570 | 37529 |
| audit/Borehole quality &#124; all bores on Gulf inventory wells, spud, API10/kept/retained | rows | 37529 | absent |
| audit/Borehole quality &#124; all bores on Gulf inventory wells, spud, API10/read/input | rows | 37529 | absent |
| audit/Borehole quality &#124; non-cancelled Gulf bores, spud, API10/kept/retained | rows | absent | 37529 |
| audit/Borehole quality &#124; non-cancelled Gulf bores, spud, API10/read/input | rows | absent | 37529 |
| audit/Completion lag &#124; Gulf inventory, API10/dropped/outside eligible Gulf inventory | rows | absent | 2041 |
| audit/Completion lag &#124; Gulf inventory, API10/kept/retained | rows | absent | 37529 |
| audit/Completion lag &#124; Gulf inventory, API10/read/input | rows | absent | 39570 |
| audit/Completion lag &#124; chronological pair, API10/kept/retained | rows | 1704 | 1700 |
| audit/Completion lag &#124; chronological pair, API10/read/input | rows | 1735 | 1731 |
| audit/Completion lag &#124; completion window, API10/dropped/no dated C completion | rows | 34580 | 32539 |
| audit/Completion lag &#124; completion window, API10/read/input | rows | 39570 | 37529 |
| audit/Completion lag &#124; first C dated 2005–2025, API10/dropped/documented pre-window production | rows | 578 | absent |
| audit/Completion lag &#124; first C dated 2005–2025, API10/dropped/outside spud cohort | rows | absent | 1035 |
| audit/Completion lag &#124; first C dated 2005–2025, API10/dropped/start coverage unestablished | rows | 453 | absent |
| audit/Completion lag &#124; first C dated 2005–2025, API10/kept/retained | rows | 1735 | 1731 |
| audit/Decline &#124; baseline eligibility, well-months/kept/retained | rows | 76884 | 76704 |
| audit/Decline &#124; baseline eligibility, well-months/read/input | rows | 90369 | 90189 |
| audit/Decline &#124; calendar ages 1–60, well-months/dropped/after month 60 | rows | 114885 | 114698 |
| audit/Decline &#124; calendar ages 1–60, well-months/dropped/before first positive month | rows | 14496 | 14444 |
| audit/Decline &#124; calendar ages 1–60, well-months/kept/retained | rows | 90369 | 90189 |
| audit/Decline &#124; calendar ages 1–60, well-months/read/input | rows | 219750 | 219331 |
| audit/Decline &#124; first three months for baseline, well-months/dropped/after baseline window | rows | 85640 | 85469 |
| audit/Decline &#124; first three months for baseline, well-months/kept/retained | rows | 4729 | 4720 |
| audit/Decline &#124; first three months for baseline, well-months/read/input | rows | 90369 | 90189 |
| audit/Decline &#124; join to start cohort, well-months/dropped/outside supported 2005–2020 start cohort | rows | 2249482 | 2249901 |
| audit/Decline &#124; join to start cohort, well-months/kept/retained | rows | 219750 | 219331 |
| audit/Decline &#124; observed baseline-eligible well-month records, ages 1–60/dropped/no usable producing-day rate | rows | 15300 | 15268 |
| audit/Decline &#124; observed baseline-eligible well-month records, ages 1–60/kept/retained | rows | 61584 | 61436 |
| audit/Decline &#124; observed baseline-eligible well-month records, ages 1–60/read/input | rows | 76884 | 76704 |
| audit/Decline &#124; start window, supported API10/dropped/first positive month outside 2005–2020 | rows | 236 | 235 |
| audit/Decline &#124; start window, supported API10/kept/retained | rows | 1577 | 1574 |
| audit/Decline &#124; start window, supported API10/read/input | rows | 1813 | 1809 |
| audit/Decline &#124; supported first production 2005–2020, API10/kept/retained | rows | 1333 | 1330 |
| audit/Decline &#124; supported first production 2005–2020, API10/read/input | rows | 1577 | 1574 |
| audit/First positive month &#124; API10 start evidence/dropped/earliest bore spud predates January 2005 | rows | 710 | absent |
| audit/First positive month &#124; API10 start evidence/dropped/earliest non-cancelled spud before 2005 | rows | absent | 7708 |
| audit/First positive month &#124; API10 start evidence/dropped/reported first production predates January 2005 | rows | 7002 | absent |
| audit/First positive month &#124; API10 start evidence/dropped/spud date incomplete | rows | absent | 8 |
| audit/First positive month &#124; API10 start evidence/kept/retained | rows | 1813 | 1809 |
| audit/Interventions &#124; supported starts, API10/dropped/unsupported start | rows | 7712 | 7716 |
| audit/Interventions &#124; supported starts, API10/kept/retained | rows | 1813 | 1809 |
| audit/Interventions &#124; year 0 anniversary, API10/kept/retained | rows | 1813 | 1809 |
| audit/Interventions &#124; year 0 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 1 anniversary, API10/kept/retained | rows | 1778 | 1774 |
| audit/Interventions &#124; year 1 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 10 anniversary, API10/dropped/anniversary after production cutoff | rows | 426 | 424 |
| audit/Interventions &#124; year 10 anniversary, API10/kept/retained | rows | 1387 | 1385 |
| audit/Interventions &#124; year 10 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 11 anniversary, API10/dropped/anniversary after production cutoff | rows | 487 | 485 |
| audit/Interventions &#124; year 11 anniversary, API10/kept/retained | rows | 1326 | 1324 |
| audit/Interventions &#124; year 11 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 12 anniversary, API10/dropped/anniversary after production cutoff | rows | 576 | 572 |
| audit/Interventions &#124; year 12 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 13 anniversary, API10/dropped/anniversary after production cutoff | rows | 661 | 657 |
| audit/Interventions &#124; year 13 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 14 anniversary, API10/dropped/anniversary after production cutoff | rows | 718 | 714 |
| audit/Interventions &#124; year 14 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 15 anniversary, API10/dropped/anniversary after production cutoff | rows | 793 | 789 |
| audit/Interventions &#124; year 15 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 16 anniversary, API10/dropped/anniversary after production cutoff | rows | 861 | 857 |
| audit/Interventions &#124; year 16 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 17 anniversary, API10/dropped/anniversary after production cutoff | rows | 950 | 946 |
| audit/Interventions &#124; year 17 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 18 anniversary, API10/dropped/anniversary after production cutoff | rows | 1103 | 1099 |
| audit/Interventions &#124; year 18 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 19 anniversary, API10/dropped/anniversary after production cutoff | rows | 1277 | 1273 |
| audit/Interventions &#124; year 19 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 2 anniversary, API10/kept/retained | rows | 1737 | 1733 |
| audit/Interventions &#124; year 2 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 20 anniversary, API10/dropped/anniversary after production cutoff | rows | 1515 | 1511 |
| audit/Interventions &#124; year 20 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 21 anniversary, API10/dropped/anniversary after production cutoff | rows | 1731 | 1727 |
| audit/Interventions &#124; year 21 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 3 anniversary, API10/kept/retained | rows | 1695 | 1691 |
| audit/Interventions &#124; year 3 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 4 anniversary, API10/dropped/anniversary after production cutoff | rows | 168 | 167 |
| audit/Interventions &#124; year 4 anniversary, API10/kept/retained | rows | 1645 | 1642 |
| audit/Interventions &#124; year 4 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 5 anniversary, API10/dropped/anniversary after production cutoff | rows | 206 | 205 |
| audit/Interventions &#124; year 5 anniversary, API10/kept/retained | rows | 1607 | 1604 |
| audit/Interventions &#124; year 5 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 6 anniversary, API10/dropped/anniversary after production cutoff | rows | 239 | 238 |
| audit/Interventions &#124; year 6 anniversary, API10/kept/retained | rows | 1574 | 1571 |
| audit/Interventions &#124; year 6 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 7 anniversary, API10/dropped/anniversary after production cutoff | rows | 280 | 279 |
| audit/Interventions &#124; year 7 anniversary, API10/kept/retained | rows | 1533 | 1530 |
| audit/Interventions &#124; year 7 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 8 anniversary, API10/dropped/anniversary after production cutoff | rows | 328 | 326 |
| audit/Interventions &#124; year 8 anniversary, API10/kept/retained | rows | 1485 | 1483 |
| audit/Interventions &#124; year 8 anniversary, API10/read/input | rows | 1813 | 1809 |
| audit/Interventions &#124; year 9 anniversary, API10/dropped/anniversary after production cutoff | rows | 384 | 382 |
| audit/Interventions &#124; year 9 anniversary, API10/kept/retained | rows | 1429 | 1427 |
| audit/Interventions &#124; year 9 anniversary, API10/read/input | rows | 1813 | 1809 |

*Table 3b. 106 headline fields changed, added or removed since round 2. An absent entry has no published field for that revision.*

## CSV verification

| CSV | Original rows / SHA-256 | Round 2 rows / SHA-256 | Round 3 rows / SHA-256 |
| --- | ---: | ---: | ---: |
| [annual_wells.csv](output/annual_wells.csv) | 110 / `656546d2445c077ab7bc5b0b0b8ec5fe36dca774d40d4fdbe49d753c17a49543` | 110 / `656546d2445c077ab7bc5b0b0b8ec5fe36dca774d40d4fdbe49d753c17a49543` | 110 / `656546d2445c077ab7bc5b0b0b8ec5fe36dca774d40d4fdbe49d753c17a49543` |
| [article_summary.csv](output/article_summary.csv) | 5 / `137afe26b97dcadf6b395e5b1f7021522294ff750ed6d8678dcbf0abc059c4f0` | 5 / `3bf1043ff55bbd0e5dd3d657ec153e7e59145cd686f2f8a991dbbcb0785a7718` | 5 / `6b27f2c861dd8bb38464ad75a9419188664375c3accec84326c239eebd7b353f` |
| [completion_lag.csv](output/completion_lag.csv) | 10 / `8919b8cb23241317cb659dcbb2478d5071ed9afc513628fd79c66de6d9847ea0` | 10 / `75d9c77e45d54a7e9eb0c907ac6ab7dc331cc31acc5844734134d08db2a5ab4f` | 10 / `a36a3e669a169f9cc900d20e019103152e54ba9d18c18fe4e665eaf981971adf` |
| [decline.csv](output/decline.csv) | 1,200 / `07f57f2fc82c22e5457feb4d77fc74b70056b6a061df78742dd1d7be9f7d3c85` | 1,200 / `95c945ef277436528a089973168cd8fc8dabc223f55bde210ac76ed507004ca1` | 1,200 / `a422de3cf9c7ef85b6b7e56ba6c7f73ffeb8c2447c565fe5e155f87c4195a252` |
| [interventions.csv](output/interventions.csv) | 220 / `d788783f5aa458a52df03013e38666919cf031de40a44aa6dcbffdd10323fa05` | 220 / `bba2a7c57cfb288d543d066c70edf16abc119ccd03299c8a808118e2d0b8b093` | 220 / `3b0a63bbea2783bae4d549e5b466283366b1afb142147201f1e101084cddbb7b` |
| [monthly_production.csv](output/monthly_production.csv) | 1,305 / `3ef353c8d0cfe1ac67b7662a0c66e4de83c2d43d763d17d47f07c2ba9dd271d1` | 1,305 / `3ef353c8d0cfe1ac67b7662a0c66e4de83c2d43d763d17d47f07c2ba9dd271d1` | 1,305 / `3ef353c8d0cfe1ac67b7662a0c66e4de83c2d43d763d17d47f07c2ba9dd271d1` |
| [record_counts.csv](output/record_counts.csv) | 148 / `54ef75a4bdea143df297753e7ed43c53880b0eddcfea1cefb02a73d631892ed4` | 286 / `254b5bf8ff55a7d4b798f4da7ef8fdfb07f8e585ca699cf8f8c036b12f7fbf32` | 287 / `9bcb72be6e4bf8948c2902c76a3a7104dd3f2a0c47edd2fe7e693fe638d43e75` |
| [spud_exclusions.csv](output/spud_exclusions.csv) | absent | absent | 5 / `6914242dab5334d30da29c45aaa5db650086c4131acaa1b4eb3a7f8f4ad725b8` |

*Table 4. Data row counts exclude the header. Each digest covers the complete CSV bytes.*

## Complete headline comparison

Across the three revisions, 388 distinct headline keys contain 1,011 distinct key-field pairs. Comparing round 3 to the original gives 500 changed, 188 added, 8 removed and 312 unchanged. Each source table below lists every published headline field, including values equal across all three revisions. Shares and relative rates use fractions. A JSON null is an undefined value, and an absent entry has no published field for that revision. [Round 3 headline definitions and source rows](output/numbers.json)

<details><summary>annual_wells.csv (81 headline fields)</summary>

| Headline key | Field | Original | Round 2 | Round 3 |
| --- | ---: | ---: | ---: | ---: |
| 100_500/period | gas_mcf | 2734747108 | 2734747108 | 2734747108 |
| 100_500/period | oil_bbl | 736921453 | 736921453 | 736921453 |
| 100_500/period | producing_wells | 9551 | 9551 | 9551 |
| 100_500/year/2005 | gas_mcf | 291036656 | 291036656 | 291036656 |
| 100_500/year/2005 | months_reported | 12 | 12 | 12 |
| 100_500/year/2005 | oil_bbl | 46385340 | 46385340 | 46385340 |
| 100_500/year/2005 | producing_wells | 707 | 707 | 707 |
| 100_500/year/2025 | gas_mcf | 34878651 | 34878651 | 34878651 |
| 100_500/year/2025 | months_reported | 12 | 12 | 12 |
| 100_500/year/2025 | oil_bbl | 20863941 | 20863941 | 20863941 |
| 100_500/year/2025 | producing_wells | 213 | 213 | 213 |
| 100_500/year/2026 | gas_mcf | 22748327 | 22748327 | 22748327 |
| 100_500/year/2026 | months_reported | 9 | 9 | 9 |
| 100_500/year/2026 | oil_bbl | 12825721 | 12825721 | 12825721 |
| 100_500/year/2026 | producing_wells | 209 | 209 | 209 |
| 1500plus/period | gas_mcf | 6775810541 | 6775810541 | 6775810541 |
| 1500plus/period | oil_bbl | 4754797277 | 4754797277 | 4754797277 |
| 1500plus/period | producing_wells | 3601 | 3601 | 3601 |
| 1500plus/year/2005 | gas_mcf | 328116645 | 328116645 | 328116645 |
| 1500plus/year/2005 | months_reported | 12 | 12 | 12 |
| 1500plus/year/2005 | oil_bbl | 65120572 | 65120572 | 65120572 |
| 1500plus/year/2005 | producing_wells | 47 | 47 | 47 |
| 1500plus/year/2025 | gas_mcf | 290814422 | 290814422 | 290814422 |
| 1500plus/year/2025 | months_reported | 12 | 12 | 12 |
| 1500plus/year/2025 | oil_bbl | 385619239 | 385619239 | 385619239 |
| 1500plus/year/2025 | producing_wells | 287 | 287 | 287 |
| 1500plus/year/2026 | gas_mcf | 228512039 | 228512039 | 228512039 |
| 1500plus/year/2026 | months_reported | 9 | 9 | 9 |
| 1500plus/year/2026 | oil_bbl | 297717080 | 297717080 | 297717080 |
| 1500plus/year/2026 | producing_wells | 287 | 287 | 287 |
| 500_1500/period | gas_mcf | 8965414392 | 8965414392 | 8965414392 |
| 500_1500/period | oil_bbl | 5476891029 | 5476891029 | 5476891029 |
| 500_1500/period | producing_wells | 7842 | 7842 | 7842 |
| 500_1500/year/2005 | gas_mcf | 766287948 | 766287948 | 766287948 |
| 500_1500/year/2005 | months_reported | 12 | 12 | 12 |
| 500_1500/year/2005 | oil_bbl | 243186191 | 243186191 | 243186191 |
| 500_1500/year/2005 | producing_wells | 314 | 314 | 314 |
| 500_1500/year/2025 | gas_mcf | 341106917 | 341106917 | 341106917 |
| 500_1500/year/2025 | months_reported | 12 | 12 | 12 |
| 500_1500/year/2025 | oil_bbl | 278587508 | 278587508 | 278587508 |
| 500_1500/year/2025 | producing_wells | 358 | 358 | 358 |
| 500_1500/year/2026 | gas_mcf | 242335474 | 242335474 | 242335474 |
| 500_1500/year/2026 | months_reported | 9 | 9 | 9 |
| 500_1500/year/2026 | oil_bbl | 204565462 | 204565462 | 204565462 |
| 500_1500/year/2026 | producing_wells | 350 | 350 | 350 |
| all/period | gas_mcf | 32778024812 | 32778024812 | 32778024812 |
| all/period | oil_bbl | 12418358076 | 12418358076 | 12418358076 |
| all/period | producing_wells | 85785 | 85785 | 85785 |
| all/year/2005 | gas_mcf | 3169144212 | 3169144212 | 3169144212 |
| all/year/2005 | months_reported | 12 | 12 | 12 |
| all/year/2005 | oil_bbl | 466956007 | 466956007 | 466956007 |
| all/year/2005 | producing_wells | 6455 | 6455 | 6455 |
| all/year/2025 | gas_mcf | 758674033 | 758674033 | 758674033 |
| all/year/2025 | months_reported | 12 | 12 | 12 |
| all/year/2025 | oil_bbl | 710792026 | 710792026 | 710792026 |
| all/year/2025 | producing_wells | 1955 | 1955 | 1955 |
| all/year/2026 | gas_mcf | 562067448 | 562067448 | 562067448 |
| all/year/2026 | months_reported | 9 | 9 | 9 |
| all/year/2026 | oil_bbl | 532544300 | 532544300 | 532544300 |
| all/year/2026 | producing_wells | 1849 | 1849 | 1849 |
| deepest_share/2005/gas_mcf | gas_mcf | 0.10353477880797682 | 0.10353477880797682 | 0.10353477880797682 |
| deepest_share/2005/oil_bbl | oil_bbl | 0.13945761704271212 | 0.13945761704271212 | 0.13945761704271212 |
| deepest_share/2025/gas_mcf | gas_mcf | 0.3833193299763299 | 0.3833193299763299 | 0.3833193299763299 |
| deepest_share/2025/oil_bbl | oil_bbl | 0.5425204910782159 | 0.5425204910782159 | 0.5425204910782159 |
| deepest_share/2026/gas_mcf | gas_mcf | 0.4065562590630582 | 0.4065562590630582 | 0.4065562590630582 |
| deepest_share/2026/oil_bbl | oil_bbl | 0.5590465995035531 | 0.5590465995035531 | 0.5590465995035531 |
| under100/period | gas_mcf | 14302052771 | 14302052771 | 14302052771 |
| under100/period | oil_bbl | 1449748317 | 1449748317 | 1449748317 |
| under100/period | producing_wells | 64791 | 64791 | 64791 |
| under100/year/2005 | gas_mcf | 1783702963 | 1783702963 | 1783702963 |
| under100/year/2005 | months_reported | 12 | 12 | 12 |
| under100/year/2005 | oil_bbl | 112263904 | 112263904 | 112263904 |
| under100/year/2005 | producing_wells | 5387 | 5387 | 5387 |
| under100/year/2025 | gas_mcf | 91874043 | 91874043 | 91874043 |
| under100/year/2025 | months_reported | 12 | 12 | 12 |
| under100/year/2025 | oil_bbl | 25721338 | 25721338 | 25721338 |
| under100/year/2025 | producing_wells | 1097 | 1097 | 1097 |
| under100/year/2026 | gas_mcf | 68471608 | 68471608 | 68471608 |
| under100/year/2026 | months_reported | 9 | 9 | 9 |
| under100/year/2026 | oil_bbl | 17436037 | 17436037 | 17436037 |
| under100/year/2026 | producing_wells | 1003 | 1003 | 1003 |

*Headline fields sourced from annual_wells.csv.*

</details>

<details><summary>article_summary.csv (75 headline fields)</summary>

| Headline key | Field | Original | Round 2 | Round 3 |
| --- | ---: | ---: | ---: | ---: |
| 100_500/period_wells | cohort_completions | 221 | 221 | 221 |
| 100_500/period_wells | distinct_producing_wells | 972 | 972 | 972 |
| 100_500/period_wells | ever_produced_wells | 214 | 214 | 214 |
| 100_500/period_wells | median_well_month_gas_mcf | 4137.0 | 4137.0 | 4137.0 |
| 100_500/period_wells | median_well_month_oil_bbl | 1684.0 | 1684.0 | 1684.0 |
| 100_500/period_wells | permit_by_cutoff_share | 0.7384615384615385 | 0.8125 | 0.8125 |
| 100_500/period_wells | permit_by_cutoff_wells | 144 | 104 | 104 |
| 100_500/period_wells | permit_signed_event_age_median_months | 12.5 | 15.0 | 15.0 |
| 100_500/period_wells | produced_in_or_after_c_month_wells | 213 | 213 | 213 |
| 100_500/period_wells | producing_well_months | 94725 | 94725 | 94725 |
| 100_500/period_wells | share_produced_in_or_after_c_month | 0.9638009049773756 | 0.9638009049773756 | 0.9638009049773756 |
| 100_500/period_wells | supported_starts | 195 | 128 | 128 |
| 100_500/period_wells | war_by_cutoff_share | 0.8051282051282052 | 0.8984375 | 0.8984375 |
| 100_500/period_wells | war_by_cutoff_wells | 157 | 115 | 115 |
| 100_500/period_wells | war_signed_event_age_median_months | 8.0 | 10.0 | 10.0 |
| 1500plus/period_wells | cohort_completions | 384 | 384 | 384 |
| 1500plus/period_wells | distinct_producing_wells | 415 | 415 | 415 |
| 1500plus/period_wells | ever_produced_wells | 353 | 353 | 353 |
| 1500plus/period_wells | median_well_month_gas_mcf | 62838.0 | 62838.0 | 62838.0 |
| 1500plus/period_wells | median_well_month_oil_bbl | 81302.0 | 81302.0 | 81302.0 |
| 1500plus/period_wells | permit_by_cutoff_share | 0.6802168021680217 | 0.6451612903225806 | 0.6440129449838188 |
| 1500plus/period_wells | permit_by_cutoff_wells | 251 | 200 | 199 |
| 1500plus/period_wells | permit_signed_event_age_median_months | 7.0 | 4.5 | 4.0 |
| 1500plus/period_wells | produced_in_or_after_c_month_wells | 353 | 353 | 353 |
| 1500plus/period_wells | producing_well_months | 35695 | 35695 | 35695 |
| 1500plus/period_wells | share_produced_in_or_after_c_month | 0.9192708333333334 | 0.9192708333333334 | 0.9192708333333334 |
| 1500plus/period_wells | supported_starts | 369 | 310 | 309 |
| 1500plus/period_wells | war_by_cutoff_share | 0.6937669376693767 | 0.6612903225806451 | 0.6601941747572816 |
| 1500plus/period_wells | war_by_cutoff_wells | 256 | 205 | 204 |
| 1500plus/period_wells | war_signed_event_age_median_months | 8.0 | 5.0 | 4.5 |
| 500_1500/period_wells | cohort_completions | 446 | 446 | 446 |
| 500_1500/period_wells | distinct_producing_wells | 683 | 683 | 683 |
| 500_1500/period_wells | ever_produced_wells | 419 | 419 | 419 |
| 500_1500/period_wells | median_well_month_gas_mcf | 44417.0 | 44417.0 | 44417.0 |
| 500_1500/period_wells | median_well_month_oil_bbl | 29340.0 | 29340.0 | 29340.0 |
| 500_1500/period_wells | permit_by_cutoff_share | 0.696969696969697 | 0.6866666666666666 | 0.6835016835016835 |
| 500_1500/period_wells | permit_by_cutoff_wells | 276 | 206 | 203 |
| 500_1500/period_wells | permit_signed_event_age_median_months | 18.0 | 14.5 | 14.0 |
| 500_1500/period_wells | produced_in_or_after_c_month_wells | 415 | 415 | 415 |
| 500_1500/period_wells | producing_well_months | 78003 | 78003 | 78003 |
| 500_1500/period_wells | share_produced_in_or_after_c_month | 0.9304932735426009 | 0.9304932735426009 | 0.9304932735426009 |
| 500_1500/period_wells | supported_starts | 396 | 300 | 297 |
| 500_1500/period_wells | war_by_cutoff_share | 0.7727272727272727 | 0.7733333333333333 | 0.7710437710437711 |
| 500_1500/period_wells | war_by_cutoff_wells | 306 | 232 | 229 |
| 500_1500/period_wells | war_signed_event_age_median_months | 9.0 | 5.0 | 5.0 |
| all/period_wells | cohort_completions | 2873 | 2873 | 2873 |
| all/period_wells | distinct_producing_wells | 9525 | 9525 | 9525 |
| all/period_wells | ever_produced_wells | 2766 | 2766 | 2766 |
| all/period_wells | median_well_month_gas_mcf | 4243.0 | 4243.0 | 4243.0 |
| all/period_wells | median_well_month_oil_bbl | 1368.0 | 1368.0 | 1368.0 |
| all/period_wells | permit_by_cutoff_share | 0.713206046141607 | 0.7291781577495863 | 0.728579325594251 |
| all/period_wells | permit_by_cutoff_wells | 1793 | 1322 | 1318 |
| all/period_wells | permit_signed_event_age_median_months | 9.0 | 8.0 | 8.0 |
| all/period_wells | produced_in_or_after_c_month_wells | 2747 | 2747 | 2747 |
| all/period_wells | producing_well_months | 827032 | 827032 | 827032 |
| all/period_wells | share_produced_in_or_after_c_month | 0.956143404107205 | 0.956143404107205 | 0.956143404107205 |
| all/period_wells | supported_starts | 2514 | 1813 | 1809 |
| all/period_wells | war_by_cutoff_share | 0.8062848050914877 | 0.8345284059569774 | 0.8341625207296849 |
| all/period_wells | war_by_cutoff_wells | 2027 | 1513 | 1509 |
| all/period_wells | war_signed_event_age_median_months | 13.0 | 14.0 | 14.0 |
| under100/period_wells | cohort_completions | 1822 | 1822 | 1822 |
| under100/period_wells | distinct_producing_wells | 7455 | 7455 | 7455 |
| under100/period_wells | ever_produced_wells | 1780 | 1780 | 1780 |
| under100/period_wells | median_well_month_gas_mcf | 2952.0 | 2952.0 | 2952.0 |
| under100/period_wells | median_well_month_oil_bbl | 956.0 | 956.0 | 956.0 |
| under100/period_wells | permit_by_cutoff_share | 0.722007722007722 | 0.7553488372093023 | 0.7553488372093023 |
| under100/period_wells | permit_by_cutoff_wells | 1122 | 812 | 812 |
| under100/period_wells | permit_signed_event_age_median_months | 7.0 | 7.0 | 7.0 |
| under100/period_wells | produced_in_or_after_c_month_wells | 1766 | 1766 | 1766 |
| under100/period_wells | producing_well_months | 618609 | 618609 | 618609 |
| under100/period_wells | share_produced_in_or_after_c_month | 0.969264544456641 | 0.969264544456641 | 0.969264544456641 |
| under100/period_wells | supported_starts | 1554 | 1075 | 1075 |
| under100/period_wells | war_by_cutoff_share | 0.8416988416988417 | 0.893953488372093 | 0.893953488372093 |
| under100/period_wells | war_by_cutoff_wells | 1308 | 961 | 961 |
| under100/period_wells | war_signed_event_age_median_months | 16.0 | 18.0 | 18.0 |

*Headline fields sourced from article_summary.csv.*

</details>

<details><summary>completion_lag.csv (60 headline fields)</summary>

| Headline key | Field | Original | Round 2 | Round 3 |
| --- | ---: | ---: | ---: | ---: |
| 100_500/lag/ordered | median_months | 0.0 | 0.0 | 0.0 |
| 100_500/lag/ordered | p25_months | 0.0 | 0.0 | 0.0 |
| 100_500/lag/ordered | p75_months | 1.0 | 1.0 | 1.0 |
| 100_500/lag/ordered | pre_completion_wells | 0 | 0 | 0 |
| 100_500/lag/ordered | same_month_wells | 95 | 71 | 71 |
| 100_500/lag/ordered | wells | 158 | 124 | 124 |
| 100_500/lag/signed | median_months | 0.0 | 0.0 | 0.0 |
| 100_500/lag/signed | p25_months | 0.0 | 0.0 | 0.0 |
| 100_500/lag/signed | p75_months | 1.0 | 1.0 | 1.0 |
| 100_500/lag/signed | pre_completion_wells | 2 | 1 | 1 |
| 100_500/lag/signed | same_month_wells | 95 | 71 | 71 |
| 100_500/lag/signed | wells | 160 | 125 | 125 |
| 1500plus/lag/ordered | median_months | 1.0 | 1.0 | 1.0 |
| 1500plus/lag/ordered | p25_months | 0.0 | 0.0 | 0.0 |
| 1500plus/lag/ordered | p75_months | 6.0 | 4.0 | 4.0 |
| 1500plus/lag/ordered | pre_completion_wells | 0 | 0 | 0 |
| 1500plus/lag/ordered | same_month_wells | 123 | 106 | 105 |
| 1500plus/lag/ordered | wells | 342 | 285 | 284 |
| 1500plus/lag/signed | median_months | 1.0 | 1.0 | 1.0 |
| 1500plus/lag/signed | p25_months | 0.0 | 0.0 | 0.0 |
| 1500plus/lag/signed | p75_months | 5.5 | 4.0 | 4.0 |
| 1500plus/lag/signed | pre_completion_wells | 9 | 9 | 9 |
| 1500plus/lag/signed | same_month_wells | 123 | 106 | 105 |
| 1500plus/lag/signed | wells | 351 | 294 | 293 |
| 500_1500/lag/ordered | median_months | 1.0 | 1.0 | 1.0 |
| 500_1500/lag/ordered | p25_months | 0.0 | 0.0 | 0.0 |
| 500_1500/lag/ordered | p75_months | 5.0 | 6.0 | 6.0 |
| 500_1500/lag/ordered | pre_completion_wells | 0 | 0 | 0 |
| 500_1500/lag/ordered | same_month_wells | 128 | 101 | 99 |
| 500_1500/lag/ordered | wells | 337 | 281 | 278 |
| 500_1500/lag/signed | median_months | 1.0 | 1.0 | 1.0 |
| 500_1500/lag/signed | p25_months | 0.0 | 0.0 | 0.0 |
| 500_1500/lag/signed | p75_months | 5.0 | 5.0 | 5.75 |
| 500_1500/lag/signed | pre_completion_wells | 20 | 8 | 8 |
| 500_1500/lag/signed | same_month_wells | 128 | 101 | 99 |
| 500_1500/lag/signed | wells | 357 | 289 | 286 |
| all/lag/ordered | median_months | 1.0 | 1.0 | 1.0 |
| all/lag/ordered | p25_months | 0.0 | 0.0 | 0.0 |
| all/lag/ordered | p75_months | 4.0 | 4.0 | 4.0 |
| all/lag/ordered | pre_completion_wells | 0 | 0 | 0 |
| all/lag/ordered | same_month_wells | 812 | 612 | 609 |
| all/lag/ordered | wells | 2132 | 1704 | 1700 |
| all/lag/signed | median_months | 1.0 | 1.0 | 1.0 |
| all/lag/signed | p25_months | 0.0 | 0.0 | 0.0 |
| all/lag/signed | p75_months | 4.0 | 4.0 | 4.0 |
| all/lag/signed | pre_completion_wells | 51 | 31 | 31 |
| all/lag/signed | same_month_wells | 812 | 612 | 609 |
| all/lag/signed | wells | 2183 | 1735 | 1731 |
| under100/lag/ordered | median_months | 1.0 | 1.0 | 1.0 |
| under100/lag/ordered | p25_months | 0.0 | 0.0 | 0.0 |
| under100/lag/ordered | p75_months | 4.0 | 4.0 | 4.0 |
| under100/lag/ordered | pre_completion_wells | 0 | 0 | 0 |
| under100/lag/ordered | same_month_wells | 466 | 334 | 334 |
| under100/lag/ordered | wells | 1295 | 1014 | 1014 |
| under100/lag/signed | median_months | 1.0 | 1.0 | 1.0 |
| under100/lag/signed | p25_months | 0.0 | 0.0 | 0.0 |
| under100/lag/signed | p75_months | 4.0 | 4.0 | 4.0 |
| under100/lag/signed | pre_completion_wells | 20 | 13 | 13 |
| under100/lag/signed | same_month_wells | 466 | 334 | 334 |
| under100/lag/signed | wells | 1315 | 1027 | 1027 |

*Headline fields sourced from completion_lag.csv.*

</details>

<details><summary>decline.csv (180 headline fields)</summary>

| Headline key | Field | Original | Round 2 | Round 3 |
| --- | ---: | ---: | ---: | ---: |
| 100_500/decline/All/1 | baseline_wells | 168 | 112 | 112 |
| 100_500/decline/All/1 | median_relative_rate | 0.691540005966238 | 0.717002748654034 | 0.717002748654034 |
| 100_500/decline/All/1 | wells | 168 | 112 | 112 |
| 100_500/decline/All/12 | baseline_wells | 168 | 112 | 112 |
| 100_500/decline/All/12 | median_relative_rate | 0.6036285417593829 | 0.5951129795060431 | 0.5951129795060431 |
| 100_500/decline/All/12 | wells | 139 | 95 | 95 |
| 100_500/decline/All/60 | baseline_wells | 168 | 112 | 112 |
| 100_500/decline/All/60 | median_relative_rate | 0.21188489516610493 | 0.1992168749770316 | 0.1992168749770316 |
| 100_500/decline/All/60 | wells | 120 | 84 | 84 |
| 100_500/decline/No subsea flag (NO)/1 | baseline_wells | 122 | 87 | 87 |
| 100_500/decline/No subsea flag (NO)/1 | median_relative_rate | 0.691540005966238 | 0.7460886055944793 | 0.7460886055944793 |
| 100_500/decline/No subsea flag (NO)/1 | wells | 122 | 87 | 87 |
| 100_500/decline/No subsea flag (NO)/12 | baseline_wells | 122 | 87 | 87 |
| 100_500/decline/No subsea flag (NO)/12 | median_relative_rate | 0.5589780858676208 | 0.50318990007837 | 0.50318990007837 |
| 100_500/decline/No subsea flag (NO)/12 | wells | 107 | 77 | 77 |
| 100_500/decline/No subsea flag (NO)/60 | baseline_wells | 122 | 87 | 87 |
| 100_500/decline/No subsea flag (NO)/60 | median_relative_rate | 0.20528191400495113 | 0.18282983210058584 | 0.18282983210058584 |
| 100_500/decline/No subsea flag (NO)/60 | wells | 92 | 68 | 68 |
| 100_500/decline/Subsea/1 | baseline_wells | 22 | 20 | 20 |
| 100_500/decline/Subsea/1 | median_relative_rate | 0.6968270194140537 | 0.6968270194140537 | 0.6968270194140537 |
| 100_500/decline/Subsea/1 | wells | 22 | 20 | 20 |
| 100_500/decline/Subsea/12 | baseline_wells | 22 | 20 | 20 |
| 100_500/decline/Subsea/12 | median_relative_rate | 1.0860186883168819 | 1.0381475035095578 | 1.0381475035095578 |
| 100_500/decline/Subsea/12 | wells | 16 | 14 | 14 |
| 100_500/decline/Subsea/60 | baseline_wells | 22 | 20 | 20 |
| 100_500/decline/Subsea/60 | median_relative_rate | 0.7591306828989919 | 0.7696773069155691 | 0.7696773069155691 |
| 100_500/decline/Subsea/60 | wells | 13 | 12 | 12 |
| 100_500/decline/Unknown/1 | baseline_wells | 24 | 5 | 5 |
| 100_500/decline/Unknown/1 | median_relative_rate | 0.7338736787666427 | 0.6146721748400853 | 0.6146721748400853 |
| 100_500/decline/Unknown/1 | wells | 24 | 5 | 5 |
| 100_500/decline/Unknown/12 | baseline_wells | 24 | 5 | 5 |
| 100_500/decline/Unknown/12 | median_relative_rate | 0.6209733696905453 | 0.8558021394137626 | 0.8558021394137626 |
| 100_500/decline/Unknown/12 | wells | 16 | 4 | 4 |
| 100_500/decline/Unknown/60 | baseline_wells | 24 | 5 | 5 |
| 100_500/decline/Unknown/60 | median_relative_rate | 0.1582561481954647 | 0.029257487227473702 | 0.029257487227473702 |
| 100_500/decline/Unknown/60 | wells | 15 | 4 | 4 |
| 1500plus/decline/All/1 | baseline_wells | 242 | 186 | 185 |
| 1500plus/decline/All/1 | median_relative_rate | 0.6303964139563368 | 0.6353176632965293 | 0.6396443552833256 |
| 1500plus/decline/All/1 | wells | 242 | 186 | 185 |
| 1500plus/decline/All/12 | baseline_wells | 242 | 186 | 185 |
| 1500plus/decline/All/12 | median_relative_rate | 0.8057434096194265 | 0.8738570580097177 | 0.8686806411837238 |
| 1500plus/decline/All/12 | wells | 211 | 162 | 161 |
| 1500plus/decline/All/60 | baseline_wells | 242 | 186 | 185 |
| 1500plus/decline/All/60 | median_relative_rate | 0.4356043524696771 | 0.47725476275618356 | 0.48087892012585004 |
| 1500plus/decline/All/60 | wells | 174 | 138 | 137 |
| 1500plus/decline/No subsea flag (NO)/1 | baseline_wells | 22 | 12 | 11 |
| 1500plus/decline/No subsea flag (NO)/1 | median_relative_rate | 0.5091803999055536 | 0.48596036708568924 | 0.46819111772974625 |
| 1500plus/decline/No subsea flag (NO)/1 | wells | 22 | 12 | 11 |
| 1500plus/decline/No subsea flag (NO)/12 | baseline_wells | 22 | 12 | 11 |
| 1500plus/decline/No subsea flag (NO)/12 | median_relative_rate | 0.9806081959002988 | 1.083104687328392 | 1.0254999315162308 |
| 1500plus/decline/No subsea flag (NO)/12 | wells | 21 | 12 | 11 |
| 1500plus/decline/No subsea flag (NO)/60 | baseline_wells | 22 | 12 | 11 |
| 1500plus/decline/No subsea flag (NO)/60 | median_relative_rate | 0.3437754405566681 | 0.477127399069896 | 0.5091752428120858 |
| 1500plus/decline/No subsea flag (NO)/60 | wells | 21 | 12 | 11 |
| 1500plus/decline/Subsea/1 | baseline_wells | 202 | 160 | 160 |
| 1500plus/decline/Subsea/1 | median_relative_rate | 0.6461828321925531 | 0.6502727748548779 | 0.6502727748548779 |
| 1500plus/decline/Subsea/1 | wells | 202 | 160 | 160 |
| 1500plus/decline/Subsea/12 | baseline_wells | 202 | 160 | 160 |
| 1500plus/decline/Subsea/12 | median_relative_rate | 0.794866613290811 | 0.8276547305428171 | 0.8276547305428171 |
| 1500plus/decline/Subsea/12 | wells | 177 | 141 | 141 |
| 1500plus/decline/Subsea/60 | baseline_wells | 202 | 160 | 160 |
| 1500plus/decline/Subsea/60 | median_relative_rate | 0.4467679504037092 | 0.5149930115006993 | 0.5149930115006993 |
| 1500plus/decline/Subsea/60 | wells | 143 | 116 | 116 |
| 1500plus/decline/Unknown/1 | baseline_wells | 18 | 14 | 14 |
| 1500plus/decline/Unknown/1 | median_relative_rate | 0.6595648615899816 | 0.7248497476018025 | 0.7248497476018025 |
| 1500plus/decline/Unknown/1 | wells | 18 | 14 | 14 |
| 1500plus/decline/Unknown/12 | baseline_wells | 18 | 14 | 14 |
| 1500plus/decline/Unknown/12 | median_relative_rate | 0.9326286484275813 | 1.355463815673406 | 1.355463815673406 |
| 1500plus/decline/Unknown/12 | wells | 13 | 9 | 9 |
| 1500plus/decline/Unknown/60 | baseline_wells | 18 | 14 | 14 |
| 1500plus/decline/Unknown/60 | median_relative_rate | 0.1983185030725605 | 0.1983185030725605 | 0.1983185030725605 |
| 1500plus/decline/Unknown/60 | wells | 10 | 10 | 10 |
| 500_1500/decline/All/1 | baseline_wells | 304 | 211 | 209 |
| 500_1500/decline/All/1 | median_relative_rate | 0.653682513196129 | 0.6204749398117749 | 0.6204749398117749 |
| 500_1500/decline/All/1 | wells | 304 | 211 | 209 |
| 500_1500/decline/All/12 | baseline_wells | 304 | 211 | 209 |
| 500_1500/decline/All/12 | median_relative_rate | 0.8471659012752638 | 0.877679892500969 | 0.877679892500969 |
| 500_1500/decline/All/12 | wells | 264 | 185 | 183 |
| 500_1500/decline/All/60 | baseline_wells | 304 | 211 | 209 |
| 500_1500/decline/All/60 | median_relative_rate | 0.39052124779410957 | 0.4119341896226457 | 0.4261019277658327 |
| 500_1500/decline/All/60 | wells | 217 | 150 | 149 |
| 500_1500/decline/No subsea flag (NO)/1 | baseline_wells | 50 | 20 | 20 |
| 500_1500/decline/No subsea flag (NO)/1 | median_relative_rate | 0.5925452677493782 | 0.4186655148141524 | 0.4186655148141524 |
| 500_1500/decline/No subsea flag (NO)/1 | wells | 50 | 20 | 20 |
| 500_1500/decline/No subsea flag (NO)/12 | baseline_wells | 50 | 20 | 20 |
| 500_1500/decline/No subsea flag (NO)/12 | median_relative_rate | 0.7592571454847497 | 0.832897544461513 | 0.832897544461513 |
| 500_1500/decline/No subsea flag (NO)/12 | wells | 44 | 20 | 20 |
| 500_1500/decline/No subsea flag (NO)/60 | baseline_wells | 50 | 20 | 20 |
| 500_1500/decline/No subsea flag (NO)/60 | median_relative_rate | 0.29714094399765645 | 0.5310857250689838 | 0.5310857250689838 |
| 500_1500/decline/No subsea flag (NO)/60 | wells | 41 | 18 | 18 |
| 500_1500/decline/Subsea/1 | baseline_wells | 207 | 179 | 177 |
| 500_1500/decline/Subsea/1 | median_relative_rate | 0.6965960199386758 | 0.6703069350892275 | 0.6703069350892275 |
| 500_1500/decline/Subsea/1 | wells | 207 | 179 | 177 |
| 500_1500/decline/Subsea/12 | baseline_wells | 207 | 179 | 177 |
| 500_1500/decline/Subsea/12 | median_relative_rate | 0.8813719862565155 | 0.8733349664489651 | 0.8733349664489651 |
| 500_1500/decline/Subsea/12 | wells | 178 | 154 | 152 |
| 500_1500/decline/Subsea/60 | baseline_wells | 207 | 179 | 177 |
| 500_1500/decline/Subsea/60 | median_relative_rate | 0.3905595367323405 | 0.3881728208619144 | 0.39052124779410957 |
| 500_1500/decline/Subsea/60 | wells | 146 | 124 | 123 |
| 500_1500/decline/Unknown/1 | baseline_wells | 47 | 12 | 12 |
| 500_1500/decline/Unknown/1 | median_relative_rate | 0.7562708965960013 | 0.5291848450970237 | 0.5291848450970237 |
| 500_1500/decline/Unknown/1 | wells | 47 | 12 | 12 |
| 500_1500/decline/Unknown/12 | baseline_wells | 47 | 12 | 12 |
| 500_1500/decline/Unknown/12 | median_relative_rate | 0.8382065083412151 | 1.4499711671227087 | 1.4499711671227087 |
| 500_1500/decline/Unknown/12 | wells | 42 | 11 | 11 |
| 500_1500/decline/Unknown/60 | baseline_wells | 47 | 12 | 12 |
| 500_1500/decline/Unknown/60 | median_relative_rate | 0.44527868459706144 | 1.5636989352468218 | 1.5636989352468218 |
| 500_1500/decline/Unknown/60 | wells | 30 | 8 | 8 |
| all/decline/All/1 | baseline_wells | 1926 | 1333 | 1330 |
| all/decline/All/1 | median_relative_rate | 0.6663887565507385 | 0.6554214251128525 | 0.6554920634920636 |
| all/decline/All/1 | wells | 1921 | 1328 | 1325 |
| all/decline/All/12 | baseline_wells | 1926 | 1333 | 1330 |
| all/decline/All/12 | median_relative_rate | 0.603035538005923 | 0.6336042243560371 | 0.6301999381879562 |
| all/decline/All/12 | wells | 1597 | 1130 | 1127 |
| all/decline/All/60 | baseline_wells | 1926 | 1333 | 1330 |
| all/decline/All/60 | median_relative_rate | 0.24791473586654306 | 0.2678890174070742 | 0.2678890174070742 |
| all/decline/All/60 | wells | 1225 | 871 | 869 |
| all/decline/No subsea flag (NO)/1 | baseline_wells | 1209 | 861 | 860 |
| all/decline/No subsea flag (NO)/1 | median_relative_rate | 0.6561007602396441 | 0.6653240359073913 | 0.6656633479972216 |
| all/decline/No subsea flag (NO)/1 | wells | 1204 | 856 | 855 |
| all/decline/No subsea flag (NO)/12 | baseline_wells | 1209 | 861 | 860 |
| all/decline/No subsea flag (NO)/12 | median_relative_rate | 0.5130003924646782 | 0.5282209460190219 | 0.5275552318523914 |
| all/decline/No subsea flag (NO)/12 | wells | 1013 | 734 | 733 |
| all/decline/No subsea flag (NO)/60 | baseline_wells | 1209 | 861 | 860 |
| all/decline/No subsea flag (NO)/60 | median_relative_rate | 0.19205330564430853 | 0.19713709711843594 | 0.19702425436510634 |
| all/decline/No subsea flag (NO)/60 | wells | 794 | 564 | 563 |
| all/decline/Subsea/1 | baseline_wells | 452 | 379 | 377 |
| all/decline/Subsea/1 | median_relative_rate | 0.6529731537148531 | 0.6533732616634171 | 0.6533732616634171 |
| all/decline/Subsea/1 | wells | 452 | 379 | 377 |
| all/decline/Subsea/12 | baseline_wells | 452 | 379 | 377 |
| all/decline/Subsea/12 | median_relative_rate | 0.8273364049722798 | 0.8377411194022683 | 0.8377411194022683 |
| all/decline/Subsea/12 | wells | 388 | 325 | 323 |
| all/decline/Subsea/60 | baseline_wells | 452 | 379 | 377 |
| all/decline/Subsea/60 | median_relative_rate | 0.43850461975060434 | 0.44541084957622357 | 0.4487021316321086 |
| all/decline/Subsea/60 | wells | 308 | 257 | 256 |
| all/decline/Unknown/1 | baseline_wells | 265 | 93 | 93 |
| all/decline/Unknown/1 | median_relative_rate | 0.7562708965960013 | 0.5693914440650732 | 0.5693914440650732 |
| all/decline/Unknown/1 | wells | 265 | 93 | 93 |
| all/decline/Unknown/12 | baseline_wells | 265 | 93 | 93 |
| all/decline/Unknown/12 | median_relative_rate | 0.5369277909740318 | 0.6879615202222072 | 0.6879615202222072 |
| all/decline/Unknown/12 | wells | 196 | 71 | 71 |
| all/decline/Unknown/60 | baseline_wells | 265 | 93 | 93 |
| all/decline/Unknown/60 | median_relative_rate | 0.20922481112310332 | 0.1983185030725605 | 0.1983185030725605 |
| all/decline/Unknown/60 | wells | 123 | 50 | 50 |
| under100/decline/All/1 | baseline_wells | 1212 | 824 | 824 |
| under100/decline/All/1 | median_relative_rate | 0.6696052261871311 | 0.6634146341463415 | 0.6634146341463415 |
| under100/decline/All/1 | wells | 1207 | 819 | 819 |
| under100/decline/All/12 | baseline_wells | 1212 | 824 | 824 |
| under100/decline/All/12 | median_relative_rate | 0.4814647377938517 | 0.505315344882074 | 0.505315344882074 |
| under100/decline/All/12 | wells | 983 | 688 | 688 |
| under100/decline/All/60 | baseline_wells | 1212 | 824 | 824 |
| under100/decline/All/60 | median_relative_rate | 0.18270508710315012 | 0.1867335829734289 | 0.1867335829734289 |
| under100/decline/All/60 | wells | 714 | 499 | 499 |
| under100/decline/No subsea flag (NO)/1 | baseline_wells | 1015 | 742 | 742 |
| under100/decline/No subsea flag (NO)/1 | median_relative_rate | 0.66640173529225 | 0.6715274625510667 | 0.6715274625510667 |
| under100/decline/No subsea flag (NO)/1 | wells | 1010 | 737 | 737 |
| under100/decline/No subsea flag (NO)/12 | baseline_wells | 1015 | 742 | 742 |
| under100/decline/No subsea flag (NO)/12 | median_relative_rate | 0.4862030343142246 | 0.5102178004840011 | 0.5102178004840011 |
| under100/decline/No subsea flag (NO)/12 | wells | 841 | 625 | 625 |
| under100/decline/No subsea flag (NO)/60 | baseline_wells | 1015 | 742 | 742 |
| under100/decline/No subsea flag (NO)/60 | median_relative_rate | 0.1855737757051021 | 0.1894001576636396 | 0.1894001576636396 |
| under100/decline/No subsea flag (NO)/60 | wells | 640 | 466 | 466 |
| under100/decline/Subsea/1 | baseline_wells | 21 | 20 | 20 |
| under100/decline/Subsea/1 | median_relative_rate | 0.5008130081300813 | 0.4803427153096631 | 0.4803427153096631 |
| under100/decline/Subsea/1 | wells | 21 | 20 | 20 |
| under100/decline/Subsea/12 | baseline_wells | 21 | 20 | 20 |
| under100/decline/Subsea/12 | median_relative_rate | 0.3915117618029281 | 0.3829256488775725 | 0.3829256488775725 |
| under100/decline/Subsea/12 | wells | 17 | 16 | 16 |
| under100/decline/Subsea/60 | baseline_wells | 21 | 20 | 20 |
| under100/decline/Subsea/60 | median_relative_rate | 0.35109698100962655 | 0.5853322304935208 | 0.5853322304935208 |
| under100/decline/Subsea/60 | wells | 6 | 5 | 5 |
| under100/decline/Unknown/1 | baseline_wells | 176 | 62 | 62 |
| under100/decline/Unknown/1 | median_relative_rate | 0.757402748533894 | 0.5678296353422287 | 0.5678296353422287 |
| under100/decline/Unknown/1 | wells | 176 | 62 | 62 |
| under100/decline/Unknown/12 | baseline_wells | 176 | 62 | 62 |
| under100/decline/Unknown/12 | median_relative_rate | 0.4120879120879121 | 0.3899207125013577 | 0.3899207125013577 |
| under100/decline/Unknown/12 | wells | 125 | 47 | 47 |
| under100/decline/Unknown/60 | baseline_wells | 176 | 62 | 62 |
| under100/decline/Unknown/60 | median_relative_rate | 0.15932561175520077 | 0.09253675974639147 | 0.09253675974639147 |
| under100/decline/Unknown/60 | wells | 68 | 28 | 28 |

*Headline fields sourced from decline.csv.*

</details>

<details><summary>interventions.csv (300 headline fields)</summary>

| Headline key | Field | Original | Round 2 | Round 3 |
| --- | ---: | ---: | ---: | ---: |
| 100_500/Intervention approval/0 | completion_observed_wells | 170 | 125 | 125 |
| 100_500/Intervention approval/0 | eligible_wells | 195 | 128 | 128 |
| 100_500/Intervention approval/0 | event_wells | 32 | 19 | 19 |
| 100_500/Intervention approval/0 | pre_origin_event_wells | 19 | 10 | 10 |
| 100_500/Intervention approval/0 | share | 0.1641025641025641 | 0.1484375 | 0.1484375 |
| 100_500/Intervention approval/0 | share_among_completion_observed | absent | 0.152 | 0.152 |
| 100_500/Intervention approval/1 | completion_observed_wells | 169 | 124 | 124 |
| 100_500/Intervention approval/1 | eligible_wells | 194 | 127 | 127 |
| 100_500/Intervention approval/1 | event_wells | 71 | 48 | 48 |
| 100_500/Intervention approval/1 | pre_origin_event_wells | 19 | 10 | 10 |
| 100_500/Intervention approval/1 | share | 0.36597938144329895 | 0.3779527559055118 | 0.3779527559055118 |
| 100_500/Intervention approval/1 | share_among_completion_observed | absent | 0.3870967741935484 | 0.3870967741935484 |
| 100_500/Intervention approval/10 | completion_observed_wells | 138 | 98 | 98 |
| 100_500/Intervention approval/10 | eligible_wells | 162 | 100 | 100 |
| 100_500/Intervention approval/10 | event_wells | 110 | 77 | 77 |
| 100_500/Intervention approval/10 | pre_origin_event_wells | 13 | 5 | 5 |
| 100_500/Intervention approval/10 | share | 0.6790123456790124 | 0.77 | 0.77 |
| 100_500/Intervention approval/10 | share_among_completion_observed | absent | 0.7857142857142857 | 0.7857142857142857 |
| 100_500/Intervention approval/20 | completion_observed_wells | 37 | 21 | 21 |
| 100_500/Intervention approval/20 | eligible_wells | 56 | 23 | 23 |
| 100_500/Intervention approval/20 | event_wells | 34 | 19 | 19 |
| 100_500/Intervention approval/20 | pre_origin_event_wells | 0 | 0 | 0 |
| 100_500/Intervention approval/20 | share | 0.6071428571428571 | 0.8260869565217391 | 0.8260869565217391 |
| 100_500/Intervention approval/20 | share_among_completion_observed | absent | 0.9047619047619048 | 0.9047619047619048 |
| 100_500/Intervention approval/5 | completion_observed_wells | 163 | 119 | 119 |
| 100_500/Intervention approval/5 | eligible_wells | 187 | 121 | 121 |
| 100_500/Intervention approval/5 | event_wells | 105 | 75 | 75 |
| 100_500/Intervention approval/5 | pre_origin_event_wells | 18 | 9 | 9 |
| 100_500/Intervention approval/5 | share | 0.5614973262032086 | 0.6198347107438017 | 0.6198347107438017 |
| 100_500/Intervention approval/5 | share_among_completion_observed | absent | 0.6302521008403361 | 0.6302521008403361 |
| 100_500/Post-completion WAR/0 | completion_observed_wells | 170 | 125 | 125 |
| 100_500/Post-completion WAR/0 | eligible_wells | 195 | 128 | 128 |
| 100_500/Post-completion WAR/0 | event_wells | 59 | 40 | 40 |
| 100_500/Post-completion WAR/0 | pre_origin_event_wells | 34 | 21 | 21 |
| 100_500/Post-completion WAR/0 | share | 0.30256410256410254 | 0.3125 | 0.3125 |
| 100_500/Post-completion WAR/0 | share_among_completion_observed | absent | 0.32 | 0.32 |
| 100_500/Post-completion WAR/1 | completion_observed_wells | 169 | 124 | 124 |
| 100_500/Post-completion WAR/1 | eligible_wells | 194 | 127 | 127 |
| 100_500/Post-completion WAR/1 | event_wells | 90 | 63 | 63 |
| 100_500/Post-completion WAR/1 | pre_origin_event_wells | 34 | 21 | 21 |
| 100_500/Post-completion WAR/1 | share | 0.4639175257731959 | 0.49606299212598426 | 0.49606299212598426 |
| 100_500/Post-completion WAR/1 | share_among_completion_observed | absent | 0.5080645161290323 | 0.5080645161290323 |
| 100_500/Post-completion WAR/10 | completion_observed_wells | 138 | 98 | 98 |
| 100_500/Post-completion WAR/10 | eligible_wells | 162 | 100 | 100 |
| 100_500/Post-completion WAR/10 | event_wells | 122 | 86 | 86 |
| 100_500/Post-completion WAR/10 | pre_origin_event_wells | 30 | 18 | 18 |
| 100_500/Post-completion WAR/10 | share | 0.7530864197530864 | 0.86 | 0.86 |
| 100_500/Post-completion WAR/10 | share_among_completion_observed | absent | 0.8775510204081632 | 0.8775510204081632 |
| 100_500/Post-completion WAR/20 | completion_observed_wells | 37 | 21 | 21 |
| 100_500/Post-completion WAR/20 | eligible_wells | 56 | 23 | 23 |
| 100_500/Post-completion WAR/20 | event_wells | 37 | 21 | 21 |
| 100_500/Post-completion WAR/20 | pre_origin_event_wells | 4 | 2 | 2 |
| 100_500/Post-completion WAR/20 | share | 0.6607142857142857 | 0.9130434782608695 | 0.9130434782608695 |
| 100_500/Post-completion WAR/20 | share_among_completion_observed | absent | 1.0 | 1.0 |
| 100_500/Post-completion WAR/5 | completion_observed_wells | 163 | 119 | 119 |
| 100_500/Post-completion WAR/5 | eligible_wells | 187 | 121 | 121 |
| 100_500/Post-completion WAR/5 | event_wells | 119 | 86 | 86 |
| 100_500/Post-completion WAR/5 | pre_origin_event_wells | 33 | 20 | 20 |
| 100_500/Post-completion WAR/5 | share | 0.6363636363636364 | 0.7107438016528925 | 0.7107438016528925 |
| 100_500/Post-completion WAR/5 | share_among_completion_observed | absent | 0.7226890756302521 | 0.7226890756302521 |
| 1500plus/Intervention approval/0 | completion_observed_wells | 355 | 298 | 297 |
| 1500plus/Intervention approval/0 | eligible_wells | 369 | 310 | 309 |
| 1500plus/Intervention approval/0 | event_wells | 71 | 66 | 66 |
| 1500plus/Intervention approval/0 | pre_origin_event_wells | 49 | 45 | 45 |
| 1500plus/Intervention approval/0 | share | 0.19241192411924118 | 0.2129032258064516 | 0.21359223300970873 |
| 1500plus/Intervention approval/0 | share_among_completion_observed | absent | 0.2214765100671141 | 0.2222222222222222 |
| 1500plus/Intervention approval/1 | completion_observed_wells | 342 | 285 | 284 |
| 1500plus/Intervention approval/1 | eligible_wells | 348 | 289 | 288 |
| 1500plus/Intervention approval/1 | event_wells | 143 | 121 | 121 |
| 1500plus/Intervention approval/1 | pre_origin_event_wells | 47 | 43 | 43 |
| 1500plus/Intervention approval/1 | share | 0.4109195402298851 | 0.4186851211072664 | 0.4201388888888889 |
| 1500plus/Intervention approval/1 | share_among_completion_observed | absent | 0.4245614035087719 | 0.426056338028169 |
| 1500plus/Intervention approval/10 | completion_observed_wells | 167 | 115 | 115 |
| 1500plus/Intervention approval/10 | eligible_wells | 172 | 118 | 118 |
| 1500plus/Intervention approval/10 | event_wells | 127 | 83 | 83 |
| 1500plus/Intervention approval/10 | pre_origin_event_wells | 17 | 13 | 13 |
| 1500plus/Intervention approval/10 | share | 0.7383720930232558 | 0.7033898305084746 | 0.7033898305084746 |
| 1500plus/Intervention approval/10 | share_among_completion_observed | absent | 0.7217391304347827 | 0.7217391304347827 |
| 1500plus/Intervention approval/20 | completion_observed_wells | 17 | 2 | 2 |
| 1500plus/Intervention approval/20 | eligible_wells | 17 | 2 | 2 |
| 1500plus/Intervention approval/20 | event_wells | 17 | 2 | 2 |
| 1500plus/Intervention approval/20 | pre_origin_event_wells | 0 | 0 | 0 |
| 1500plus/Intervention approval/20 | share | 1.0 | 1.0 | 1.0 |
| 1500plus/Intervention approval/20 | share_among_completion_observed | absent | 1.0 | 1.0 |
| 1500plus/Intervention approval/5 | completion_observed_wells | 266 | 210 | 209 |
| 1500plus/Intervention approval/5 | eligible_wells | 272 | 214 | 213 |
| 1500plus/Intervention approval/5 | event_wells | 161 | 127 | 126 |
| 1500plus/Intervention approval/5 | pre_origin_event_wells | 28 | 24 | 24 |
| 1500plus/Intervention approval/5 | share | 0.5919117647058824 | 0.5934579439252337 | 0.5915492957746479 |
| 1500plus/Intervention approval/5 | share_among_completion_observed | absent | 0.6047619047619047 | 0.6028708133971292 |
| 1500plus/Post-completion WAR/0 | completion_observed_wells | 355 | 298 | 297 |
| 1500plus/Post-completion WAR/0 | eligible_wells | 369 | 310 | 309 |
| 1500plus/Post-completion WAR/0 | event_wells | 97 | 84 | 84 |
| 1500plus/Post-completion WAR/0 | pre_origin_event_wells | 77 | 65 | 65 |
| 1500plus/Post-completion WAR/0 | share | 0.26287262872628725 | 0.2709677419354839 | 0.27184466019417475 |
| 1500plus/Post-completion WAR/0 | share_among_completion_observed | absent | 0.28187919463087246 | 0.2828282828282828 |
| 1500plus/Post-completion WAR/1 | completion_observed_wells | 342 | 285 | 284 |
| 1500plus/Post-completion WAR/1 | eligible_wells | 348 | 289 | 288 |
| 1500plus/Post-completion WAR/1 | event_wells | 139 | 113 | 113 |
| 1500plus/Post-completion WAR/1 | pre_origin_event_wells | 73 | 61 | 61 |
| 1500plus/Post-completion WAR/1 | share | 0.3994252873563218 | 0.39100346020761245 | 0.3923611111111111 |
| 1500plus/Post-completion WAR/1 | share_among_completion_observed | absent | 0.39649122807017545 | 0.397887323943662 |
| 1500plus/Post-completion WAR/10 | completion_observed_wells | 167 | 115 | 115 |
| 1500plus/Post-completion WAR/10 | eligible_wells | 172 | 118 | 118 |
| 1500plus/Post-completion WAR/10 | event_wells | 137 | 90 | 90 |
| 1500plus/Post-completion WAR/10 | pre_origin_event_wells | 35 | 23 | 23 |
| 1500plus/Post-completion WAR/10 | share | 0.7965116279069767 | 0.7627118644067796 | 0.7627118644067796 |
| 1500plus/Post-completion WAR/10 | share_among_completion_observed | absent | 0.782608695652174 | 0.782608695652174 |
| 1500plus/Post-completion WAR/20 | completion_observed_wells | 17 | 2 | 2 |
| 1500plus/Post-completion WAR/20 | eligible_wells | 17 | 2 | 2 |
| 1500plus/Post-completion WAR/20 | event_wells | 17 | 2 | 2 |
| 1500plus/Post-completion WAR/20 | pre_origin_event_wells | 0 | 0 | 0 |
| 1500plus/Post-completion WAR/20 | share | 1.0 | 1.0 | 1.0 |
| 1500plus/Post-completion WAR/20 | share_among_completion_observed | absent | 1.0 | 1.0 |
| 1500plus/Post-completion WAR/5 | completion_observed_wells | 266 | 210 | 209 |
| 1500plus/Post-completion WAR/5 | eligible_wells | 272 | 214 | 213 |
| 1500plus/Post-completion WAR/5 | event_wells | 165 | 127 | 126 |
| 1500plus/Post-completion WAR/5 | pre_origin_event_wells | 48 | 36 | 36 |
| 1500plus/Post-completion WAR/5 | share | 0.6066176470588235 | 0.5934579439252337 | 0.5915492957746479 |
| 1500plus/Post-completion WAR/5 | share_among_completion_observed | absent | 0.6047619047619047 | 0.6028708133971292 |
| 500_1500/Intervention approval/0 | completion_observed_wells | 349 | 286 | 283 |
| 500_1500/Intervention approval/0 | eligible_wells | 396 | 300 | 297 |
| 500_1500/Intervention approval/0 | event_wells | 63 | 53 | 53 |
| 500_1500/Intervention approval/0 | pre_origin_event_wells | 42 | 34 | 34 |
| 500_1500/Intervention approval/0 | share | 0.1590909090909091 | 0.17666666666666667 | 0.17845117845117844 |
| 500_1500/Intervention approval/0 | share_among_completion_observed | absent | 0.1853146853146853 | 0.1872791519434629 |
| 500_1500/Intervention approval/1 | completion_observed_wells | 346 | 282 | 279 |
| 500_1500/Intervention approval/1 | eligible_wells | 385 | 289 | 286 |
| 500_1500/Intervention approval/1 | event_wells | 119 | 97 | 96 |
| 500_1500/Intervention approval/1 | pre_origin_event_wells | 42 | 34 | 34 |
| 500_1500/Intervention approval/1 | share | 0.3090909090909091 | 0.3356401384083045 | 0.3356643356643357 |
| 500_1500/Intervention approval/1 | share_among_completion_observed | absent | 0.34397163120567376 | 0.34408602150537637 |
| 500_1500/Intervention approval/10 | completion_observed_wells | 232 | 165 | 163 |
| 500_1500/Intervention approval/10 | eligible_wells | 262 | 167 | 165 |
| 500_1500/Intervention approval/10 | event_wells | 173 | 118 | 116 |
| 500_1500/Intervention approval/10 | pre_origin_event_wells | 20 | 13 | 13 |
| 500_1500/Intervention approval/10 | share | 0.6603053435114504 | 0.7065868263473054 | 0.703030303030303 |
| 500_1500/Intervention approval/10 | share_among_completion_observed | absent | 0.7151515151515152 | 0.7116564417177914 |
| 500_1500/Intervention approval/20 | completion_observed_wells | 46 | 7 | 7 |
| 500_1500/Intervention approval/20 | eligible_wells | 67 | 8 | 8 |
| 500_1500/Intervention approval/20 | event_wells | 43 | 6 | 6 |
| 500_1500/Intervention approval/20 | pre_origin_event_wells | 1 | 0 | 0 |
| 500_1500/Intervention approval/20 | share | 0.6417910447761194 | 0.75 | 0.75 |
| 500_1500/Intervention approval/20 | share_among_completion_observed | absent | 0.8571428571428571 | 0.8571428571428571 |
| 500_1500/Intervention approval/5 | completion_observed_wells | 292 | 224 | 222 |
| 500_1500/Intervention approval/5 | eligible_wells | 324 | 228 | 226 |
| 500_1500/Intervention approval/5 | event_wells | 180 | 131 | 129 |
| 500_1500/Intervention approval/5 | pre_origin_event_wells | 30 | 22 | 22 |
| 500_1500/Intervention approval/5 | share | 0.5555555555555556 | 0.5745614035087719 | 0.5707964601769911 |
| 500_1500/Intervention approval/5 | share_among_completion_observed | absent | 0.5848214285714286 | 0.581081081081081 |
| 500_1500/Post-completion WAR/0 | completion_observed_wells | 349 | 286 | 283 |
| 500_1500/Post-completion WAR/0 | eligible_wells | 396 | 300 | 297 |
| 500_1500/Post-completion WAR/0 | event_wells | 111 | 90 | 89 |
| 500_1500/Post-completion WAR/0 | pre_origin_event_wells | 71 | 53 | 53 |
| 500_1500/Post-completion WAR/0 | share | 0.2803030303030303 | 0.3 | 0.2996632996632997 |
| 500_1500/Post-completion WAR/0 | share_among_completion_observed | absent | 0.3146853146853147 | 0.31448763250883394 |
| 500_1500/Post-completion WAR/1 | completion_observed_wells | 346 | 282 | 279 |
| 500_1500/Post-completion WAR/1 | eligible_wells | 385 | 289 | 286 |
| 500_1500/Post-completion WAR/1 | event_wells | 162 | 131 | 129 |
| 500_1500/Post-completion WAR/1 | pre_origin_event_wells | 70 | 52 | 52 |
| 500_1500/Post-completion WAR/1 | share | 0.42077922077922075 | 0.4532871972318339 | 0.45104895104895104 |
| 500_1500/Post-completion WAR/1 | share_among_completion_observed | absent | 0.4645390070921986 | 0.46236559139784944 |
| 500_1500/Post-completion WAR/10 | completion_observed_wells | 232 | 165 | 163 |
| 500_1500/Post-completion WAR/10 | eligible_wells | 262 | 167 | 165 |
| 500_1500/Post-completion WAR/10 | event_wells | 195 | 136 | 134 |
| 500_1500/Post-completion WAR/10 | pre_origin_event_wells | 47 | 30 | 30 |
| 500_1500/Post-completion WAR/10 | share | 0.7442748091603053 | 0.8143712574850299 | 0.8121212121212121 |
| 500_1500/Post-completion WAR/10 | share_among_completion_observed | absent | 0.8242424242424242 | 0.8220858895705522 |
| 500_1500/Post-completion WAR/20 | completion_observed_wells | 46 | 7 | 7 |
| 500_1500/Post-completion WAR/20 | eligible_wells | 67 | 8 | 8 |
| 500_1500/Post-completion WAR/20 | event_wells | 45 | 7 | 7 |
| 500_1500/Post-completion WAR/20 | pre_origin_event_wells | 5 | 0 | 0 |
| 500_1500/Post-completion WAR/20 | share | 0.6716417910447762 | 0.875 | 0.875 |
| 500_1500/Post-completion WAR/20 | share_among_completion_observed | absent | 1.0 | 1.0 |
| 500_1500/Post-completion WAR/5 | completion_observed_wells | 292 | 224 | 222 |
| 500_1500/Post-completion WAR/5 | eligible_wells | 324 | 228 | 226 |
| 500_1500/Post-completion WAR/5 | event_wells | 206 | 151 | 149 |
| 500_1500/Post-completion WAR/5 | pre_origin_event_wells | 54 | 36 | 36 |
| 500_1500/Post-completion WAR/5 | share | 0.6358024691358025 | 0.6622807017543859 | 0.6592920353982301 |
| 500_1500/Post-completion WAR/5 | share_among_completion_observed | absent | 0.6741071428571429 | 0.6711711711711712 |
| all/Intervention approval/0 | completion_observed_wells | 2262 | 1725 | 1721 |
| all/Intervention approval/0 | eligible_wells | 2514 | 1813 | 1809 |
| all/Intervention approval/0 | event_wells | 505 | 380 | 380 |
| all/Intervention approval/0 | pre_origin_event_wells | 336 | 240 | 240 |
| all/Intervention approval/0 | share | 0.20087509944311854 | 0.20959735245449532 | 0.21006080707573244 |
| all/Intervention approval/0 | share_among_completion_observed | absent | 0.22028985507246376 | 0.22080185938407904 |
| all/Intervention approval/1 | completion_observed_wells | 2250 | 1709 | 1705 |
| all/Intervention approval/1 | eligible_wells | 2479 | 1778 | 1774 |
| all/Intervention approval/1 | event_wells | 982 | 741 | 740 |
| all/Intervention approval/1 | pre_origin_event_wells | 334 | 238 | 238 |
| all/Intervention approval/1 | share | 0.3961274707543364 | 0.4167604049493813 | 0.41713641488162345 |
| all/Intervention approval/1 | share_among_completion_observed | absent | 0.43358689291983615 | 0.4340175953079179 |
| all/Intervention approval/10 | completion_observed_wells | 1863 | 1335 | 1333 |
| all/Intervention approval/10 | eligible_wells | 2067 | 1387 | 1385 |
| all/Intervention approval/10 | event_wells | 1454 | 1024 | 1022 |
| all/Intervention approval/10 | pre_origin_event_wells | 269 | 175 | 175 |
| all/Intervention approval/10 | share | 0.7034349298500242 | 0.738284066330209 | 0.7379061371841156 |
| all/Intervention approval/10 | share_among_completion_observed | absent | 0.7670411985018727 | 0.7666916729182296 |
| all/Intervention approval/20 | completion_observed_wells | 492 | 257 | 257 |
| all/Intervention approval/20 | eligible_wells | 643 | 298 | 298 |
| all/Intervention approval/20 | event_wells | 426 | 212 | 212 |
| all/Intervention approval/20 | pre_origin_event_wells | 64 | 29 | 29 |
| all/Intervention approval/20 | share | 0.6625194401244168 | 0.7114093959731543 | 0.7114093959731543 |
| all/Intervention approval/20 | share_among_completion_observed | absent | 0.8249027237354085 | 0.8249027237354085 |
| all/Intervention approval/5 | completion_observed_wells | 2098 | 1552 | 1549 |
| all/Intervention approval/5 | eligible_wells | 2306 | 1607 | 1604 |
| all/Intervention approval/5 | event_wells | 1423 | 1036 | 1033 |
| all/Intervention approval/5 | pre_origin_event_wells | 299 | 203 | 203 |
| all/Intervention approval/5 | share | 0.6170858629661752 | 0.6446795270690728 | 0.6440149625935162 |
| all/Intervention approval/5 | share_among_completion_observed | absent | 0.6675257731958762 | 0.6668818592640413 |
| all/Post-completion WAR/0 | completion_observed_wells | 2262 | 1725 | 1721 |
| all/Post-completion WAR/0 | eligible_wells | 2514 | 1813 | 1809 |
| all/Post-completion WAR/0 | event_wells | 634 | 447 | 446 |
| all/Post-completion WAR/0 | pre_origin_event_wells | 444 | 297 | 297 |
| all/Post-completion WAR/0 | share | 0.25218774860779636 | 0.2465526751241037 | 0.24654505251520176 |
| all/Post-completion WAR/0 | share_among_completion_observed | absent | 0.2591304347826087 | 0.25915165601394535 |
| all/Post-completion WAR/1 | completion_observed_wells | 2250 | 1709 | 1705 |
| all/Post-completion WAR/1 | eligible_wells | 2479 | 1778 | 1774 |
| all/Post-completion WAR/1 | event_wells | 983 | 719 | 717 |
| all/Post-completion WAR/1 | pre_origin_event_wells | 439 | 292 | 292 |
| all/Post-completion WAR/1 | share | 0.39653085921742637 | 0.4043869516310461 | 0.4041713641488162 |
| all/Post-completion WAR/1 | share_among_completion_observed | absent | 0.42071386775892333 | 0.42052785923753666 |
| all/Post-completion WAR/10 | completion_observed_wells | 1863 | 1335 | 1333 |
| all/Post-completion WAR/10 | eligible_wells | 2067 | 1387 | 1385 |
| all/Post-completion WAR/10 | event_wells | 1614 | 1155 | 1153 |
| all/Post-completion WAR/10 | pre_origin_event_wells | 362 | 218 | 218 |
| all/Post-completion WAR/10 | share | 0.7808417997097242 | 0.832732516222062 | 0.8324909747292418 |
| all/Post-completion WAR/10 | share_among_completion_observed | absent | 0.8651685393258427 | 0.8649662415603901 |
| all/Post-completion WAR/20 | completion_observed_wells | 492 | 257 | 257 |
| all/Post-completion WAR/20 | eligible_wells | 643 | 298 | 298 |
| all/Post-completion WAR/20 | event_wells | 481 | 254 | 254 |
| all/Post-completion WAR/20 | pre_origin_event_wells | 80 | 29 | 29 |
| all/Post-completion WAR/20 | share | 0.7480559875583204 | 0.8523489932885906 | 0.8523489932885906 |
| all/Post-completion WAR/20 | share_among_completion_observed | absent | 0.9883268482490273 | 0.9883268482490273 |
| all/Post-completion WAR/5 | completion_observed_wells | 2098 | 1552 | 1549 |
| all/Post-completion WAR/5 | eligible_wells | 2306 | 1607 | 1604 |
| all/Post-completion WAR/5 | event_wells | 1503 | 1093 | 1090 |
| all/Post-completion WAR/5 | pre_origin_event_wells | 392 | 245 | 245 |
| all/Post-completion WAR/5 | share | 0.6517779705117086 | 0.6801493466085874 | 0.6795511221945137 |
| all/Post-completion WAR/5 | share_among_completion_observed | absent | 0.7042525773195877 | 0.7036797934151066 |
| under100/Intervention approval/0 | completion_observed_wells | 1388 | 1016 | 1016 |
| under100/Intervention approval/0 | eligible_wells | 1554 | 1075 | 1075 |
| under100/Intervention approval/0 | event_wells | 339 | 242 | 242 |
| under100/Intervention approval/0 | pre_origin_event_wells | 226 | 151 | 151 |
| under100/Intervention approval/0 | share | 0.21814671814671815 | 0.22511627906976744 | 0.22511627906976744 |
| under100/Intervention approval/0 | share_among_completion_observed | absent | 0.23818897637795275 | 0.23818897637795275 |
| under100/Intervention approval/1 | completion_observed_wells | 1393 | 1018 | 1018 |
| under100/Intervention approval/1 | eligible_wells | 1552 | 1073 | 1073 |
| under100/Intervention approval/1 | event_wells | 649 | 475 | 475 |
| under100/Intervention approval/1 | pre_origin_event_wells | 226 | 151 | 151 |
| under100/Intervention approval/1 | share | 0.4181701030927835 | 0.4426840633737186 | 0.4426840633737186 |
| under100/Intervention approval/1 | share_among_completion_observed | absent | 0.46660117878192536 | 0.46660117878192536 |
| under100/Intervention approval/10 | completion_observed_wells | 1326 | 957 | 957 |
| under100/Intervention approval/10 | eligible_wells | 1471 | 1002 | 1002 |
| under100/Intervention approval/10 | event_wells | 1044 | 746 | 746 |
| under100/Intervention approval/10 | pre_origin_event_wells | 219 | 144 | 144 |
| under100/Intervention approval/10 | share | 0.7097212780421482 | 0.7445109780439122 | 0.7445109780439122 |
| under100/Intervention approval/10 | share_among_completion_observed | absent | 0.7795193312434692 | 0.7795193312434692 |
| under100/Intervention approval/20 | completion_observed_wells | 392 | 227 | 227 |
| under100/Intervention approval/20 | eligible_wells | 503 | 265 | 265 |
| under100/Intervention approval/20 | event_wells | 332 | 185 | 185 |
| under100/Intervention approval/20 | pre_origin_event_wells | 63 | 29 | 29 |
| under100/Intervention approval/20 | share | 0.6600397614314115 | 0.6981132075471698 | 0.6981132075471698 |
| under100/Intervention approval/20 | share_among_completion_observed | absent | 0.8149779735682819 | 0.8149779735682819 |
| under100/Intervention approval/5 | completion_observed_wells | 1377 | 999 | 999 |
| under100/Intervention approval/5 | eligible_wells | 1523 | 1044 | 1044 |
| under100/Intervention approval/5 | event_wells | 977 | 703 | 703 |
| under100/Intervention approval/5 | pre_origin_event_wells | 223 | 148 | 148 |
| under100/Intervention approval/5 | share | 0.6414970453053185 | 0.6733716475095786 | 0.6733716475095786 |
| under100/Intervention approval/5 | share_among_completion_observed | absent | 0.7037037037037037 | 0.7037037037037037 |
| under100/Post-completion WAR/0 | completion_observed_wells | 1388 | 1016 | 1016 |
| under100/Post-completion WAR/0 | eligible_wells | 1554 | 1075 | 1075 |
| under100/Post-completion WAR/0 | event_wells | 367 | 233 | 233 |
| under100/Post-completion WAR/0 | pre_origin_event_wells | 262 | 158 | 158 |
| under100/Post-completion WAR/0 | share | 0.23616473616473616 | 0.21674418604651163 | 0.21674418604651163 |
| under100/Post-completion WAR/0 | share_among_completion_observed | absent | 0.22933070866141733 | 0.22933070866141733 |
| under100/Post-completion WAR/1 | completion_observed_wells | 1393 | 1018 | 1018 |
| under100/Post-completion WAR/1 | eligible_wells | 1552 | 1073 | 1073 |
| under100/Post-completion WAR/1 | event_wells | 592 | 412 | 412 |
| under100/Post-completion WAR/1 | pre_origin_event_wells | 262 | 158 | 158 |
| under100/Post-completion WAR/1 | share | 0.38144329896907214 | 0.38397017707362535 | 0.38397017707362535 |
| under100/Post-completion WAR/1 | share_among_completion_observed | absent | 0.40471512770137524 | 0.40471512770137524 |
| under100/Post-completion WAR/10 | completion_observed_wells | 1326 | 957 | 957 |
| under100/Post-completion WAR/10 | eligible_wells | 1471 | 1002 | 1002 |
| under100/Post-completion WAR/10 | event_wells | 1160 | 843 | 843 |
| under100/Post-completion WAR/10 | pre_origin_event_wells | 250 | 147 | 147 |
| under100/Post-completion WAR/10 | share | 0.7885791978246091 | 0.8413173652694611 | 0.8413173652694611 |
| under100/Post-completion WAR/10 | share_among_completion_observed | absent | 0.8808777429467085 | 0.8808777429467085 |
| under100/Post-completion WAR/20 | completion_observed_wells | 392 | 227 | 227 |
| under100/Post-completion WAR/20 | eligible_wells | 503 | 265 | 265 |
| under100/Post-completion WAR/20 | event_wells | 382 | 224 | 224 |
| under100/Post-completion WAR/20 | pre_origin_event_wells | 71 | 27 | 27 |
| under100/Post-completion WAR/20 | share | 0.7594433399602386 | 0.8452830188679246 | 0.8452830188679246 |
| under100/Post-completion WAR/20 | share_among_completion_observed | absent | 0.986784140969163 | 0.986784140969163 |
| under100/Post-completion WAR/5 | completion_observed_wells | 1377 | 999 | 999 |
| under100/Post-completion WAR/5 | eligible_wells | 1523 | 1044 | 1044 |
| under100/Post-completion WAR/5 | event_wells | 1013 | 729 | 729 |
| under100/Post-completion WAR/5 | pre_origin_event_wells | 257 | 153 | 153 |
| under100/Post-completion WAR/5 | share | 0.6651346027577151 | 0.6982758620689655 | 0.6982758620689655 |
| under100/Post-completion WAR/5 | share_among_completion_observed | absent | 0.7297297297297297 | 0.7297297297297297 |

*Headline fields sourced from interventions.csv.*

</details>

<details><summary>monthly_production.csv (105 headline fields)</summary>

| Headline key | Field | Original | Round 2 | Round 3 |
| --- | ---: | ---: | ---: | ---: |
| 100_500/month/2005-12 | gas_mcf | 17730164 | 17730164 | 17730164 |
| 100_500/month/2005-12 | monthly_producing_wells | 361 | 361 | 361 |
| 100_500/month/2005-12 | oil_bbl | 3043722 | 3043722 | 3043722 |
| 100_500/month/2025-12 | gas_mcf | 3212329 | 3212329 | 3212329 |
| 100_500/month/2025-12 | monthly_producing_wells | 192 | 192 | 192 |
| 100_500/month/2025-12 | oil_bbl | 1740233 | 1740233 | 1740233 |
| 100_500/month/2026-08 | gas_mcf | 2401822 | 2401822 | 2401822 |
| 100_500/month/2026-08 | monthly_producing_wells | 169 | 169 | 169 |
| 100_500/month/2026-08 | oil_bbl | 1362825 | 1362825 | 1362825 |
| 100_500/month/2026-09 | gas_mcf | 697184 | 697184 | 697184 |
| 100_500/month/2026-09 | monthly_producing_wells | 121 | 121 | 121 |
| 100_500/month/2026-09 | oil_bbl | 603676 | 603676 | 603676 |
| 100_500/monthly_mean/2005 | gas_mcf | 24253054.666666668 | 24253054.666666668 | 24253054.666666668 |
| 100_500/monthly_mean/2005 | monthly_producing_wells | 523.4166666666666 | 523.4166666666666 | 523.4166666666666 |
| 100_500/monthly_mean/2005 | oil_bbl | 3865445.0 | 3865445.0 | 3865445.0 |
| 100_500/monthly_mean/2025 | gas_mcf | 2906554.25 | 2906554.25 | 2906554.25 |
| 100_500/monthly_mean/2025 | monthly_producing_wells | 195.08333333333334 | 195.08333333333334 | 195.08333333333334 |
| 100_500/monthly_mean/2025 | oil_bbl | 1738661.75 | 1738661.75 | 1738661.75 |
| 100_500/monthly_mean/2026 | gas_mcf | 2527591.888888889 | 2527591.888888889 | 2527591.888888889 |
| 100_500/monthly_mean/2026 | monthly_producing_wells | 179.22222222222223 | 179.22222222222223 | 179.22222222222223 |
| 100_500/monthly_mean/2026 | oil_bbl | 1425080.111111111 | 1425080.111111111 | 1425080.111111111 |
| 1500plus/month/2005-12 | gas_mcf | 26062435 | 26062435 | 26062435 |
| 1500plus/month/2005-12 | monthly_producing_wells | 39 | 39 | 39 |
| 1500plus/month/2005-12 | oil_bbl | 6755553 | 6755553 | 6755553 |
| 1500plus/month/2025-12 | gas_mcf | 28879852 | 28879852 | 28879852 |
| 1500plus/month/2025-12 | monthly_producing_wells | 256 | 256 | 256 |
| 1500plus/month/2025-12 | oil_bbl | 36596490 | 36596490 | 36596490 |
| 1500plus/month/2026-08 | gas_mcf | 29050637 | 29050637 | 29050637 |
| 1500plus/month/2026-08 | monthly_producing_wells | 273 | 273 | 273 |
| 1500plus/month/2026-08 | oil_bbl | 36955458 | 36955458 | 36955458 |
| 1500plus/month/2026-09 | gas_mcf | 16453415 | 16453415 | 16453415 |
| 1500plus/month/2026-09 | monthly_producing_wells | 135 | 135 | 135 |
| 1500plus/month/2026-09 | oil_bbl | 19035989 | 19035989 | 19035989 |
| 1500plus/monthly_mean/2005 | gas_mcf | 27343053.75 | 27343053.75 | 27343053.75 |
| 1500plus/monthly_mean/2005 | monthly_producing_wells | 37.25 | 37.25 | 37.25 |
| 1500plus/monthly_mean/2005 | oil_bbl | 5426714.333333333 | 5426714.333333333 | 5426714.333333333 |
| 1500plus/monthly_mean/2025 | gas_mcf | 24234535.166666668 | 24234535.166666668 | 24234535.166666668 |
| 1500plus/monthly_mean/2025 | monthly_producing_wells | 245.75 | 245.75 | 245.75 |
| 1500plus/monthly_mean/2025 | oil_bbl | 32134936.583333332 | 32134936.583333332 | 32134936.583333332 |
| 1500plus/monthly_mean/2026 | gas_mcf | 25390226.555555556 | 25390226.555555556 | 25390226.555555556 |
| 1500plus/monthly_mean/2026 | monthly_producing_wells | 251.44444444444446 | 251.44444444444446 | 251.44444444444446 |
| 1500plus/monthly_mean/2026 | oil_bbl | 33079675.555555556 | 33079675.555555556 | 33079675.555555556 |
| 500_1500/month/2005-12 | gas_mcf | 60578717 | 60578717 | 60578717 |
| 500_1500/month/2005-12 | monthly_producing_wells | 220 | 220 | 220 |
| 500_1500/month/2005-12 | oil_bbl | 18303096 | 18303096 | 18303096 |
| 500_1500/month/2025-12 | gas_mcf | 29055465 | 29055465 | 29055465 |
| 500_1500/month/2025-12 | monthly_producing_wells | 310 | 310 | 310 |
| 500_1500/month/2025-12 | oil_bbl | 24559519 | 24559519 | 24559519 |
| 500_1500/month/2026-08 | gas_mcf | 28191642 | 28191642 | 28191642 |
| 500_1500/month/2026-08 | monthly_producing_wells | 306 | 306 | 306 |
| 500_1500/month/2026-08 | oil_bbl | 23389268 | 23389268 | 23389268 |
| 500_1500/month/2026-09 | gas_mcf | 18751798 | 18751798 | 18751798 |
| 500_1500/month/2026-09 | monthly_producing_wells | 202 | 202 | 202 |
| 500_1500/month/2026-09 | oil_bbl | 15805218 | 15805218 | 15805218 |
| 500_1500/monthly_mean/2005 | gas_mcf | 63857329.0 | 63857329.0 | 63857329.0 |
| 500_1500/monthly_mean/2005 | monthly_producing_wells | 235.25 | 235.25 | 235.25 |
| 500_1500/monthly_mean/2005 | oil_bbl | 20265515.916666668 | 20265515.916666668 | 20265515.916666668 |
| 500_1500/monthly_mean/2025 | gas_mcf | 28425576.416666668 | 28425576.416666668 | 28425576.416666668 |
| 500_1500/monthly_mean/2025 | monthly_producing_wells | 298.1666666666667 | 298.1666666666667 | 298.1666666666667 |
| 500_1500/monthly_mean/2025 | oil_bbl | 23215625.666666668 | 23215625.666666668 | 23215625.666666668 |
| 500_1500/monthly_mean/2026 | gas_mcf | 26926163.777777776 | 26926163.777777776 | 26926163.777777776 |
| 500_1500/monthly_mean/2026 | monthly_producing_wells | 297.44444444444446 | 297.44444444444446 | 297.44444444444446 |
| 500_1500/monthly_mean/2026 | oil_bbl | 22729495.777777776 | 22729495.777777776 | 22729495.777777776 |
| all/month/2005-12 | gas_mcf | 234712396 | 234712396 | 234712396 |
| all/month/2005-12 | monthly_producing_wells | 3311 | 3311 | 3311 |
| all/month/2005-12 | oil_bbl | 35118978 | 35118978 | 35118978 |
| all/month/2025-12 | gas_mcf | 69959743 | 69959743 | 69959743 |
| all/month/2025-12 | monthly_producing_wells | 1665 | 1665 | 1665 |
| all/month/2025-12 | oil_bbl | 65057376 | 65057376 | 65057376 |
| all/month/2026-08 | gas_mcf | 66977246 | 66977246 | 66977246 |
| all/month/2026-08 | monthly_producing_wells | 1635 | 1635 | 1635 |
| all/month/2026-08 | oil_bbl | 63587543 | 63587543 | 63587543 |
| all/month/2026-09 | gas_mcf | 41076638 | 41076638 | 41076638 |
| all/month/2026-09 | monthly_producing_wells | 1050 | 1050 | 1050 |
| all/month/2026-09 | oil_bbl | 36770623 | 36770623 | 36770623 |
| all/monthly_mean/2005 | gas_mcf | 264095351.0 | 264095351.0 | 264095351.0 |
| all/monthly_mean/2005 | monthly_producing_wells | 4571.916666666667 | 4571.916666666667 | 4571.916666666667 |
| all/monthly_mean/2005 | oil_bbl | 38913000.583333336 | 38913000.583333336 | 38913000.583333336 |
| all/monthly_mean/2025 | gas_mcf | 63222836.083333336 | 63222836.083333336 | 63222836.083333336 |
| all/monthly_mean/2025 | monthly_producing_wells | 1646.5833333333333 | 1646.5833333333333 | 1646.5833333333333 |
| all/monthly_mean/2025 | oil_bbl | 59232668.833333336 | 59232668.833333336 | 59232668.833333336 |
| all/monthly_mean/2026 | gas_mcf | 62451938.666666664 | 62451938.666666664 | 62451938.666666664 |
| all/monthly_mean/2026 | monthly_producing_wells | 1591.5555555555557 | 1591.5555555555557 | 1591.5555555555557 |
| all/monthly_mean/2026 | oil_bbl | 59171588.88888889 | 59171588.88888889 | 59171588.88888889 |
| under100/month/2005-12 | gas_mcf | 130341080 | 130341080 | 130341080 |
| under100/month/2005-12 | monthly_producing_wells | 2691 | 2691 | 2691 |
| under100/month/2005-12 | oil_bbl | 7016607 | 7016607 | 7016607 |
| under100/month/2025-12 | gas_mcf | 8812097 | 8812097 | 8812097 |
| under100/month/2025-12 | monthly_producing_wells | 907 | 907 | 907 |
| under100/month/2025-12 | oil_bbl | 2161134 | 2161134 | 2161134 |
| under100/month/2026-08 | gas_mcf | 7333145 | 7333145 | 7333145 |
| under100/month/2026-08 | monthly_producing_wells | 887 | 887 | 887 |
| under100/month/2026-08 | oil_bbl | 1879992 | 1879992 | 1879992 |
| under100/month/2026-09 | gas_mcf | 5174241 | 5174241 | 5174241 |
| under100/month/2026-09 | monthly_producing_wells | 592 | 592 | 592 |
| under100/month/2026-09 | oil_bbl | 1325740 | 1325740 | 1325740 |
| under100/monthly_mean/2005 | gas_mcf | 148641913.58333334 | 148641913.58333334 | 148641913.58333334 |
| under100/monthly_mean/2005 | monthly_producing_wells | 3776.0 | 3776.0 | 3776.0 |
| under100/monthly_mean/2005 | oil_bbl | 9355325.333333334 | 9355325.333333334 | 9355325.333333334 |
| under100/monthly_mean/2025 | gas_mcf | 7656170.25 | 7656170.25 | 7656170.25 |
| under100/monthly_mean/2025 | monthly_producing_wells | 907.5833333333334 | 907.5833333333334 | 907.5833333333334 |
| under100/monthly_mean/2025 | oil_bbl | 2143444.8333333335 | 2143444.8333333335 | 2143444.8333333335 |
| under100/monthly_mean/2026 | gas_mcf | 7607956.444444444 | 7607956.444444444 | 7607956.444444444 |
| under100/monthly_mean/2026 | monthly_producing_wells | 863.4444444444445 | 863.4444444444445 | 863.4444444444445 |
| under100/monthly_mean/2026 | oil_bbl | 1937337.4444444445 | 1937337.4444444445 | 1937337.4444444445 |

*Headline fields sourced from monthly_production.csv.*

</details>

<details><summary>record_counts.csv (210 headline fields)</summary>

| Headline key | Field | Original | Round 2 | Round 3 |
| --- | ---: | ---: | ---: | ---: |
| audit/Article summary &#124; Gulf inventory, API10/dropped/outside eligible Gulf inventory | rows | absent | absent | 2041 |
| audit/Article summary &#124; Gulf inventory, API10/kept/retained | rows | absent | absent | 37529 |
| audit/Article summary &#124; Gulf inventory, API10/read/input | rows | absent | absent | 39570 |
| audit/Article summary &#124; assigned band, completion cohort API10/kept/retained | rows | absent | 2873 | 2873 |
| audit/Article summary &#124; assigned band, completion cohort API10/read/input | rows | absent | 2873 | 2873 |
| audit/Article summary &#124; completion window, API10/dropped/first C after 2025 | rows | absent | 33 | 33 |
| audit/Article summary &#124; completion window, API10/dropped/first C before 2005 | rows | absent | 2084 | 2084 |
| audit/Article summary &#124; completion window, API10/dropped/no dated C completion | rows | absent | 34580 | 32539 |
| audit/Article summary &#124; completion window, API10/kept/retained | rows | absent | 2873 | 2873 |
| audit/Article summary &#124; completion window, API10/read/input | rows | absent | 39570 | 37529 |
| audit/Article summary &#124; permit_date by cutoff, inventory API10/dropped/no dated qualifying event | rows | absent | 35444 | 33403 |
| audit/Article summary &#124; permit_date by cutoff, inventory API10/dropped/no positive joined OGOR month | rows | absent | 155 | 155 |
| audit/Article summary &#124; permit_date by cutoff, inventory API10/dropped/unsupported production start | rows | absent | 2649 | 2653 |
| audit/Article summary &#124; permit_date by cutoff, inventory API10/kept/retained | rows | absent | 1322 | 1318 |
| audit/Article summary &#124; permit_date by cutoff, inventory API10/read/input | rows | absent | 39570 | 37529 |
| audit/Article summary &#124; war_date by cutoff, inventory API10/dropped/no dated qualifying event | rows | absent | 34993 | 32952 |
| audit/Article summary &#124; war_date by cutoff, inventory API10/dropped/no positive joined OGOR month | rows | absent | 216 | 216 |
| audit/Article summary &#124; war_date by cutoff, inventory API10/dropped/unsupported production start | rows | absent | 2848 | 2852 |
| audit/Article summary &#124; war_date by cutoff, inventory API10/kept/retained | rows | absent | 1513 | 1509 |
| audit/Article summary &#124; war_date by cutoff, inventory API10/read/input | rows | absent | 39570 | 37529 |
| audit/Borehole inventory &#124; assigned depth, API10/dropped/cancelled_only | rows | absent | 762 | 762 |
| audit/Borehole inventory &#124; assigned depth, API10/dropped/outside_gulf | rows | absent | 1279 | 1279 |
| audit/Borehole inventory &#124; assigned depth, API10/dropped/unresolved depth | rows | absent | 7 | 7 |
| audit/Borehole inventory &#124; assigned depth, API10/kept/retained | rows | absent | 37522 | 37522 |
| audit/Borehole inventory &#124; assigned depth, API10/read/input | rows | absent | 39570 | 39570 |
| audit/Borehole quality &#124; all bores on Gulf inventory wells, spud, API10/kept/retained | rows | absent | 37529 | absent |
| audit/Borehole quality &#124; all bores on Gulf inventory wells, spud, API10/read/input | rows | absent | 37529 | absent |
| audit/Borehole quality &#124; non-cancelled Gulf bores, depth, API10/kept/retained | rows | absent | 37529 | 37529 |
| audit/Borehole quality &#124; non-cancelled Gulf bores, depth, API10/read/input | rows | absent | 37529 | 37529 |
| audit/Borehole quality &#124; non-cancelled Gulf bores, spud, API10/kept/retained | rows | absent | absent | 37529 |
| audit/Borehole quality &#124; non-cancelled Gulf bores, spud, API10/read/input | rows | absent | absent | 37529 |
| audit/Completion lag &#124; Gulf inventory, API10/dropped/outside eligible Gulf inventory | rows | absent | absent | 2041 |
| audit/Completion lag &#124; Gulf inventory, API10/kept/retained | rows | absent | absent | 37529 |
| audit/Completion lag &#124; Gulf inventory, API10/read/input | rows | absent | absent | 39570 |
| audit/Completion lag &#124; chronological pair, API10/dropped/first production month before first C month | rows | 51 | 31 | 31 |
| audit/Completion lag &#124; chronological pair, API10/kept/retained | rows | 2132 | 1704 | 1700 |
| audit/Completion lag &#124; chronological pair, API10/read/input | rows | 2183 | 1735 | 1731 |
| audit/Completion lag &#124; completion window, API10/dropped/first C after 2025 | rows | absent | 33 | 33 |
| audit/Completion lag &#124; completion window, API10/dropped/first C before 2005 | rows | absent | 2084 | 2084 |
| audit/Completion lag &#124; completion window, API10/dropped/no dated C completion | rows | absent | 34580 | 32539 |
| audit/Completion lag &#124; completion window, API10/kept/retained | rows | absent | 2873 | 2873 |
| audit/Completion lag &#124; completion window, API10/read/input | rows | absent | 39570 | 37529 |
| audit/Completion lag &#124; first C dated 2005–2025, API10/dropped/documented pre-window production | rows | 578 | 578 | absent |
| audit/Completion lag &#124; first C dated 2005–2025, API10/dropped/no positive joined OGOR month | rows | 107 | 107 | 107 |
| audit/Completion lag &#124; first C dated 2005–2025, API10/dropped/outside spud cohort | rows | absent | absent | 1035 |
| audit/Completion lag &#124; first C dated 2005–2025, API10/dropped/start coverage unestablished | rows | 5 | 453 | absent |
| audit/Completion lag &#124; first C dated 2005–2025, API10/kept/retained | rows | 2183 | 1735 | 1731 |
| audit/Completion lag &#124; first C dated 2005–2025, API10/read/input | rows | 2873 | 2873 | 2873 |
| audit/Decline &#124; baseline eligibility, well-months/dropped/well excluded from baseline | rows | absent | 13485 | 13485 |
| audit/Decline &#124; baseline eligibility, well-months/kept/retained | rows | absent | 76884 | 76704 |
| audit/Decline &#124; baseline eligibility, well-months/read/input | rows | absent | 90369 | 90189 |
| audit/Decline &#124; calendar ages 1–60, well-months/dropped/after month 60 | rows | absent | 114885 | 114698 |
| audit/Decline &#124; calendar ages 1–60, well-months/dropped/before first positive month | rows | absent | 14496 | 14444 |
| audit/Decline &#124; calendar ages 1–60, well-months/kept/retained | rows | absent | 90369 | 90189 |
| audit/Decline &#124; calendar ages 1–60, well-months/read/input | rows | absent | 219750 | 219331 |
| audit/Decline &#124; first three months for baseline, well-months/dropped/after baseline window | rows | absent | 85640 | 85469 |
| audit/Decline &#124; first three months for baseline, well-months/kept/retained | rows | absent | 4729 | 4720 |
| audit/Decline &#124; first three months for baseline, well-months/read/input | rows | absent | 90369 | 90189 |
| audit/Decline &#124; join to start cohort, well-months/dropped/outside supported 2005–2020 start cohort | rows | absent | 2249482 | 2249901 |
| audit/Decline &#124; join to start cohort, well-months/kept/retained | rows | absent | 219750 | 219331 |
| audit/Decline &#124; join to start cohort, well-months/read/input | rows | absent | 2469232 | 2469232 |
| audit/Decline &#124; observed baseline-eligible well-month records, ages 1–60/dropped/no usable producing-day rate | rows | 24110 | 15300 | 15268 |
| audit/Decline &#124; observed baseline-eligible well-month records, ages 1–60/kept/retained | rows | 86920 | 61584 | 61436 |
| audit/Decline &#124; observed baseline-eligible well-month records, ages 1–60/read/input | rows | 111030 | 76884 | 76704 |
| audit/Decline &#124; start window, supported API10/dropped/first positive month outside 2005–2020 | rows | absent | 236 | 235 |
| audit/Decline &#124; start window, supported API10/kept/retained | rows | absent | 1577 | 1574 |
| audit/Decline &#124; start window, supported API10/read/input | rows | absent | 1813 | 1809 |
| audit/Decline &#124; supported first production 2005–2020, API10/dropped/no positive measurable oil rate in first three calendar months | rows | 239 | 158 | 158 |
| audit/Decline &#124; supported first production 2005–2020, API10/dropped/positive oil but producing-day rate unresolved in first three months | rows | 109 | 86 | 86 |
| audit/Decline &#124; supported first production 2005–2020, API10/kept/retained | rows | 1926 | 1333 | 1330 |
| audit/Decline &#124; supported first production 2005–2020, API10/read/input | rows | 2274 | 1577 | 1574 |
| audit/First positive month &#124; API10 start evidence/dropped/earliest bore spud predates January 2005 | rows | absent | 710 | absent |
| audit/First positive month &#124; API10 start evidence/dropped/earliest non-cancelled spud before 2005 | rows | absent | absent | 7708 |
| audit/First positive month &#124; API10 start evidence/dropped/no timely in-window spud or reported start | rows | 9 | absent | absent |
| audit/First positive month &#124; API10 start evidence/dropped/reported first production predates January 2005 | rows | 7002 | 7002 | absent |
| audit/First positive month &#124; API10 start evidence/dropped/spud date incomplete | rows | absent | absent | 8 |
| audit/First positive month &#124; API10 start evidence/kept/retained | rows | 2514 | 1813 | 1809 |
| audit/First positive month &#124; API10 start evidence/read/input | rows | 9525 | 9525 | 9525 |
| audit/Interventions &#124; supported starts, API10/dropped/unsupported start | rows | absent | 7712 | 7716 |
| audit/Interventions &#124; supported starts, API10/kept/retained | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; supported starts, API10/read/input | rows | absent | 9525 | 9525 |
| audit/Interventions &#124; year 0 anniversary, API10/kept/retained | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 0 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 1 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 35 | 35 |
| audit/Interventions &#124; year 1 anniversary, API10/kept/retained | rows | absent | 1778 | 1774 |
| audit/Interventions &#124; year 1 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 10 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 426 | 424 |
| audit/Interventions &#124; year 10 anniversary, API10/kept/retained | rows | absent | 1387 | 1385 |
| audit/Interventions &#124; year 10 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 11 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 487 | 485 |
| audit/Interventions &#124; year 11 anniversary, API10/kept/retained | rows | absent | 1326 | 1324 |
| audit/Interventions &#124; year 11 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 12 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 576 | 572 |
| audit/Interventions &#124; year 12 anniversary, API10/kept/retained | rows | absent | 1237 | 1237 |
| audit/Interventions &#124; year 12 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 13 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 661 | 657 |
| audit/Interventions &#124; year 13 anniversary, API10/kept/retained | rows | absent | 1152 | 1152 |
| audit/Interventions &#124; year 13 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 14 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 718 | 714 |
| audit/Interventions &#124; year 14 anniversary, API10/kept/retained | rows | absent | 1095 | 1095 |
| audit/Interventions &#124; year 14 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 15 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 793 | 789 |
| audit/Interventions &#124; year 15 anniversary, API10/kept/retained | rows | absent | 1020 | 1020 |
| audit/Interventions &#124; year 15 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 16 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 861 | 857 |
| audit/Interventions &#124; year 16 anniversary, API10/kept/retained | rows | absent | 952 | 952 |
| audit/Interventions &#124; year 16 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 17 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 950 | 946 |
| audit/Interventions &#124; year 17 anniversary, API10/kept/retained | rows | absent | 863 | 863 |
| audit/Interventions &#124; year 17 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 18 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 1103 | 1099 |
| audit/Interventions &#124; year 18 anniversary, API10/kept/retained | rows | absent | 710 | 710 |
| audit/Interventions &#124; year 18 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 19 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 1277 | 1273 |
| audit/Interventions &#124; year 19 anniversary, API10/kept/retained | rows | absent | 536 | 536 |
| audit/Interventions &#124; year 19 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 2 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 76 | 76 |
| audit/Interventions &#124; year 2 anniversary, API10/kept/retained | rows | absent | 1737 | 1733 |
| audit/Interventions &#124; year 2 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 20 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 1515 | 1511 |
| audit/Interventions &#124; year 20 anniversary, API10/kept/retained | rows | absent | 298 | 298 |
| audit/Interventions &#124; year 20 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 21 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 1731 | 1727 |
| audit/Interventions &#124; year 21 anniversary, API10/kept/retained | rows | absent | 82 | 82 |
| audit/Interventions &#124; year 21 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 3 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 118 | 118 |
| audit/Interventions &#124; year 3 anniversary, API10/kept/retained | rows | absent | 1695 | 1691 |
| audit/Interventions &#124; year 3 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 4 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 168 | 167 |
| audit/Interventions &#124; year 4 anniversary, API10/kept/retained | rows | absent | 1645 | 1642 |
| audit/Interventions &#124; year 4 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 5 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 206 | 205 |
| audit/Interventions &#124; year 5 anniversary, API10/kept/retained | rows | absent | 1607 | 1604 |
| audit/Interventions &#124; year 5 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 6 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 239 | 238 |
| audit/Interventions &#124; year 6 anniversary, API10/kept/retained | rows | absent | 1574 | 1571 |
| audit/Interventions &#124; year 6 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 7 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 280 | 279 |
| audit/Interventions &#124; year 7 anniversary, API10/kept/retained | rows | absent | 1533 | 1530 |
| audit/Interventions &#124; year 7 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 8 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 328 | 326 |
| audit/Interventions &#124; year 8 anniversary, API10/kept/retained | rows | absent | 1485 | 1483 |
| audit/Interventions &#124; year 8 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/Interventions &#124; year 9 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 384 | 382 |
| audit/Interventions &#124; year 9 anniversary, API10/kept/retained | rows | absent | 1429 | 1427 |
| audit/Interventions &#124; year 9 anniversary, API10/read/input | rows | absent | 1813 | 1809 |
| audit/OGOR archives combined &#124; source depth join/dropped/cancelled_only | gas_mcf | 0.0 | 0.0 | 0.0 |
| audit/OGOR archives combined &#124; source depth join/dropped/cancelled_only | oil_bbl | 0.0 | 0.0 | 0.0 |
| audit/OGOR archives combined &#124; source depth join/dropped/cancelled_only | rows | 34 | 34 | 34 |
| audit/OGOR archives combined &#124; source depth join/dropped/gulf_without_resolved_depth | gas_mcf | 903500.0 | 903500.0 | 903500.0 |
| audit/OGOR archives combined &#124; source depth join/dropped/gulf_without_resolved_depth | oil_bbl | 713710.0 | 713710.0 | 713710.0 |
| audit/OGOR archives combined &#124; source depth join/dropped/gulf_without_resolved_depth | rows | 1326 | 1326 | 1326 |
| audit/OGOR archives combined &#124; source depth join/kept/retained | gas_mcf | 32778024812.0 | 32778024812.0 | 32778024812.0 |
| audit/OGOR archives combined &#124; source depth join/kept/retained | oil_bbl | 12418358076.0 | 12418358076.0 | 12418358076.0 |
| audit/OGOR archives combined &#124; source depth join/kept/retained | rows | 2719886 | 2719886 | 2719886 |
| audit/OGOR archives combined &#124; source depth join/read/input | gas_mcf | 32778928312.0 | 32778928312.0 | 32778928312.0 |
| audit/OGOR archives combined &#124; source depth join/read/input | oil_bbl | 12419071786.0 | 12419071786.0 | 12419071786.0 |
| audit/OGOR archives combined &#124; source depth join/read/input | rows | 2721246 | 2721246 | 2721246 |
| audit/OGOR raw recount / 2026-08/dropped/outside classified Gulf inventory | rows | absent | 1 | 1 |
| audit/OGOR raw recount / 2026-08/kept/retained | rows | absent | 4457 | 4457 |
| audit/OGOR raw recount / 2026-08/read/input | rows | absent | 4458 | 4458 |
| audit/OGOR raw recount / 2026-09/kept/retained | rows | absent | 2688 | 2688 |
| audit/OGOR raw recount / 2026-09/read/input | rows | absent | 2688 | 2688 |
| audit/OGOR well-months / exact oil rate/dropped/invalid_days | rows | 33 | 33 | 33 |
| audit/OGOR well-months / exact oil rate/dropped/no_hydrocarbon_production | rows | 1642200 | 1642200 | 1642200 |
| audit/OGOR well-months / exact oil rate/dropped/unresolved_overlap | rows | 12645 | 12645 | 12645 |
| audit/OGOR well-months / exact oil rate/kept/retained | rows | 814354 | 814354 | 814354 |
| audit/OGOR well-months / exact oil rate/read/input | rows | 2469232 | 2469232 | 2469232 |
| audit/OGOR well-months / producing activity/dropped/no positive net oil or gas | rows | absent | 1642200 | 1642200 |
| audit/OGOR well-months / producing activity/kept/retained | rows | absent | 827032 | 827032 |
| audit/OGOR well-months / producing activity/read/input | rows | absent | 2469232 | 2469232 |
| audit/borehole API rows for inventory/kept/retained | rows | 57520 | 57520 | 57520 |
| audit/borehole API rows for inventory/read/input | rows | 57520 | 57520 | 57520 |
| audit/borehole rows for Gulf depth and spud/dropped/cancelled bore | rows | 994 | absent | absent |
| audit/borehole rows for Gulf depth and spud/dropped/region outside or unresolved | rows | 1934 | absent | absent |
| audit/borehole rows for Gulf depth and spud/kept/retained | rows | 54592 | absent | absent |
| audit/borehole rows for Gulf depth and spud/read/input | rows | 57520 | absent | absent |
| audit/borehole rows for Gulf depth/dropped/cancelled bore | rows | absent | 994 | 994 |
| audit/borehole rows for Gulf depth/dropped/region outside or unresolved | rows | absent | 1934 | 1934 |
| audit/borehole rows for Gulf depth/kept/retained | rows | absent | 54592 | 54592 |
| audit/borehole rows for Gulf depth/read/input | rows | absent | 57520 | 57520 |
| audit/eWell APM approvals for classified well work/dropped/event after production cutoff | rows | absent | 130 | 130 |
| audit/eWell APM approvals for classified well work/dropped/event on or before completion | rows | 2986 | 2986 | 2986 |
| audit/eWell APM approvals for classified well work/dropped/no dated C completion | rows | 9331 | 9283 | 9283 |
| audit/eWell APM approvals for classified well work/dropped/outside series well-work groups | rows | 69636 | 69636 | 69636 |
| audit/eWell APM approvals for classified well work/kept/retained | rows | 19997 | 19915 | 19915 |
| audit/eWell APM approvals for classified well work/read/input | rows | 101950 | 101950 | 101950 |
| audit/eWell APM descriptions/dropped/no selected permit | rows | 116 | 116 | 116 |
| audit/eWell APM descriptions/kept/retained | rows | 100892 | 100892 | 100892 |
| audit/eWell APM descriptions/read/input | rows | 101008 | 101008 | 101008 |
| audit/eWell APM permit identities/dropped/repeated permit | rows | 207 | 207 | 207 |
| audit/eWell APM permit identities/kept/retained | rows | 101970 | 101970 | 101970 |
| audit/eWell APM permit identities/read/input | rows | 102177 | 102177 | 102177 |
| audit/eWell APM permits for series classification/dropped/outside eligible Gulf inventory | rows | 20 | 20 | 20 |
| audit/eWell APM permits for series classification/kept/retained | rows | 101950 | 101950 | 101950 |
| audit/eWell APM permits for series classification/read/input | rows | 101970 | 101970 | 101970 |
| audit/eWell APM suboperation rows/dropped/no selected permit | rows | 1756 | 1756 | 1756 |
| audit/eWell APM suboperation rows/kept/retained | rows | 111522 | 111522 | 111522 |
| audit/eWell APM suboperation rows/read/input | rows | 113278 | 113278 | 113278 |
| audit/eWell EOR operation code dictionary/kept/retained | rows | 4 | 4 | 4 |
| audit/eWell EOR operation code dictionary/read/input | rows | 4 | 4 | 4 |
| audit/eWell EOR rows for first completion/dropped/other EOR operation | rows | 37221 | 37221 | 37221 |
| audit/eWell EOR rows for first completion/kept/retained | rows | 8446 | 8446 | 8446 |
| audit/eWell EOR rows for first completion/read/input | rows | 45667 | 45667 | 45667 |
| audit/eWell WAR rows for observed work/dropped/event after production cutoff | rows | absent | 858 | 858 |
| audit/eWell WAR rows for observed work/dropped/event on or before completion | rows | 61898 | 61898 | 61898 |
| audit/eWell WAR rows for observed work/dropped/no dated C completion | rows | 230900 | 230336 | 230336 |
| audit/eWell WAR rows for observed work/dropped/outside eligible Gulf inventory | rows | 18 | 18 | 18 |
| audit/eWell WAR rows for observed work/kept/retained | rows | 77963 | 77669 | 77669 |
| audit/eWell WAR rows for observed work/read/input | rows | 370779 | 370779 | 370779 |

*Headline fields sourced from record_counts.csv.*

</details>
