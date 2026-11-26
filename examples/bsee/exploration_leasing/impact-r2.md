# Impact of the second exploration leasing derivation

Baseline `aef6d6c`, using the four archive digests in [source_pins.json](source_pins.json). [Pre-fix measurements](measure-r2.md) give the alternative term rules and the event-free status split.

The corrected boundary adds four crude leases (54 to 58) and six hydrocarbon leases (57 to 63) to the past-term counts. The observed samples and all published quartiles are identical in both builds. The pooled right-censored counts are 1,137 for first crude, 1,126 for first hydrocarbon and 287 for the first exploratory spud.

The [headline file](output/numbers.json) has 439 entries, compared with 376 at baseline. 8 existing values changed, 66 keys were added, 3 were retired and 365 entries are identical. In the tables below, **absent** means the row, column or key did not exist, **blank** is an empty CSV cell, and **null** is a JSON null. Zero is a measured count.

## first_production.csv


| depth_band | event | Column | Old | New |
|---|---|---|---|---|
| <100 m | Crude oil | open_without_observed_event | absent | 45 |
| <100 m | Crude oil | over_term_leases | 14 | 16 |
| <100 m | Any hydrocarbon | open_without_observed_event | absent | 36 |
| <100 m | Any hydrocarbon | over_term_leases | 17 | 21 |
| 100 to <500 m | Crude oil | open_without_observed_event | absent | 27 |
| 100 to <500 m | Any hydrocarbon | open_without_observed_event | absent | 26 |
| 500 to <1,500 m | Crude oil | open_without_observed_event | absent | 428 |
| 500 to <1,500 m | Crude oil | over_term_leases | 15 | 16 |
| 500 to <1,500 m | Any hydrocarbon | open_without_observed_event | absent | 428 |
| 500 to <1,500 m | Any hydrocarbon | over_term_leases | 15 | 16 |
| ≥1,500 m | Crude oil | open_without_observed_event | absent | 637 |
| ≥1,500 m | Crude oil | over_term_leases | 18 | 19 |
| ≥1,500 m | Any hydrocarbon | open_without_observed_event | absent | 636 |
| ≥1,500 m | Any hydrocarbon | over_term_leases | 18 | 19 |
| Unknown | Crude oil | open_without_observed_event | absent | 0 |
| Unknown | Any hydrocarbon | open_without_observed_event | absent | 0 |
| All bands | Crude oil | open_without_observed_event | absent | 1137 |
| All bands | Crude oil | over_term_leases | 54 | 58 |
| All bands | Any hydrocarbon | open_without_observed_event | absent | 1126 |
| All bands | Any hydrocarbon | over_term_leases | 57 | 63 |


## exploration.csv

Every cell in the new open_without_observed_event column was absent at baseline. Each entry below is the new count for that year and block band.

| Effective year | <100 m | 100 to <500 m | 500 to <1,500 m | ≥1,500 m | Unknown | All bands |
|---|---|---|---|---|---|---|
| 2005 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2006 | 1 | 0 | 5 | 5 | 0 | 11 |
| 2007 | 0 | 1 | 0 | 0 | 0 | 1 |
| 2008 | 4 | 0 | 0 | 7 | 0 | 11 |
| 2009 | 1 | 1 | 3 | 1 | 0 | 6 |
| 2010 | 2 | 0 | 1 | 2 | 0 | 5 |
| 2011 | 0 | 0 | 0 | 2 | 0 | 2 |
| 2012 | 0 | 0 | 1 | 0 | 0 | 1 |
| 2013 | 1 | 0 | 3 | 0 | 0 | 4 |
| 2014 | 0 | 1 | 0 | 2 | 0 | 3 |
| 2015 | 0 | 0 | 0 | 1 | 0 | 1 |
| 2016 | 0 | 1 | 0 | 1 | 0 | 2 |
| 2017 | 2 | 0 | 6 | 53 | 0 | 61 |
| 2018 | 5 | 0 | 0 | 35 | 0 | 40 |
| 2019 | 1 | 1 | 13 | 98 | 0 | 113 |
| 2020 | 1 | 1 | 8 | 16 | 0 | 26 |
| All years | 18 | 6 | 40 | 223 | 0 | 287 |


## coverage.csv


| metric | Column | Old | New |
|---|---|---|---|
| bounds_both_endpoints | number | absent | 416.0 |
| bounds_both_endpoints | text | absent | blank |
| bounds_both_endpoints | source | absent | LSETAPE.DAT + mv_boreholes_all.txt |
| bounds_both_endpoints | meaning | absent | Dated bottom and surface matches, any bore type, leases effective in 2005 to 2020 |
| bounds_additional_any_date | number | absent | 41.0 |
| bounds_additional_any_date | text | absent | blank |
| bounds_additional_any_date | source | absent | LSETAPE.DAT + mv_boreholes_all.txt |
| bounds_additional_any_date | meaning | absent | Additional leases when the date rule is removed, any bore type, leases effective in 2005 to 2020 |
| bounds_earlier_only | number | absent | 18.0 |
| bounds_earlier_only | text | absent | blank |
| bounds_earlier_only | source | absent | LSETAPE.DAT + mv_boreholes_all.txt |
| bounds_earlier_only | meaning | absent | Additional leases with only pre-effective spuds, any bore type, leases effective in 2005 to 2020 |
| bounds_undated_only | number | absent | 23.0 |
| bounds_undated_only | text | absent | blank |
| bounds_undated_only | source | absent | LSETAPE.DAT + mv_boreholes_all.txt |
| bounds_undated_only | meaning | absent | Additional leases with only undated listings, any bore type, leases effective in 2005 to 2020 |

The issuance, current_status, exploration_site_depth and lease_match_bounds CSVs are byte-identical to baseline.

## Record counts and flags

The audit ledger now records stage parents and separates exclusions from flags. The table lists every changed nonzero cell and every changed text cell. For compactness, numeric changes between zero and an absent cell are encoded by the column and stage changes below.

- Added columns: `upstream_stage`, `drop__issued_after_2020`, `drop__missing_comparison_depth`, `flag__nonpositive_depth_nulled`, `flag__missing_site_depth`, `flag__ambiguous_site_band`, `drop__additional_positive_lease_month`, `drop__pre_effective_event`, `drop__missing_or_nonpositive_primary_term`.
- Retired columns: `drop__missing_site_depth`, `drop__ambiguous_site_band`.
- Added stages: `BoreholeRawData site depth cleaning`, `Distinct observed any hydrocarbon leases`, `Distinct observed crude oil leases`, `Exploration cohort effective through 2020`, `Matched lease depths comparable across sources`, `Timed any hydrocarbon leases`, `Timed any hydrocarbon leases with positive primary term`, `Timed crude oil leases`, `Timed crude oil leases with positive primary term`, `Timed leases classified by measured site band`.
- Retired stages: `Timed leases with a resolved measured site band`.

On an added numeric column or stage, each omitted new cell is zero where the cell was previously absent. On a retired numeric column or stage, each omitted old cell was zero and is now absent. A column and stage which never coexist have no cell in that generation.

| Stage | Column | Old | New |
|---|---|---|---|
| LSETAPE effective Gulf lease cohort | upstream_stage | absent | blank |
| Exploration cohort effective through 2020 | upstream_stage | absent | LSETAPE effective Gulf lease cohort |
| Exploration cohort effective through 2020 | rows_read | absent | 8327 |
| Exploration cohort effective through 2020 | rows_kept | absent | 7126 |
| Exploration cohort effective through 2020 | rows_dropped | absent | 1201 |
| Exploration cohort effective through 2020 | drop__issued_after_2020 | absent | 1201 |
| ProductionRawData depth lookup matched to cohort for unit comparison | upstream_stage | absent | blank |
| Matched lease depths comparable across sources | upstream_stage | absent | ProductionRawData depth lookup matched to cohort for unit comparison |
| Matched lease depths comparable across sources | rows_read | absent | 8327 |
| Matched lease depths comparable across sources | rows_kept | absent | 8327 |
| BoreholeRawData site depth cleaning | upstream_stage | absent | blank |
| BoreholeRawData site depth cleaning | rows_read | absent | 57520 |
| BoreholeRawData site depth cleaning | rows_kept | absent | 57520 |
| BoreholeRawData site depth cleaning | flag__nonpositive_depth_nulled | absent | 84 |
| BoreholeRawData, dated Gulf bore records | upstream_stage | absent | BoreholeRawData site depth cleaning |
| Dated Gulf bore records at earliest API10 spud | upstream_stage | absent | BoreholeRawData, dated Gulf bore records |
| Earliest-spud bore records grouped into distinct Gulf API10s | upstream_stage | absent | Dated Gulf bore records at earliest API10 spud |
| Original-spud API10s attributable to effective cohort leases | upstream_stage | absent | Earliest-spud bore records grouped into distinct Gulf API10s |
| Cohort API10s originally spudded as exploratory | upstream_stage | absent | Original-spud API10s attributable to effective cohort leases |
| All dated Gulf bores for E-bore lease sensitivity | upstream_stage | absent | BoreholeRawData, dated Gulf bore records |
| Original-spud API10s for well-site exploration timing | upstream_stage | absent | Original-spud API10s attributable to effective cohort leases |
| First exploration spud on each lease at measured well site | upstream_stage | absent | Original-spud API10s for well-site exploration timing |
| First-spud exploratory API10s grouped into distinct timed leases | upstream_stage | absent | First exploration spud on each lease at measured well site |
| Timed leases classified by measured site band | upstream_stage | absent | First-spud exploratory API10s grouped into distinct timed leases |
| Timed leases classified by measured site band | rows_read | absent | 432 |
| Timed leases classified by measured site band | rows_kept | absent | 432 |
| ProductionRawData monthly detail matched to issuance cohort | upstream_stage | absent | blank |
| Matched lease-month rows with positive crude oil | upstream_stage | absent | ProductionRawData monthly detail matched to issuance cohort |
| Distinct observed crude oil leases | upstream_stage | absent | Matched lease-month rows with positive crude oil |
| Distinct observed crude oil leases | rows_read | absent | 8444 |
| Distinct observed crude oil leases | rows_kept | absent | 126 |
| Distinct observed crude oil leases | rows_dropped | absent | 8318 |
| Distinct observed crude oil leases | drop__additional_positive_lease_month | absent | 8318 |
| Matched lease-month rows with positive any hydrocarbon | upstream_stage | absent | ProductionRawData monthly detail matched to issuance cohort |
| Distinct observed any hydrocarbon leases | upstream_stage | absent | Matched lease-month rows with positive any hydrocarbon |
| Distinct observed any hydrocarbon leases | rows_read | absent | 15051 |
| Distinct observed any hydrocarbon leases | rows_kept | absent | 211 |
| Distinct observed any hydrocarbon leases | rows_dropped | absent | 14840 |
| Distinct observed any hydrocarbon leases | drop__additional_positive_lease_month | absent | 14840 |
| Timed crude oil leases | upstream_stage | absent | Distinct observed crude oil leases |
| Timed crude oil leases | rows_read | absent | 126 |
| Timed crude oil leases | rows_kept | absent | 122 |
| Timed crude oil leases | rows_dropped | absent | 4 |
| Timed crude oil leases | drop__pre_effective_event | absent | 4 |
| Timed crude oil leases with positive primary term | upstream_stage | absent | Timed crude oil leases |
| Timed crude oil leases with positive primary term | rows_read | absent | 122 |
| Timed crude oil leases with positive primary term | rows_kept | absent | 122 |
| Timed any hydrocarbon leases | upstream_stage | absent | Distinct observed any hydrocarbon leases |
| Timed any hydrocarbon leases | rows_read | absent | 211 |
| Timed any hydrocarbon leases | rows_kept | absent | 206 |
| Timed any hydrocarbon leases | rows_dropped | absent | 5 |
| Timed any hydrocarbon leases | drop__pre_effective_event | absent | 5 |
| Timed any hydrocarbon leases with positive primary term | upstream_stage | absent | Timed any hydrocarbon leases |
| Timed any hydrocarbon leases with positive primary term | rows_read | absent | 206 |
| Timed any hydrocarbon leases with positive primary term | rows_kept | absent | 206 |
| LeaseOwnerRawData current assignments on cohort leases | upstream_stage | absent | blank |
| Timed leases with a resolved measured site band | rows_read | 432 | absent |
| Timed leases with a resolved measured site band | rows_kept | 432 | absent |


## Headline values

Keys and values match the JSON precision. Timing, share and count units and CSV selectors are recorded for each key in [numbers.json](output/numbers.json).

### Changed existing headlines


| Key | Old | New |
|---|---|---|
| `hydrocarbon.1500_plus.over_term_leases` | 18 | 19 |
| `hydrocarbon.500_to_1500.over_term_leases` | 15 | 16 |
| `hydrocarbon.all.over_term_leases` | 57 | 63 |
| `hydrocarbon.under_100.over_term_leases` | 17 | 21 |
| `oil.1500_plus.over_term_leases` | 18 | 19 |
| `oil.500_to_1500.over_term_leases` | 15 | 16 |
| `oil.all.over_term_leases` | 54 | 58 |
| `oil.under_100.over_term_leases` | 14 | 16 |


### Added headlines


| Key | Old | New |
|---|---|---|
| `audit.BoreholeRawData site depth cleaning.flag__nonpositive_depth_nulled` | absent | 84 |
| `audit.BoreholeRawData site depth cleaning.rows_dropped` | absent | 0 |
| `audit.BoreholeRawData site depth cleaning.rows_kept` | absent | 57520 |
| `audit.BoreholeRawData site depth cleaning.rows_read` | absent | 57520 |
| `audit.Distinct observed any hydrocarbon leases.drop__additional_positive_lease_month` | absent | 14840 |
| `audit.Distinct observed any hydrocarbon leases.rows_dropped` | absent | 14840 |
| `audit.Distinct observed any hydrocarbon leases.rows_kept` | absent | 211 |
| `audit.Distinct observed any hydrocarbon leases.rows_read` | absent | 15051 |
| `audit.Distinct observed crude oil leases.drop__additional_positive_lease_month` | absent | 8318 |
| `audit.Distinct observed crude oil leases.rows_dropped` | absent | 8318 |
| `audit.Distinct observed crude oil leases.rows_kept` | absent | 126 |
| `audit.Distinct observed crude oil leases.rows_read` | absent | 8444 |
| `audit.Exploration cohort effective through 2020.drop__issued_after_2020` | absent | 1201 |
| `audit.Exploration cohort effective through 2020.rows_dropped` | absent | 1201 |
| `audit.Exploration cohort effective through 2020.rows_kept` | absent | 7126 |
| `audit.Exploration cohort effective through 2020.rows_read` | absent | 8327 |
| `audit.Matched lease depths comparable across sources.rows_dropped` | absent | 0 |
| `audit.Matched lease depths comparable across sources.rows_kept` | absent | 8327 |
| `audit.Matched lease depths comparable across sources.rows_read` | absent | 8327 |
| `audit.Timed any hydrocarbon leases with positive primary term.rows_dropped` | absent | 0 |
| `audit.Timed any hydrocarbon leases with positive primary term.rows_kept` | absent | 206 |
| `audit.Timed any hydrocarbon leases with positive primary term.rows_read` | absent | 206 |
| `audit.Timed any hydrocarbon leases.drop__pre_effective_event` | absent | 5 |
| `audit.Timed any hydrocarbon leases.rows_dropped` | absent | 5 |
| `audit.Timed any hydrocarbon leases.rows_kept` | absent | 206 |
| `audit.Timed any hydrocarbon leases.rows_read` | absent | 211 |
| `audit.Timed crude oil leases with positive primary term.rows_dropped` | absent | 0 |
| `audit.Timed crude oil leases with positive primary term.rows_kept` | absent | 122 |
| `audit.Timed crude oil leases with positive primary term.rows_read` | absent | 122 |
| `audit.Timed crude oil leases.drop__pre_effective_event` | absent | 4 |
| `audit.Timed crude oil leases.rows_dropped` | absent | 4 |
| `audit.Timed crude oil leases.rows_kept` | absent | 122 |
| `audit.Timed crude oil leases.rows_read` | absent | 126 |
| `audit.Timed leases classified by measured site band.rows_dropped` | absent | 0 |
| `audit.Timed leases classified by measured site band.rows_kept` | absent | 432 |
| `audit.Timed leases classified by measured site band.rows_read` | absent | 432 |
| `bounds.a.matched_leases` | absent | 520 |
| `bounds.b.matched_leases` | absent | 442 |
| `bounds.c.matched_leases` | absent | 546 |
| `bounds.c.share_pct` | absent | 7.66 |
| `bounds.d.matched_leases` | absent | 477 |
| `bounds.d.share_pct` | absent | 6.69 |
| `bounds.e.matched_leases` | absent | 587 |
| `bounds.e.share_pct` | absent | 8.24 |
| `coverage.bounds_additional_any_date` | absent | 41 |
| `coverage.bounds_both_endpoints` | absent | 416 |
| `coverage.bounds_earlier_only` | absent | 18 |
| `coverage.bounds_undated_only` | absent | 23 |
| `exploration.100_to_500.open_without_observed_event` | absent | 6 |
| `exploration.1500_plus.open_without_observed_event` | absent | 223 |
| `exploration.500_to_1500.open_without_observed_event` | absent | 40 |
| `exploration.all.open_without_observed_event` | absent | 287 |
| `exploration.under_100.open_without_observed_event` | absent | 18 |
| `exploration.unknown.open_without_observed_event` | absent | 0 |
| `hydrocarbon.100_to_500.open_without_observed_event` | absent | 26 |
| `hydrocarbon.1500_plus.open_without_observed_event` | absent | 636 |
| `hydrocarbon.500_to_1500.open_without_observed_event` | absent | 428 |
| `hydrocarbon.all.open_without_observed_event` | absent | 1126 |
| `hydrocarbon.under_100.open_without_observed_event` | absent | 36 |
| `hydrocarbon.unknown.open_without_observed_event` | absent | 0 |
| `oil.100_to_500.open_without_observed_event` | absent | 27 |
| `oil.1500_plus.open_without_observed_event` | absent | 637 |
| `oil.500_to_1500.open_without_observed_event` | absent | 428 |
| `oil.all.open_without_observed_event` | absent | 1137 |
| `oil.under_100.open_without_observed_event` | absent | 45 |
| `oil.unknown.open_without_observed_event` | absent | 0 |


### Retired headlines


| Key | Old | New |
|---|---|---|
| `audit.Timed leases with a resolved measured site band.rows_dropped` | 0 | absent |
| `audit.Timed leases with a resolved measured site band.rows_kept` | 432 | absent |
| `audit.Timed leases with a resolved measured site band.rows_read` | 432 | absent |


### Identical headlines


| Key | Old | New |
|---|---|---|
| `audit.All dated Gulf bores for E-bore lease sensitivity.drop__bore_spud_before_lease_effective` | 25 | 25 |
| `audit.All dated Gulf bores for E-bore lease sensitivity.drop__bottom_lease_outside_cohort` | 18420 | 18420 |
| `audit.All dated Gulf bores for E-bore lease sensitivity.drop__not_exploratory` | 35254 | 35254 |
| `audit.All dated Gulf bores for E-bore lease sensitivity.rows_dropped` | 53699 | 53699 |
| `audit.All dated Gulf bores for E-bore lease sensitivity.rows_kept` | 862 | 862 |
| `audit.All dated Gulf bores for E-bore lease sensitivity.rows_read` | 54561 | 54561 |
| `audit.BoreholeRawData, dated Gulf bore records.drop__other_region` | 1934 | 1934 |
| `audit.BoreholeRawData, dated Gulf bore records.drop__undated_cancelled` | 994 | 994 |
| `audit.BoreholeRawData, dated Gulf bore records.drop__undated_permit_or_approved_sidetrack` | 31 | 31 |
| `audit.BoreholeRawData, dated Gulf bore records.rows_dropped` | 2959 | 2959 |
| `audit.BoreholeRawData, dated Gulf bore records.rows_kept` | 54561 | 54561 |
| `audit.BoreholeRawData, dated Gulf bore records.rows_read` | 57520 | 57520 |
| `audit.Cohort API10s originally spudded as exploratory.drop__first_spud_not_type_E` | 139 | 139 |
| `audit.Cohort API10s originally spudded as exploratory.rows_dropped` | 139 | 139 |
| `audit.Cohort API10s originally spudded as exploratory.rows_kept` | 595 | 595 |
| `audit.Cohort API10s originally spudded as exploratory.rows_read` | 734 | 734 |
| `audit.Dated Gulf bore records at earliest API10 spud.drop__later_bore_of_same_api10` | 16996 | 16996 |
| `audit.Dated Gulf bore records at earliest API10 spud.rows_dropped` | 16996 | 16996 |
| `audit.Dated Gulf bore records at earliest API10 spud.rows_kept` | 37565 | 37565 |
| `audit.Dated Gulf bore records at earliest API10 spud.rows_read` | 54561 | 54561 |
| `audit.Earliest-spud bore records grouped into distinct Gulf API10s.drop__additional_bore_on_same_well_spud_date` | 52 | 52 |
| `audit.Earliest-spud bore records grouped into distinct Gulf API10s.rows_dropped` | 52 | 52 |
| `audit.Earliest-spud bore records grouped into distinct Gulf API10s.rows_kept` | 37513 | 37513 |
| `audit.Earliest-spud bore records grouped into distinct Gulf API10s.rows_read` | 37565 | 37565 |
| `audit.First exploration spud on each lease at measured well site.drop__later_exploration_well_on_same_lease` | 157 | 157 |
| `audit.First exploration spud on each lease at measured well site.rows_dropped` | 157 | 157 |
| `audit.First exploration spud on each lease at measured well site.rows_kept` | 432 | 432 |
| `audit.First exploration spud on each lease at measured well site.rows_read` | 589 | 589 |
| `audit.First-spud exploratory API10s grouped into distinct timed leases.rows_dropped` | 0 | 0 |
| `audit.First-spud exploratory API10s grouped into distinct timed leases.rows_kept` | 432 | 432 |
| `audit.First-spud exploratory API10s grouped into distinct timed leases.rows_read` | 432 | 432 |
| `audit.LSETAPE effective Gulf lease cohort.drop__effective_year_outside_2005_2026` | 21748 | 21748 |
| `audit.LSETAPE effective Gulf lease cohort.drop__missing_effective_date` | 1646 | 1646 |
| `audit.LSETAPE effective Gulf lease cohort.rows_dropped` | 23394 | 23394 |
| `audit.LSETAPE effective Gulf lease cohort.rows_kept` | 8327 | 8327 |
| `audit.LSETAPE effective Gulf lease cohort.rows_read` | 31721 | 31721 |
| `audit.LeaseOwnerRawData current assignments on cohort leases.drop__assignment_status_other_than_current` | 4 | 4 |
| `audit.LeaseOwnerRawData current assignments on cohort leases.drop__lease_outside_effective_cohort` | 1356 | 1356 |
| `audit.LeaseOwnerRawData current assignments on cohort leases.rows_dropped` | 1360 | 1360 |
| `audit.LeaseOwnerRawData current assignments on cohort leases.rows_kept` | 2195 | 2195 |
| `audit.LeaseOwnerRawData current assignments on cohort leases.rows_read` | 3555 | 3555 |
| `audit.Matched lease-month rows with positive any hydrocarbon.drop__no_positive_reported_volume` | 4047 | 4047 |
| `audit.Matched lease-month rows with positive any hydrocarbon.rows_dropped` | 4047 | 4047 |
| `audit.Matched lease-month rows with positive any hydrocarbon.rows_kept` | 15051 | 15051 |
| `audit.Matched lease-month rows with positive any hydrocarbon.rows_read` | 19098 | 19098 |
| `audit.Matched lease-month rows with positive crude oil.drop__no_positive_reported_volume` | 10654 | 10654 |
| `audit.Matched lease-month rows with positive crude oil.rows_dropped` | 10654 | 10654 |
| `audit.Matched lease-month rows with positive crude oil.rows_kept` | 8444 | 8444 |
| `audit.Matched lease-month rows with positive crude oil.rows_read` | 19098 | 19098 |
| `audit.Original-spud API10s attributable to effective cohort leases.drop__bottom_lease_outside_cohort` | 36677 | 36677 |
| `audit.Original-spud API10s attributable to effective cohort leases.drop__conflicting_bottom_leases_at_first_spud` | 2 | 2 |
| `audit.Original-spud API10s attributable to effective cohort leases.drop__conflicting_types_at_first_spud` | 6 | 6 |
| `audit.Original-spud API10s attributable to effective cohort leases.drop__well_spud_before_lease_effective` | 94 | 94 |
| `audit.Original-spud API10s attributable to effective cohort leases.rows_dropped` | 36779 | 36779 |
| `audit.Original-spud API10s attributable to effective cohort leases.rows_kept` | 734 | 734 |
| `audit.Original-spud API10s attributable to effective cohort leases.rows_read` | 37513 | 37513 |
| `audit.Original-spud API10s for well-site exploration timing.drop__not_exploratory` | 139 | 139 |
| `audit.Original-spud API10s for well-site exploration timing.drop__outside_2005_2020_lease_cohort` | 6 | 6 |
| `audit.Original-spud API10s for well-site exploration timing.rows_dropped` | 145 | 145 |
| `audit.Original-spud API10s for well-site exploration timing.rows_kept` | 589 | 589 |
| `audit.Original-spud API10s for well-site exploration timing.rows_read` | 734 | 734 |
| `audit.ProductionRawData depth lookup matched to cohort for unit comparison.drop__lease_outside_cohort` | 23394 | 23394 |
| `audit.ProductionRawData depth lookup matched to cohort for unit comparison.rows_dropped` | 23394 | 23394 |
| `audit.ProductionRawData depth lookup matched to cohort for unit comparison.rows_kept` | 8327 | 8327 |
| `audit.ProductionRawData depth lookup matched to cohort for unit comparison.rows_read` | 31721 | 31721 |
| `audit.ProductionRawData monthly detail matched to issuance cohort.drop__lease_outside_cohort` | 853964 | 853964 |
| `audit.ProductionRawData monthly detail matched to issuance cohort.drop__missing_lease_id` | 19 | 19 |
| `audit.ProductionRawData monthly detail matched to issuance cohort.rows_dropped` | 853983 | 853983 |
| `audit.ProductionRawData monthly detail matched to issuance cohort.rows_kept` | 19098 | 19098 |
| `audit.ProductionRawData monthly detail matched to issuance cohort.rows_read` | 873081 | 873081 |
| `coverage.cohort_current_companies` | 173 | 173 |
| `coverage.cohort_current_leases` | 1224 | 1224 |
| `coverage.compared_block_depths` | 8327 | 8327 |
| `coverage.continuous_date_without_positive_month` | 2 | 2 |
| `coverage.depths_within_one_metre` | 8327 | 8327 |
| `coverage.first_effective_date` | 2005-04-01 | 2005-04-01 |
| `coverage.first_source_month` | 1947-11 | 1947-11 |
| `coverage.invalid_ranges` | 0 | 0 |
| `coverage.last_effective_date` | 2026-10-01 | 2026-10-01 |
| `coverage.last_gulf_spud` | 2026-11-06 | 2026-11-06 |
| `coverage.last_source_month` | 2026-10 | 2026-10 |
| `coverage.last_source_month_rows` | 21 | 21 |
| `coverage.missing_assignment_effective_dates` | 12 | 12 |
| `coverage.missing_ranges` | 0 | 0 |
| `coverage.no_sale_number` | 7 | 7 |
| `coverage.oil_before_effective_month` | 4 | 4 |
| `coverage.owner_status_C` | 3551 | 3551 |
| `coverage.owner_status_T` | 4 | 4 |
| `coverage.positive_month_without_continuous_date` | 8 | 8 |
| `coverage.pre_effective_e_bores_2005_2026` | 25 | 25 |
| `coverage.primary_term_missing_or_nonpositive` | 0 | 0 |
| `coverage.production_before_effective_month` | 5 | 5 |
| `coverage.source_rows` | 873081 | 873081 |
| `coverage.straddling_ranges` | 944 | 944 |
| `coverage.suspensions_with_ordered_dates` | 556 | 556 |
| `coverage.tape_file_date` | 2026-11-02 | 2026-11-02 |
| `coverage.tape_first_production_date_present` | 205 | 205 |
| `coverage.termination_dates_present` | 0 | 0 |
| `coverage.tied_first_spud_conflicting_cohort_lease_api10s` | 1 | 1 |
| `coverage.tied_first_spud_conflicting_cohort_type_api10s` | 0 | 0 |
| `coverage.undated_e_APD` | 3 | 3 |
| `coverage.undated_e_AST` | 2 | 2 |
| `coverage.undated_e_CNL` | 41 | 41 |
| `coverage.unmapped_status_codes` | CANCEL, EXPIR, OPERNS, PRIMRY, RELINQ, TERMIN | CANCEL, EXPIR, OPERNS, PRIMRY, RELINQ, TERMIN |
| `exploration.100_to_500.any_e_bore_share_pct` | 3.7478705281090288 | 3.7478705281090288 |
| `exploration.100_to_500.days_to_any_e_bore_median` | 974.5 | 974.5 |
| `exploration.100_to_500.days_to_any_e_bore_p25` | 627.25 | 627.25 |
| `exploration.100_to_500.days_to_any_e_bore_p75` | 1648.5 | 1648.5 |
| `exploration.100_to_500.days_to_spud_median` | 974.5 | 974.5 |
| `exploration.100_to_500.days_to_spud_p25` | 627.25 | 627.25 |
| `exploration.100_to_500.days_to_spud_p75` | 1648.5 | 1648.5 |
| `exploration.100_to_500.exploration_wells` | 23 | 23 |
| `exploration.100_to_500.explored_leases` | 22 | 22 |
| `exploration.100_to_500.explored_within_five_years` | 19 | 19 |
| `exploration.100_to_500.five_year_share_pct` | 3.2367972742759794 | 3.2367972742759794 |
| `exploration.100_to_500.leases` | 587 | 587 |
| `exploration.100_to_500.leases_with_any_e_bore` | 22 | 22 |
| `exploration.100_to_500.share_pct` | 3.7478705281090288 | 3.7478705281090288 |
| `exploration.1500_plus.any_e_bore_share_pct` | 4.359673024523161 | 4.359673024523161 |
| `exploration.1500_plus.days_to_any_e_bore_median` | 1764 | 1764 |
| `exploration.1500_plus.days_to_any_e_bore_p25` | 953.25 | 953.25 |
| `exploration.1500_plus.days_to_any_e_bore_p75` | 2514 | 2514 |
| `exploration.1500_plus.days_to_spud_median` | 1730.5 | 1730.5 |
| `exploration.1500_plus.days_to_spud_p25` | 953.25 | 953.25 |
| `exploration.1500_plus.days_to_spud_p75` | 2474.75 | 2474.75 |
| `exploration.1500_plus.exploration_wells` | 192 | 192 |
| `exploration.1500_plus.explored_leases` | 108 | 108 |
| `exploration.1500_plus.explored_within_five_years` | 57 | 57 |
| `exploration.1500_plus.five_year_share_pct` | 2.2187621642662516 | 2.2187621642662516 |
| `exploration.1500_plus.leases` | 2569 | 2569 |
| `exploration.1500_plus.leases_with_any_e_bore` | 112 | 112 |
| `exploration.1500_plus.share_pct` | 4.203970416504476 | 4.203970416504476 |
| `exploration.500_to_1500.any_e_bore_share_pct` | 5.255941499085923 | 5.255941499085923 |
| `exploration.500_to_1500.days_to_any_e_bore_median` | 1251 | 1251 |
| `exploration.500_to_1500.days_to_any_e_bore_p25` | 615.5 | 615.5 |
| `exploration.500_to_1500.days_to_any_e_bore_p75` | 2244.5 | 2244.5 |
| `exploration.500_to_1500.days_to_spud_median` | 1270 | 1270 |
| `exploration.500_to_1500.days_to_spud_p25` | 628.25 | 628.25 |
| `exploration.500_to_1500.days_to_spud_p75` | 2226.75 | 2226.75 |
| `exploration.500_to_1500.exploration_wells` | 153 | 153 |
| `exploration.500_to_1500.explored_leases` | 106 | 106 |
| `exploration.500_to_1500.explored_within_five_years` | 75 | 75 |
| `exploration.500_to_1500.five_year_share_pct` | 3.4277879341864717 | 3.4277879341864717 |
| `exploration.500_to_1500.leases` | 2188 | 2188 |
| `exploration.500_to_1500.leases_with_any_e_bore` | 115 | 115 |
| `exploration.500_to_1500.share_pct` | 4.844606946983546 | 4.844606946983546 |
| `exploration.all.any_e_bore_share_pct` | 6.314903171484704 | 6.314903171484704 |
| `exploration.all.days_to_any_e_bore_median` | 907 | 907 |
| `exploration.all.days_to_any_e_bore_p25` | 439.5 | 439.5 |
| `exploration.all.days_to_any_e_bore_p75` | 1776.75 | 1776.75 |
| `exploration.all.days_to_spud_median` | 893.5 | 893.5 |
| `exploration.all.days_to_spud_p25` | 440.5 | 440.5 |
| `exploration.all.days_to_spud_p75` | 1756.5 | 1756.5 |
| `exploration.all.exploration_wells` | 589 | 589 |
| `exploration.all.explored_leases` | 432 | 432 |
| `exploration.all.explored_within_five_years` | 339 | 339 |
| `exploration.all.five_year_share_pct` | 4.757227055851811 | 4.757227055851811 |
| `exploration.all.leases` | 7126 | 7126 |
| `exploration.all.leases_with_any_e_bore` | 450 | 450 |
| `exploration.all.share_pct` | 6.0623070446253156 | 6.0623070446253156 |
| `exploration.under_100.any_e_bore_share_pct` | 11.27946127946128 | 11.27946127946128 |
| `exploration.under_100.days_to_any_e_bore_median` | 517 | 517 |
| `exploration.under_100.days_to_any_e_bore_p25` | 321 | 321 |
| `exploration.under_100.days_to_any_e_bore_p75` | 1118 | 1118 |
| `exploration.under_100.days_to_spud_median` | 504.5 | 504.5 |
| `exploration.under_100.days_to_spud_p25` | 319 | 319 |
| `exploration.under_100.days_to_spud_p75` | 1007.75 | 1007.75 |
| `exploration.under_100.exploration_wells` | 221 | 221 |
| `exploration.under_100.explored_leases` | 196 | 196 |
| `exploration.under_100.explored_within_five_years` | 188 | 188 |
| `exploration.under_100.five_year_share_pct` | 10.549943883277217 | 10.549943883277217 |
| `exploration.under_100.leases` | 1782 | 1782 |
| `exploration.under_100.leases_with_any_e_bore` | 201 | 201 |
| `exploration.under_100.share_pct` | 10.998877665544333 | 10.998877665544333 |
| `exploration.unknown.any_e_bore_share_pct` | null | null |
| `exploration.unknown.days_to_any_e_bore_median` | null | null |
| `exploration.unknown.days_to_any_e_bore_p25` | null | null |
| `exploration.unknown.days_to_any_e_bore_p75` | null | null |
| `exploration.unknown.days_to_spud_median` | null | null |
| `exploration.unknown.days_to_spud_p25` | null | null |
| `exploration.unknown.days_to_spud_p75` | null | null |
| `exploration.unknown.exploration_wells` | 0 | 0 |
| `exploration.unknown.explored_leases` | 0 | 0 |
| `exploration.unknown.explored_within_five_years` | 0 | 0 |
| `exploration.unknown.five_year_share_pct` | null | null |
| `exploration.unknown.leases` | 0 | 0 |
| `exploration.unknown.leases_with_any_e_bore` | 0 | 0 |
| `exploration.unknown.share_pct` | null | null |
| `hydrocarbon.100_to_500.months_median` | 59 | 59 |
| `hydrocarbon.100_to_500.months_p25` | 33.5 | 33.5 |
| `hydrocarbon.100_to_500.months_p75` | 88 | 88 |
| `hydrocarbon.100_to_500.observed_leases` | 17 | 17 |
| `hydrocarbon.100_to_500.over_term_leases` | 7 | 7 |
| `hydrocarbon.100_to_500.primary_term_pct_median` | 83.125 | 83.125 |
| `hydrocarbon.100_to_500.primary_term_pct_p25` | 45.41666666666667 | 45.41666666666667 |
| `hydrocarbon.100_to_500.primary_term_pct_p75` | 125 | 125 |
| `hydrocarbon.100_to_500.term_leases` | 16 | 16 |
| `hydrocarbon.100_to_500.timed_leases` | 16 | 16 |
| `hydrocarbon.100_to_500.without_observed_event` | 618 | 618 |
| `hydrocarbon.1500_plus.months_median` | 125.5 | 125.5 |
| `hydrocarbon.1500_plus.months_p25` | 89.25 | 89.25 |
| `hydrocarbon.1500_plus.months_p75` | 189.5 | 189.5 |
| `hydrocarbon.1500_plus.observed_leases` | 34 | 34 |
| `hydrocarbon.1500_plus.primary_term_pct_median` | 104.58333333333334 | 104.58333333333334 |
| `hydrocarbon.1500_plus.primary_term_pct_p25` | 74.375 | 74.375 |
| `hydrocarbon.1500_plus.primary_term_pct_p75` | 157.91666666666669 | 157.91666666666669 |
| `hydrocarbon.1500_plus.term_leases` | 34 | 34 |
| `hydrocarbon.1500_plus.timed_leases` | 34 | 34 |
| `hydrocarbon.1500_plus.without_observed_event` | 2970 | 2970 |
| `hydrocarbon.500_to_1500.months_median` | 69 | 69 |
| `hydrocarbon.500_to_1500.months_p25` | 54 | 54 |
| `hydrocarbon.500_to_1500.months_p75` | 112 | 112 |
| `hydrocarbon.500_to_1500.observed_leases` | 39 | 39 |
| `hydrocarbon.500_to_1500.primary_term_pct_median` | 80.95238095238095 | 80.95238095238095 |
| `hydrocarbon.500_to_1500.primary_term_pct_p25` | 46.979166666666664 | 46.979166666666664 |
| `hydrocarbon.500_to_1500.primary_term_pct_p75` | 121.13095238095238 | 121.13095238095238 |
| `hydrocarbon.500_to_1500.term_leases` | 39 | 39 |
| `hydrocarbon.500_to_1500.timed_leases` | 39 | 39 |
| `hydrocarbon.500_to_1500.without_observed_event` | 2566 | 2566 |
| `hydrocarbon.all.months_median` | 51.5 | 51.5 |
| `hydrocarbon.all.months_p25` | 26 | 26 |
| `hydrocarbon.all.months_p75` | 80.75 | 80.75 |
| `hydrocarbon.all.observed_leases` | 211 | 211 |
| `hydrocarbon.all.primary_term_pct_median` | 67.5 | 67.5 |
| `hydrocarbon.all.primary_term_pct_p25` | 38.333333333333336 | 38.333333333333336 |
| `hydrocarbon.all.primary_term_pct_p75` | 104.58333333333333 | 104.58333333333333 |
| `hydrocarbon.all.term_leases` | 206 | 206 |
| `hydrocarbon.all.timed_leases` | 206 | 206 |
| `hydrocarbon.all.without_observed_event` | 8116 | 8116 |
| `hydrocarbon.under_100.months_median` | 29 | 29 |
| `hydrocarbon.under_100.months_p25` | 20 | 20 |
| `hydrocarbon.under_100.months_p75` | 56 | 56 |
| `hydrocarbon.under_100.observed_leases` | 121 | 121 |
| `hydrocarbon.under_100.primary_term_pct_median` | 48.333333333333336 | 48.333333333333336 |
| `hydrocarbon.under_100.primary_term_pct_p25` | 33.333333333333336 | 33.333333333333336 |
| `hydrocarbon.under_100.primary_term_pct_p75` | 93.33333333333333 | 93.33333333333333 |
| `hydrocarbon.under_100.term_leases` | 117 | 117 |
| `hydrocarbon.under_100.timed_leases` | 117 | 117 |
| `hydrocarbon.under_100.without_observed_event` | 1962 | 1962 |
| `hydrocarbon.unknown.months_median` | null | null |
| `hydrocarbon.unknown.months_p25` | null | null |
| `hydrocarbon.unknown.months_p75` | null | null |
| `hydrocarbon.unknown.observed_leases` | 0 | 0 |
| `hydrocarbon.unknown.over_term_leases` | 0 | 0 |
| `hydrocarbon.unknown.primary_term_pct_median` | null | null |
| `hydrocarbon.unknown.primary_term_pct_p25` | null | null |
| `hydrocarbon.unknown.primary_term_pct_p75` | null | null |
| `hydrocarbon.unknown.term_leases` | 0 | 0 |
| `hydrocarbon.unknown.timed_leases` | 0 | 0 |
| `hydrocarbon.unknown.without_observed_event` | 0 | 0 |
| `issued.100_to_500` | 635 | 635 |
| `issued.1500_plus` | 3004 | 3004 |
| `issued.500_to_1500` | 2605 | 2605 |
| `issued.all` | 8327 | 8327 |
| `issued.under_100` | 2083 | 2083 |
| `issued.unknown` | 0 | 0 |
| `issued_2008` | 1512 | 1512 |
| `issued_2025` | 0 | 0 |
| `issued_2026` | 215 | 215 |
| `issued_total` | 8327 | 8327 |
| `oil.100_to_500.months_median` | 70.5 | 70.5 |
| `oil.100_to_500.months_p25` | 36.25 | 36.25 |
| `oil.100_to_500.months_p75` | 89 | 89 |
| `oil.100_to_500.observed_leases` | 13 | 13 |
| `oil.100_to_500.over_term_leases` | 7 | 7 |
| `oil.100_to_500.primary_term_pct_median` | 113.33333333333333 | 113.33333333333333 |
| `oil.100_to_500.primary_term_pct_p25` | 60.416666666666664 | 60.416666666666664 |
| `oil.100_to_500.primary_term_pct_p75` | 130.41666666666666 | 130.41666666666666 |
| `oil.100_to_500.term_leases` | 12 | 12 |
| `oil.100_to_500.timed_leases` | 12 | 12 |
| `oil.100_to_500.without_observed_event` | 622 | 622 |
| `oil.1500_plus.months_median` | 129 | 129 |
| `oil.1500_plus.months_p25` | 88 | 88 |
| `oil.1500_plus.months_p75` | 190 | 190 |
| `oil.1500_plus.observed_leases` | 33 | 33 |
| `oil.1500_plus.primary_term_pct_median` | 107.5 | 107.5 |
| `oil.1500_plus.primary_term_pct_p25` | 73.33333333333333 | 73.33333333333333 |
| `oil.1500_plus.primary_term_pct_p75` | 158.33333333333334 | 158.33333333333334 |
| `oil.1500_plus.term_leases` | 33 | 33 |
| `oil.1500_plus.timed_leases` | 33 | 33 |
| `oil.1500_plus.without_observed_event` | 2971 | 2971 |
| `oil.500_to_1500.months_median` | 82 | 82 |
| `oil.500_to_1500.months_p25` | 62 | 62 |
| `oil.500_to_1500.months_p75` | 112.25 | 112.25 |
| `oil.500_to_1500.observed_leases` | 36 | 36 |
| `oil.500_to_1500.primary_term_pct_median` | 90.41666666666667 | 90.41666666666667 |
| `oil.500_to_1500.primary_term_pct_p25` | 68.45238095238096 | 68.45238095238096 |
| `oil.500_to_1500.primary_term_pct_p75` | 130.20833333333331 | 130.20833333333331 |
| `oil.500_to_1500.term_leases` | 36 | 36 |
| `oil.500_to_1500.timed_leases` | 36 | 36 |
| `oil.500_to_1500.without_observed_event` | 2569 | 2569 |
| `oil.all.months_median` | 75 | 75 |
| `oil.all.months_p25` | 45 | 45 |
| `oil.all.months_p75` | 119.5 | 119.5 |
| `oil.all.observed_leases` | 126 | 126 |
| `oil.all.primary_term_pct_median` | 95 | 95 |
| `oil.all.primary_term_pct_p25` | 63.54166666666667 | 63.54166666666667 |
| `oil.all.primary_term_pct_p75` | 128.95833333333331 | 128.95833333333331 |
| `oil.all.term_leases` | 122 | 122 |
| `oil.all.timed_leases` | 122 | 122 |
| `oil.all.without_observed_event` | 8201 | 8201 |
| `oil.under_100.months_median` | 48 | 48 |
| `oil.under_100.months_p25` | 26 | 26 |
| `oil.under_100.months_p75` | 69 | 69 |
| `oil.under_100.observed_leases` | 44 | 44 |
| `oil.under_100.primary_term_pct_median` | 80 | 80 |
| `oil.under_100.primary_term_pct_p25` | 43.333333333333336 | 43.333333333333336 |
| `oil.under_100.primary_term_pct_p75` | 115 | 115 |
| `oil.under_100.term_leases` | 41 | 41 |
| `oil.under_100.timed_leases` | 41 | 41 |
| `oil.under_100.without_observed_event` | 2039 | 2039 |
| `oil.unknown.months_median` | null | null |
| `oil.unknown.months_p25` | null | null |
| `oil.unknown.months_p75` | null | null |
| `oil.unknown.observed_leases` | 0 | 0 |
| `oil.unknown.over_term_leases` | 0 | 0 |
| `oil.unknown.primary_term_pct_median` | null | null |
| `oil.unknown.primary_term_pct_p25` | null | null |
| `oil.unknown.primary_term_pct_p75` | null | null |
| `oil.unknown.term_leases` | 0 | 0 |
| `oil.unknown.timed_leases` | 0 | 0 |
| `oil.unknown.without_observed_event` | 0 | 0 |
| `peak_effective_year` | 2008 | 2008 |
| `status.CANCEL.leases` | 4 | 4 |
| `status.CANCEL.share_pct` | 0.04803650774588687 | 0.04803650774588687 |
| `status.EXPIR.leases` | 1851 | 1851 |
| `status.EXPIR.share_pct` | 22.228893959409152 | 22.228893959409152 |
| `status.OPERNS.leases` | 3 | 3 |
| `status.OPERNS.share_pct` | 0.03602738080941516 | 0.03602738080941516 |
| `status.PRIMRY.leases` | 1071 | 1071 |
| `status.PRIMRY.share_pct` | 12.86177494896121 | 12.86177494896121 |
| `status.PROD.leases` | 61 | 61 |
| `status.PROD.share_pct` | 0.7325567431247748 | 0.7325567431247748 |
| `status.RELINQ.leases` | 5090 | 5090 |
| `status.RELINQ.share_pct` | 61.126456106641044 | 61.126456106641044 |
| `status.SOP.leases` | 1 | 1 |
| `status.SOP.share_pct` | 0.012009126936471718 | 0.012009126936471718 |
| `status.TERMIN.leases` | 150 | 150 |
| `status.TERMIN.share_pct` | 1.8013690404707579 | 1.8013690404707579 |
| `status.UNIT.leases` | 96 | 96 |
| `status.UNIT.share_pct` | 1.152876185901285 | 1.152876185901285 |
| `well_site.100_to_500.days_to_spud_median` | 1169.5 | 1169.5 |
| `well_site.100_to_500.days_to_spud_p25` | 848.5 | 848.5 |
| `well_site.100_to_500.days_to_spud_p75` | 1770.75 | 1770.75 |
| `well_site.100_to_500.timed_leases` | 18 | 18 |
| `well_site.1500_plus.days_to_spud_median` | 1730.5 | 1730.5 |
| `well_site.1500_plus.days_to_spud_p25` | 967.25 | 967.25 |
| `well_site.1500_plus.days_to_spud_p75` | 2510 | 2510 |
| `well_site.1500_plus.timed_leases` | 96 | 96 |
| `well_site.500_to_1500.days_to_spud_median` | 1297.5 | 1297.5 |
| `well_site.500_to_1500.days_to_spud_p25` | 638.75 | 638.75 |
| `well_site.500_to_1500.days_to_spud_p75` | 2282.75 | 2282.75 |
| `well_site.500_to_1500.timed_leases` | 116 | 116 |
| `well_site.all.days_to_spud_median` | 893.5 | 893.5 |
| `well_site.all.days_to_spud_p25` | 440.5 | 440.5 |
| `well_site.all.days_to_spud_p75` | 1756.5 | 1756.5 |
| `well_site.all.timed_leases` | 432 | 432 |
| `well_site.under_100.days_to_spud_median` | 511 | 511 |
| `well_site.under_100.days_to_spud_p25` | 324 | 324 |
| `well_site.under_100.days_to_spud_p75` | 1075.25 | 1075.25 |
| `well_site.under_100.timed_leases` | 202 | 202 |
| `well_site.unknown.days_to_spud_median` | null | null |
| `well_site.unknown.days_to_spud_p25` | null | null |
| `well_site.unknown.days_to_spud_p75` | null | null |
| `well_site.unknown.timed_leases` | 0 | 0 |
