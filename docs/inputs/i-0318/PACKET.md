# Public-data input packet

## Summary

Request: refresh HSE, drilling/completion analyses, and interactive public pages; relevant surfaces are [R1], [H1], and [S4].
Found: report inventory, duration tables, quality counts, website snapshots, and historical HSE profiles [R1], [D1-D4], [D10], [H2-H4], [S2].
**SPEC-PARTLY:** embed the quality counts [D10] and define missing-data handling; the complete defect list remains UNVERIFIED [D4], [H6].

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-24 | Pin public input evidence and identify unresolved defects for later specification [R1], [D4], [H6]. |

## Source inventory

WED denotes this repository; SITE denotes the website checkout containing [S1-S5].
WED revision: `a2956f045dc8655f5d17722911537b0ff89b6272`; SITE revision: `21dff6519755593fabd3fac7d298621d02815dba`.
Digests cover opened file bytes; sizes use bytes; file dates are last commit dates; [E1-E2] use UTC retrieval times, not dataset vintages.
References resolve below; [S2] uses a uniquely resolved filename glob.
Software/documentation reuse follows [L1]; third-party payload rights require separate confirmation [H5], [H6].
Only paths, digests, schemas, and permitted metadata are reproduced; publication permissions below apply to this metadata [H6].

| ID | Location | SHA256 | Size | Commit date | Contents | Units and population | Reuse; public eligibility |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| R1 | `WED:docs/modules/report-inventory.csv` | `116b0711a7ea202cca3df236ca9c65ea8d3f62716dfba1c366eee3b03197691f` | 36395 bytes | 2026-10-21 | Report publication inventory | entries; 306 entries | ours; MIT; metadata: yes |
| D1 | `WED:docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days_v21_kc.csv` | `a6fdd82382ef6c564c0fa0576625630f0f49a969390cdadfb66c02bb5a3bfd64` | 20834 bytes | 2026-07-07 | Retained drilling/completion export | days, ft, ppg; 253 rows | public origin; terms UNVERIFIED; metadata: yes |
| D2 | `WED:docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.xlsx` | `3ecfa1128b33edf73db3a793f8839c98c50bc27184487a8af579c5ef22795e7f` | 36744 bytes | 2026-03-24 | Retained workbook, Sheet1 | days, ft, ppg; 217 keyed rows | public origin; terms UNVERIFIED; metadata: yes |
| D3 | `WED:docs/data-sources/bsee/analysis/rig_days/day_basis_comparison.csv` | `a54e487cd18a9dd50a4c350f5a08121dd9c82ab51d6382f79d85e62047e7db4b` | 204882 bytes | 2026-10-13 | Comparison and coverage diagnostics | days, percent; 550 source/bore rows | ours; MIT; metadata: yes |
| D4 | `WED:docs/data-sources/bsee/analysis/rig_days/day_basis_comparison.md` | `41a056960e9a95e2ed49a03e8878cf3ce925a6544d65f5f651527efae6dbc92a` | 30604 bytes | 2026-10-20 | Inventory, methods, unmatched identifiers | days; report, not cases | ours; MIT; yes |
| D5 | `WED:data/modules/bsee/current/operations/well_activity_summary.csv` | `38b7a5af590621831bcd6aa7b7864724eedd55faaeae8f6d4232d840c20f605d` | 9431 bytes | 2026-03-24 | Sparse weekly activity sample | dates, ft, ppg; 100 rows | public origin; terms UNVERIFIED; metadata: yes |
| D6 | `WED:docs/modules/bsee/analysis/rig_days/war_data_608124003301.csv` | `e8373153ecff585c8c49bd1b2598640498f080815b30bc19779c8335c34cf121` | 9072 bytes | 2026-03-24 | Coded weekly history | dates, ft, ppg; 32 rows | public origin; terms UNVERIFIED; metadata: yes |
| D7 | `WED:docs/modules/bsee/analysis/rig_days/war_data_608124009500.csv` | `6c4726fa88c8ec88c06358bc65b55cec6e1fcede1241285a6021758a184c0a14` | 12281 bytes | 2026-03-24 | Coded weekly history | dates, ft, ppg; 45 rows | public origin; terms UNVERIFIED; metadata: yes |
| D8 | `WED:packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/ratified_day_basis_comparison.py` | `b93853c3911b427860dca33fec4179486d3714093e375f0d9f367115b12a14d5` | 15860 bytes | 2026-10-20 | Executable date and interval definitions | days; code, not cases | ours; MIT; yes |
| D9 | `WED:config/analysis/bsee/completion_intervention.json` | `59730d05cecf07a1ec62519961f6438133e60f7680c766a0b6aafc9d736ded02` | 3352 bytes | 2026-10-14 | Pinned archive URLs, digests, and criteria | not applicable; configuration | ours; MIT; metadata: yes |
| D10 | `WED:docs/modules/bsee/analysis/completion_intervention/results.json` | `04b5674f53a71c640ecf50d3eed2e7c5553dc9f09779d62b8e20f1b415b95b76` | 406434 bytes | 2026-10-14 | Completion/intervention catalogue and quality counts | records; 72844 completion rows, 369775 WAR rows | ours; MIT; metadata: yes |
| D11 | `WED:docs/modules/bsee/analysis/completion_intervention/manifest.json` | `bf7286a56c66ab19c80d96da55fee980f2cca7213a38590ba17fe29772cc1bc4` | 3727 bytes | 2026-10-14 | Output digests and source provenance | not applicable; manifest | ours; MIT; metadata: yes |
| D12 | `WED:packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/completion_intervention/activity.py` | `0bba2c9447d2fd462908f641b47a0939133cd68e17da84fb5e82f2bd08a57c12` | 18465 bytes | 2026-10-14 | Join keys and quality-counter definitions | records; code, not cases | ours; MIT; metadata: yes |
| H1 | `WED:reports/hse/wrk012_hse_data_audit.md` | `f1cfa3de5b9659442e7cd7a6d9d32a476d48f34baeee26352ca63272e85b2fad` | 19234 bytes | 2026-03-24 | Historical HSE coverage and defect audit | incident counts; report, not cases | ours; MIT; metadata: yes |
| H2 | `WED:reports/hse/intervention-hse-patterns-2026-05-18-explore.json` | `5671e784e38de631dc65be1da48ea5d6c46bb48bdbb707321468abef279f4259` | 4042 bytes | 2026-05-24 | Historical database and WAR profile | incidents, bytes; aggregate profile | ours; MIT; metadata: yes |
| H3 | `WED:reports/hse/drilling-hse-patterns-2026-07-05.json` | `d47430f758ac610a0a11dcd1b6fa639ae5a88603dec08f7b5fed0fbb6c9216bf` | 2765 bytes | 2026-07-06 | Historical drilling classifier results | incidents, percent; aggregate profile | ours; MIT; metadata: yes |
| H4 | `WED:data/modules/hse/offshore/collection_manifest.json` | `8f09fc889e0fed8687e3e53f1a0cd7a5ac5851035730e898e24f4533c17c7ad9` | 2066 bytes | 2026-10-19 | Candidate collection acceptance gates | events; 50 candidates, 0 accepted | ours; MIT; metadata: yes |
| H5 | `WED:data/modules/hse/offshore/source_registry.json` | `3f4634917ef4aa0d0fe5eadf0e9a797c53393f0ca91105cfa1a6590fe6b56f0e` | 8282 bytes | 2026-10-19 | Source URLs and reuse restrictions | not applicable; registry | third-party terms recorded; metadata: yes |
| H6 | `WED:data/modules/hse/offshore/README.md` | `75da251722dd012077e31af03a7e3aa3be924072bba6cc2976dee8affab77616` | 7528 bytes | 2026-10-24 | Canonical index and review requirements | not applicable; documentation | ours; MIT; yes |
| H7 | `WED:packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incinv_importer.py` | `b12a33b5090f7558ba954e97d5a456bc611617202255644c4e404cf5b0d70737` | 11241 bytes | 2026-06-24 | Incident schema and generated keys | dates, incident counts; code | ours; MIT; yes |
| H8 | `WED:packages/worldenergydata-bsee/src/worldenergydata/hse/acquirers/bsee_acquirer.py` | `ff7d4962ff13c65b6a9c9636491f9dc1529f69fb2258587c2a31361bc0cce84d` | 10709 bytes | 2026-06-24 | Regulator acquisition URLs | not applicable; code | ours; MIT; yes |
| S1 | `SITE:demos/hse-risk-dashboard-data.js` | `53057448b3c094418dceab3bd45b5108a8edbacd45a0d2994ba3f37978587ab4` | 11338 bytes | 2026-02-24 | Embedded risk scores | dimensionless scores, incident counts; code | reuse UNVERIFIED; metadata: yes |
| S2 | `SITE:data/hf-cache/*__dc_bores.json` | `c0ac5fd09ffb9763f55cd7f484f0a0f34bbb61d8d3e2abc8d9cae7ce823f32a5` | 131091 bytes | 2026-07-26 | Website drilling/completion snapshot | days, ft, ppg; 253 rows | reuse UNVERIFIED; metadata: yes |
| S3 | `SITE:scripts/generate_marine_safety_data.py` | `d4edcf131f8913f7288fbbb3f23ccccf263394563557f8adae5f81b813da5987` | 8126 bytes | 2026-02-13 | Sample-data generator | incident counts; code, not cases | reuse UNVERIFIED; metadata: yes |
| S4 | `SITE:demos/hse-risk-dashboard.html` | `985c2fa1aeac5181a16ff915e221c8c3d73356ef55e74aa7d04d9944286e3de9` | 35619 bytes | 2026-08-04 | Interactive dashboard and limitations | dimensionless scores; page | reuse UNVERIFIED; metadata: yes |
| S5 | `SITE:scripts/refresh-hf-data.js` | `fe7c339d31d927a25b44003c658b7cb6ecc2f9221ca4593524987eb457488c59` | 2050 bytes | 2026-07-26 | Snapshot refresh and publication route | not applicable; code | reuse UNVERIFIED; metadata: yes |
| L1 | `WED:LICENSE` | `abe9282066701ba45ec516e77329e14f5e27e5ae462fd1fd23fe9f62e27d4d91` | 1071 bytes | 2026-03-24 | Software and documentation licence | not applicable; licence | ours; MIT; yes |
| E1 | <https://www.data.bsee.gov/Main/HtmlPage.aspx?page=boreholeFields> | `7d3eb1bf9a1d1b91328f55031720ab5911134ebcfb41aa03d224d2bd6cf013d3` | 35001 bytes | 2026-10-25T02:08:22Z retrieved | Regulator borehole status definitions | not applicable; reference page | public page; metadata: yes; payload terms UNVERIFIED |
| E2 | <https://www.bsee.gov/stats-facts/offshore-incident-statistics> | `6b623967787488b8c1b6f6bc17cbcad011f0caf313b0ca296a115883cff2e611` | 88966 bytes | 2026-10-25T02:08:44Z retrieved | Regulator incident statistics landing page | not applicable; reference page | public page; metadata: yes; payload terms UNVERIFIED |

## Inventory coverage and schemas

[R1] contains 306 report entries: 266 current, 32 undetermined, 5 unverified, and 3 one-off entries.
Its schema is `path,classification,evidence`; publication classification does not certify calculation correctness [R1].
[D1] contains 253 unique API12 identifiers; [D2] contains 217 keyed Sheet1 rows, excluding headers and the unkeyed footer.
Core duration columns are `API_WELL_NUMBER,WELL_SPUD_DATE,TOTAL_DEPTH_DATE,DRILLING_DAYS,COMPLETION_DAYS`; depth uses ft and fluid weight uses ppg [D1], [D2].
[D3] contains 550 source/bore comparisons; 13 rows have held weekly calculations and 537 rows lack repository weekly records.
Coverage concerns 253 distinct bores: 4 matched and 249 unmatched; unmatched API12 identifiers are enumerated in [D4].
Weekly schema requires `API_WELL_NUMBER,WAR_START_DT,WAR_END_DT,WELL_ACTIVITY_CD`; regulator table joins additionally require `SN_WAR` [D4], [D6], [D7].
[D5] has 100 sample rows and no `SN_WAR` column; all 100 rows retain API identifiers.
Affected row locators are CSV lines 2 through 101 in [D5]; these locators are not canonical incident or well keys.
[D6] and [D7] contain 32 and 45 weekly rows respectively, with API identifiers and `SN_WAR` keys.
Milestone drilling means calendar TD minus spud, in days; completion unions reported days from TD onward, including interval endpoints [D8].
Missing or reversed milestones remain unavailable; activity-code unions retain DRL and COM separately; gaps add no days [D4], [D8].
[H7] reads `DATE_OCCURRED,MILITARY_TIME,LEASE_NUMBER,AREA_BLOCK,ACCIDENT_TYPE,PANEL_DISTRICT,STATUS`.
Its incident key combines date, lease, and source-row index; no stable agency incident identifier is supplied by that schema [H7].
[H2] reports 97993 historical incident rows; [H3] reports 1987 investigations and 85 drilling-classified incidents.
These are historical aggregates, not refreshed counts or a record-level defect list [H2], [H3].
[H4] records 50 candidate events, 52 source rows, 0 accepted events, and unavailable complete canonical indexes.
[S1] embeds 20 risk rows with dimensionless scores and incident counts; [S4] describes percentile normalization and proxy limitations.
[S3] generates sample counts using random variation; those outputs cannot establish observed incident trends.
[S2] retains 253 fetched rows without truncation; [S5] reads registered tables and writes snapshots.

## Located defects and intended treatment

[D10] reports 1969 completion rows missing API attribution, 1788 WAR rows missing properties, and 31 completion rows missing parents.
Missing properties mean absent `SN_WAR` matches; missing parents mean absent `SN_EOR` matches; these differ from blank-key counts [D12].
Counters cover different populations and must not be added to derive unique affected records [D10], [D12].
WAR joins use `SN_WAR`; completion-parent joins use `SN_EOR_FK` against `SN_EOR`; missing-record identifiers are not retained in [D10-D12].
[D1] and [S2] share 38 bore records missing both spud and TD dates; their API12 identifiers follow.
Identifiers are dimensionless strings; each listed item represents one bore record in each source [D1], [S2].

`608074033000 608074033100 608074033200 608074033300 608074033400 608074033500`
`608074033600 608074033700 608074034100 608074034300 608074034400 608084007200`
`608084007700 608084007701 608114076100 608114076101 608114076900 608114079600`
`608124005900 608124006300 608124006301 608124006400 608124006401 608124006402`
`608124006403 608124006900 608124007000 608124007200 608124007300 608124007400`
`608124012602 608124014002 608124015200 608124015300 608124015500 608124015501`
`608124015502 608124015503`

[D2] has 31 keyed rows missing at least one milestone; its population differs from [D1] and must remain separate.
Workbook affected API12 identifiers are dimensionless strings; each identifies one keyed row [D2].

`608074033000 608074033100 608114076100 608114076900 608124005900 608124006300`
`608124006301 608124006400 608124006401 608124006402 608124006403 608124006404`
`608124006900 608124007000 608124007200 608124007300 608124007400 608124012602`
`608124013900 608124014000 608124014001 608124014002 608124014003 608124015200`
`608124015300 608124015400 608124015500 608124015501 608124015502 608124015503`
`608124015504`

Across [D1], [D2], [S2], and 177 weekly rows in [D5-D7], the inspected date pairs contain 0 reversed pairs.
Reversed dates remain UNVERIFIED for the requested population; nulls are not reversed dates [D4], [D8].
The export has 0 blank API identifiers and 0 blank lease names; the website snapshot has 0 blank API identifiers [D1], [S2].
The omitted sample join column is established; a missing-key defect in the complete population remains UNVERIFIED [D4], [D5].
Use null durations pending sourced milestone recovery; never swap dates automatically or infer zero activity from missing histories [D4], [D8].
Recover `SN_WAR` from authoritative weekly records before property joins; the sparse sample cannot establish complete histories [D4], [D5].
Resolve missing parents and properties against pinned tables; retain unmatched rows with unknown attribution until evidence supports correction [D9-D12].
[H1] records historical dropped violation/statistics fields and incorrect download targets; current defect counts and affected incident keys remain UNVERIFIED.
[H6] requires complete identity indexes and independent evidence review before canonical acceptance; [H4] records these gates as unmet.

## Official source URLs

Opened regulator pages returned HTTP 200 on 2026-10-25 UTC; source vintages remain distinct from retrieval dates [E1], [E2].

- <https://www.data.bsee.gov/Main/HtmlPage.aspx?page=boreholeFields> lists borehole status definitions, including DRL, COM, DSI, and TA.
- <https://www.bsee.gov/stats-facts/offshore-incident-statistics> provides incident statistics and reporting context.

These status definitions do not independently establish weekly activity-code semantics; [D4] identifies that inference limit.
[H8] identifies <https://www.data.bsee.gov/Other/Files/IncInvRawData.zip>; archive contents and current availability are UNVERIFIED.
[D9] records <https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip> and <https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip>; archive bytes were not opened.
[D9-D11] retain archive digests and table schemas; live archive availability and byte agreement remain UNVERIFIED.
[H5] records source-specific restrictions; links do not authorize copying report text or publishing personal details [H6].

## Missing evidence and next steps

| Missing item | Exact inspected limitation | Single next step |
| --- | --- | --- |
| Ledger-pinned inventory and complete defect crosswalk | [R1] inventories reports; [D3] compares durations; neither links the request to defect records. | Maintainer supplies the ledger attachment or public crosswalk identifying affected records. |
| Reversed-date records and corrected values | No reversed pairs occur in inspected [D1], [D2], [D5-D7], [S2]; the alleged population is UNVERIFIED. | Maintainer identifies the source snapshot and affected record identifiers. |
| Full weekly histories and missing-key counts | [D4] names 249 unmatched bores; `data/modules/bsee/bin/war/mv_war_main.bin` and `data/modules/bsee/.local/war/eWellWARRawData.zip` returned `No such file or directory`. | Data maintainer supplies a digest-bound public export of the regulator tables named in [D4]. |
| Canonical HSE records and indexes | [H2] is historical; `data/modules/hse/hse_incidents.db` and `data/modules/hse/raw/bsee/IncInvRawData/mv_acc_investigations.txt` returned `No such file or directory`; [H4], [H6] record unavailable indexes. | HSE maintainer exports complete privacy-reviewed identity indexes under [H6]. |
| Completion/intervention defect identifiers | [D10] preserves aggregate counters, without orphan source keys. | Data maintainer exports failing `SN_WAR`, `SN_EOR_FK`, and completion row identifiers from the snapshots pinned in [D9-D11]. |
| Current HSE defect keys and corrections | [H1] describes importer defects without affected incident identifiers; [H3] contains aggregates. | HSE maintainer supplies a row-level defect export bound to the current database digest. |
| Dashboard numerical lineage and reuse | [S1] embeds scores; [S3] generates samples; [H5] does not qualify every website payload. | Website maintainer supplies source digests, transformations, denominators, and public reuse approval for each retained chart. |

Shared-data replicas referenced by [H3], [D4] also returned `No such file or directory`; no sandbox access denial occurred.

## Recommendation

**SPEC-PARTLY:** embed [R1], [D1-D12], [H4-H8], and [S1-S5] by digest for inventory, null handling, and provenance requirements.
Include the 38 affected export identifiers above; preserve workbook/export populations and distinguish sample outputs from observed statistics [D1], [D2], [S3].
Defer complete numerical refresh and corrected public figures until the missing crosswalk, authoritative histories, and accepted HSE indexes exist [D4], [H6].
Absence outside the opened sources remains UNVERIFIED; no workbook, archive, database, or original report is copied into this packet [D1-D7], [H6].
