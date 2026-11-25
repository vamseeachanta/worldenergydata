# Round 2 impact on production-by-depth results

The comparison uses the committed outputs at `396d3d400660b6e02908d682dda1cd717c448bbf` and the local round 2 rebuild from the same 29 pinned archives. The observation window runs from January 2005 through provisional September 2026. [Pre-fix measurement](measure-finding3.md) · [Input pins](source_pins.json)

## Article headlines

| Pooled measure | Original | Revised | Difference |
| --- | ---: | ---: | ---: |
| Distinct producing wells | 9,525 | 9,525 | +0 |
| Signed oil volume (billion bbl) | 12.418 | 12.418 | +0.000 |
| Signed gas volume (trillion cf) | 32.778 | 32.778 | +0.000 |
| Subsea flag YES, month-60 median rate (% of baseline) | 43.9 | 44.5 | +0.7 |
| Subsea flag NO, month-60 median rate (% of baseline) | 19.2 | 19.7 | +0.5 |

*Table 1. Full-window headcount and signed volumes, and median oil-rate ratios at age 60 months by completion flag at startup. Rate differences are calculated before rounding and expressed in percentage points. Displayed volumes are rounded to three decimals.*

| Depth band | Supported starts | Ordered lag, median (P25 to P75), months | Month-60 median oil rate (% of baseline) | Year-5 WAR (%) | Year-5 approval (%) |
| --- | ---: | ---: | ---: | ---: | ---: |
| <100 m | 1,554 → 1,075 | 1 (0 to 4) → 1 (0 to 4) | 18.3 → 18.7 | 66.5 → 69.8 | 64.1 → 67.3 |
| 100–<500 m | 195 → 128 | 0 (0 to 1) → 0 (0 to 1) | 21.2 → 19.9 | 63.6 → 71.1 | 56.1 → 62.0 |
| 500–<1,500 m | 396 → 300 | 1 (0 to 5) → 1 (0 to 6) | 39.1 → 41.2 | 63.6 → 66.2 | 55.6 → 57.5 |
| ≥1,500 m | 369 → 310 | 1 (0 to 6) → 1 (0 to 4) | 43.6 → 47.7 | 60.7 → 59.3 | 59.2 → 59.3 |
| All | 2,514 → 1,813 | 1 (0 to 4) → 1 (0 to 4) | 24.8 → 26.8 | 65.2 → 68.0 | 61.7 → 64.5 |

*Table 2. Each cell gives original → revised. Event denominators include all supported starts that reached year 5 by the cutoff.*

## CSV byte comparison

5 of 7 CSV files changed. The files `annual_wells.csv` and `monthly_production.csv` match byte for byte.

| CSV | Original data rows | Revised data rows | Original SHA-256 | Revised SHA-256 |
| --- | ---: | ---: | --- | --- |
| [article_summary.csv](output/article_summary.csv) | 5 | 5 | `137afe26b97dcadf6b395e5b1f7021522294ff750ed6d8678dcbf0abc059c4f0` | `3bf1043ff55bbd0e5dd3d657ec153e7e59145cd686f2f8a991dbbcb0785a7718` |
| [completion_lag.csv](output/completion_lag.csv) | 10 | 10 | `8919b8cb23241317cb659dcbb2478d5071ed9afc513628fd79c66de6d9847ea0` | `75d9c77e45d54a7e9eb0c907ac6ab7dc331cc31acc5844734134d08db2a5ab4f` |
| [decline.csv](output/decline.csv) | 1200 | 1200 | `07f57f2fc82c22e5457feb4d77fc74b70056b6a061df78742dd1d7be9f7d3c85` | `95c945ef277436528a089973168cd8fc8dabc223f55bde210ac76ed507004ca1` |
| [interventions.csv](output/interventions.csv) | 220 | 220 | `d788783f5aa458a52df03013e38666919cf031de40a44aa6dcbffdd10323fa05` | `bba2a7c57cfb288d543d066c70edf16abc119ccd03299c8a808118e2d0b8b093` |
| [record_counts.csv](output/record_counts.csv) | 148 | 286 | `54ef75a4bdea143df297753e7ed43c53880b0eddcfea1cefb02a73d631892ed4` | `254b5bf8ff55a7d4b798f4da7ef8fdfb07f8e585ca699cf8f8c036b12f7fbf32` |

*Table 3. Byte-level comparison of the delivered CSV files against the original Git blobs.*

## Complete headline field comparison

There are 277 headline keys with at least one changed, added or removed field. Across these keys, 500 existing values changed, 180 fields were added and 5 fields were removed. Each row names its complete JSON headline key and field. Difference is revised minus original in the source field's units. Shares and relative rates are fractions in this table. An absent field had no entry in that version. A JSON null denotes an undefined quantity. Differences involving either are n/a. [Revised headline values and source rows](output/numbers.json)

| Headline key | Field | Original | Revised | Difference |
| --- | --- | ---: | ---: | ---: |
| 100_500/Intervention approval/0 | completion_observed_wells | 170 | 125 | -45 |
| 100_500/Intervention approval/0 | eligible_wells | 195 | 128 | -67 |
| 100_500/Intervention approval/0 | event_wells | 32 | 19 | -13 |
| 100_500/Intervention approval/0 | pre_origin_event_wells | 19 | 10 | -9 |
| 100_500/Intervention approval/0 | share | 0.1641025641025641 | 0.1484375 | -0.0156650641025641 |
| 100_500/Intervention approval/0 | share_among_completion_observed | absent | 0.152 | n/a |
| 100_500/Intervention approval/1 | completion_observed_wells | 169 | 124 | -45 |
| 100_500/Intervention approval/1 | eligible_wells | 194 | 127 | -67 |
| 100_500/Intervention approval/1 | event_wells | 71 | 48 | -23 |
| 100_500/Intervention approval/1 | pre_origin_event_wells | 19 | 10 | -9 |
| 100_500/Intervention approval/1 | share | 0.36597938144329895 | 0.3779527559055118 | +0.01197337446221285 |
| 100_500/Intervention approval/1 | share_among_completion_observed | absent | 0.3870967741935484 | n/a |
| 100_500/Intervention approval/10 | completion_observed_wells | 138 | 98 | -40 |
| 100_500/Intervention approval/10 | eligible_wells | 162 | 100 | -62 |
| 100_500/Intervention approval/10 | event_wells | 110 | 77 | -33 |
| 100_500/Intervention approval/10 | pre_origin_event_wells | 13 | 5 | -8 |
| 100_500/Intervention approval/10 | share | 0.6790123456790124 | 0.77 | +0.0909876543209876 |
| 100_500/Intervention approval/10 | share_among_completion_observed | absent | 0.7857142857142857 | n/a |
| 100_500/Intervention approval/20 | completion_observed_wells | 37 | 21 | -16 |
| 100_500/Intervention approval/20 | eligible_wells | 56 | 23 | -33 |
| 100_500/Intervention approval/20 | event_wells | 34 | 19 | -15 |
| 100_500/Intervention approval/20 | share | 0.6071428571428571 | 0.8260869565217391 | +0.2189440993788820 |
| 100_500/Intervention approval/20 | share_among_completion_observed | absent | 0.9047619047619048 | n/a |
| 100_500/Intervention approval/5 | completion_observed_wells | 163 | 119 | -44 |
| 100_500/Intervention approval/5 | eligible_wells | 187 | 121 | -66 |
| 100_500/Intervention approval/5 | event_wells | 105 | 75 | -30 |
| 100_500/Intervention approval/5 | pre_origin_event_wells | 18 | 9 | -9 |
| 100_500/Intervention approval/5 | share | 0.5614973262032086 | 0.6198347107438017 | +0.0583373845405931 |
| 100_500/Intervention approval/5 | share_among_completion_observed | absent | 0.6302521008403361 | n/a |
| 100_500/Post-completion WAR/0 | completion_observed_wells | 170 | 125 | -45 |
| 100_500/Post-completion WAR/0 | eligible_wells | 195 | 128 | -67 |
| 100_500/Post-completion WAR/0 | event_wells | 59 | 40 | -19 |
| 100_500/Post-completion WAR/0 | pre_origin_event_wells | 34 | 21 | -13 |
| 100_500/Post-completion WAR/0 | share | 0.30256410256410254 | 0.3125 | +0.00993589743589746 |
| 100_500/Post-completion WAR/0 | share_among_completion_observed | absent | 0.32 | n/a |
| 100_500/Post-completion WAR/1 | completion_observed_wells | 169 | 124 | -45 |
| 100_500/Post-completion WAR/1 | eligible_wells | 194 | 127 | -67 |
| 100_500/Post-completion WAR/1 | event_wells | 90 | 63 | -27 |
| 100_500/Post-completion WAR/1 | pre_origin_event_wells | 34 | 21 | -13 |
| 100_500/Post-completion WAR/1 | share | 0.4639175257731959 | 0.49606299212598426 | +0.03214546635278836 |
| 100_500/Post-completion WAR/1 | share_among_completion_observed | absent | 0.5080645161290323 | n/a |
| 100_500/Post-completion WAR/10 | completion_observed_wells | 138 | 98 | -40 |
| 100_500/Post-completion WAR/10 | eligible_wells | 162 | 100 | -62 |
| 100_500/Post-completion WAR/10 | event_wells | 122 | 86 | -36 |
| 100_500/Post-completion WAR/10 | pre_origin_event_wells | 30 | 18 | -12 |
| 100_500/Post-completion WAR/10 | share | 0.7530864197530864 | 0.86 | +0.1069135802469136 |
| 100_500/Post-completion WAR/10 | share_among_completion_observed | absent | 0.8775510204081632 | n/a |
| 100_500/Post-completion WAR/20 | completion_observed_wells | 37 | 21 | -16 |
| 100_500/Post-completion WAR/20 | eligible_wells | 56 | 23 | -33 |
| 100_500/Post-completion WAR/20 | event_wells | 37 | 21 | -16 |
| 100_500/Post-completion WAR/20 | pre_origin_event_wells | 4 | 2 | -2 |
| 100_500/Post-completion WAR/20 | share | 0.6607142857142857 | 0.9130434782608695 | +0.2523291925465838 |
| 100_500/Post-completion WAR/20 | share_among_completion_observed | absent | 1.0 | n/a |
| 100_500/Post-completion WAR/5 | completion_observed_wells | 163 | 119 | -44 |
| 100_500/Post-completion WAR/5 | eligible_wells | 187 | 121 | -66 |
| 100_500/Post-completion WAR/5 | event_wells | 119 | 86 | -33 |
| 100_500/Post-completion WAR/5 | pre_origin_event_wells | 33 | 20 | -13 |
| 100_500/Post-completion WAR/5 | share | 0.6363636363636364 | 0.7107438016528925 | +0.0743801652892561 |
| 100_500/Post-completion WAR/5 | share_among_completion_observed | absent | 0.7226890756302521 | n/a |
| 100_500/decline/All/1 | baseline_wells | 168 | 112 | -56 |
| 100_500/decline/All/1 | median_relative_rate | 0.691540005966238 | 0.717002748654034 | +0.025462742687796 |
| 100_500/decline/All/1 | wells | 168 | 112 | -56 |
| 100_500/decline/All/12 | baseline_wells | 168 | 112 | -56 |
| 100_500/decline/All/12 | median_relative_rate | 0.6036285417593829 | 0.5951129795060431 | -0.0085155622533398 |
| 100_500/decline/All/12 | wells | 139 | 95 | -44 |
| 100_500/decline/All/60 | baseline_wells | 168 | 112 | -56 |
| 100_500/decline/All/60 | median_relative_rate | 0.21188489516610493 | 0.1992168749770316 | -0.01266802018907333 |
| 100_500/decline/All/60 | wells | 120 | 84 | -36 |
| 100_500/decline/No subsea flag (NO)/1 | baseline_wells | 122 | 87 | -35 |
| 100_500/decline/No subsea flag (NO)/1 | median_relative_rate | 0.691540005966238 | 0.7460886055944793 | +0.0545485996282413 |
| 100_500/decline/No subsea flag (NO)/1 | wells | 122 | 87 | -35 |
| 100_500/decline/No subsea flag (NO)/12 | baseline_wells | 122 | 87 | -35 |
| 100_500/decline/No subsea flag (NO)/12 | median_relative_rate | 0.5589780858676208 | 0.50318990007837 | -0.0557881857892508 |
| 100_500/decline/No subsea flag (NO)/12 | wells | 107 | 77 | -30 |
| 100_500/decline/No subsea flag (NO)/60 | baseline_wells | 122 | 87 | -35 |
| 100_500/decline/No subsea flag (NO)/60 | median_relative_rate | 0.20528191400495113 | 0.18282983210058584 | -0.02245208190436529 |
| 100_500/decline/No subsea flag (NO)/60 | wells | 92 | 68 | -24 |
| 100_500/decline/Subsea/1 | baseline_wells | 22 | 20 | -2 |
| 100_500/decline/Subsea/1 | wells | 22 | 20 | -2 |
| 100_500/decline/Subsea/12 | baseline_wells | 22 | 20 | -2 |
| 100_500/decline/Subsea/12 | median_relative_rate | 1.0860186883168819 | 1.0381475035095578 | -0.0478711848073241 |
| 100_500/decline/Subsea/12 | wells | 16 | 14 | -2 |
| 100_500/decline/Subsea/60 | baseline_wells | 22 | 20 | -2 |
| 100_500/decline/Subsea/60 | median_relative_rate | 0.7591306828989919 | 0.7696773069155691 | +0.0105466240165772 |
| 100_500/decline/Subsea/60 | wells | 13 | 12 | -1 |
| 100_500/decline/Unknown/1 | baseline_wells | 24 | 5 | -19 |
| 100_500/decline/Unknown/1 | median_relative_rate | 0.7338736787666427 | 0.6146721748400853 | -0.1192015039265574 |
| 100_500/decline/Unknown/1 | wells | 24 | 5 | -19 |
| 100_500/decline/Unknown/12 | baseline_wells | 24 | 5 | -19 |
| 100_500/decline/Unknown/12 | median_relative_rate | 0.6209733696905453 | 0.8558021394137626 | +0.2348287697232173 |
| 100_500/decline/Unknown/12 | wells | 16 | 4 | -12 |
| 100_500/decline/Unknown/60 | baseline_wells | 24 | 5 | -19 |
| 100_500/decline/Unknown/60 | median_relative_rate | 0.1582561481954647 | 0.029257487227473702 | -0.128998660967990998 |
| 100_500/decline/Unknown/60 | wells | 15 | 4 | -11 |
| 100_500/lag/ordered | same_month_wells | 95 | 71 | -24 |
| 100_500/lag/ordered | wells | 158 | 124 | -34 |
| 100_500/lag/signed | pre_completion_wells | 2 | 1 | -1 |
| 100_500/lag/signed | same_month_wells | 95 | 71 | -24 |
| 100_500/lag/signed | wells | 160 | 125 | -35 |
| 100_500/period_wells | permit_by_cutoff_share | 0.7384615384615385 | 0.8125 | +0.0740384615384615 |
| 100_500/period_wells | permit_by_cutoff_wells | 144 | 104 | -40 |
| 100_500/period_wells | permit_signed_event_age_median_months | 12.5 | 15.0 | +2.5 |
| 100_500/period_wells | supported_starts | 195 | 128 | -67 |
| 100_500/period_wells | war_by_cutoff_share | 0.8051282051282052 | 0.8984375 | +0.0933092948717948 |
| 100_500/period_wells | war_by_cutoff_wells | 157 | 115 | -42 |
| 100_500/period_wells | war_signed_event_age_median_months | 8.0 | 10.0 | +2.0 |
| 1500plus/Intervention approval/0 | completion_observed_wells | 355 | 298 | -57 |
| 1500plus/Intervention approval/0 | eligible_wells | 369 | 310 | -59 |
| 1500plus/Intervention approval/0 | event_wells | 71 | 66 | -5 |
| 1500plus/Intervention approval/0 | pre_origin_event_wells | 49 | 45 | -4 |
| 1500plus/Intervention approval/0 | share | 0.19241192411924118 | 0.2129032258064516 | +0.02049130168721042 |
| 1500plus/Intervention approval/0 | share_among_completion_observed | absent | 0.2214765100671141 | n/a |
| 1500plus/Intervention approval/1 | completion_observed_wells | 342 | 285 | -57 |
| 1500plus/Intervention approval/1 | eligible_wells | 348 | 289 | -59 |
| 1500plus/Intervention approval/1 | event_wells | 143 | 121 | -22 |
| 1500plus/Intervention approval/1 | pre_origin_event_wells | 47 | 43 | -4 |
| 1500plus/Intervention approval/1 | share | 0.4109195402298851 | 0.4186851211072664 | +0.0077655808773813 |
| 1500plus/Intervention approval/1 | share_among_completion_observed | absent | 0.4245614035087719 | n/a |
| 1500plus/Intervention approval/10 | completion_observed_wells | 167 | 115 | -52 |
| 1500plus/Intervention approval/10 | eligible_wells | 172 | 118 | -54 |
| 1500plus/Intervention approval/10 | event_wells | 127 | 83 | -44 |
| 1500plus/Intervention approval/10 | pre_origin_event_wells | 17 | 13 | -4 |
| 1500plus/Intervention approval/10 | share | 0.7383720930232558 | 0.7033898305084746 | -0.0349822625147812 |
| 1500plus/Intervention approval/10 | share_among_completion_observed | absent | 0.7217391304347827 | n/a |
| 1500plus/Intervention approval/20 | completion_observed_wells | 17 | 2 | -15 |
| 1500plus/Intervention approval/20 | eligible_wells | 17 | 2 | -15 |
| 1500plus/Intervention approval/20 | event_wells | 17 | 2 | -15 |
| 1500plus/Intervention approval/20 | share_among_completion_observed | absent | 1.0 | n/a |
| 1500plus/Intervention approval/5 | completion_observed_wells | 266 | 210 | -56 |
| 1500plus/Intervention approval/5 | eligible_wells | 272 | 214 | -58 |
| 1500plus/Intervention approval/5 | event_wells | 161 | 127 | -34 |
| 1500plus/Intervention approval/5 | pre_origin_event_wells | 28 | 24 | -4 |
| 1500plus/Intervention approval/5 | share | 0.5919117647058824 | 0.5934579439252337 | +0.0015461792193513 |
| 1500plus/Intervention approval/5 | share_among_completion_observed | absent | 0.6047619047619047 | n/a |
| 1500plus/Post-completion WAR/0 | completion_observed_wells | 355 | 298 | -57 |
| 1500plus/Post-completion WAR/0 | eligible_wells | 369 | 310 | -59 |
| 1500plus/Post-completion WAR/0 | event_wells | 97 | 84 | -13 |
| 1500plus/Post-completion WAR/0 | pre_origin_event_wells | 77 | 65 | -12 |
| 1500plus/Post-completion WAR/0 | share | 0.26287262872628725 | 0.2709677419354839 | +0.00809511320919665 |
| 1500plus/Post-completion WAR/0 | share_among_completion_observed | absent | 0.28187919463087246 | n/a |
| 1500plus/Post-completion WAR/1 | completion_observed_wells | 342 | 285 | -57 |
| 1500plus/Post-completion WAR/1 | eligible_wells | 348 | 289 | -59 |
| 1500plus/Post-completion WAR/1 | event_wells | 139 | 113 | -26 |
| 1500plus/Post-completion WAR/1 | pre_origin_event_wells | 73 | 61 | -12 |
| 1500plus/Post-completion WAR/1 | share | 0.3994252873563218 | 0.39100346020761245 | -0.00842182714870935 |
| 1500plus/Post-completion WAR/1 | share_among_completion_observed | absent | 0.39649122807017545 | n/a |
| 1500plus/Post-completion WAR/10 | completion_observed_wells | 167 | 115 | -52 |
| 1500plus/Post-completion WAR/10 | eligible_wells | 172 | 118 | -54 |
| 1500plus/Post-completion WAR/10 | event_wells | 137 | 90 | -47 |
| 1500plus/Post-completion WAR/10 | pre_origin_event_wells | 35 | 23 | -12 |
| 1500plus/Post-completion WAR/10 | share | 0.7965116279069767 | 0.7627118644067796 | -0.0337997635001971 |
| 1500plus/Post-completion WAR/10 | share_among_completion_observed | absent | 0.782608695652174 | n/a |
| 1500plus/Post-completion WAR/20 | completion_observed_wells | 17 | 2 | -15 |
| 1500plus/Post-completion WAR/20 | eligible_wells | 17 | 2 | -15 |
| 1500plus/Post-completion WAR/20 | event_wells | 17 | 2 | -15 |
| 1500plus/Post-completion WAR/20 | share_among_completion_observed | absent | 1.0 | n/a |
| 1500plus/Post-completion WAR/5 | completion_observed_wells | 266 | 210 | -56 |
| 1500plus/Post-completion WAR/5 | eligible_wells | 272 | 214 | -58 |
| 1500plus/Post-completion WAR/5 | event_wells | 165 | 127 | -38 |
| 1500plus/Post-completion WAR/5 | pre_origin_event_wells | 48 | 36 | -12 |
| 1500plus/Post-completion WAR/5 | share | 0.6066176470588235 | 0.5934579439252337 | -0.0131597031335898 |
| 1500plus/Post-completion WAR/5 | share_among_completion_observed | absent | 0.6047619047619047 | n/a |
| 1500plus/decline/All/1 | baseline_wells | 242 | 186 | -56 |
| 1500plus/decline/All/1 | median_relative_rate | 0.6303964139563368 | 0.6353176632965293 | +0.0049212493401925 |
| 1500plus/decline/All/1 | wells | 242 | 186 | -56 |
| 1500plus/decline/All/12 | baseline_wells | 242 | 186 | -56 |
| 1500plus/decline/All/12 | median_relative_rate | 0.8057434096194265 | 0.8738570580097177 | +0.0681136483902912 |
| 1500plus/decline/All/12 | wells | 211 | 162 | -49 |
| 1500plus/decline/All/60 | baseline_wells | 242 | 186 | -56 |
| 1500plus/decline/All/60 | median_relative_rate | 0.4356043524696771 | 0.47725476275618356 | +0.04165041028650646 |
| 1500plus/decline/All/60 | wells | 174 | 138 | -36 |
| 1500plus/decline/No subsea flag (NO)/1 | baseline_wells | 22 | 12 | -10 |
| 1500plus/decline/No subsea flag (NO)/1 | median_relative_rate | 0.5091803999055536 | 0.48596036708568924 | -0.02322003281986436 |
| 1500plus/decline/No subsea flag (NO)/1 | wells | 22 | 12 | -10 |
| 1500plus/decline/No subsea flag (NO)/12 | baseline_wells | 22 | 12 | -10 |
| 1500plus/decline/No subsea flag (NO)/12 | median_relative_rate | 0.9806081959002988 | 1.083104687328392 | +0.1024964914280932 |
| 1500plus/decline/No subsea flag (NO)/12 | wells | 21 | 12 | -9 |
| 1500plus/decline/No subsea flag (NO)/60 | baseline_wells | 22 | 12 | -10 |
| 1500plus/decline/No subsea flag (NO)/60 | median_relative_rate | 0.3437754405566681 | 0.477127399069896 | +0.1333519585132279 |
| 1500plus/decline/No subsea flag (NO)/60 | wells | 21 | 12 | -9 |
| 1500plus/decline/Subsea/1 | baseline_wells | 202 | 160 | -42 |
| 1500plus/decline/Subsea/1 | median_relative_rate | 0.6461828321925531 | 0.6502727748548779 | +0.0040899426623248 |
| 1500plus/decline/Subsea/1 | wells | 202 | 160 | -42 |
| 1500plus/decline/Subsea/12 | baseline_wells | 202 | 160 | -42 |
| 1500plus/decline/Subsea/12 | median_relative_rate | 0.794866613290811 | 0.8276547305428171 | +0.0327881172520061 |
| 1500plus/decline/Subsea/12 | wells | 177 | 141 | -36 |
| 1500plus/decline/Subsea/60 | baseline_wells | 202 | 160 | -42 |
| 1500plus/decline/Subsea/60 | median_relative_rate | 0.4467679504037092 | 0.5149930115006993 | +0.0682250610969901 |
| 1500plus/decline/Subsea/60 | wells | 143 | 116 | -27 |
| 1500plus/decline/Unknown/1 | baseline_wells | 18 | 14 | -4 |
| 1500plus/decline/Unknown/1 | median_relative_rate | 0.6595648615899816 | 0.7248497476018025 | +0.0652848860118209 |
| 1500plus/decline/Unknown/1 | wells | 18 | 14 | -4 |
| 1500plus/decline/Unknown/12 | baseline_wells | 18 | 14 | -4 |
| 1500plus/decline/Unknown/12 | median_relative_rate | 0.9326286484275813 | 1.355463815673406 | +0.4228351672458247 |
| 1500plus/decline/Unknown/12 | wells | 13 | 9 | -4 |
| 1500plus/decline/Unknown/60 | baseline_wells | 18 | 14 | -4 |
| 1500plus/lag/ordered | p75_months | 6.0 | 4.0 | -2.0 |
| 1500plus/lag/ordered | same_month_wells | 123 | 106 | -17 |
| 1500plus/lag/ordered | wells | 342 | 285 | -57 |
| 1500plus/lag/signed | p75_months | 5.5 | 4.0 | -1.5 |
| 1500plus/lag/signed | same_month_wells | 123 | 106 | -17 |
| 1500plus/lag/signed | wells | 351 | 294 | -57 |
| 1500plus/period_wells | permit_by_cutoff_share | 0.6802168021680217 | 0.6451612903225806 | -0.0350555118454411 |
| 1500plus/period_wells | permit_by_cutoff_wells | 251 | 200 | -51 |
| 1500plus/period_wells | permit_signed_event_age_median_months | 7.0 | 4.5 | -2.5 |
| 1500plus/period_wells | supported_starts | 369 | 310 | -59 |
| 1500plus/period_wells | war_by_cutoff_share | 0.6937669376693767 | 0.6612903225806451 | -0.0324766150887316 |
| 1500plus/period_wells | war_by_cutoff_wells | 256 | 205 | -51 |
| 1500plus/period_wells | war_signed_event_age_median_months | 8.0 | 5.0 | -3.0 |
| 500_1500/Intervention approval/0 | completion_observed_wells | 349 | 286 | -63 |
| 500_1500/Intervention approval/0 | eligible_wells | 396 | 300 | -96 |
| 500_1500/Intervention approval/0 | event_wells | 63 | 53 | -10 |
| 500_1500/Intervention approval/0 | pre_origin_event_wells | 42 | 34 | -8 |
| 500_1500/Intervention approval/0 | share | 0.1590909090909091 | 0.17666666666666667 | +0.01757575757575757 |
| 500_1500/Intervention approval/0 | share_among_completion_observed | absent | 0.1853146853146853 | n/a |
| 500_1500/Intervention approval/1 | completion_observed_wells | 346 | 282 | -64 |
| 500_1500/Intervention approval/1 | eligible_wells | 385 | 289 | -96 |
| 500_1500/Intervention approval/1 | event_wells | 119 | 97 | -22 |
| 500_1500/Intervention approval/1 | pre_origin_event_wells | 42 | 34 | -8 |
| 500_1500/Intervention approval/1 | share | 0.3090909090909091 | 0.3356401384083045 | +0.0265492293173954 |
| 500_1500/Intervention approval/1 | share_among_completion_observed | absent | 0.34397163120567376 | n/a |
| 500_1500/Intervention approval/10 | completion_observed_wells | 232 | 165 | -67 |
| 500_1500/Intervention approval/10 | eligible_wells | 262 | 167 | -95 |
| 500_1500/Intervention approval/10 | event_wells | 173 | 118 | -55 |
| 500_1500/Intervention approval/10 | pre_origin_event_wells | 20 | 13 | -7 |
| 500_1500/Intervention approval/10 | share | 0.6603053435114504 | 0.7065868263473054 | +0.0462814828358550 |
| 500_1500/Intervention approval/10 | share_among_completion_observed | absent | 0.7151515151515152 | n/a |
| 500_1500/Intervention approval/20 | completion_observed_wells | 46 | 7 | -39 |
| 500_1500/Intervention approval/20 | eligible_wells | 67 | 8 | -59 |
| 500_1500/Intervention approval/20 | event_wells | 43 | 6 | -37 |
| 500_1500/Intervention approval/20 | pre_origin_event_wells | 1 | 0 | -1 |
| 500_1500/Intervention approval/20 | share | 0.6417910447761194 | 0.75 | +0.1082089552238806 |
| 500_1500/Intervention approval/20 | share_among_completion_observed | absent | 0.8571428571428571 | n/a |
| 500_1500/Intervention approval/5 | completion_observed_wells | 292 | 224 | -68 |
| 500_1500/Intervention approval/5 | eligible_wells | 324 | 228 | -96 |
| 500_1500/Intervention approval/5 | event_wells | 180 | 131 | -49 |
| 500_1500/Intervention approval/5 | pre_origin_event_wells | 30 | 22 | -8 |
| 500_1500/Intervention approval/5 | share | 0.5555555555555556 | 0.5745614035087719 | +0.0190058479532163 |
| 500_1500/Intervention approval/5 | share_among_completion_observed | absent | 0.5848214285714286 | n/a |
| 500_1500/Post-completion WAR/0 | completion_observed_wells | 349 | 286 | -63 |
| 500_1500/Post-completion WAR/0 | eligible_wells | 396 | 300 | -96 |
| 500_1500/Post-completion WAR/0 | event_wells | 111 | 90 | -21 |
| 500_1500/Post-completion WAR/0 | pre_origin_event_wells | 71 | 53 | -18 |
| 500_1500/Post-completion WAR/0 | share | 0.2803030303030303 | 0.3 | +0.0196969696969697 |
| 500_1500/Post-completion WAR/0 | share_among_completion_observed | absent | 0.3146853146853147 | n/a |
| 500_1500/Post-completion WAR/1 | completion_observed_wells | 346 | 282 | -64 |
| 500_1500/Post-completion WAR/1 | eligible_wells | 385 | 289 | -96 |
| 500_1500/Post-completion WAR/1 | event_wells | 162 | 131 | -31 |
| 500_1500/Post-completion WAR/1 | pre_origin_event_wells | 70 | 52 | -18 |
| 500_1500/Post-completion WAR/1 | share | 0.42077922077922075 | 0.4532871972318339 | +0.03250797645261315 |
| 500_1500/Post-completion WAR/1 | share_among_completion_observed | absent | 0.4645390070921986 | n/a |
| 500_1500/Post-completion WAR/10 | completion_observed_wells | 232 | 165 | -67 |
| 500_1500/Post-completion WAR/10 | eligible_wells | 262 | 167 | -95 |
| 500_1500/Post-completion WAR/10 | event_wells | 195 | 136 | -59 |
| 500_1500/Post-completion WAR/10 | pre_origin_event_wells | 47 | 30 | -17 |
| 500_1500/Post-completion WAR/10 | share | 0.7442748091603053 | 0.8143712574850299 | +0.0700964483247246 |
| 500_1500/Post-completion WAR/10 | share_among_completion_observed | absent | 0.8242424242424242 | n/a |
| 500_1500/Post-completion WAR/20 | completion_observed_wells | 46 | 7 | -39 |
| 500_1500/Post-completion WAR/20 | eligible_wells | 67 | 8 | -59 |
| 500_1500/Post-completion WAR/20 | event_wells | 45 | 7 | -38 |
| 500_1500/Post-completion WAR/20 | pre_origin_event_wells | 5 | 0 | -5 |
| 500_1500/Post-completion WAR/20 | share | 0.6716417910447762 | 0.875 | +0.2033582089552238 |
| 500_1500/Post-completion WAR/20 | share_among_completion_observed | absent | 1.0 | n/a |
| 500_1500/Post-completion WAR/5 | completion_observed_wells | 292 | 224 | -68 |
| 500_1500/Post-completion WAR/5 | eligible_wells | 324 | 228 | -96 |
| 500_1500/Post-completion WAR/5 | event_wells | 206 | 151 | -55 |
| 500_1500/Post-completion WAR/5 | pre_origin_event_wells | 54 | 36 | -18 |
| 500_1500/Post-completion WAR/5 | share | 0.6358024691358025 | 0.6622807017543859 | +0.0264782326185834 |
| 500_1500/Post-completion WAR/5 | share_among_completion_observed | absent | 0.6741071428571429 | n/a |
| 500_1500/decline/All/1 | baseline_wells | 304 | 211 | -93 |
| 500_1500/decline/All/1 | median_relative_rate | 0.653682513196129 | 0.6204749398117749 | -0.0332075733843541 |
| 500_1500/decline/All/1 | wells | 304 | 211 | -93 |
| 500_1500/decline/All/12 | baseline_wells | 304 | 211 | -93 |
| 500_1500/decline/All/12 | median_relative_rate | 0.8471659012752638 | 0.877679892500969 | +0.0305139912257052 |
| 500_1500/decline/All/12 | wells | 264 | 185 | -79 |
| 500_1500/decline/All/60 | baseline_wells | 304 | 211 | -93 |
| 500_1500/decline/All/60 | median_relative_rate | 0.39052124779410957 | 0.4119341896226457 | +0.02141294182853613 |
| 500_1500/decline/All/60 | wells | 217 | 150 | -67 |
| 500_1500/decline/No subsea flag (NO)/1 | baseline_wells | 50 | 20 | -30 |
| 500_1500/decline/No subsea flag (NO)/1 | median_relative_rate | 0.5925452677493782 | 0.4186655148141524 | -0.1738797529352258 |
| 500_1500/decline/No subsea flag (NO)/1 | wells | 50 | 20 | -30 |
| 500_1500/decline/No subsea flag (NO)/12 | baseline_wells | 50 | 20 | -30 |
| 500_1500/decline/No subsea flag (NO)/12 | median_relative_rate | 0.7592571454847497 | 0.832897544461513 | +0.0736403989767633 |
| 500_1500/decline/No subsea flag (NO)/12 | wells | 44 | 20 | -24 |
| 500_1500/decline/No subsea flag (NO)/60 | baseline_wells | 50 | 20 | -30 |
| 500_1500/decline/No subsea flag (NO)/60 | median_relative_rate | 0.29714094399765645 | 0.5310857250689838 | +0.23394478107132735 |
| 500_1500/decline/No subsea flag (NO)/60 | wells | 41 | 18 | -23 |
| 500_1500/decline/Subsea/1 | baseline_wells | 207 | 179 | -28 |
| 500_1500/decline/Subsea/1 | median_relative_rate | 0.6965960199386758 | 0.6703069350892275 | -0.0262890848494483 |
| 500_1500/decline/Subsea/1 | wells | 207 | 179 | -28 |
| 500_1500/decline/Subsea/12 | baseline_wells | 207 | 179 | -28 |
| 500_1500/decline/Subsea/12 | median_relative_rate | 0.8813719862565155 | 0.8733349664489651 | -0.0080370198075504 |
| 500_1500/decline/Subsea/12 | wells | 178 | 154 | -24 |
| 500_1500/decline/Subsea/60 | baseline_wells | 207 | 179 | -28 |
| 500_1500/decline/Subsea/60 | median_relative_rate | 0.3905595367323405 | 0.3881728208619144 | -0.0023867158704261 |
| 500_1500/decline/Subsea/60 | wells | 146 | 124 | -22 |
| 500_1500/decline/Unknown/1 | baseline_wells | 47 | 12 | -35 |
| 500_1500/decline/Unknown/1 | median_relative_rate | 0.7562708965960013 | 0.5291848450970237 | -0.2270860514989776 |
| 500_1500/decline/Unknown/1 | wells | 47 | 12 | -35 |
| 500_1500/decline/Unknown/12 | baseline_wells | 47 | 12 | -35 |
| 500_1500/decline/Unknown/12 | median_relative_rate | 0.8382065083412151 | 1.4499711671227087 | +0.6117646587814936 |
| 500_1500/decline/Unknown/12 | wells | 42 | 11 | -31 |
| 500_1500/decline/Unknown/60 | baseline_wells | 47 | 12 | -35 |
| 500_1500/decline/Unknown/60 | median_relative_rate | 0.44527868459706144 | 1.5636989352468218 | +1.11842025064976036 |
| 500_1500/decline/Unknown/60 | wells | 30 | 8 | -22 |
| 500_1500/lag/ordered | p75_months | 5.0 | 6.0 | +1.0 |
| 500_1500/lag/ordered | same_month_wells | 128 | 101 | -27 |
| 500_1500/lag/ordered | wells | 337 | 281 | -56 |
| 500_1500/lag/signed | pre_completion_wells | 20 | 8 | -12 |
| 500_1500/lag/signed | same_month_wells | 128 | 101 | -27 |
| 500_1500/lag/signed | wells | 357 | 289 | -68 |
| 500_1500/period_wells | permit_by_cutoff_share | 0.696969696969697 | 0.6866666666666666 | -0.0103030303030304 |
| 500_1500/period_wells | permit_by_cutoff_wells | 276 | 206 | -70 |
| 500_1500/period_wells | permit_signed_event_age_median_months | 18.0 | 14.5 | -3.5 |
| 500_1500/period_wells | supported_starts | 396 | 300 | -96 |
| 500_1500/period_wells | war_by_cutoff_share | 0.7727272727272727 | 0.7733333333333333 | +0.0006060606060606 |
| 500_1500/period_wells | war_by_cutoff_wells | 306 | 232 | -74 |
| 500_1500/period_wells | war_signed_event_age_median_months | 9.0 | 5.0 | -4.0 |
| all/Intervention approval/0 | completion_observed_wells | 2262 | 1725 | -537 |
| all/Intervention approval/0 | eligible_wells | 2514 | 1813 | -701 |
| all/Intervention approval/0 | event_wells | 505 | 380 | -125 |
| all/Intervention approval/0 | pre_origin_event_wells | 336 | 240 | -96 |
| all/Intervention approval/0 | share | 0.20087509944311854 | 0.20959735245449532 | +0.00872225301137678 |
| all/Intervention approval/0 | share_among_completion_observed | absent | 0.22028985507246376 | n/a |
| all/Intervention approval/1 | completion_observed_wells | 2250 | 1709 | -541 |
| all/Intervention approval/1 | eligible_wells | 2479 | 1778 | -701 |
| all/Intervention approval/1 | event_wells | 982 | 741 | -241 |
| all/Intervention approval/1 | pre_origin_event_wells | 334 | 238 | -96 |
| all/Intervention approval/1 | share | 0.3961274707543364 | 0.4167604049493813 | +0.0206329341950449 |
| all/Intervention approval/1 | share_among_completion_observed | absent | 0.43358689291983615 | n/a |
| all/Intervention approval/10 | completion_observed_wells | 1863 | 1335 | -528 |
| all/Intervention approval/10 | eligible_wells | 2067 | 1387 | -680 |
| all/Intervention approval/10 | event_wells | 1454 | 1024 | -430 |
| all/Intervention approval/10 | pre_origin_event_wells | 269 | 175 | -94 |
| all/Intervention approval/10 | share | 0.7034349298500242 | 0.738284066330209 | +0.0348491364801848 |
| all/Intervention approval/10 | share_among_completion_observed | absent | 0.7670411985018727 | n/a |
| all/Intervention approval/20 | completion_observed_wells | 492 | 257 | -235 |
| all/Intervention approval/20 | eligible_wells | 643 | 298 | -345 |
| all/Intervention approval/20 | event_wells | 426 | 212 | -214 |
| all/Intervention approval/20 | pre_origin_event_wells | 64 | 29 | -35 |
| all/Intervention approval/20 | share | 0.6625194401244168 | 0.7114093959731543 | +0.0488899558487375 |
| all/Intervention approval/20 | share_among_completion_observed | absent | 0.8249027237354085 | n/a |
| all/Intervention approval/5 | completion_observed_wells | 2098 | 1552 | -546 |
| all/Intervention approval/5 | eligible_wells | 2306 | 1607 | -699 |
| all/Intervention approval/5 | event_wells | 1423 | 1036 | -387 |
| all/Intervention approval/5 | pre_origin_event_wells | 299 | 203 | -96 |
| all/Intervention approval/5 | share | 0.6170858629661752 | 0.6446795270690728 | +0.0275936641028976 |
| all/Intervention approval/5 | share_among_completion_observed | absent | 0.6675257731958762 | n/a |
| all/Post-completion WAR/0 | completion_observed_wells | 2262 | 1725 | -537 |
| all/Post-completion WAR/0 | eligible_wells | 2514 | 1813 | -701 |
| all/Post-completion WAR/0 | event_wells | 634 | 447 | -187 |
| all/Post-completion WAR/0 | pre_origin_event_wells | 444 | 297 | -147 |
| all/Post-completion WAR/0 | share | 0.25218774860779636 | 0.2465526751241037 | -0.00563507348369266 |
| all/Post-completion WAR/0 | share_among_completion_observed | absent | 0.2591304347826087 | n/a |
| all/Post-completion WAR/1 | completion_observed_wells | 2250 | 1709 | -541 |
| all/Post-completion WAR/1 | eligible_wells | 2479 | 1778 | -701 |
| all/Post-completion WAR/1 | event_wells | 983 | 719 | -264 |
| all/Post-completion WAR/1 | pre_origin_event_wells | 439 | 292 | -147 |
| all/Post-completion WAR/1 | share | 0.39653085921742637 | 0.4043869516310461 | +0.00785609241361973 |
| all/Post-completion WAR/1 | share_among_completion_observed | absent | 0.42071386775892333 | n/a |
| all/Post-completion WAR/10 | completion_observed_wells | 1863 | 1335 | -528 |
| all/Post-completion WAR/10 | eligible_wells | 2067 | 1387 | -680 |
| all/Post-completion WAR/10 | event_wells | 1614 | 1155 | -459 |
| all/Post-completion WAR/10 | pre_origin_event_wells | 362 | 218 | -144 |
| all/Post-completion WAR/10 | share | 0.7808417997097242 | 0.832732516222062 | +0.0518907165123378 |
| all/Post-completion WAR/10 | share_among_completion_observed | absent | 0.8651685393258427 | n/a |
| all/Post-completion WAR/20 | completion_observed_wells | 492 | 257 | -235 |
| all/Post-completion WAR/20 | eligible_wells | 643 | 298 | -345 |
| all/Post-completion WAR/20 | event_wells | 481 | 254 | -227 |
| all/Post-completion WAR/20 | pre_origin_event_wells | 80 | 29 | -51 |
| all/Post-completion WAR/20 | share | 0.7480559875583204 | 0.8523489932885906 | +0.1042930057302702 |
| all/Post-completion WAR/20 | share_among_completion_observed | absent | 0.9883268482490273 | n/a |
| all/Post-completion WAR/5 | completion_observed_wells | 2098 | 1552 | -546 |
| all/Post-completion WAR/5 | eligible_wells | 2306 | 1607 | -699 |
| all/Post-completion WAR/5 | event_wells | 1503 | 1093 | -410 |
| all/Post-completion WAR/5 | pre_origin_event_wells | 392 | 245 | -147 |
| all/Post-completion WAR/5 | share | 0.6517779705117086 | 0.6801493466085874 | +0.0283713760968788 |
| all/Post-completion WAR/5 | share_among_completion_observed | absent | 0.7042525773195877 | n/a |
| all/decline/All/1 | baseline_wells | 1926 | 1333 | -593 |
| all/decline/All/1 | median_relative_rate | 0.6663887565507385 | 0.6554214251128525 | -0.0109673314378860 |
| all/decline/All/1 | wells | 1921 | 1328 | -593 |
| all/decline/All/12 | baseline_wells | 1926 | 1333 | -593 |
| all/decline/All/12 | median_relative_rate | 0.603035538005923 | 0.6336042243560371 | +0.0305686863501141 |
| all/decline/All/12 | wells | 1597 | 1130 | -467 |
| all/decline/All/60 | baseline_wells | 1926 | 1333 | -593 |
| all/decline/All/60 | median_relative_rate | 0.24791473586654306 | 0.2678890174070742 | +0.01997428154053114 |
| all/decline/All/60 | wells | 1225 | 871 | -354 |
| all/decline/No subsea flag (NO)/1 | baseline_wells | 1209 | 861 | -348 |
| all/decline/No subsea flag (NO)/1 | median_relative_rate | 0.6561007602396441 | 0.6653240359073913 | +0.0092232756677472 |
| all/decline/No subsea flag (NO)/1 | wells | 1204 | 856 | -348 |
| all/decline/No subsea flag (NO)/12 | baseline_wells | 1209 | 861 | -348 |
| all/decline/No subsea flag (NO)/12 | median_relative_rate | 0.5130003924646782 | 0.5282209460190219 | +0.0152205535543437 |
| all/decline/No subsea flag (NO)/12 | wells | 1013 | 734 | -279 |
| all/decline/No subsea flag (NO)/60 | baseline_wells | 1209 | 861 | -348 |
| all/decline/No subsea flag (NO)/60 | median_relative_rate | 0.19205330564430853 | 0.19713709711843594 | +0.00508379147412741 |
| all/decline/No subsea flag (NO)/60 | wells | 794 | 564 | -230 |
| all/decline/Subsea/1 | baseline_wells | 452 | 379 | -73 |
| all/decline/Subsea/1 | median_relative_rate | 0.6529731537148531 | 0.6533732616634171 | +0.0004001079485640 |
| all/decline/Subsea/1 | wells | 452 | 379 | -73 |
| all/decline/Subsea/12 | baseline_wells | 452 | 379 | -73 |
| all/decline/Subsea/12 | median_relative_rate | 0.8273364049722798 | 0.8377411194022683 | +0.0104047144299885 |
| all/decline/Subsea/12 | wells | 388 | 325 | -63 |
| all/decline/Subsea/60 | baseline_wells | 452 | 379 | -73 |
| all/decline/Subsea/60 | median_relative_rate | 0.43850461975060434 | 0.44541084957622357 | +0.00690622982561923 |
| all/decline/Subsea/60 | wells | 308 | 257 | -51 |
| all/decline/Unknown/1 | baseline_wells | 265 | 93 | -172 |
| all/decline/Unknown/1 | median_relative_rate | 0.7562708965960013 | 0.5693914440650732 | -0.1868794525309281 |
| all/decline/Unknown/1 | wells | 265 | 93 | -172 |
| all/decline/Unknown/12 | baseline_wells | 265 | 93 | -172 |
| all/decline/Unknown/12 | median_relative_rate | 0.5369277909740318 | 0.6879615202222072 | +0.1510337292481754 |
| all/decline/Unknown/12 | wells | 196 | 71 | -125 |
| all/decline/Unknown/60 | baseline_wells | 265 | 93 | -172 |
| all/decline/Unknown/60 | median_relative_rate | 0.20922481112310332 | 0.1983185030725605 | -0.01090630805054282 |
| all/decline/Unknown/60 | wells | 123 | 50 | -73 |
| all/lag/ordered | same_month_wells | 812 | 612 | -200 |
| all/lag/ordered | wells | 2132 | 1704 | -428 |
| all/lag/signed | pre_completion_wells | 51 | 31 | -20 |
| all/lag/signed | same_month_wells | 812 | 612 | -200 |
| all/lag/signed | wells | 2183 | 1735 | -448 |
| all/period_wells | permit_by_cutoff_share | 0.713206046141607 | 0.7291781577495863 | +0.0159721116079793 |
| all/period_wells | permit_by_cutoff_wells | 1793 | 1322 | -471 |
| all/period_wells | permit_signed_event_age_median_months | 9.0 | 8.0 | -1.0 |
| all/period_wells | supported_starts | 2514 | 1813 | -701 |
| all/period_wells | war_by_cutoff_share | 0.8062848050914877 | 0.8345284059569774 | +0.0282436008654897 |
| all/period_wells | war_by_cutoff_wells | 2027 | 1513 | -514 |
| all/period_wells | war_signed_event_age_median_months | 13.0 | 14.0 | +1.0 |
| audit/Article summary \| assigned band, completion cohort API10/kept/retained | rows | absent | 2873 | n/a |
| audit/Article summary \| assigned band, completion cohort API10/read/input | rows | absent | 2873 | n/a |
| audit/Article summary \| completion window, API10/dropped/first C after 2025 | rows | absent | 33 | n/a |
| audit/Article summary \| completion window, API10/dropped/first C before 2005 | rows | absent | 2084 | n/a |
| audit/Article summary \| completion window, API10/dropped/no dated C completion | rows | absent | 34580 | n/a |
| audit/Article summary \| completion window, API10/kept/retained | rows | absent | 2873 | n/a |
| audit/Article summary \| completion window, API10/read/input | rows | absent | 39570 | n/a |
| audit/Article summary \| permit_date by cutoff, inventory API10/dropped/no dated qualifying event | rows | absent | 35444 | n/a |
| audit/Article summary \| permit_date by cutoff, inventory API10/dropped/no positive joined OGOR month | rows | absent | 155 | n/a |
| audit/Article summary \| permit_date by cutoff, inventory API10/dropped/unsupported production start | rows | absent | 2649 | n/a |
| audit/Article summary \| permit_date by cutoff, inventory API10/kept/retained | rows | absent | 1322 | n/a |
| audit/Article summary \| permit_date by cutoff, inventory API10/read/input | rows | absent | 39570 | n/a |
| audit/Article summary \| war_date by cutoff, inventory API10/dropped/no dated qualifying event | rows | absent | 34993 | n/a |
| audit/Article summary \| war_date by cutoff, inventory API10/dropped/no positive joined OGOR month | rows | absent | 216 | n/a |
| audit/Article summary \| war_date by cutoff, inventory API10/dropped/unsupported production start | rows | absent | 2848 | n/a |
| audit/Article summary \| war_date by cutoff, inventory API10/kept/retained | rows | absent | 1513 | n/a |
| audit/Article summary \| war_date by cutoff, inventory API10/read/input | rows | absent | 39570 | n/a |
| audit/Borehole inventory \| assigned depth, API10/dropped/cancelled_only | rows | absent | 762 | n/a |
| audit/Borehole inventory \| assigned depth, API10/dropped/outside_gulf | rows | absent | 1279 | n/a |
| audit/Borehole inventory \| assigned depth, API10/dropped/unresolved depth | rows | absent | 7 | n/a |
| audit/Borehole inventory \| assigned depth, API10/kept/retained | rows | absent | 37522 | n/a |
| audit/Borehole inventory \| assigned depth, API10/read/input | rows | absent | 39570 | n/a |
| audit/Borehole quality \| all bores on Gulf inventory wells, spud, API10/kept/retained | rows | absent | 37529 | n/a |
| audit/Borehole quality \| all bores on Gulf inventory wells, spud, API10/read/input | rows | absent | 37529 | n/a |
| audit/Borehole quality \| non-cancelled Gulf bores, depth, API10/kept/retained | rows | absent | 37529 | n/a |
| audit/Borehole quality \| non-cancelled Gulf bores, depth, API10/read/input | rows | absent | 37529 | n/a |
| audit/Completion lag \| chronological pair, API10/dropped/first production month before first C month | rows | 51 | 31 | -20 |
| audit/Completion lag \| chronological pair, API10/kept/retained | rows | 2132 | 1704 | -428 |
| audit/Completion lag \| chronological pair, API10/read/input | rows | 2183 | 1735 | -448 |
| audit/Completion lag \| completion window, API10/dropped/first C after 2025 | rows | absent | 33 | n/a |
| audit/Completion lag \| completion window, API10/dropped/first C before 2005 | rows | absent | 2084 | n/a |
| audit/Completion lag \| completion window, API10/dropped/no dated C completion | rows | absent | 34580 | n/a |
| audit/Completion lag \| completion window, API10/kept/retained | rows | absent | 2873 | n/a |
| audit/Completion lag \| completion window, API10/read/input | rows | absent | 39570 | n/a |
| audit/Completion lag \| first C dated 2005–2025, API10/dropped/start coverage unestablished | rows | 5 | 453 | +448 |
| audit/Completion lag \| first C dated 2005–2025, API10/kept/retained | rows | 2183 | 1735 | -448 |
| audit/Decline \| baseline eligibility, well-months/dropped/well excluded from baseline | rows | absent | 13485 | n/a |
| audit/Decline \| baseline eligibility, well-months/kept/retained | rows | absent | 76884 | n/a |
| audit/Decline \| baseline eligibility, well-months/read/input | rows | absent | 90369 | n/a |
| audit/Decline \| calendar ages 1–60, well-months/dropped/after month 60 | rows | absent | 114885 | n/a |
| audit/Decline \| calendar ages 1–60, well-months/dropped/before first positive month | rows | absent | 14496 | n/a |
| audit/Decline \| calendar ages 1–60, well-months/kept/retained | rows | absent | 90369 | n/a |
| audit/Decline \| calendar ages 1–60, well-months/read/input | rows | absent | 219750 | n/a |
| audit/Decline \| first three months for baseline, well-months/dropped/after baseline window | rows | absent | 85640 | n/a |
| audit/Decline \| first three months for baseline, well-months/kept/retained | rows | absent | 4729 | n/a |
| audit/Decline \| first three months for baseline, well-months/read/input | rows | absent | 90369 | n/a |
| audit/Decline \| join to start cohort, well-months/dropped/outside supported 2005–2020 start cohort | rows | absent | 2249482 | n/a |
| audit/Decline \| join to start cohort, well-months/kept/retained | rows | absent | 219750 | n/a |
| audit/Decline \| join to start cohort, well-months/read/input | rows | absent | 2469232 | n/a |
| audit/Decline \| observed baseline-eligible well-month records, ages 1–60/dropped/no usable producing-day rate | rows | 24110 | 15300 | -8810 |
| audit/Decline \| observed baseline-eligible well-month records, ages 1–60/kept/retained | rows | 86920 | 61584 | -25336 |
| audit/Decline \| observed baseline-eligible well-month records, ages 1–60/read/input | rows | 111030 | 76884 | -34146 |
| audit/Decline \| start window, supported API10/dropped/first positive month outside 2005–2020 | rows | absent | 236 | n/a |
| audit/Decline \| start window, supported API10/kept/retained | rows | absent | 1577 | n/a |
| audit/Decline \| start window, supported API10/read/input | rows | absent | 1813 | n/a |
| audit/Decline \| supported first production 2005–2020, API10/dropped/no positive measurable oil rate in first three calendar months | rows | 239 | 158 | -81 |
| audit/Decline \| supported first production 2005–2020, API10/dropped/positive oil but producing-day rate unresolved in first three months | rows | 109 | 86 | -23 |
| audit/Decline \| supported first production 2005–2020, API10/kept/retained | rows | 1926 | 1333 | -593 |
| audit/Decline \| supported first production 2005–2020, API10/read/input | rows | 2274 | 1577 | -697 |
| audit/First positive month \| API10 start evidence/dropped/earliest bore spud predates January 2005 | rows | absent | 710 | n/a |
| audit/First positive month \| API10 start evidence/dropped/no timely in-window spud or reported start | rows | 9 | absent | n/a |
| audit/First positive month \| API10 start evidence/kept/retained | rows | 2514 | 1813 | -701 |
| audit/Interventions \| supported starts, API10/dropped/unsupported start | rows | absent | 7712 | n/a |
| audit/Interventions \| supported starts, API10/kept/retained | rows | absent | 1813 | n/a |
| audit/Interventions \| supported starts, API10/read/input | rows | absent | 9525 | n/a |
| audit/Interventions \| year 0 anniversary, API10/kept/retained | rows | absent | 1813 | n/a |
| audit/Interventions \| year 0 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 1 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 35 | n/a |
| audit/Interventions \| year 1 anniversary, API10/kept/retained | rows | absent | 1778 | n/a |
| audit/Interventions \| year 1 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 10 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 426 | n/a |
| audit/Interventions \| year 10 anniversary, API10/kept/retained | rows | absent | 1387 | n/a |
| audit/Interventions \| year 10 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 11 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 487 | n/a |
| audit/Interventions \| year 11 anniversary, API10/kept/retained | rows | absent | 1326 | n/a |
| audit/Interventions \| year 11 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 12 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 576 | n/a |
| audit/Interventions \| year 12 anniversary, API10/kept/retained | rows | absent | 1237 | n/a |
| audit/Interventions \| year 12 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 13 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 661 | n/a |
| audit/Interventions \| year 13 anniversary, API10/kept/retained | rows | absent | 1152 | n/a |
| audit/Interventions \| year 13 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 14 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 718 | n/a |
| audit/Interventions \| year 14 anniversary, API10/kept/retained | rows | absent | 1095 | n/a |
| audit/Interventions \| year 14 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 15 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 793 | n/a |
| audit/Interventions \| year 15 anniversary, API10/kept/retained | rows | absent | 1020 | n/a |
| audit/Interventions \| year 15 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 16 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 861 | n/a |
| audit/Interventions \| year 16 anniversary, API10/kept/retained | rows | absent | 952 | n/a |
| audit/Interventions \| year 16 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 17 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 950 | n/a |
| audit/Interventions \| year 17 anniversary, API10/kept/retained | rows | absent | 863 | n/a |
| audit/Interventions \| year 17 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 18 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 1103 | n/a |
| audit/Interventions \| year 18 anniversary, API10/kept/retained | rows | absent | 710 | n/a |
| audit/Interventions \| year 18 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 19 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 1277 | n/a |
| audit/Interventions \| year 19 anniversary, API10/kept/retained | rows | absent | 536 | n/a |
| audit/Interventions \| year 19 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 2 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 76 | n/a |
| audit/Interventions \| year 2 anniversary, API10/kept/retained | rows | absent | 1737 | n/a |
| audit/Interventions \| year 2 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 20 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 1515 | n/a |
| audit/Interventions \| year 20 anniversary, API10/kept/retained | rows | absent | 298 | n/a |
| audit/Interventions \| year 20 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 21 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 1731 | n/a |
| audit/Interventions \| year 21 anniversary, API10/kept/retained | rows | absent | 82 | n/a |
| audit/Interventions \| year 21 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 3 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 118 | n/a |
| audit/Interventions \| year 3 anniversary, API10/kept/retained | rows | absent | 1695 | n/a |
| audit/Interventions \| year 3 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 4 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 168 | n/a |
| audit/Interventions \| year 4 anniversary, API10/kept/retained | rows | absent | 1645 | n/a |
| audit/Interventions \| year 4 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 5 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 206 | n/a |
| audit/Interventions \| year 5 anniversary, API10/kept/retained | rows | absent | 1607 | n/a |
| audit/Interventions \| year 5 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 6 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 239 | n/a |
| audit/Interventions \| year 6 anniversary, API10/kept/retained | rows | absent | 1574 | n/a |
| audit/Interventions \| year 6 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 7 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 280 | n/a |
| audit/Interventions \| year 7 anniversary, API10/kept/retained | rows | absent | 1533 | n/a |
| audit/Interventions \| year 7 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 8 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 328 | n/a |
| audit/Interventions \| year 8 anniversary, API10/kept/retained | rows | absent | 1485 | n/a |
| audit/Interventions \| year 8 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/Interventions \| year 9 anniversary, API10/dropped/anniversary after production cutoff | rows | absent | 384 | n/a |
| audit/Interventions \| year 9 anniversary, API10/kept/retained | rows | absent | 1429 | n/a |
| audit/Interventions \| year 9 anniversary, API10/read/input | rows | absent | 1813 | n/a |
| audit/OGOR raw recount / 2026-08/dropped/outside classified Gulf inventory | rows | absent | 1 | n/a |
| audit/OGOR raw recount / 2026-08/kept/retained | rows | absent | 4457 | n/a |
| audit/OGOR raw recount / 2026-08/read/input | rows | absent | 4458 | n/a |
| audit/OGOR raw recount / 2026-09/kept/retained | rows | absent | 2688 | n/a |
| audit/OGOR raw recount / 2026-09/read/input | rows | absent | 2688 | n/a |
| audit/OGOR well-months / producing activity/dropped/no positive net oil or gas | rows | absent | 1642200 | n/a |
| audit/OGOR well-months / producing activity/kept/retained | rows | absent | 827032 | n/a |
| audit/OGOR well-months / producing activity/read/input | rows | absent | 2469232 | n/a |
| audit/borehole rows for Gulf depth and spud/dropped/cancelled bore | rows | 994 | absent | n/a |
| audit/borehole rows for Gulf depth and spud/dropped/region outside or unresolved | rows | 1934 | absent | n/a |
| audit/borehole rows for Gulf depth and spud/kept/retained | rows | 54592 | absent | n/a |
| audit/borehole rows for Gulf depth and spud/read/input | rows | 57520 | absent | n/a |
| audit/borehole rows for Gulf depth/dropped/cancelled bore | rows | absent | 994 | n/a |
| audit/borehole rows for Gulf depth/dropped/region outside or unresolved | rows | absent | 1934 | n/a |
| audit/borehole rows for Gulf depth/kept/retained | rows | absent | 54592 | n/a |
| audit/borehole rows for Gulf depth/read/input | rows | absent | 57520 | n/a |
| audit/eWell APM approvals for classified well work/dropped/event after production cutoff | rows | absent | 130 | n/a |
| audit/eWell APM approvals for classified well work/dropped/no dated C completion | rows | 9331 | 9283 | -48 |
| audit/eWell APM approvals for classified well work/kept/retained | rows | 19997 | 19915 | -82 |
| audit/eWell WAR rows for observed work/dropped/event after production cutoff | rows | absent | 858 | n/a |
| audit/eWell WAR rows for observed work/dropped/no dated C completion | rows | 230900 | 230336 | -564 |
| audit/eWell WAR rows for observed work/kept/retained | rows | 77963 | 77669 | -294 |
| under100/Intervention approval/0 | completion_observed_wells | 1388 | 1016 | -372 |
| under100/Intervention approval/0 | eligible_wells | 1554 | 1075 | -479 |
| under100/Intervention approval/0 | event_wells | 339 | 242 | -97 |
| under100/Intervention approval/0 | pre_origin_event_wells | 226 | 151 | -75 |
| under100/Intervention approval/0 | share | 0.21814671814671815 | 0.22511627906976744 | +0.00696956092304929 |
| under100/Intervention approval/0 | share_among_completion_observed | absent | 0.23818897637795275 | n/a |
| under100/Intervention approval/1 | completion_observed_wells | 1393 | 1018 | -375 |
| under100/Intervention approval/1 | eligible_wells | 1552 | 1073 | -479 |
| under100/Intervention approval/1 | event_wells | 649 | 475 | -174 |
| under100/Intervention approval/1 | pre_origin_event_wells | 226 | 151 | -75 |
| under100/Intervention approval/1 | share | 0.4181701030927835 | 0.4426840633737186 | +0.0245139602809351 |
| under100/Intervention approval/1 | share_among_completion_observed | absent | 0.46660117878192536 | n/a |
| under100/Intervention approval/10 | completion_observed_wells | 1326 | 957 | -369 |
| under100/Intervention approval/10 | eligible_wells | 1471 | 1002 | -469 |
| under100/Intervention approval/10 | event_wells | 1044 | 746 | -298 |
| under100/Intervention approval/10 | pre_origin_event_wells | 219 | 144 | -75 |
| under100/Intervention approval/10 | share | 0.7097212780421482 | 0.7445109780439122 | +0.0347897000017640 |
| under100/Intervention approval/10 | share_among_completion_observed | absent | 0.7795193312434692 | n/a |
| under100/Intervention approval/20 | completion_observed_wells | 392 | 227 | -165 |
| under100/Intervention approval/20 | eligible_wells | 503 | 265 | -238 |
| under100/Intervention approval/20 | event_wells | 332 | 185 | -147 |
| under100/Intervention approval/20 | pre_origin_event_wells | 63 | 29 | -34 |
| under100/Intervention approval/20 | share | 0.6600397614314115 | 0.6981132075471698 | +0.0380734461157583 |
| under100/Intervention approval/20 | share_among_completion_observed | absent | 0.8149779735682819 | n/a |
| under100/Intervention approval/5 | completion_observed_wells | 1377 | 999 | -378 |
| under100/Intervention approval/5 | eligible_wells | 1523 | 1044 | -479 |
| under100/Intervention approval/5 | event_wells | 977 | 703 | -274 |
| under100/Intervention approval/5 | pre_origin_event_wells | 223 | 148 | -75 |
| under100/Intervention approval/5 | share | 0.6414970453053185 | 0.6733716475095786 | +0.0318746022042601 |
| under100/Intervention approval/5 | share_among_completion_observed | absent | 0.7037037037037037 | n/a |
| under100/Post-completion WAR/0 | completion_observed_wells | 1388 | 1016 | -372 |
| under100/Post-completion WAR/0 | eligible_wells | 1554 | 1075 | -479 |
| under100/Post-completion WAR/0 | event_wells | 367 | 233 | -134 |
| under100/Post-completion WAR/0 | pre_origin_event_wells | 262 | 158 | -104 |
| under100/Post-completion WAR/0 | share | 0.23616473616473616 | 0.21674418604651163 | -0.01942055011822453 |
| under100/Post-completion WAR/0 | share_among_completion_observed | absent | 0.22933070866141733 | n/a |
| under100/Post-completion WAR/1 | completion_observed_wells | 1393 | 1018 | -375 |
| under100/Post-completion WAR/1 | eligible_wells | 1552 | 1073 | -479 |
| under100/Post-completion WAR/1 | event_wells | 592 | 412 | -180 |
| under100/Post-completion WAR/1 | pre_origin_event_wells | 262 | 158 | -104 |
| under100/Post-completion WAR/1 | share | 0.38144329896907214 | 0.38397017707362535 | +0.00252687810455321 |
| under100/Post-completion WAR/1 | share_among_completion_observed | absent | 0.40471512770137524 | n/a |
| under100/Post-completion WAR/10 | completion_observed_wells | 1326 | 957 | -369 |
| under100/Post-completion WAR/10 | eligible_wells | 1471 | 1002 | -469 |
| under100/Post-completion WAR/10 | event_wells | 1160 | 843 | -317 |
| under100/Post-completion WAR/10 | pre_origin_event_wells | 250 | 147 | -103 |
| under100/Post-completion WAR/10 | share | 0.7885791978246091 | 0.8413173652694611 | +0.0527381674448520 |
| under100/Post-completion WAR/10 | share_among_completion_observed | absent | 0.8808777429467085 | n/a |
| under100/Post-completion WAR/20 | completion_observed_wells | 392 | 227 | -165 |
| under100/Post-completion WAR/20 | eligible_wells | 503 | 265 | -238 |
| under100/Post-completion WAR/20 | event_wells | 382 | 224 | -158 |
| under100/Post-completion WAR/20 | pre_origin_event_wells | 71 | 27 | -44 |
| under100/Post-completion WAR/20 | share | 0.7594433399602386 | 0.8452830188679246 | +0.0858396789076860 |
| under100/Post-completion WAR/20 | share_among_completion_observed | absent | 0.986784140969163 | n/a |
| under100/Post-completion WAR/5 | completion_observed_wells | 1377 | 999 | -378 |
| under100/Post-completion WAR/5 | eligible_wells | 1523 | 1044 | -479 |
| under100/Post-completion WAR/5 | event_wells | 1013 | 729 | -284 |
| under100/Post-completion WAR/5 | pre_origin_event_wells | 257 | 153 | -104 |
| under100/Post-completion WAR/5 | share | 0.6651346027577151 | 0.6982758620689655 | +0.0331412593112504 |
| under100/Post-completion WAR/5 | share_among_completion_observed | absent | 0.7297297297297297 | n/a |
| under100/decline/All/1 | baseline_wells | 1212 | 824 | -388 |
| under100/decline/All/1 | median_relative_rate | 0.6696052261871311 | 0.6634146341463415 | -0.0061905920407896 |
| under100/decline/All/1 | wells | 1207 | 819 | -388 |
| under100/decline/All/12 | baseline_wells | 1212 | 824 | -388 |
| under100/decline/All/12 | median_relative_rate | 0.4814647377938517 | 0.505315344882074 | +0.0238506070882223 |
| under100/decline/All/12 | wells | 983 | 688 | -295 |
| under100/decline/All/60 | baseline_wells | 1212 | 824 | -388 |
| under100/decline/All/60 | median_relative_rate | 0.18270508710315012 | 0.1867335829734289 | +0.00402849587027878 |
| under100/decline/All/60 | wells | 714 | 499 | -215 |
| under100/decline/No subsea flag (NO)/1 | baseline_wells | 1015 | 742 | -273 |
| under100/decline/No subsea flag (NO)/1 | median_relative_rate | 0.66640173529225 | 0.6715274625510667 | +0.0051257272588167 |
| under100/decline/No subsea flag (NO)/1 | wells | 1010 | 737 | -273 |
| under100/decline/No subsea flag (NO)/12 | baseline_wells | 1015 | 742 | -273 |
| under100/decline/No subsea flag (NO)/12 | median_relative_rate | 0.4862030343142246 | 0.5102178004840011 | +0.0240147661697765 |
| under100/decline/No subsea flag (NO)/12 | wells | 841 | 625 | -216 |
| under100/decline/No subsea flag (NO)/60 | baseline_wells | 1015 | 742 | -273 |
| under100/decline/No subsea flag (NO)/60 | median_relative_rate | 0.1855737757051021 | 0.1894001576636396 | +0.0038263819585375 |
| under100/decline/No subsea flag (NO)/60 | wells | 640 | 466 | -174 |
| under100/decline/Subsea/1 | baseline_wells | 21 | 20 | -1 |
| under100/decline/Subsea/1 | median_relative_rate | 0.5008130081300813 | 0.4803427153096631 | -0.0204702928204182 |
| under100/decline/Subsea/1 | wells | 21 | 20 | -1 |
| under100/decline/Subsea/12 | baseline_wells | 21 | 20 | -1 |
| under100/decline/Subsea/12 | median_relative_rate | 0.3915117618029281 | 0.3829256488775725 | -0.0085861129253556 |
| under100/decline/Subsea/12 | wells | 17 | 16 | -1 |
| under100/decline/Subsea/60 | baseline_wells | 21 | 20 | -1 |
| under100/decline/Subsea/60 | median_relative_rate | 0.35109698100962655 | 0.5853322304935208 | +0.23423524948389425 |
| under100/decline/Subsea/60 | wells | 6 | 5 | -1 |
| under100/decline/Unknown/1 | baseline_wells | 176 | 62 | -114 |
| under100/decline/Unknown/1 | median_relative_rate | 0.757402748533894 | 0.5678296353422287 | -0.1895731131916653 |
| under100/decline/Unknown/1 | wells | 176 | 62 | -114 |
| under100/decline/Unknown/12 | baseline_wells | 176 | 62 | -114 |
| under100/decline/Unknown/12 | median_relative_rate | 0.4120879120879121 | 0.3899207125013577 | -0.0221671995865544 |
| under100/decline/Unknown/12 | wells | 125 | 47 | -78 |
| under100/decline/Unknown/60 | baseline_wells | 176 | 62 | -114 |
| under100/decline/Unknown/60 | median_relative_rate | 0.15932561175520077 | 0.09253675974639147 | -0.06678885200880930 |
| under100/decline/Unknown/60 | wells | 68 | 28 | -40 |
| under100/lag/ordered | same_month_wells | 466 | 334 | -132 |
| under100/lag/ordered | wells | 1295 | 1014 | -281 |
| under100/lag/signed | pre_completion_wells | 20 | 13 | -7 |
| under100/lag/signed | same_month_wells | 466 | 334 | -132 |
| under100/lag/signed | wells | 1315 | 1027 | -288 |
| under100/period_wells | permit_by_cutoff_share | 0.722007722007722 | 0.7553488372093023 | +0.0333411152015803 |
| under100/period_wells | permit_by_cutoff_wells | 1122 | 812 | -310 |
| under100/period_wells | supported_starts | 1554 | 1075 | -479 |
| under100/period_wells | war_by_cutoff_share | 0.8416988416988417 | 0.893953488372093 | +0.0522546466732513 |
| under100/period_wells | war_by_cutoff_wells | 1308 | 961 | -347 |
| under100/period_wells | war_signed_event_age_median_months | 16.0 | 18.0 | +2.0 |

*Table 4. Every changed, added and removed headline field, including the dispositions in the record-count ledger.*
