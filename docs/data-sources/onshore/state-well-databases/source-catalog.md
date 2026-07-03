# State Well-Database Source Catalog (Multi-State Survey)

Issue: [#711](https://github.com/vamseeachanta/worldenergydata/issues/711)
(parent epic [#708](https://github.com/vamseeachanta/worldenergydata/issues/708)).

This catalog surveys US state oil & gas regulator databases beyond Texas RRC
for bulk-downloadable well data, with a specific focus on **initial/shut-in
pressure and well-test observations** needed by the under-pressured
gas/condensate screen (#708). It follows the Texas RRC pilot pattern
(`docs/data-sources/onshore/texas-rrc/source-catalog.md`): official state
sources are the durable source of record; heavy data lives under `/mnt/ace`,
the repository carries only catalogs, loaders, validators, tests, and report
builders.

Survey date: 2026-07-02. Access details verified against live pages where
possible; entries marked UNVERIFIED need confirmation during ingestion
planning.

## Executive Summary — Pressure-Data Availability

The screening question (#708) needs initial/shut-in pressure per well. Bulk
availability varies enormously by state:

| State | Agency | Wells+production in bulk | **Pressure/test data in bulk** | Cost | Ingestion effort (pressure) |
| --- | --- | --- | --- | --- | --- |
| Kansas | KGS (KCC filings) | Yes — clean CSV | **YES — `kansas_proration_pressures.txt`: per-well annual SHUT_IN_PRESS + deliverability (Hugoton/Panoma program; frozen at 2013)** | Free | **Low** |
| Oklahoma | OCC | Yes — CSV/XLSX + dictionaries | **YES (2010+) — completions extract carries Shut_In_Pressure, Flow_Tubing_Pressure per completion**; Form 1016 back-pressure tests imaged only | Free | **Low-medium** |
| Colorado | ECMC | Yes — CSV/SHP daily | Partial — monthly wellhead tubing/casing pressures in bulk production CSVs (1999+); initial tests structured but per-well scrape only | Free | Low (bulk) / medium-high (initial tests) |
| Louisiana | SONRIS DSS | Yes — paid DSS extract | Structured **WELL_TESTS** table in paid DSS Well set; free portal bans automation | $300–$900/set | Low-medium (after purchase) |
| New Mexico | EMNRD OCD | Yes — nightly FTP XML | **NO — verified absent from bulk export**; C-105/C-122 pressures imaged only | Free | High (OCR) |
| Wyoming | WOGCC | Headers only (WFS); production per-well scrape | No — Form 10 tests + DSTs imaged; structured DST DB incomplete/partially broken | Free | High |
| North Dakota | NDIC | Yes (subscription) | No — IP rates on scout tickets; BHP/DST pressures in scanned well files | $100–$500/yr | High (OCR) |
| Utah | OGM | Yes — clean free CSV | No — imaged Form 8 completions only | Free | High |
| Montana | BOGC | Query-export CSV (no full dump) | UNVERIFIED — completions export fields undocumented; likely imaged | Free | Medium-high |
| Pennsylvania | DEP | Yes — CSV extracts | No — effectively not feasible in bulk | Free | n/a |

Texas RRC (existing pilot) sits alongside these: structured completion/test
bulk data is partial, with W-2/G-1 form fidelity requiring document extraction
(see `../texas-rrc/source-catalog.md`).

## Kansas — Kansas Geological Survey (KGS)

*(KGS is the de facto data publisher for Kansas; KCC filings flow to KGS via the joint KOLAR e-filing system — see KCC notes below.)*

### Bulk datasets

| Dataset | Coverage/fields | URL | Format | Refresh cadence | License/cost | Status |
|---|---|---|---|---|---|---|
| Wells master (`ks_wells.zip`, ~44 MB) | All KS wells: KID, API, lease/well, field, lat/lon, TWN/RGE/SEC, operator, elevation, depth, formation at TD, spud/completion/plug dates, status | https://www.kgs.ku.edu/PRS/petroDB.html → https://www.kgs.ku.edu/PRS/Ora_Archive/ks_wells.zip | Zipped comma-delimited text | Periodic (~monthly; last 2026-06-05) | Free, public | VERIFIED (HEAD 200, 43.8 MB) |
| Wells (GIS, nightly) | Same well layer via ArcGIS Hub; CSV/SHP/GeoJSON/KML/FGDB | https://kgs-gis-data-and-maps-ku.hub.arcgis.com/datasets/KU::oil-and-gas-wells-download/about | Multiple GIS formats | Nightly | Free, public | VERIFIED (page) |
| Lease-level production | Monthly oil & gas volumes for ALL leases, split by decade (1980s → 2020-present); pre-1987 partly cumulative | https://www.kgs.ku.edu/Magellan/Field/lease.html → e.g. https://www.kgs.ku.edu/PRS/Ora_Archive/gas_leases_2020_present.zip ; format doc: https://www.kgs.ku.edu/Magellan/Field/lease_file_format.html | Zipped CSV | ~Monthly (KDOR feed; June 2026 files carry data thru Feb 2026) | Free, public | VERIFIED (page + URLs) |
| County/state production | Annual + monthly aggregates 1950–2026 | https://www.kgs.ku.edu/PRS/petro/interactive.html | XLS/XLSX, ZIP | ~Monthly | Free, public | VERIFIED (page) |
| **Gas proration pressure tests** (`kansas_proration_pressures.txt`, 14 MB) | Per-well **yearly**: SHUT_IN_PRESS, WORKING_PRES, DAILY_RATE, OPEN_FLOW, ADJ_DELIVER, WATER_PROD, METER_PRES, acreage, API, lat/lon, operator — i.e., the Hugoton/Panoma annual shut-in & deliverability program | https://www.kgs.ku.edu/Magellan/Proration/index.html → https://www.kgs.ku.edu/PRS/Ora_Archive/kansas_proration_pressures.txt | Quoted CSV (single flat file) | **Frozen — last updated 2013-10-08; no future additions expected** | Free, public | VERIFIED (sampled file; header + rows confirmed) |
| DST index (`ks_dst_wells.zip`) | Index of all wells with drill-stem tests (digital or scanned), with well attributes + URL to well page; DST measurement values live in the per-well online DB | https://apps.kgs.ku.edu/web/DST/ → https://www.kgs.ku.edu/PRS/Ora_Archive/ks_dst_wells.zip | Zipped CSV (index only) | Periodic (2026-06-05) | Free, public | VERIFIED (downloaded, 10 MB txt; note duplicate rows) |
| Formation tops (`ks_tops.zip`) | Tops statewide, various sources, "not necessarily confirmed by KGS" | https://www.kgs.ku.edu/PRS/Ora_Archive/ks_tops.zip | Zipped CSV | Periodic (2026-06-05) | Free, public | VERIFIED (link) |
| LAS logs index (`ks_las_files.zip`) | Index of 21,780 digital wireline logs (as of 2024-12-31) with per-well LAS download URLs; LAS fetched per well (scriptable) | https://www.kgs.ku.edu/Magellan/Logs/index.html → https://www.kgs.ku.edu/PRS/Ora_Archive/ks_las_files.zip | Zipped CSV index → LAS files | Periodic (2026-06-05) | Free, public | VERIFIED (HEAD 200) |
| Well record scans (ACO-1 etc.) | Scanned ACO-1 completion forms, drillers logs, intents, plugging reports, indexed by API | https://www.kgs.ku.edu/Magellan/ACO/index.html | PDF/TIFF images (indexed) | Ongoing | Free, public | VERIFIED (page) |

### Pressure/test data availability
**Yes — structured bulk pressure data exists and is exactly the Hugoton screen we want.** The Kansas Gas Proration Database bulk file (`kansas_proration_pressures.txt`) contains per-well *annual* SHUT_IN_PRESS, WORKING_PRES, OPEN_FLOW and ADJ_DELIVER from the KCC proration testing program (sampled rows are Hugoton-area wells, e.g. API 15-067-*, 1996–2013 vintages); the file is frozen as of Oct 2013 but fully covers the virgin-to-depleted pressure history question. DST records (initial/final shut-in and flow pressures) exist as digital data for a subset of wells and scans for the rest — the bulk file is only an *index*; digital DST values must be scraped per well from the KGS well pages (chasm.kgs.ku.edu ords endpoints). The Kansas completion form is the **ACO-1** (filed via KOLAR); ACO-1s themselves are imaged only — no structured statewide extract of ACO-1 initial-test data was found (UNVERIFIED whether KGS can supply one on request).

KCC (the regulator) publishes essentially no bulk data itself; its filings are digitized and served by KGS. Post-2013 proration test summaries appear only in KCC orders/dockets (PDF) — UNVERIFIED whether any post-2013 structured extract exists.

### Ingestion effort estimate
**Low.** Everything is flat quoted-CSV over plain HTTP, no auth, no pagination, no rate limits observed. Gotchas: the proration file has a mangled first header line (a stray wrapped fragment `RES","DIFFERENT","COEFF"` on line 2 — skip/repair it); `ks_dst_wells.txt` contains exact duplicate rows; dates are Oracle `DD-Mon-YYYY`; per-well DST/LAS retrieval is a polite crawl (~10⁴–10⁵ requests), not a single download.

## Oklahoma — Oklahoma Corporation Commission (OCC)

### Bulk datasets

| Dataset | Coverage/fields | URL | Format | Refresh cadence | License/cost | Status |
|---|---|---|---|---|---|---|
| Wells master (RBDMS) | All OK wells: API, name, operator, status, type, surface lat/lon, county, PLSS, footages, + deep-link to imaged well records | https://oklahoma.gov/occ/divisions/oil-gas/oil-gas-data.html → https://oklahoma.gov/content/dam/ok/en/occ/documents/og/ogdatafiles/rbdms-wells.csv (+ data dictionary `rbdms-wells-data-dictionary.xlsx`) | CSV (also shapefile: `.../og/esri/files/RBDMS_WELLS.zip`) | Nightly | Free, public | VERIFIED (sampled header + rows) |
| **Completions (1002A extract), 2010-present** | Per completion/formation: API, dates (spud/completion/first prod), TD/TVD, BH location, formation name/code/depth, perf top/bottom, acid/frac, casing, and **initial test block: Test_Date, Oil_BBL_Per_Day, Oil_Gravity, Gas_MCF_Per_Day, GOR, Water_BBL_Per_Day, Pumping_Flowing, Shut_In_Pressure, Choke_Size, Flow_Tubing_Pressure** | `.../ogdatafiles/completions-wells-formations-base.xlsx` (76 MB) + `-daily.xlsx` + `-data-dictionary.xlsx` | XLSX | ~Daily (base last-mod 2026-06-30) | Free, public | VERIFIED + IMPLEMENTED ([#740](https://github.com/vamseeachanta/worldenergydata/issues/740); live `/mnt/ace` snapshot 2026-07-03) |
| Completions legacy (pre-2010) | Historical completions from old Oracle DB (97 MB) | `.../ogdatafiles/completions-wells-legacy.xlsx` | XLSX | Static (last-mod 2025-07-15) | Free, public | VERIFIED file exists; **field list UNVERIFIED** (may or may not carry test pressures) |
| Intent to Drill | Master (154 MB) + 7-day files, w/ formations | `.../ogdatafiles/ITD-wells-formations-base.xlsx`, `ITD-wells-formations-daily.xlsx`, dictionary | XLSX | Daily | Free, public | VERIFIED (HEAD 200) |
| UIC injection volumes | Annual volumes 2006–2025 (+ Arbuckle daily 1012D 2012–2026) | `.../ogdatafiles/20XX-uic-injection-volumes.xlsx`, `dly1012d_20XX.xlsx` | XLSX | Weekly for recent years | Free, public | VERIFIED (links scraped) |
| Operator/purchaser/plugger lists, orphan/state-fund wells, transfers, incidents | Reference/company tables | Same page (`operator-list.xlsx`, `orphan-well-list.xlsx`, `well-transfers-daily.xlsx`, `ogcd-incidents.csv`) | XLSX/CSV | Daily/weekly | Free, public | VERIFIED (links scraped) |
| GIS open data portal | RBDMS wells, well-log layers, etc.; CSV/KML/SHP/GeoJSON export + REST services | https://gisdata-occokc.opendata.arcgis.com/ | ArcGIS Hub | Nightly (wells) | Free, public | VERIFIED (page) |
| Imaged well records | Scanned forms by API: 1002A completions, **Form 1016 back-pressure tests**, logs, etc. (Laserfiche) | https://public.occ.ok.gov/OGCDWellRecords/CustomSearch.aspx?SearchName=OilandGasWellRecordsSearch&dbid=0&repo=OCC ; also https://wellbrowse.occ.ok.gov/ | PDF/TIFF images | Ongoing | Free, public | VERIFIED (pages) |
| Production | **Not at OCC** — kept by Oklahoma Tax Commission (PUN basis, July 1990+); OCC page links out | https://oktap.tax.ok.gov/OkTAP/web?link=PUBLICPUNLKP | Web lookup | n/a | Free lookup | VERIFIED (link); no open bulk download found — UNVERIFIED whether OTC supplies bulk extracts on request (commercial vendors resell it) |

### Pressure/test data availability
**Yes for initial completion tests, no for back-pressure/deliverability tests.** The OCC "Monthly Well Completions" bulk XLSX (2010-present, from Form 1002A filings) carries a structured initial-test block per formation completion including **Shut_In_Pressure**, **Flow_Tubing_Pressure**, Choke_Size, Test_Date and test rates — confirmed from the published data dictionary. Pre-2010 tests are in the legacy XLSX (field content UNVERIFIED) and otherwise only on imaged 1002A scans. **Form 1016 (Back Pressure Test for Natural Gas Wells** — single-point and four-point tests, the Guymon-Hugoton deliverability record) exists **only as imaged documents** in the OCC Well Records imaging system; no structured 1016 extract appears anywhere in the OG data files list.

OGS (Oklahoma Geological Survey / OPIC well data library) is a physical archive (367,000+ wells of paper/microfiche logs, scout tickets) — a manual acquisition channel, not a pipeline source.

### Ingestion effort estimate
**Low-medium.** No auth/rate limits; single-URL downloads with published data dictionaries. Gotchas: workhorse files are large XLSX (76–154 MB — need streaming parse); completion records are one row per formation/test (dedupe by API+Completion_No); nightly overwrite means snapshotting for history; panhandle (Guymon-Hugoton) virgin-pressure work pre-1990 forces imaged Form 1016/1002A parsing (high-effort OCR lane). OTC production has no verified bulk endpoint (per-PUN lookup only).

### Implemented [#740](https://github.com/vamseeachanta/worldenergydata/issues/740) snapshot

The Oklahoma completion-pressure lane now has a direct-source pipeline:

```text
/mnt/ace/worldenergydata/data/modules/oklahoma_occ/
  raw/
    completions-wells-formations-base.xlsx
    completions-wells-formations-data-dictionary.xlsx
    manifest.json
  normalized/completions/completion_pressure_rows.parquet
  curated/pressure/well_pressure_observations.parquet
  curated/pressure/oklahoma_occ_pressure_observation_quality.json
```

Live run 2026-07-03 against the OCC direct URLs downloaded the 76,131,895-byte
base workbook (`Last-Modified: Tue, 30 Jun 2026 00:34:55 GMT`) and dictionary.
The parser read 202,745 completion rows and emitted 108,518 curated pressure
observations across 19,972 Oklahoma wells after filtering to `test_year`
2010-2026. Source anomalies outside that window are counted in the quality
sidecar (`filtered_out_of_window_test_year_count: 8,917`) rather than silently
loaded into the screen.

The pressure observation mix is 78,000 `WHP_shut_in` rows and 30,518
`WHP_flowing_tubing` fallback rows. Both are treated as surface wellhead
screening pressures in the multi-state screen, with the same static gas-column
correction and `era: completion_test_2010_present`. This does not replace a
Form 1016 back-pressure/deliverability lane for Guymon-Hugoton-style
pre-2010/virgin-pressure evidence.

## New Mexico — EMNRD Oil Conservation Division (OCD)

### Bulk datasets
| Dataset | Coverage/fields | URL | Format | Refresh cadence | License/cost | Status |
|---|---|---|---|---|---|---|
| Wells master (`wellhistory`) | Statewide well headers: API, well name/number, well type, status, spud/plug dates, MD/TVD, elevation, directional flag, footages, NAD83 surface location, APD dates | ftp://164.64.106.6/Public/OCD/OCD Interface v1.1/core/wellhistory/wellhistory.zip (anonymous FTP, port 21) | Zipped XML (one XML file per table) | Nightly (verified: file timestamps 2026-07-01/02) | Free, public | VERIFIED (listed + file dates checked) |
| Well completions (`wchistory`) | Per-completion: API+pool, completion date, perf top/bottom depth, first oil/gas production dates, test date (`tst_dte`), C-115 status, well type, production method | ftp://164.64.106.6/Public/OCD/OCD Interface v1.1/core/wchistory/wchistory.zip (40 MB) | Zipped XML | Nightly (verified) | Free | VERIFIED |
| Production/injection volumes (`wcproduction`, `wcinjection`) | C-115 monthly volumes per well completion: month/year, days produced, oil/gas/water volumes, disposition; `wcinjection` includes `inj_pres_num` (injection pressure, PSI) | ftp://164.64.106.6/Public/OCD/OCD Interface v1.1/volumes/ (wcproduction.zip = 962 MB) | Zipped XML | Nightly (verified) | Free | VERIFIED |
| Reference tables (`pool`, `ogrid`, `pod`, `acreage`, `spacingunit`, `property`, `punevent`) | Pool definitions (incl. `del_basis_num` deliverability factor for prorated pools), operators, spacing, allowable-related data | ftp://164.64.106.6/Public/OCD/OCD Interface v1.1/core/ + data dictionary: `OCD Interface v1.1 Data Dictionary.xlsx` in same dir (287 field definitions) | Zipped XML + XLSX dictionary | Nightly | Free | VERIFIED |
| Well tests / pressure | **Not present as a bulk table** — see below | — | — | — | — | VERIFIED ABSENT from bulk export |
| Imaged well files (C-105, C-104, C-103, C-122 etc.) | Scanned/PDF well file documents per API | https://ocdimage.emnrd.nm.gov/imaging/ (OCD Imaging); per-well retrieval only | PDF/TIFF images | As filed | Free | VERIFIED (no bulk image export) |
| GIS | Well surface locations + attributes, districts, units | https://ocd-hub-nm-emnrd.hub.arcgis.com/ (FTP GIS folder deprecated 2023+) | CSV, Shapefile, GeoJSON, KML via ArcGIS Hub / REST API | Ongoing (UNVERIFIED exact cadence) | Free | VERIFIED (hub live; per-dataset cadence unverified) |

The FTP hostname is published only as an image on https://www.emnrd.nm.gov/ocd/ocd-data/ftp-server/ — it is **164.64.106.6** (anonymous, port 21; verified working). EMNRD also runs a REST API portal (https://api.emnrd.nm.gov) — UNVERIFIED whether it adds anything beyond the FTP export for this use case.

### Pressure/test data availability
No initial/shut-in BHP, shut-in wellhead pressure, or deliverability-test values exist in the structured bulk export — full data dictionary dumped: the only pressure field anywhere is monthly injection pressure (`wcinjection.inj_pres_num`), and `wchistory` carries only a test *date* (`tst_dte`). Initial-test data (test date, choke size, **flowing tubing pressure, casing pressure**, rates) lives in Section 5 of Form **C-105** (Well Completion or Recompletion Report — verified on the current form PDF), and San Juan basin back-pressure/deliverability data is on Forms **C-122/C-122-A/B/C** (gas well deliverability tests, shut-in pressures in psia) — all available only as imaged PDFs in OCD Imaging / OCD Permitting attachments. The OCD Online well-detail web pages (wwwapps.emnrd.nm.gov/OCD/OCDPermitting/Data/WellDetails.aspx?api=...) do not display test pressures either, so there is no structured extract to scrape.

### Ingestion effort estimate
**Medium** for the bulk export: anonymous FTP, well-documented schema (XLSX dictionary), but tables are single large XML files (wcproduction.zip ~1 GB compressed, multi-GB uncompressed) requiring streaming XML→columnar parsing; no auth, pagination, or rate limits observed. Getting virgin BHP/SI pressures would be **high** effort — OCR/LLM extraction from imaged C-105/C-122 forms fetched per-API from OCD Imaging.

## Colorado — ECMC (Energy & Carbon Management Commission, formerly COGCC)

### Bulk datasets
| Dataset | Coverage/fields | URL | Format | Refresh cadence | License/cost | Status |
|---|---|---|---|---|---|---|
| Wells master / GIS | ~98k+ well spots: API, well name, operator, status, spud date, field, plus directional bottomhole locations and directional lines | https://ecmc.state.co.us/documents/data/downloads/gis/WELLS_SHP.ZIP (15.7 MB); DIRECTIONAL_BOTTOMHOLE_LOCATIONS_SHP.ZIP; DIRECTIONAL_LINES_SHP.ZIP; COGCC_FIELDS_SHP.zip (field polygons w/ producing formations) | Shapefile (.dbf usable as table); county KMZs also offered | Daily (verified last-modified 2026-07-02) | Free | VERIFIED |
| Production — full report-level | Every Form 7 monthly report per well, 1999–present, one file per year: API, month, days produced, formation code, oil/gas/water volumes, sales, BTU, flared/vented, **GasPressureTubing, GasPressureCasing, WaterPressureTubing, WaterPressureCasing** | https://ecmc.state.co.us/documents/data/downloads/production/{YYYY}_prod_reports.csv (or .zip); current-year rolling monthly_prod.csv (62 MB) | CSV (header verified by sampling) | Annual files static; monthly_prod.csv ~monthly (last-mod 2026-06-12) | Free | VERIFIED (header row fetched) |
| Production summaries + completions table | Per year 1999–2025: "Colorado Annual Production" + "Colorado Well Completions" tables (completed formation per API, spud date, TD date, wellbore status, first production date) | https://ecmc.state.co.us/documents/data/downloads/production/CO%202025%20Annual%20Production%20Summary-xp.zip (pattern `co YYYY Annual Production Summary-xp.zip`) | MS Access .mdb inside zip | Annual (2025 file last-mod 2026-04-24) | Free | VERIFIED |
| Well tests — Mechanical Integrity (Form 21) | MIT test records statewide | https://ecmc.state.co.us/documents/data/downloads/Engineering/MIT.zip (3.2 MB) | Zip (Access/Excel) | Monthly (verified last-mod 2026-07-01) | Free | VERIFIED |
| Daily Activity Dashboard full export | 9 activity datasets (pending/approved permits Form 2/2A, spuds, completions activity, etc.) | https://ecmc.state.co.us/documents/data/downloads/Dashboard/DAD_Export.zip (26 MB) | Zip of tables | Daily (verified last-mod 2026-07-02) | Free | VERIFIED |
| Well analytical (chemistry) data | Gas/produced-water analytical sample data (useful for gas composition, not pressure) | https://ecmc.state.co.us/documents/data/downloads/environmental/ProdWellDownLoad.zip | .mdb in zip | Labeled "Updated Monthly" but last-mod 2024-03-01 (stale) | Free | VERIFIED (staleness noted) |
| Spacing orders | Section/twp/range, cause/order number, well density, unit size, formation code | CauseOrderTabl_Download.zip via spacing-download page | Access .mdb | Post-hearings | Free | Landing page verified; zip path UNVERIFIED |
| Formation tops / initial completion tests | Tops (with logged/cored/DST flags), casing/cement, completed-interval and **Initial Test Data** — per-well COGIS scout pages only, not bulk | https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail?api={CCSSSSS}&type=WELL (verified rendering tops + initial test block) | HTML (structured, scrapeable) | Live DB | Free | VERIFIED (no bulk download exists) |

Master index: https://ecmc.colorado.gov/data-maps-reports/downloadable-data-documents (403 to non-browser user agents). Download guide: https://ecmc.state.co.us/documents/data/downloads/ECMC_Download_Guidance_v2_ada.pdf.

### Pressure/test data availability
Partially structured. The bulk production CSVs (Form 7 report-level, 1999–present) contain **monthly reported wellhead tubing and casing pressures for gas and water** (`GasPressureTubing`, `GasPressureCasing`, `WaterPressureTubing`, `WaterPressureCasing`) — verified in the file header — which supports late-life/shut-in wellhead-pressure screening but is not virgin BHP. Initial completion test data comes from Form 5A (Completed Interval Report) and is stored structured in COGIS: the per-well scout card renders an "Initial Test Data" block (test date, method, hours tested, choke, test-type/measure pairs — verified on an oil-well example showing BBLS_OIL/GRAVITY_OIL; whether gas-well records carry SITP/CAOF measures is UNVERIFIED) plus formation tops with a DSTs column — but **there is no bulk download of the Form 5A test or tops tables**; you scrape FacilityDetail pages by API number. Bradenhead (Form 17) annulus-pressure tests exist as imaged forms only. MIT (Form 21) test data is a genuine structured monthly bulk download.

### Ingestion effort estimate
**Low** for wells master, production CSVs, MIT, and DAD exports: static HTTPS files with stable URL patterns, no auth — gotchas: ecmc.colorado.gov landing pages 403 without a browser User-Agent, annual summary files are Access .mdb (need mdbtools/UCanAccess), 2023 production file has a nonstandard name (`2023_prod_reports_20240903.csv`). Initial-test/tops data is **medium-high**: a ~100k-page scrape of COGIS FacilityDetail (simple `api=` parameter, HTML parse; throttle politely).

## Louisiana — Dept. of Energy & Natural Resources (now Dept. of Conservation & Energy), Office of Conservation — SONRIS

### Bulk datasets

| Dataset | Coverage/fields | URL | Format | Refresh cadence | License/cost | Status |
|---|---|---|---|---|---|---|
| **Data Subscription Service (DSS) — "Well" data set** (wells master + completions + well tests) | Full SONRIS Oracle extract since 1977: WELLS, WELL_HISTORY, WELL_SURFACE_COORDS, BOTTOM_HOLE_COORDS, CASINGS, TUBINGS, PACKERS, PERFORATIONS, SANDS, **WELL_TESTS**, SCOUT_TICKETS/SCOUT_DETAILS, ALLOWABLES, LUW_WELLS/LUWS, PLUG_AND_ABANDONS, code tables (~45 tables; ERD: https://sonlite.dnr.state.la.us/HELP/Wells_erd.pdf) | App: https://adfprodadm.dnr.state.la.us/DataSubscription/ (login); FAQ: http://srfrxprod.dnr.state.la.us/Data_Subscription_Frequently_Asked_Questions.pdf | Structured machine-readable flat-file extracts; app generates a wget download script | Monthly (4th Saturday), full set + incremental | Paid: Well set $300 one-time / $150/mo annual; PayPal cards | VERIFIED (FAQ + login app live) |
| **DSS — "OGP" production data set** | Monthly oil/gas/condensate production since 1977 at LUW (lease/unit/well-group) level (ERD: https://sonlite.dnr.state.la.us/HELP/Ogp_erd.pdf) | Same DSS app | Flat-file extracts + wget script | Monthly | $900 one-time / $350/mo annual | VERIFIED |
| DSS — other sets (Injection, Lease, Royalty, TAS) | Injection incl. perforations, MASIP history, volumes ($75); Lease ($650); Royalty ($950); TAS ($575) | Same DSS app | Flat files | Monthly | Paid per set | VERIFIED |
| **Interactive Data Reports (IDR)** — free query path | Well Profile (261,030 wells), Well Information Search, Well Casings, Well Logs, Production Audit, etc.; per-well tabs incl. **Tests**, Perforations, Casing, OGP production | https://sonlite.dnr.state.la.us/ords/r/sonris_pub/sonris_public/home (www.sonris.com redirects here); guides: https://www.dce.louisiana.gov/page/sonris-guides | Oracle APEX interactive reports, filter + export to Excel/CSV per report | Live DB | Free, but **reCAPTCHA-gated; Terms of Use ban all automated access (7-day+ IP bans)** | VERIFIED |
| GIS — wells/fields layers | DNRSvc/OC MapServer: layer 0 Oil/Gas Wells, 1 Bottom Holes/Bores, 2 Oil/Gas Fields, 9 Injection Wells, Haynesville/TMS subsets, units | https://sonris-gis.dnr.la.gov/arcgis/rest/services (DNRSvc/OC/MapServer) | ArcGIS REST query (JSON, paginated) | UNVERIFIED (likely nightly) | Free | VERIFIED endpoint |
| Document Access (imaged well files) | Scanned well documents (well history/completion forms, test filings) linked from well serial number | Via portal "Document Access" card | TIFF/PDF images | As filed | Free (same anti-bot terms) | VERIFIED exists |

### Pressure/test data availability
Yes — structured, in bulk, via the paid DSS "Well" data set: it contains a **WELL_TESTS table keyed to WELL_SERIAL_NUM** (verified in the Wells ERD) plus SCOUT_TICKETS/SCOUT_DETAILS, and the free per-well IDR "Well Profile" report exposes the same records under a "Tests" tab. These are the potential/well-test records (rates, choke, tubing/casing pressures; exact column list UNVERIFIED — sample files viewable via "Browse Subscription Data" on the DSS site). Original test/completion filings are also imaged, but the tabular test history needs no OCR. Note LA production (OGP) is reported at LUW level, not per well — join through LUW_WELLS.

### Ingestion effort estimate
**Low-medium.** The DSS is purpose-built for this: monthly full + incremental structured extracts with an auto-generated wget script and published ERDs; main gotchas are cost ($300–$900 per set first month), account signup (PayPal, ADF login app), the LUW→well production mapping, and the fact that scraping the free portal is explicitly prohibited (CAPTCHA + IP bans) — DSS is the only sanctioned bulk path. The free ArcGIS REST services cover well headers/locations only.

## Wyoming — Wyoming Oil and Gas Conservation Commission (WOGCC)

### Bulk datasets

| Dataset | Coverage/fields | URL | Format | Refresh cadence | License/cost | Status |
|---|---|---|---|---|---|---|
| **Wells master (GIS/WFS)** | 120,951 wells statewide via GeoServer WFS layer `WY_SHPS:WELL` (+ WELLBH, WELLTRACK, per-type layers, APD layers, WAR). Thin attributes: API (WellId), name, status, type, slant, confidentiality | https://dataexplorer.wogcc.wyo.gov/geoserver/wfs?service=WFS&request=GetCapabilities (WYDE app: https://dataexplorer.wogcc.wyo.gov/) | WFS GetFeature — GeoJSON/GML/CSV/shapefile, no auth | UNVERIFIED (app is live-synced RBDMS) | Free | VERIFIED (sample feature pulled) |
| Wells (ArcGIS Hub mirror) | "WOGCC Well Data" incl. oil/gas/CBM/monitoring/water wells | https://data.geospatialhub.org/datasets/46d3629e4e3b4ef6978cb5e6598f97bb_0 | Hub download (CSV/shapefile/GeoJSON) | UNVERIFIED | Free | VERIFIED exists |
| Statewide well-header Excel download (legacy) | Historically "Down Load" menu offered statewide well data in Excel | https://pipeline.wyo.gov/Download.cfm (field-picker builder) | Excel | — | Free | **BROKEN** — renders an empty field-picker; treat as defunct |
| Production | Per-well/per-reservoir via well page ("Down Load Production/Sales", reservoirexcel.cfm) and a per-API/per-section download cart; county/field/year summary reports | https://pipeline.wyo.gov/ (frames site; e.g. reservoirexcel.cfm?nAPINO=3530933) | HTML/Excel-flavored HTML per well; no statewide flat file found | Live DB | Free | VERIFIED per-well; statewide bulk NOT FOUND |
| **Well tests — Form 10 (Production Test & GOR Report)** | Index queryable by API or township/range (API, well, field, formation, location per test) with links to each test document | https://pipeline.wyo.gov/Form10_entry.cfm (POST Form10.cfm); detail: whatupcores.cfm?nautonum=NNN | Index = HTML table (scrapeable); **test detail = scanned PDF image** (verified) | As filed | Free | VERIFIED |
| Pressure/DST database | "Form 10/Pressure/DST Menu": DSTs by formation/field/location; per-well Cores/Reports/Surveys tab lists DSTs | https://pipeline.wyo.gov/DstOptionMenu.cfm | Map/HTML query; township drill-down (DstTypef.cfm) currently returns 404 | Menu warns data entry is a "long term project… dependent on staffing" (incomplete) | Free | PARTIALLY BROKEN |
| Completions / per-well records | Structured HTML per well: completion (Form 3: spud/completion dates, TD, IP oil/gas/water, formation), casing, perfs, tops, treatments, sundries, "DownLoad All Records" | POST nAPINO to https://pipeline.wyo.gov/wellapi.cfm (frame: Wellapino.cfm) | HTML (Excel-styled) | Live DB | Free | VERIFIED (sampled Jonah well 49-035-30933) |
| Logs | Per-well "Logs-LAS" link on well page | via Wellapino page (2Wyl0gs.cfm) | LAS/images per well | As filed | Free | VERIFIED link exists (content UNVERIFIED) |

### Pressure/test data availability
Mostly **imaged, not bulk-structured**. Form 10 production tests (the file that carries test rates and pressures) exist as scanned PDFs behind a structured HTML index (API/formation/field/location); the index is scrapeable but pressures themselves require OCR of each PDF. A structured DST/pressure database exists behind the "Form 10/Pressure/DST" menu (query by formation — e.g. FRONTIER returns a statewide marker map), but the per-township drill-down 404s today and WOGCC itself flags DST data entry as incomplete; completion records (structured per-well HTML) carry IP rates but no BHP/SIP fields were observed. No statewide flat file of initial/shut-in pressures was found; for GGRB basin-centered-gas screening, expect per-well scraping + Form 10/DST PDF OCR, or a data request to WOGCC (307-234-7147).

### Ingestion effort estimate
**Low for well headers** (clean anonymous WFS → GeoJSON/CSV), **high for production and pressure/test data**: the data site is a 1990s ColdFusion frameset with per-API/per-township queries, a WAF that rejects some URL patterns, Excel-styled HTML needing parsing, per-well PDF images for Form 10s, and a partially broken DST drill-down — plus large-scale scraping load on a state site should be cleared with WOGCC first since the advertised statewide Excel download path is defunct.

## North Dakota — NDIC Department of Mineral Resources, Oil & Gas Division

### Bulk datasets
| Dataset | Coverage/fields | URL | Format | Refresh cadence | License/cost | Status |
|---|---|---|---|---|---|---|
| Monthly Production Reports (statewide, per-well per-month oil/gas/water) | 2003–present; well list with monthly volumes | https://www.dmr.nd.gov/oilgas/mprindex.asp | Searchable PDF (Excel versions also posted, flagged as not amendment-corrected) | ~1 month + 15 days after month end | FREE | Verified |
| Drilling & production statistics (state/county/field historical totals) | Historical oil/gas prod, rig counts, permits | https://www.dmr.nd.gov/oilgas/stats/statisticsvw.asp | PDF/HTML | Monthly | FREE | Verified |
| Public well search + GIS Map Server (surface locations, status, operator) | All permitted wells; "well data updating hourly" | https://www.dmr.nd.gov/oilgas/findwellsvw.asp | HTML/GIS | Hourly | FREE | Verified |
| Well Index (complete index of all ND permitted wells) | File no, API, location, operator, status, dates | Basic Services area (login) | Excel (.zip) | UNVERIFIED (likely daily/weekly) | Basic subscription — $100/yr | Verified (tier content from official Subscriptions PDF) |
| Scout Ticket Data (per-well) | Well header, log/formation tops, casing, completion data, IP test (date, pool, IP oil/MCF/water), cumulative prod, DST recoveries | https://www.dmr.nd.gov/oilgas/basic/getscoutticket.asp (login) | HTML per well (scrapeable, keyed on NDIC file no.) | Ongoing | Basic $100/yr (Premium adds log links, cores, performance curves) | Verified |
| Well/unit/field-pool production & injection histories | Monthly BBL oil, runs, water, MCF prod/sold, vent/flare | Basic/Premium subscriber pages | HTML tables per well/field | Monthly | Basic $100/yr | Verified |
| Well files (complete scanned file: forms, sundries, geological reports, DST reports, core analyses) | All non-confidential wells | Basic Services "Well Files" (login) | Scanned PDF | Ongoing | Basic $100/yr | Verified |
| Flat-file downloads: Well_Index.zip, LogTops.zip, LogTops_Information.zip | Statewide well index + formation tops | Premium "Well Index & Downloads" (login) | Zipped flat files (~3 MB each) | UNVERIFIED | Premium — $500/yr | Verified (shown in official Subscriptions PDF) |
| Digital & image logs (100,600+ logs, 18,650+ wells, incl. DST .las files) | LAS + TIFF; searchable by operator/field/location | Premium "Digital & Image Logs" (login) | LAS/TIFF | Ongoing | Premium $500/yr | Verified |

Tier pricing verified from https://www.dmr.nd.gov/oilgas/Subscription_Services.pdf: **Basic $100/yr, Premium $500/yr** (rates effective Jan 1, 2026). Sign-up: https://www.dmr.nd.gov/oilgas/subscriptionservice.asp; Basic contents: https://www.dmr.nd.gov/oilgas/basicservice.asp.

### Pressure/test data availability
Scout tickets (Basic tier) carry structured-ish per-well test data, but the "Production Test Data" block is **IP rates only** (IP test date, pool, IP oil / IP MCF / IP water) — no BHP or shut-in pressures. DST *recoveries* are listed on scout tickets and DST digital pressure charts exist as .las files under Premium, but actual initial/final shut-in pressures and BHP readings live in the **scanned DST reports and completion forms inside the PDF well file** (Basic tier) — imaged forms, not a structured bulk table. The ND Geological Survey has county-level DST compilations (with shut-in times/pressures) as PDF publications only (https://www.dmr.nd.gov/dmr/ndgs/oil-gas-publications). Bottom line: production and well headers are cheap structured bulk ($100/yr, or free via monthly PDFs/Excels); virgin-pressure screening requires PDF extraction from well files or DST las charts (Premium).

### Ingestion effort estimate
**Medium** for production/header/tops (Excel index + per-well HTML scout tickets keyed on NDIC file number), but the pressure signal itself is **high** effort — OCR/parse of scanned DST/completion PDFs per well. Gotchas: confidential wells excluded; free monthly Excel files don't carry amendments; subscriber pages have a user agreement that should be checked before automated scraping.

## Utah — Division of Oil, Gas & Mining (OGM)

### Bulk datasets
| Dataset | Coverage/fields | URL | Format | Refresh cadence | License/cost | Status |
|---|---|---|---|---|---|---|
| Well Data (all wells: header, API, location, lat/long+UTM, status, type, cum oil/gas/water, lease, confidentiality) | Statewide, 1 record/well | https://oilgas.ogm.utah.gov/pub/Database/Wells.zip (from Data Center https://oilgas.ogm.utah.gov/oilgasweb/data-center/dc-main.xhtml) | Zipped CSV | Ongoing (UNVERIFIED cadence; likely nightly) | FREE | Verified (readme fields inspected) |
| Well History | Historical well event records | /pub/Database/WellHistory.zip | Zipped CSV | Ongoing | FREE | Verified (file exists; field list UNVERIFIED — readme URL redirects) |
| Monthly production 1984–present (5-yr chunks, e.g. Production2020To2024.zip) + pre-1984 legacy (oldprod.exe) | Per-well monthly oil/gas/water incl. shut-in & TA wells | /pub/Database/Production*.zip | Zipped CSV | Monthly | FREE | Verified |
| Disposition, Lat/Long & UTM coordinates, Fields, Operators | Support tables | /pub/Database/*.zip | Zipped CSV | Ongoing | FREE | Verified |
| Data Explorer (live search + scanned well files, logs) | Per-well documents | https://dataexplorer.ogm.utah.gov/ | HTML + imaged PDF/TIFF | Live | FREE | Verified |

### Pressure/test data availability
No dedicated bulk well-test or pressure download exists — the Data Center offers no test/pressure/tops dataset, and the Well Data file's verified schema has no pressure fields. Initial potential tests and shut-in/flowing pressures are on **imaged completion reports (Form 8) and sundries** in the free scanned well files via Data Explorer. Whether WellHistory.zip carries any test values is UNVERIFIED (readme unretrievable). Everything is free.

### Ingestion effort estimate
**Low** for wells+production (clean documented CSVs, API-keyed); **high** if pressures are needed (per-well image parsing via Data Explorer).

## Montana — Board of Oil & Gas Conservation (BOGC)

### Bulk datasets
| Dataset | Coverage/fields | URL | Format | Refresh cadence | License/cost | Status |
|---|---|---|---|---|---|---|
| Data Miner query/export system: wells, formations (tops), cores, coordinates, production by well, field/county/operator production, permits, completions, UIC, leases, board orders | Statewide; query by API/operator/field/county/TRS | https://bogapps.dnrc.mt.gov/dataminer/ (production: http://www.bogc.dnrc.mt.gov/WebApps/DataMiner/Production/ProductionByWell.aspx) | CSV (Excel) or Text export per query | Live database | FREE | Verified (CSV/Text export confirmed on production page) |
| GIS shapefiles (well surface, well paths, field boundaries, units, CBM PODs) | Statewide | https://bogwebfiles.dnrc.mt.gov/GISData/ | Zipped shapefiles | Periodic | FREE | Verified |
| MBOGC file repository (annual reviews, weekly activity letters, hearings) | Documents | https://bogwebfiles.dnrc.mt.gov/ | PDF | Weekly/annual | FREE | Verified |

### Pressure/test data availability
Data Miner exposes completions and formation-tops tables as free CSV exports, but whether the completion export includes IP rates or shut-in pressures is UNVERIFIED (no test/DST/pressure fields documented, no dedicated pressure dataset listed). DST and completion-report pressures for older Montana wells are generally in scanned well documents accessible per-well through Data Miner (imaged, free). No paywall anywhere.

### Ingestion effort estimate
**Medium-low**: free CSV exports, but no single full-database dump — bulk assembly means chunked queries (by county/operator) against ASP.NET pages, which is scrape-fragile.

## Pennsylvania — DEP Office of Oil and Gas Management

### Bulk datasets
| Dataset | Coverage/fields | URL | Format | Refresh cadence | License/cost | Status |
|---|---|---|---|---|---|---|
| Production Report Extracts (statewide, per-well oil/gas/condensate; unconventional monthly, conventional annual) | Monthly back to ~2012, annual to 1980; up to 13 periods per pull (statewide) | https://greenport.pa.gov/ReportExtracts/OG/OilGasWellProdReport | CSV | Monthly (unconventional) / annual (conventional) | FREE | Verified |
| Waste Report Extracts | Unconventional monthly back to 2009 + annual conventional | https://greenport.pa.gov/ReportExtracts/OG/OilGasWellWasteReport | CSV | Monthly/annual | FREE | Verified |
| SPUD data, permits issued, operator well inventory, plugged wells, compliance, well formations, well pad reports | Interactive reports with data download | https://www.pa.gov/agencies/dep/data-and-tools/reports/oil-and-gas-reports | CSV/Excel export from report viewers | Daily–monthly | FREE | Verified (report list; per-report format partly UNVERIFIED) |
| Data dictionary for all report fields | — | https://files.dep.state.pa.us/oilgas/bogm/bogmportalfiles/oilgasreports/HelpDocs/SSRS_Report_Data_Dictionary/DEP_Oil_and_GAS_Reports_Data_Dictionary.pdf | PDF | — | FREE | Verified |

### Pressure/test data availability
PA DEP publishes **no structured well-test or pressure data in bulk** — extracts cover production, waste, SPUD, permits, compliance, and formation names only. Well record/completion reports containing test data exist only as per-well filed documents (imaged), and historical exploration well records sit with DCNR's PA*IRIS/WIS system rather than DEP (UNVERIFIED depth of test content). All access is free.

### Ingestion effort estimate
**Low** for production/waste/SPUD (clean statewide CSV extracts with an official data dictionary); the 13-period-per-pull limit means iterating requests. Pressure screening from PA public data is effectively not feasible in bulk.


## Storage-Contract Extension

Each ingested state extends the existing `/mnt/ace` contract with a sibling
module directory mirroring the `texas_rrc` layout:

```text
/mnt/ace/worldenergydata/data/modules/<state>_<agency>/
  raw/         # official downloads, verbatim, with manifest
  normalized/  # typed, schema-stable tables (parquet)
  curated/     # analysis-ready outputs (e.g., pressure/well_pressure_observations)
```

Module naming: `kansas_kgs`, `oklahoma_occ`, `new_mexico_ocd`,
`louisiana_sonris`, `wyoming_wogcc`, `colorado_ecmc`, `north_dakota_ndic`.
Path rules, manifest requirements, and no-large-files-in-git rules are
inherited unchanged from
`docs/data-sources/onshore/texas-rrc/storage-contract.md`.

## Package-Structure Recommendation

**Recommendation: one generic `worldenergydata-state_regulators` package with
per-state adapters**, not one package per state.

Rationale:

- The Texas RRC pilot proved the shape (api_client / endpoints / processors /
  validators / cache), but that shape is ~90% state-agnostic. Seven copies of
  it would multiply maintenance the same way the pre-monorepo reorg did.
- States differ in *endpoints and file formats*, not in pipeline concept.
  That difference fits an adapter interface
  (`StateSourceAdapter`: catalog → fetch → normalize) with per-state config in
  `config/<state>_<agency>.yml`, consistent with the externalize-config rule.
- `worldenergydata-texas_rrc` stays as-is (it is live and referenced); it can
  be migrated behind the adapter interface later if convergence is worth it.
- Cross-state analysis (the under-pressured screen) then consumes one
  normalized schema — per-well pressure observations keyed by API number —
  regardless of source state.

## Go / No-Go Ranking (which states first)

Ranked by value-per-effort for the under-pressured screen (#708):

1. **Kansas — GO, ingest first (effort: low, ~1 slice).** The
   `kansas_proration_pressures.txt` file is a direct, structured,
   free answer to the screening question for the exact analog trend the
   Collide thread named (Hugoton/Panoma): per-well annual shut-in pressure,
   working pressure, open flow, and adjusted deliverability, joinable to
   `ks_wells.zip` (depth, formation, location) for gradient computation.
   One 14 MB file + one 44 MB wells file. The 2013 freeze does not hurt —
   the virgin-to-depleted pressure history is what the screen needs.
2. **Oklahoma — IMPLEMENTED ([#740](https://github.com/vamseeachanta/worldenergydata/issues/740); effort: low-medium).** The OCC
   completions extract (2010-present, dictionary-verified) provides
   `Shut_In_Pressure` and `Flow_Tubing_Pressure` per formation completion,
   plus TD/TVD and formation depth for the gradient denominator. The live
   [#740](https://github.com/vamseeachanta/worldenergydata/issues/740)
   pipeline writes `/mnt/ace/.../oklahoma_occ/` raw, normalized, curated,
   and quality outputs and feeds the multi-state screen. Pre-2010 legacy XLSX
   interpretation and Form 1016 image extraction remain later OCR/acquisition
   lanes.
3. **Colorado — GO, ingest third (effort: low for bulk).** Monthly wellhead
   tubing/casing pressures in the 1999+ production CSVs give a late-life
   pressure screen out of the box (and Piceance BCG coverage); virgin-test
   values need the COGIS per-well scrape (medium-high, defer to its own
   slice).
4. **New Mexico — DEFER for pressure; optional well-spine ingest.** Excellent
   free nightly bulk export (wells/completions/production), but pressure data
   is verified absent from it — San Juan C-122 deliverability tests are
   imaged only. Ingest the spine only when a consumer needs it; pressure
   extraction is an OCR project.
5. **Louisiana — DEFER pending purchase decision.** The DSS Well set
   ($300 one-time) contains a structured WELL_TESTS table and is the only
   sanctioned bulk path (the free portal bans automation). Worth buying if
   Gulf-coast onshore coverage becomes a priority; not needed for the
   Hugoton-analog screen.
6. **Wyoming, North Dakota, Utah, Montana, Pennsylvania — NO-GO for the
   pressure screen now.** Well headers/production are cheap to add later,
   but pressure evidence in all five is imaged (or paywalled + imaged, ND),
   i.e., an OCR/document-extraction program rather than an ingestion slice.

Suggested follow-on issues once this survey is accepted: (a) Colorado ECMC
wellhead-pressure ingest, (b) Oklahoma Form 1016 image/OCR acquisition for
Panhandle deliverability tests, (c) Oklahoma OTC production acquisition if a
sanctioned bulk path or data-request route is identified.
