# Gulf of America exploration and leasing

Part 1 of *Life of a Gulf of America well* follows 8,327 federal Gulf leases from their effective dates in 2005 through 2026 to their first observed exploratory spud and first reported production. Each lease number counts once, including leases with no drilling or production. The November 2026 Bureau of Safety and Environmental Enforcement (BSEE) snapshots support a shorter exploration cohort with at least five years of follow-up.

**Of 7,126 leases effective from 2005 through 2020, 432 (6.06%) were recorded as the bottom lease at an original exploratory spud on or after the lease's effective date.** The count changes with the boreholes, endpoints and dates admitted.

| Matching rule | Matched leases | Share of 7,126 (%) |
| --- | ---: | ---: |
| Original type E spud on the bottom lease (published rule) | 432 | 6.06 |
| Any dated type E bore, bottom lease | 450 | 6.31 |
| Any dated type E bore, bottom or surface lease (variant d) | 477 | 6.69 |
| Any dated bore of any type, bottom or surface lease (variant c) | 546 | 7.66 |
| Any listing of any type at either endpoint, including earlier and undated listings (variant e) | 587 | 8.24 |

*Table 1. Each row counts distinct leases across all water depths. Dated matches require a spud on or after the effective date of the matched lease.* [Exploration counts](output/exploration.csv) · [Bounds by cohort and depth](output/lease_match_bounds.csv)

A surface match identifies where a bore started. Its bottom may lie on another lease. Among the 546 leases with a dated match of any type, 520 have a bottom match, 442 a surface match and 416 both. Of the 41 additional leases counted when both date requirements are removed, 18 have only earlier spuds and 23 have only undated listings. An undated listing alone cannot establish drilling. Neither the endpoint fields nor the snapshot establish intervening well-path crossings or eventual drilling.

## Lease cohort, depth and status

The lease tape (LSETAPE) records a **Lease Effective Date**. No separate issue date is available. The first cohort date is April 1, 2005 and the last is October 1, 2026. The 2025 effective cohort is empty and 2026 is partial. All serial types, sale numbers and current statuses are eligible. Seven leases lack a sale number. The tape has 1,646 undated records that cannot be assigned to a year. The counts describe effective leases and do not measure auction bids or awards. [Lease counts](output/issuance.csv) · [Issuance chart](output/issuance.svg)

Lease IDs retain case, the G prefix where present and leading zeros. Only outer whitespace is stripped. Legacy numeric lease IDs qualify with a Gulf planning-area code. All included records carry a central, eastern or western Gulf planning area.

Each lease, including an undrilled lease, is grouped by its **Block Max Water Depth**. The fixed-width layout supplies low and maximum depths without a field-level unit. The unit dictionary specifies feet. Converted at 0.3048 m/ft, all 8,327 block maxima agree within one metre with the whole-metre maximum in the BSEE production archive's lease lookup. The bands start at 0, 100, 500 and 1,500 m, inclusive of the lower edge. Missing or invalid ranges have an Unknown category. Every cohort lease has a valid range, but 944 ranges cross a band boundary. A borehole on the block can be in a shallower band.

Status is the single **Lease Status Code** on the November 2, 2026 tape, including leases whose rights ended. Each status share uses all leases in the same effective year and depth band as its denominator. The dictionary supports PROD (Production), SOP (Suspension) and UNIT (Unitized). SOP alone does not specify the suspension type. CANCEL, EXPIR, OPERNS, PRIMRY, RELINQ and TERMIN retain their tape spellings because they lack exact dictionary entries. A snapshot cannot reconstruct the status history or establish which leases were legally held in an earlier year. Current PROD status and a past positive crude report measure different outcomes. For censoring, open means PRIMRY, SOP, OPERNS, PROD or UNIT on this tape. Ended means CANCEL, EXPIR, RELINQ or TERMIN. An open lease with no qualifying event in the corresponding file counts as right-censored for that event. This classification describes recorded lease-level events. Unit or production status alone cannot supply a lease-level date. [Status counts and denominators](output/current_status.csv) · [Status chart](output/current_status.svg)

## Spud dates and water depth at the well

The first ten digits of a valid 12-digit API/UWI identify a well. Its earliest dated Gulf spud is selected across all boreholes before any lease or cohort filter. The same earliest record supplies the bore type and bottom lease. Tied earliest records with conflicting types or bottom leases exclude the well. The published rule requires type E (exploratory), an exact bottom-lease ID match and a spud on or after that lease's effective date. The effective day qualifies. No lease-end-date filter applies. The borehole collection cutoff was November 23, 2026 and the latest observed Gulf spud was November 6, 2026.

Leases without a qualifying event remain in the incidence denominator. Timing uses one observation per matched lease, in days from effectiveness to the first qualifying spud, with linearly interpolated quartiles. Across all 432 matched leases, the median is 893.5 days and the middle half spans 440.5 to 1,756.5 days. The medians in both spud charts use leases with an observed event. Leases still open without a qualifying spud bias those medians low. The exploration table reports their count by effective year and band in `open_without_observed_event`. Follow-up varies by issue year. For equal follow-up, `five_year_share_pct` counts leases explored on or before their fifth anniversary. The separate `leases_with_any_e_bore` measure admits subsequent exploratory branches onto the bottom lease. [Lease-block exploration chart](output/exploration.svg)

The well-site table groups those same 432 first events by the borehole's measured **WATER_DEPTH**, converted from feet. Missing or conflicting bands are Unknown. A lease with no spud has no measured site depth. The site table therefore supplies timing only. Its counts overlap the lease-block table. Among 2005 through 2020 leases, the source also lists undated E records with statuses APD (3), AST (2) and CNL (41). No spud is imputed. In the full 2005 through 2026 cohort, 25 E bores predate effectiveness and one well touches a cohort lease with conflicting bottom leases at its first spud. Its candidate leases remain in the denominator. [Well-site timing](output/exploration_site_depth.csv) · [Well-site chart](output/exploration_site_depth.svg)

## First production and primary term

The monthly lease detail credits production to a lease. First crude oil is the earliest month with positive `LEASE_OIL_PROD`, excluding condensate. First hydrocarbon is the earliest month with positive oil, condensate, gas-well gas or oil-well gas. Water-only and zero-volume months do not qualify. Each fluid is tested independently. No production is reassigned across leases. The detail spans November 1947 through October 2026. Only 21 records appear in the final month across the source, so recent production is provisional.

Elapsed time is the difference in calendar month indices. An event in the effective month counts as zero. The source cannot resolve days. Five first hydrocarbon months and four first crude months predate the effective month and are excluded from timing. Among 206 leases with ordered hydrocarbon dates, the median is 51.5 months. Among 122 with ordered crude dates, it is 75 months. These medians use leases with an observed event and are biased low by leases still open without the event, especially in recent cohorts with limited follow-up. In each row, `open_without_observed_event` is the right-censored subset of `without_observed_event`. The difference counts ended leases. [Production counts and quartiles](output/first_production.csv) · [Production chart](output/first_production.svg)

For each timed lease, original term used (%) equals 100 times elapsed months divided by the primary term in months. All cohort leases have a positive primary term. The quartiles retain values above 100%. Every lease in this cohort took effect on the first of a month. A lease reaches the first month past its original term when elapsed months equal 12 times its term in years. For a five-year term, months 0 through 59 are within term and month 60 is past term. The tape records ordered suspension dates on 556 cohort leases. One pair of dates cannot establish total suspended time or legal extensions. Elapsed time includes suspensions. Two leases have a date of first continuous commercial production on the tape without any positive hydrocarbon month in the production detail. Eight have a positive month without that tape date.

## Ownership and audit trail

The ownership snapshot has 3,551 current and four terminated assignment rows. None has a termination date, and 12 lack an effective assignment date. Distinct current company IDs can be counted, but year-by-year historical ownership cannot be reconstructed. [Coverage and source limits](output/coverage.csv)

Each headline specifies its CSV, row filter, column and unit. Each figure is drawn from its saved CSV and is available as SVG and PNG in `output/`. “All bands” and “All years” are separate totals. A blank percentage or quartile has no eligible observations. Zero is a measured value. Audit rows reconcile within each stage and across linked stages. The unit may be a bore record, well, lease-month or lease. Flagged rows stay in the sample. [Headline values](output/numbers.json) · [Record counts and exclusions](output/record_counts.csv) · [Build checks](output/checks.txt)

## Rerun from the four source archives

Run these commands from this example directory. The script reads the ZIP files directly. BSEE replaces archives at the same URLs. A later download with different bytes will fail the SHA-256 check. Reproduction then requires a retained copy matching the pin.

```sh
mkdir -p bsee-inputs
curl -fL https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip -o bsee-inputs/BoreholeRawData.zip
curl -fL https://www.data.bsee.gov/Leasing/Files/lsetapefixed.zip -o bsee-inputs/lsetapefixed.zip
curl -fL https://www.data.bsee.gov/Production/Files/ProductionRawData.zip -o bsee-inputs/ProductionRawData.zip
curl -fL https://www.data.bsee.gov/Leasing/Files/LeaseOwnerRawData.zip -o bsee-inputs/LeaseOwnerRawData.zip
uv run derive.py --data-dir bsee-inputs
```

`BSEE_EXP_DATA_DIR` can supply the input directory in place of `--data-dir`. To write a separate copy of the tables, checks and figures, pass `--output-dir`. The destination is a dedicated output directory. A successful build replaces its contents as a directory, including obsolete files. Replacing a nonempty build requires filesystem support for atomic directory exchange. A fresh destination works without exchange support. Dependencies are declared in the script.

| BSEE archive | BSEE Last-Modified | SHA-256 |
| --- | --- | --- |
| [BoreholeRawData.zip](https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip) | Mon, 23 Nov 2026 10:31:21 GMT | `72fa55e55fd28db26c59e52b3a43c7d053f9d12a6d06b0a0f6a46ef541c66a5c` |
| [lsetapefixed.zip](https://www.data.bsee.gov/Leasing/Files/lsetapefixed.zip) | Mon, 02 Nov 2026 16:44:04 GMT | `46e11a22d1314fe838f31093358f2dbf435d3c5460635d224b4718db77a91c08` |
| [ProductionRawData.zip](https://www.data.bsee.gov/Production/Files/ProductionRawData.zip) | Wed, 18 Nov 2026 22:03:55 GMT | `7583e1dbdc44b1e72f48608b5427cd0a02af3e2664d658dc508bdc83942cb089` |
| [LeaseOwnerRawData.zip](https://www.data.bsee.gov/Leasing/Files/LeaseOwnerRawData.zip) | Tue, 24 Nov 2026 10:45:57 GMT | `1066f324181c52dead37a6c7fe7bb3e61eb74331487b2269e24af8fa6dcc6d22` |

*Table 2. The well snapshot was collected November 23, 2026 UTC and the leasing and production snapshots November 25, 2026 UTC. Last-Modified is the BSEE archive header recorded at collection.* [Machine-readable input pins](source_pins.json)

This build reads the fixed-width parser, layouts and field definitions from **this repository**. The lease parser is `packages/worldenergydata-bsee/src/worldenergydata/bsee/lease_ingest.py`. The fixed-width lease offsets and owner field layout are in `data/modules/bsee/leases/source_schema.json` and `data/modules/bsee/boem_lease_history_layout.json`. The relevant dictionaries in `docs/knowledge-base/bsee/data-dictionaries/` are `leasing/lease-fields.md`, `common/unit-conversions.md`, `wells/borehole-fields.md`, `wells/type-codes.md` and `production/production-fields.md`. The production archive supplies publisher-aggregated lease-months. The build needs no annual OGOR-A or eWell archives.
