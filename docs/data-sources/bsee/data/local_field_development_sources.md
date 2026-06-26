# Local Field Development Data Sources

Verified: 2026-06-19

This page documents local field-development data sources found under
`/mnt/ace`. These sources support Gulf of Mexico field, lease, well,
production, reserves, and development-plan analysis.

No durable SubseaIQ export, SubseaIQ file name, or obvious SubseaIQ ID
column was found in the inspected files. Treat these as BSEE/BOEM and
project-derived sources. If a SubseaIQ source is added later, likely
join keys are normalized field name, operator, water depth, area/block,
first production year, and lease number.

## Canonical Local Data Root

The large BSEE data tier is outside git:

`/mnt/ace/worldenergydata/data/modules/bsee/`

`/mnt/ace/worldenergydata/RELOCATION-LOG.md` records that:

- `data/modules/bsee/bin/` was relocated to
  `/mnt/ace/worldenergydata/data/modules/bsee/bin/`.
- `data/modules/bsee/zip/` was relocated to
  `/mnt/ace/worldenergydata/data/modules/bsee/zip/`.

For implementation details and refresh behavior, see
[`docs/data/bsee-source-catalog.md`](../../../data/bsee-source-catalog.md).
For a worked field-level infrastructure inventory, see
[`field_structure_inventory_julia_stones_saint_malo.md`](field_structure_inventory_julia_stones_saint_malo.md).
For the product-facing export contract, see
[`field_infrastructure_bundle_contract.md`](field_infrastructure_bundle_contract.md).

## Primary BSEE DataFrames

These files are pandas-pickled DataFrames under
`/mnt/ace/worldenergydata/data/modules/bsee/bin/`.

| Source file | Role | Key fields | Notes |
|---|---|---|---|
| `deepqual/mv_deep_water_field_leases.bin` | Field anchor table | `FLD_NICK_NAME`, `FIELD_NAME_CODE`, `LEASE_NUMBER`, `AREA_CODE`, `BLOCK_NUMBER`, `FLD_AVG_WTR_DPTH`, `BUS_ASC_NAME`, `FLD_DISCVR_DATE`, `FIRST_PROD_DATE` | Best field-level anchor. |
| `apiraw/mv_api_list_all.bin` | Well/API registry | `API_WELL_NUMBER`, `WELL_NAME`, `COMPANY_NAME`, `BOTM_FLD_NAME_CD`, surface/bottom area/block/lease columns | `BOTM_FLD_NAME_CD` likely joins to `FIELD_NAME_CODE`. |
| `platstruc/mv_platstruc_structures.bin` | Platform/structure table | `FIELD_NAME_CODE`, `STRUCTURE_NAME`, `COMPLEX_ID_NUM`, `LEASE_NUMBER`, `WATER_DEPTH` | Adds structure and water-depth context. |
| `production_raw/mv_productiondata.bin` | Lease-month production | `LEASE_NUMBER`, `PROD_MONTH`, `PROD_YEAR`, oil/gas/condensate/water production columns | Joins to fields through lease number. |
| `lab/mv_lease_area_block.bin` | Lease/area/block register | `LEASE_NUMBER`, `AREA_CODE`, `BLOCK_NUM`, `LEASE_STATUS_CD`, `BLK_MAX_WTR_DPTH` | Lease/block normalization. |
| `serialreg/mv_serreg_leases.bin` | Serial lease register | `LEASE_NUMBER`, `LEASE_EFF_DATE`, `LEASE_STATUS_CD`, `SALE_NUMBER`, `SALE_DATE`, `DESCRIPTION` | Sale/status context. |
| `permstruc/mv_subsea_boreholes.bin` | Subsea borehole table | `BUS_ASC_NAME`, `AREA_CODE`, `BLOCK_NUMBER`, `WELL_NAME`, `WATER_DEPTH` | Subsea support table; no SubseaIQ ID observed. |
| `mcpflow/*.bin` | Measurement/commingling systems | system, unit, lease, area/block columns | Bridges systems, units, leases, and operators. |

## Join Pattern

Use `deepqual/mv_deep_water_field_leases.bin` as the anchor:

1. Resolve field to leases with `FIELD_NAME_CODE` and `LEASE_NUMBER`.
2. Join wells through `apiraw/mv_api_list_all.bin` using
   `BOTM_FLD_NAME_CD = FIELD_NAME_CODE`.
3. Join production through `production_raw/mv_productiondata.bin` using
   `LEASE_NUMBER`.
4. Add lease/block context through `lab/mv_lease_area_block.bin`,
   `serialreg/mv_serreg_leases.bin`, and `mcpflow/mv_mcpflowareablock.bin`.
5. Add structure/subsea context through `platstruc/mv_platstruc_structures.bin`
   and `permstruc/mv_subsea_boreholes.bin`.

Code references:

- `src/worldenergydata/bsee/pipeline/field_query.py`
- `src/worldenergydata/bsee/data/refresh/url_registry.py`
- `src/worldenergydata/bsee/data/field_names.py`

## Infrastructure and Structure Data Sources

BSEE also exposes Gulf of America offshore infrastructure data. The
best-supported structure classes are pipelines, pipeline appurtenances,
pipeline ROW, platforms, FMP/measurement locations, commingling-flow
systems, scanned pipeline/plan/ROW document indexes, subsea boreholes,
and decommissioning-cost records.

Official source pages:

- BSEE Offshore Data and Tools:
  `https://www.bsee.gov/offshore-data-tools`
- BSEE Data Center page map:
  `https://www.data.bsee.gov/Main/HtmlPage.aspx?page=presentations`
- Pipeline Information:
  `https://catalog.data.gov/dataset/bsee-data-center-pipeline-information`
- Platform/Rig Information:
  `https://catalog.data.gov/dataset/bsee-data-center-platform-rig-information`
- Geographic Mapping Data:
  `https://catalog.data.gov/dataset/bsee-data-center-geographic-mapping-data-in-digital-format`
- Other Available Resources:
  `https://catalog.data.gov/dataset/bsee-data-center-other-available-resources`

Local structured tables verified on 2026-06-20:

| Structure class | Local table | Verified shape | Key fields | Notes |
|---|---|---:|---|---|
| Pipeline centerline/location points | `pipeloc/mv_pipelinelocation.bin` | 1,946,951 rows x 13 columns | `SEGMENT_NUM`, `ASBUILT_SEQ_NUM`, `LATITUDE`, `LONGITUDE`, `NAD_YEAR_CD`, `PROJ_CODE`, `PPL_APURT_TYPE`, `BIDIR_FLAG` | Best local pipeline geometry-like source. It stores point/sequence records, not engineering drawings. |
| Pipeline ROW descriptions | `rowdesc/mv_rowdescriptions.bin` | 4,522 rows x 7 columns | `ROW_NUMBER`, `PPL_ROW_PRMTE`, `BUS_ASC_NAME`, `ROW_STATUS_CD`, `ROW_DESC` | ROW/permit context; join to scanned ROW and platform ROW records by `ROW_NUMBER`. |
| Platform structures | `platstruc/mv_platstruc_structures.bin` | 7,091 rows x 28 columns | `AREA_CODE`, `BLOCK_NUMBER`, `FIELD_NAME_CODE`, `STRUCTURE_NAME`, `STRUCTURE_NUMBER`, `STRUC_TYPE_CODE`, `COMPLEX_ID_NUM`, `LEASE_NUMBER`, `WATER_DEPTH`, `LATITUDE`, `LONGITUDE` | Best local platform/floating-structure source. Includes installed and removed structures. |
| Platform lease lookup | `platstruc/mv_platstruc_leases.bin` | 31,666 rows x 2 columns | `LEASE_NUMBER`, `LEASE_STATUS_CD` | Lease status bridge for platform joins. |
| Platform ROW lookup | `platstruc/mv_platstruc_rightofways.bin` | 5,225 rows x 4 columns | `SN_ROW`, `ROW_NUMBER`, `ROW_STATUS_CD`, `BUS_ASC_NAME` | ROW bridge for platform/ROW context. |
| Permanent platforms | `permstruc/mv_perm_platforms.bin` | 59 rows x 7 columns | `BUS_ASC_NAME`, `AREA_CODE`, `BLOCK_NUMBER`, `STRUCTURE_NAME`, `MANNED_24_HR_FL`, `WATER_DEPTH`, `INSTALL_DATE` | Small permanent-platform support table. |
| Subsea boreholes | `permstruc/mv_subsea_boreholes.bin` | 593 rows x 5 columns | `BUS_ASC_NAME`, `AREA_CODE`, `BLOCK_NUMBER`, `WELL_NAME`, `WATER_DEPTH` | Subsea support table; no riser/jumper columns observed. |
| FMP measurement locations | `fmp/mv_fmp_meas_locations_all.bin` | 1,187 rows x 16 columns | `SN_MEAS_LOC`, `FMP_NUMBER`, `FMP_NAME`, `COMPLEX_ID_NUM`, `AREA_CODE`, `BLOCK_NUMBER`, `FMP_LOC_NAME`, `FMP_MEAS_TYP_CD`, `BUS_ASC_NAME` | Production measurement infrastructure; joins to platforms by `COMPLEX_ID_NUM` where populated. |
| FMP lease map | `fmp/mv_fmplist_all.bin` | 1,974 rows x 5 columns | `SN_MEAS_LOC_FK`, `LEASE_NUMBER`, `UNIT_AGT_NUMBER`, `UNIT_ALOC_SUFFIX` | Links measurement locations to leases/units. |
| Commingling systems | `mcpflow/mv_mcpflowsystems.bin` | 250 rows x 7 columns | `COMGL_SYS_NUM`, `COMGL_SYS_TYP_CD`, `COMGL_SYS_NAME`, `COMGL_SYS_LOC`, `COMGL_SYS_OPER`, `SORT_NAME` | System-level production/flow context. |
| Commingling measurement locations | `mcpflow/mv_mcpflowmeaslocations.bin` | 8,948 rows x 16 columns | `SN_MEAS_LOC`, `FMP_NUMBER`, `FMP_LOC_NAME`, `COMGL_SYS_NUM`, `FMP_MEAS_TYP_CD`, `SORT_NAME` | Measurement-location bridge into commingling systems. |
| Scanned pipeline maps index | `scanneddocs/scan_pipeline_maps.bin` | 19,853 rows x 15 columns | `DOC_ID`, `SEGMENT_NUMBER`, origin/destination area/block/lease fields, `PPL_SIZE_CODE`, `DOC_TYPE`, `DOC_DATE` | Index to scanned pipeline-map documents, not geometry itself. |
| Scanned ROW index | `scanneddocs/scan_row.bin` | 29,618 rows x 10 columns | `DOC_ID`, `ROW_NUMBER`, `SEGMENT_NUMBER`, `DOC_TYPE`, `DOC_NOTES`, `DOC_DATE` | Best local index for ROW document retrieval. |
| Scanned plans index | `scanneddocs/scan_plans.bin` | 36,109 rows x 10 columns | `DOC_ID`, `LEASE_NUMBER`, `AREA_BLOCK`, `CONTROL_NUMBER`, `DOC_TYPE`, `DATE_RECEIVED` | Likely place to discover plan documents that mention risers, jumpers, tiebacks, or umbilicals. |
| Installed pipeline decom cost | `decomcost/mv_decom_cost_inst_pipe.bin` | 4,418 rows x 19 columns | `AUTH_TYPE_CODE`, `AUTH_NUMBER`, `SEGMENT_NUM`, origin/destination lease/area/block fields, `PPL_SIZE_CODE`, `PROD_CODE`, decom P50/P70/P90 fields | Infrastructure lifecycle/cost data, not as-built geometry. |
| Proposed pipeline decom cost | `decomcost/mv_decom_cost_prop_pipe.bin` | 271 rows x 19 columns | Same as installed-pipeline decom table | Proposed pipeline lifecycle/cost data. |
| Installed platform decom cost | `decomcost/mv_decom_cost_inst_plat.bin` | 1,438 rows x 16 columns | `COMPLEX_ID_NUM`, `STRUCTURE_NUMBER`, `AREA_CODE`, `BLOCK_NUMBER`, `STRUCTURE_NAME`, platform removal/site-clearance P50/P70/P90 fields | Platform lifecycle/cost data. |
| Proposed platform decom cost | `decomcost/mv_decom_cost_prop_plat.bin` | 4 rows x 16 columns | Same as installed-platform decom table | Proposed platform lifecycle/cost data. |

`src/worldenergydata/bsee/data/refresh/url_registry.py` maps these local
tables to BSEE bulk downloads:

- `Pipeline/Files/PipeLocRawData.zip` -> `pipeloc`
- `Pipeline/Files/RowDescRawData.zip` -> `rowdesc`
- `Platform/Files/PlatStrucRawData.zip` -> `platstruc`
- `Other/Files/PermStrucRawData.zip` -> `permstruc`
- `Production/Files/FMPRawData.zip` -> `fmp`
- `Production/Files/MCPFlowRawData.zip` -> `mcpflow`
- `Other/Files/ScannedDocsRawData.zip` -> `scanneddocs`
- `Leasing/Files/DecomCostEstRawData.zip` -> `decomcost`

Riser, jumper, and umbilical status:

- No local BSEE bin filename or inspected column name matched `riser`,
  `jumper`, or `umbilical`.
- Field-level joins found `RISER` values in
  `pipeloc/mv_pipelinelocation.bin` through `PPL_APURT_TYPE`.
- Pipeline decom rows expose product-code and endpoint-name clues such as
  `UMB`, `UMBE`, `UMBH`, `UBEH`, `PLET`, `PLEM`, `manifold`, `FLET`,
  `HIPPS`, `UTA`, and `MFLD`.
- The best structured proxy for jumpers/risers/umbilicals is the pipeline
  location table plus `PPL_APURT_TYPE`, decom endpoint names, pipeline
  appurtenance downloads, scanned pipeline maps, scanned plans, and ROW
  documents.
- APD tables include `RIG_ANCHOR_FLAG`; this is drilling-rig anchoring
  context, not a permanent subsea anchor geometry table.
- BSEE's Other Available Resources page lists a Concrete Anchors ZIP,
  but that file is not currently registered in `url_registry.py`.

## Project-Derived Field Bundles

`/mnt/ace/aceengineercode/config/ong_field_development/results/*.json`
contains named field-development result bundles, including `Julia`,
`St Malo`, `Jack`, `Stones`, `Cascade-Chinook`, and `Anchor`.

Common keys:

- `field_summary_df_dict`
- `well_high_level_df_dict`
- `well_location_df_dict`
- `well_drill_info_df_dict`
- `well_production_summary_df_dict`
- `reserves_dict`
- `oilReserves`
- `fieldReserves`

Treat these as derived/report artifacts rather than raw source-of-record
tables.

## Project Raw Extracts

`/mnt/ace/client_projects/energy_bsee/raw_data/` contains older or
project-scoped BSEE-style extracts:

| Source file | Data type |
|---|---|
| `ExplDevPlans.csv` | Development plans, bottom/surface lease/area/block, operator, water depth |
| `2017 Hist.csv` | Field reserves and cumulative oil/gas history |
| `BHPS_00s.csv`, `BHPS_05s.csv`, `BHPS_10s.csv` | Field, lease, API well, reservoir, pressure-test data |
| `EOR.csv` | End-of-operations well, company, lease, area, and block data |
| `ProdData_*.csv` | Lease production by month/year |
| `LeaseAreaBlock.csv` | Lease/area/block status and water depth |
| `LeaseLiabilities.csv` | Lease decom liability and water depth |
| `PipelinePermitsSegments.csv` | Pipeline segment, lease, operator, ROW, and water-depth metadata |

## Project Excel and SQL Sources

`/mnt/ace/client_projects/energy_bsee/data/O&G/` contains field-specific
Excel workbooks:

- `Stones APDs.xls`
- `jack/CVX APD for jack st malo.xls`
- `woodmac/buckskin_(kc_872).xls`
- `woodmac/shenandoah_(wr_52).xls`
- `stones/Stones_location_data.csv`

`/mnt/ace/aceengineercode/data_manager/sql/bsee.*.sql` contains
API10-focused query definitions for well, production, WAR, directional
survey, and all-wells workflows.
