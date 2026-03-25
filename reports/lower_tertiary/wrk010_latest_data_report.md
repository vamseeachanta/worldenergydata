# WRK-010: Lower Tertiary Extended Analysis Report

> **Data Vintage**: OGOR through Oct 2025, WTI through Oct 2025
> **Time Period**: Sep 2000 through Oct 2025
> **Baseline**: FDAS V30 (Sep 2000 through May 2025)
> **Generated**: 2026-01-31

## Summary

Extended the V30 lower tertiary production analysis from May 2025 to Oct 2025 using
the same BSEE OGOR-A data file (`ogora2025delimit.zip`) and V30 lease mappings. All 7
producing developments gained production. Four fields flagged as significant deviations
(>5% change): Big Foot (+7.93%), Cascade Chinook (+12.44%), Anchor (+96.80%), and
Shenandoah (+156,961%).

This update adds OGOR-code-based well-test classification (PRODUCT_CODE, WELL_STAT_CD)
and corrects Cascade Chinook's first_oil from 2014-01-01 to 2012-09-01, adding ~3.26M
bbl of previously excluded commercial production.

## Production Comparison

| Development | V30 Oil (BBL) | Latest Oil (BBL) | Delta (BBL) | Delta % | Significant |
|---|---:|---:|---:|---:|:---:|
| Jack St Malo | 406,571,771 | 421,032,342 | +14,460,571 | +3.56% | |
| Stones | 83,657,789 | 86,326,766 | +2,668,977 | +3.19% | |
| Julia | 70,936,158 | 74,028,262 | +3,092,104 | +4.36% | |
| Big Foot | 66,870,656 | 72,174,604 | +5,303,948 | +7.93% | YES |
| Cascade Chinook | 34,322,807 | 38,593,041 | +4,270,234 | +12.44% | YES |
| Anchor | 6,912,846 | 13,604,598 | +6,691,752 | +96.80% | YES |
| Shenandoah | 3,784 | 5,943,207 | +5,939,423 | +156,961% | YES |

## Revenue Comparison

| Development | V30 Revenue (USD) | Latest Revenue (USD) | Delta (USD) | Delta % |
|---|---:|---:|---:|---:|
| Jack St Malo | 25,648,472,772 | 26,591,680,309 | +943,207,537 | +3.68% |
| Stones | 5,582,443,249 | 5,756,376,040 | +173,932,791 | +3.12% |
| Julia | 4,715,155,663 | 4,916,924,582 | +201,768,918 | +4.28% |
| Big Foot | 4,737,808,706 | 5,083,426,680 | +345,617,974 | +7.29% |
| Cascade Chinook | 2,326,873,536 | 2,703,406,692 | +376,533,156 | +16.18% |
| Anchor | 476,309,534 | 912,358,986 | +436,049,453 | +91.55% |
| Shenandoah | 270,670 | 372,451,942 | +372,181,272 | +137,504% |

## WTI Price Sources

| Month | WTI ($/bbl) | Source |
|---|---:|---|
| Jan 1986 -- Jul 2025 | (historical) | V30 wti_monthly.xlsx (475 months) |
| Aug 2025 | 64.86 | EIA GitHub CSV |
| Sep 2025 | 63.96 | EIA GitHub CSV |
| Oct 2025 | 60.89 | EIA GitHub CSV |

WTI declined ~11% from Jul 2025 ($68.39) to Oct 2025 ($60.89). This reduces
per-barrel revenue for the new production months relative to the V30 period average.

## Deviation Analysis

### Big Foot (+7.93%)

Big Foot continues to produce at significant rates. The 5 new months (Jun--Oct 2025)
added 5.3M barrels, representing an average of ~1.06M bbl/month. This is consistent
with its recent production profile and does not indicate a data anomaly.

### Anchor (+96.80%)

Anchor achieved first oil in Aug 2024 and had only 10 months of production in the V30
baseline (6.9M bbl). The extended window adds 5 months (Jun--Oct 2025) during the
ramp-up phase, nearly doubling cumulative production to 13.6M bbl across 15 months.
Average monthly production of ~907K bbl/month indicates a healthy ramp-up trajectory.

### Cascade Chinook (+12.44%)

Cascade Chinook's first_oil was corrected from 2014-01-01 (golden baseline) to
2012-09-01 based on OGOR production records showing sustained single-well commercial
output starting Sep 2012. This adds ~16 months of production (Sep 2012 -- Dec 2013,
~3.26M bbl) that were previously excluded by the V30 first_oil boundary. The golden
baseline is not modified; the correction is applied via `first_oil_overrides` in code.

### Shenandoah (+156,961%)

Shenandoah achieved first oil in Feb 2025 and had minimal production in the V30
baseline (3,784 bbl over 4 months -- likely well-test volumes). The extended window
captures 5 producing months (Feb--Oct 2025, noting some months now have real production
volumes) totaling 5.9M bbl. This is the expected transition from well-test to
commercial production.

## Well-Test vs Commercial Classification

OGOR records are classified using a priority-based scheme:

1. `PRODUCT_CODE='T'` => well_test (test production code)
2. `WELL_STAT_CD='1'` (Exploratory) + oil > 0 => well_test
3. date < first_oil for the development => well_test (pre-commercial boundary)
4. oil > 0 => commercial
5. oil == 0 => non_producing

| Development | Commercial Oil (BBL) | Well-Test Oil (BBL) | Well-Test Records |
|---|---:|---:|---:|
| Jack St Malo | 421,032,342 | 205,380 | 3 |
| Stones | 86,326,766 | 0 | 0 |
| Julia | 74,028,262 | 0 | 0 |
| Big Foot | 72,174,604 | 0 | 0 |
| Cascade Chinook | 38,593,041 | 0 | 0 |
| Anchor | 13,604,598 | 0 | 0 |
| Shenandoah | 5,943,207 | 0 | 0 |

Jack St Malo has 2 OGOR records with `PRODUCT_CODE='T'` (Aug 2012: 46,451 bbl;
Jan 2013: 76,878 bbl) plus 1 additional well-test record, totaling 205,380 bbl
of well-test production. These pre-date JSM's commercial first oil (Dec 2014)
and were already excluded from V30 totals by the first_oil filter.

## Exploration Projects (Unchanged)

- **North Platte**: No production (pre-FID)
- **Kaskida**: No production (pre-FID)
- **Tiber**: No production (pre-FID)

## Changes from V30 Inputs

| Component | V30 | Latest |
|---|---|---|
| OGOR data file | ogora2025delimit.zip | Same file |
| Production window | Sep 2000 -- May 2025 | Sep 2000 -- Oct 2025 |
| WTI prices | Jan 1986 -- Jul 2025 (xlsx) | Jan 1986 -- Oct 2025 (xlsx + EIA) |
| Lease mappings | leases.xlsx | Same (no changes) |
| First oil dates | golden_baseline_v30.yml | CC corrected: 2012-09-01 (via overrides) |
| Nov 2025 OGOR | N/A | Excluded (partial: 2,671 records) |

## Verification

- V30 regression tests: 12/12 passed (no regression from first_oil_overrides)
- WTI price tests: 7/7 passed
- Extended production tests: 22/22 passed
- Latest runner tests: 11/11 passed (incl. classification + CC correction)
- Production classifier tests: 11/11 passed (8 unit + 2 integration + 1 summary)
- Field inputs tests: 4/4 passed
- **Total: 67/67 tests passed**
