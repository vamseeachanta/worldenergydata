# Gulf of America well production by water depth

This part of *Life of a Gulf of America well* follows federal Gulf wells from completion to first production, then through changes in oil rate and the first recorded work after completion. The Bureau of Safety and Environmental Enforcement (BSEE) files cover 261 consecutive production months from January 2005 through September 2026. The nine months of 2026 form a partial year. September is provisional.

| Water depth (m) | Producing wells in 2005 | Producing wells in 2025 | Completion lag, median (middle half), months | Month 60 median oil rate, % of baseline (wells) | Year 5 activity report, % | Year 5 intervention approval, % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Under 100 | 5,387 | 1,097 | 1 (0 to 4) | 18.7 (499) | 69.8 | 67.3 |
| 100 to under 500 | 707 | 213 | 0 (0 to 1) | 19.9 (84) | 71.1 | 62.0 |
| 500 to under 1,500 | 314 | 358 | 1 (0 to 6) | 42.6 (149) | 65.9 | 57.1 |
| 1,500 and deeper | 47 | 287 | 1 (0 to 4) | 48.1 (137) | 59.2 | 59.2 |
| All assigned depths | 6,455 | 1,955 | 1 (0 to 4) | 26.8 (869) | 68.0 | 64.4 |

*Table 1. Headcounts use distinct producing wells in the year. The lag, oil rate and event columns cover only the spud cohort defined under Completion and first production. Lag uses pairs with first production in or after the completion month. Oil rates use wells with measurable rates at month 60. Event shares use wells observed long enough to reach year 5.* [Headline values and source rows](output/numbers.json)

## Rerun the analysis

Run from this example directory in a checkout with LF line endings for `source_pins.json` and the two hash-verified Python references. The script uses the series' existing API number normalizer and intervention classifier and declares its Python package versions for `uv`. The following commands download each ZIP from its BSEE URL into the input directory and regenerate the eight CSVs, headline JSON, check record and five SVG/PNG pairs in `output/`.

```sh
export BSEE_PROD_DATA_DIR="$(mktemp -d)"
python3 - <<'PY'
import json
import os
from pathlib import Path
from subprocess import run

directory = Path(os.environ["BSEE_PROD_DATA_DIR"])
for source in json.loads(Path("source_pins.json").read_text())["sources"]:
    run(["curl", "--fail", "--location", "--show-error", "--silent",
         "--output", str(directory / source["name"]), source["url"]], check=True)
PY
uv run derive.py --data-dir "$BSEE_PROD_DATA_DIR"
```

With the environment variable set, `uv run derive.py` uses the same directory. To write a separate build, pass `--output-dir` with a destination directory. BSEE replaces archives at these URLs in place. A later download of a replaced file fails the SHA-256 check. Reproducing the tables requires the exact ZIP bytes in the pin table below.

## Production and depth

A well is the first ten digits of its API number (API10). A well enters the Gulf inventory when its boreholes consistently carry region code `G` and its boreholes include a non-cancelled bore. The series selects the `ST00BP00` original hole, preferring an API ending in `00`, then the earliest spud, then the lowest API. If that hole has no usable depth, its non-cancelled bores must agree on a single available nonnegative depth. BSEE reports water depth in feet. The series converts feet to metres. Each depth band includes its lower limit. [Borehole field definitions](../../../docs/knowledge-base/bsee/data-dictionaries/wells/borehole-fields.md)

Of 37,529 Gulf wells with a non-cancelled bore, 2,133 have differing depths across bores and seven have no assignable depth. The shallowest band includes 64 wells whose selected depth is recorded as zero. The production join excludes 1,326 rows with unresolved Gulf depth (713,710 bbl and 903,500 Mcf) and 34 cancelled-only rows (zero volume of both fluids). [Record counts and volumes by exclusion reason](output/record_counts.csv)

The monthly series sums signed oil and gas volumes from every retained completion record in the headerless OGOR-A files, across product codes. Oil is in barrels (bbl) and gas in thousands of cubic feet (Mcf). A well counts as producing when its signed monthly sum across completions is positive for either oil or gas. Fully reversed bookings contribute their signed volumes and do not qualify a month as producing. Annual headcounts count each producing well once in the year. Adding annual headcounts gives 85,785 well-years across the window, during which 9,525 distinct wells produced. [Monthly production chart](output/monthly_production.svg) · [Monthly CSV](output/monthly_production.csv) · [Annual wells chart](output/annual_wells.svg) · [Annual CSV](output/annual_wells.csv) · [Production data guide](../../../docs/modules/bsee/PRODUCTION_DATA_RETRIEVAL_GUIDE.md)

August 2026 contains 4,458 OGOR-A records and 1,635 producing Gulf wells with assigned depths, yielding 63,587,543 bbl and 66,977,246 Mcf. In September, 2,688 records yield 1,050 wells, 36,770,623 bbl and 41,076,638 Mcf. The files cannot distinguish delayed reporting from changes in operations. Annual monthly means average only the months present. [Monthly CSV](output/monthly_production.csv)

## Completion and first production

The completion month comes from the earliest effective borehole status date (`BOREHOLE_STAT_DT`) on an eWell End of Operations Report (EOR) with operation code `C`, meaning completion. All bores and available years are searched before applying the cohort dates. For 58 Gulf wells, an earliest report carries a status other than `COM`. Electronic reports can carry status dates from before electronic filing began and can describe later work on older wells. Earlier paper completions may be missing.

A producing API10 enters the age cohort when it has a first positive OGOR-A month and every non-cancelled bore (`BOREHOLE_STAT_CD` other than `CNL`, any suffix) has a parseable `WELL_SPUD_DATE`, the earliest on or after 1 January 2005. The ledger assigns “spud date incomplete” to 8 producers with a missing or unparseable date, including those with another bore known to predate the cutoff. A further 7,708 producers have complete spud records and an earlier spud. The cohort contains 1,809 wells. Among them, independent checks found zero API10s with an eWell `C` completion before the cutoff and zero with an earlier nonblank OGOR `FIRST_PROD_DATE`, including records without production. The reported date refers to a completion. For 119 cohort wells its earliest reported month differs from the first positive OGOR-A month, which sets the age origin. Production totals include older wells. The prior cohort included wells with blank spud dates on non-cancelled sidetracks. [Cohort changes by depth](impact-r2.md) · [Start counts](output/record_counts.csv) · [Source checks](output/checks.txt)

Wells spudded before 2005 that first produced in 2005 or later fall outside the cohort by definition. Of the 2,514 earlier supported starts, 701 had a pre-window spud and reported first production in the window. The exclusions comprise 479 under 100 m, 67 from 100 to under 500 m, 96 from 500 to under 1,500 m, and 59 at 1,500 m or deeper. Because a well enters only when spudded inside the production window, a well first producing in a given year can have taken no longer than the time since the window opened to develop. Multi-year developments are therefore missing from the earliest start years and from the longest intervention horizons, and the lag quartiles are biased low. [Exclusions by water depth](output/spud_exclusions.csv) · [Earlier supported starts](measure-finding3.md)

Of 2,873 wells with depth and a first recorded completion in 2005 to 2025, 2,766 produced in the observed window and 2,747 produced in or after the completion month. Lag is the difference in calendar months. Of the 2,873 wells, 107 have no positive month and 1,035 producers fall outside the spud cohort. The signed series includes 1,731 pairs. In 31 of those, production predates the first completion month. The chart uses the 1,700 pairs whose production began in or after the completion month, with linearly interpolated quartiles. Dates within the same month yield no elapsed calendar months. The September 2026 cutoff leaves 2025 completions with only 9 to 20 calendar months of follow-up. Wells still awaiting first observed production contribute no lag, so right-censoring can bias the observed 2025 lags downward. The data cannot establish elapsed days, physical tie-in dates or reasons for delay. [Completion lag chart](output/completion_lag.svg) · [Signed and ordered pairs](output/completion_lag.csv)

## Oil rate after first production

For supported starts in 2005 to 2020, month 1 is the first positive month of either fluid. Ages 2 to 60 count calendar months, including gaps. Each well's oil rate is oil volume divided by the number of distinct days with some hydrocarbon production. For multiple completion records, that day count lies between the largest individual count and the smaller of their sum and the days in the month. The rate is measurable only when the bounds coincide and all producing records have valid day counts. In the production window, overlapping day counts leave 12,645 positive well-months unresolved, and another 33 have invalid counts. These exclusions affect rates only. Gas-only months remain in the series when their producing-day rate is measurable. They contribute no oil per producing day.

Each rate is divided by the well's highest measurable oil rate in its first three calendar months. An unresolved positive-oil rate during that period excludes 86 wells. Another 158 lack a positive measurable baseline. Of the remaining 1,330 wells, 869 contribute a rate at month 60. Across ages 1 to 60, 15,268 observed well-months with an eligible baseline lack a usable rate. The median weights contributing wells equally and can exceed the baseline after month 3. Shut-ins, unavailable day counts and the changing set of wells affect the curve. Daily operating histories, reservoir decline parameters, completion-type effects and workover uplift cannot be inferred. [Oil decline chart](output/decline.svg) · [Cohort sizes, contributors and median ratios](output/decline.csv)

Completion type at startup uses the `SUBSEA_COMPLETION_FLAG` on the earliest dated `C` report, when that report falls in or before the startup month. The flag records subsea completion as `YES` or `NO`. An explicit `NO` gives no dry-tree design information. Missing and conflicting flags are unknown, including 61 sets of earliest-date reports with differing flag values. Of the supported starts, 57 have no dated completion report and another 31 first report completion in a later month. Those wells also have unknown completion type at startup. The records cannot resolve ordering within a month.

## Activity and intervention approvals

Two first events are dated strictly after the effective completion date. The first eWell Well Activity Report (WAR) uses `WAR_START_DT`, excluding the completion day itself. It measures reported activity. Incomplete activity-code definitions prevent a classification of every report as a specific intervention. The permit measure uses the first Application for Permit to Modify (APM) approval date (`ACC_STATUS_DATE`) classified as workover/recompletion, production enhancement or other well work. The series classifier excludes initial completion, new-hole preparations and abandonment. Approval does not establish that work took place or when it occurred. [Series permit classifier](../interventions_by_depth/count_interventions.py) · [WAR activity-code evidence](../../../docs/data-sources/bsee/data/WELL_ACTIVITY_CD/publication_status.md)

At year *y*, the denominator includes every supported start whose first positive month plus *12y* months falls within the window. The numerator counts wells with the event by the end of that anniversary month. A well remains eligible after production ceases. Year zero includes earlier events and events during the startup month. A separate count identifies strictly earlier-month events. The startup month does not establish which event occurred first within that month. The final OGOR production month sets the inclusive cutoff for both measures. WAR start dates and classified APM approval dates through 30 September 2026 are eligible. Later dates in the November well snapshot are excluded before selecting the first event per API10.

At year 5, 1,549 of 1,604 eligible wells have a recorded completion by that month. Wells lacking a recorded completion stay in the denominator and cannot contribute a post-completion event. Among those 1,549 wells, 70.4% have a WAR and 66.7% have a qualifying approval by year 5. The intervention CSV and headline JSON identify this denominator as `share_among_completion_observed`. Recent starts drop out at longer horizons, so the share can fall between anniversaries. [Activity and approvals chart](output/interventions.svg) · [Event counts, denominators and shares](output/interventions.csv)

## Checking the results

The headline file gives the source table, filter, fields, operation and values for each citation. The companion table reports distinct producers, median volumes across positive well-months, production after a recorded completion and events by the cutoff. Its by-cutoff shares use all supported starts in each band. A 2005 start has more than 20 years of follow-up, while a 2026 start has at most eight elapsed months. These shares mix unequal periods of observation across depths. Their signed median event ages include only events observed by the cutoff. For comparisons at a common age, use the anniversary shares in Table 1. The coverage, lag, decline and intervention columns have different denominators. [Headline numbers](output/numbers.json) · [Article summary](output/article_summary.csv)

The disposition ledger records the raw August and September row counts and the exclusions that determine the startup cohort. The check record includes the depth, completion and startup diagnostics cited above. The build checks that band counts and volumes sum to the pooled values. Pooled medians use the underlying wells, and pooled shares use the pooled numerator and denominator. The ledger records reason-coded drops for each filter. Separate conservation checks compare retained permits with source duplicates and anniversary eligibility with the count of wells that have yet to reach that age. In the borehole quality stages, a `flagged` row counts retained API10s with a missing or invalid value on any bore. These diagnostic counts are excluded from the drop totals and audit headlines. A row can pass through several stages, so totals across stages would repeat observations. Checks also cover the source hashes, an independent raw CSV recount for the last two months, CSV and JSON readback, PNG decoding and SVG markup. [Check record](output/checks.txt) · [Disposition ledger](output/record_counts.csv)

From the repository root, `uv run pytest -q tests/unit/bsee/test_production_by_depth.py` checks the delivered tables and pins. With `BSEE_PROD_DATA_DIR` set to the directory of pinned ZIPs, the suite also rebuilds and compares output bytes.

## BSEE input pins

The well snapshot was collected on 23 November 2026 and the production and lease snapshot on 25 November 2026 (UTC). The two manifest hashes in the check record identify the original manifests verified when their public file pins were exported. On rerun, the build verifies the portable pin set and hashes all 29 ZIPs before calculation. The four well archives and 22 OGOR-A archives supply the calculations. The lease-level production, lease owner and lease tape archives enter only the archive digest check. [Machine-readable pins](source_pins.json) · [BSEE Data Center](https://www.data.bsee.gov/Main/RawData.aspx)

| Archive and BSEE URL | BSEE Last-Modified (GMT) | SHA-256 | Use |
| --- | --- | --- | --- |
| [BoreholeRawData.zip](https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip) | Mon, 23 Nov 2026 10:31:21 GMT | `72fa55e55fd28db26c59e52b3a43c7d053f9d12a6d06b0a0f6a46ef541c66a5c` | Calculation |
| [eWellEORRawData.zip](https://www.data.bsee.gov/Well/Files/eWellEORRawData.zip) | Mon, 23 Nov 2026 10:36:30 GMT | `b67c61826ea90aa51d7e1f01c2df94bba6e869665a7992cd5438ea538ee603bc` | Calculation |
| [eWellAPMRawData.zip](https://www.data.bsee.gov/Well/Files/eWellAPMRawData.zip) | Mon, 23 Nov 2026 10:36:24 GMT | `1a38ed6cf9eab1f8079bf65d8e5b389cb41cc343cde4ce679e2b6e057fd7da50` | Calculation |
| [eWellWARRawData.zip](https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip) | Mon, 23 Nov 2026 10:42:43 GMT | `84a5860c019d1ae2021c933fbe39127b08f8ab58a8443c6cb285e693aac84e8c` | Calculation |
| [LeaseOwnerRawData.zip](https://www.data.bsee.gov/Leasing/Files/LeaseOwnerRawData.zip) | Tue, 24 Nov 2026 10:45:57 GMT | `1066f324181c52dead37a6c7fe7bb3e61eb74331487b2269e24af8fa6dcc6d22` | Inventory only |
| [ProductionRawData.zip](https://www.data.bsee.gov/Production/Files/ProductionRawData.zip) | Wed, 18 Nov 2026 22:03:55 GMT | `7583e1dbdc44b1e72f48608b5427cd0a02af3e2664d658dc508bdc83942cb089` | Inventory only |
| [lsetapefixed.zip](https://www.data.bsee.gov/Leasing/Files/lsetapefixed.zip) | Mon, 02 Nov 2026 16:44:04 GMT | `46e11a22d1314fe838f31093358f2dbf435d3c5460635d224b4718db77a91c08` | Inventory only |
| [ogora2005delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2005delimit.zip) | Sun, 01 Nov 2026 12:40:41 GMT | `dde7408adfaa0a050851a86306db33516a8e484d9540d80e92ed678e242a74e4` | Calculation |
| [ogora2006delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2006delimit.zip) | Sun, 01 Nov 2026 12:41:31 GMT | `c37ba12045f3c83a09bc8fe24be7f6b19e4b15f9d65b6226ac379527f0457795` | Calculation |
| [ogora2007delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2007delimit.zip) | Sun, 15 Nov 2026 12:26:03 GMT | `0b695d97359be53b8529014c449eb389a35a8ee1d480d9f0de3be431fdf5669f` | Calculation |
| [ogora2008delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2008delimit.zip) | Sun, 15 Nov 2026 12:26:36 GMT | `bace68c4d7580219e1d6cadd95846a3e05eace0c11f9b1d8a46c77f4092701de` | Calculation |
| [ogora2009delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2009delimit.zip) | Sun, 15 Nov 2026 12:27:08 GMT | `7b4577e8e361569e3e7bc2cb9ff50e596bcc9d395c80dabf667dbd6798ed3b00` | Calculation |
| [ogora2010delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2010delimit.zip) | Sun, 15 Nov 2026 12:27:39 GMT | `02725b8066898d448d6cd05bd70b78c1dd93007b88e83f935b1f4392de6b36d7` | Calculation |
| [ogora2011delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2011delimit.zip) | Sun, 15 Nov 2026 12:28:10 GMT | `b856d33cf82842f33fd0a1d203fc01009fed98b1e38d294811e391d854756148` | Calculation |
| [ogora2012delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2012delimit.zip) | Sun, 15 Nov 2026 12:28:40 GMT | `c7ce2e9214b93ca60aea9c53a675e89622e1249a34164cbdab2ff2c2e3da90a3` | Calculation |
| [ogora2013delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2013delimit.zip) | Sun, 15 Nov 2026 12:29:07 GMT | `c8e7aa351c793b8bbff315ef7a83d8ba3a8680a399a11da5b5defedf75b902f1` | Calculation |
| [ogora2014delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2014delimit.zip) | Sun, 15 Nov 2026 12:29:33 GMT | `1792ae0518390563d99e499212024c458ad5031747164d66e47934c4f17940c6` | Calculation |
| [ogora2015delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2015delimit.zip) | Sun, 15 Nov 2026 12:30:00 GMT | `ac5cff42c494029e6b534ceb86ec6d7a5f7e2378eec1fc286eec127bc1a11651` | Calculation |
| [ogora2016delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2016delimit.zip) | Sun, 01 Nov 2026 11:42:48 GMT | `a55205533bbc77590ef61ad046ae02f6dd5805db30f0d9a3a5827b043fff7d76` | Calculation |
| [ogora2017delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2017delimit.zip) | Sun, 01 Nov 2026 11:42:23 GMT | `747cdc105fc38a2a45bcd5b6531b57df4df047126d8e95ad4de49e467b1e675e` | Calculation |
| [ogora2018delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2018delimit.zip) | Sun, 01 Nov 2026 11:41:46 GMT | `003d6b276ba997148daa54d92117d9de67af72fd4ceb6b28f7f842131794ccc0` | Calculation |
| [ogora2019delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2019delimit.zip) | Sun, 01 Nov 2026 11:41:10 GMT | `074d113ef23a066f4f4c80001584082c1e3936d350c4b57389460c19c8c82b43` | Calculation |
| [ogora2020delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2020delimit.zip) | Sun, 01 Nov 2026 11:40:57 GMT | `0275ccb21a7833a92391711830617be98aa8ac254e99198afc5f50e925b45fad` | Calculation |
| [ogora2021delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2021delimit.zip) | Sun, 01 Nov 2026 11:40:45 GMT | `076a38e433eac74830ffb524da7b6da1c4ff7823f54630075f0879c088f15f41` | Calculation |
| [ogora2022delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2022delimit.zip) | Sun, 01 Nov 2026 11:40:18 GMT | `cfced4c6fdea540240a4699dfa8a0c23d0952e008b23c34119364329844eda25` | Calculation |
| [ogora2023delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2023delimit.zip) | Sun, 01 Nov 2026 11:39:54 GMT | `2fe009536793135af0d4f3122be4485ccc24ecf25c87562d97906557673edf51` | Calculation |
| [ogora2024delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2024delimit.zip) | Sun, 01 Nov 2026 11:46:35 GMT | `7aa113ca35279aa24c10972d1f682fe0f08b875b37e243dd78eefd5121ce6ef7` | Calculation |
| [ogora2025delimit.zip](https://www.data.bsee.gov/Production/Files/ogora2025delimit.zip) | Sun, 01 Nov 2026 11:47:04 GMT | `95b376d8f15982ad646e71c1a03e04ced90722858714dee193ce595b5d4a5663` | Calculation |
| [ogoradelimit.zip](https://www.data.bsee.gov/Production/Files/ogoradelimit.zip) | Mon, 16 Nov 2026 19:33:29 GMT | `4000c89cc5d07055d2a28b2b1b9578682e51a7169f2af59fd205ee6dec3cdba1` | Calculation |

*Table 2. Source archive versions identified by BSEE response headers and SHA-256 digests of the ZIP bytes.*
