## Data Definitions

## Downloaded files (Before 2021)

### Data Downloaded

<https://github.com/vamseeachanta/energydata/blob/8bc9bd788008fc116f57057c7bca28fb0c8eab52/src/energydata/tests/legacy/data>

## Required for Analysis

### Documentation

| File | Key Columns |
|---|---|
| WAR  (Well Activity Report) |  |
| mv_war_main  | SN_WAR, 
Start day, 
end day, 
Rig Name, 
SideTrack Suffix,
 ByPass Suffix,
BOP Test : Test Date, RAM Pressure, Annular Pressure |
| mv_war_main_prop_remark | SN_WAR, TEXT_REMARK |
| mv_war_tubular_summaries_prop | SN_WAR_FK, 
SNWAR_CSNG_INT_FK, 
Casing Setting Bottom MD, 
Casing Setting Top MD
 |
| mv_war_tubular_summaries | SN_WAR_FK, Casing Interval Type CD, Casing hole Size, Casing Size, Casing Weight, Casing Grade, Casing Liner test pressure, Casing Shoe test Pressure, Casing Cement Volume, SN_WAR_CSNG_INTV |
| mv_war_boreholes_view | [API_WELL_NUMBER], [BOTM_LEASE_NUM],[WELL_SPUD_DATE], [TOTAL_DEPTH_DATE], [BOREHOLE_STAT_DT], [BH_TOTAL_MD], [WELL_BORE_TVD] |
| mv_war_main_prop | [SN_WAR],[WELL_NAME_SUFFIX],[WELL_ACTV_START_DT], [TOTAL_DEPTH_DATE],[WELL_ACTIVITY_CD], [WELL_ACTV_END_DT],[DRILLING_MD],[DRILLING_TVD], [DRILL_FLUID_WGT],[GEOCHEM_SMPL_COLLECTED_CD], [LITHO_SAMPLE_COLLECTED_CD],[PALEO_SAMPLE_COLLECTED_CD], [SIDEWALL_SMPL_COLLECTED_CD],[CONV_CORE_COLLECTED_CD], [VELOCITY_SURV_COLLECTED_CD] |
| mv_war_open_hole_tools | SN_OPEN_HOLE_FK, 
LOG_TOOL_TYPE_CODE |
| mv_war_open_hole_runs | SN_WAR_FK, 
BUS_ASC_NAME, 
OPERATIONS_COMPLETED_DATE, 
TOOL_LOGGING_METHOD_NAME, 
LOG_INTV_TOP_MD, 
LOG_INTV_BOTM_MD, 
SN_OPEN_HOLE |
| BOREHOLE_STATUS_CDS | [Value],[Description] |
| EOR (End Of Operations Report) |  |
|  |  |
|  |  |
| mv_eor_completions | [SN_EOR_FK] ,[SN_EOR_WELL_COMP], Production Interval, [COMP_LEASE_NUMBER], [COMP_AREA_CODE], [COMP_BLOCK_NUMBER],[COMP_STATUS_CD] |
| mv_eor_completionsprop | [SN_EOR_FK], 
[SN_EOR_WELL_COMP], 
[COMP_LATITUDE], [COMP_LONGITUDE], 
[COMP_RSVR_NAME], 
[COMP_INTERVAL_NAME] |
| mv_eor_compstatcodes | Reference Table; Value, Value_Description |
| mv_eor_cut_casings |        SN_EOR_FK , CASING_SIZE , CASING_CUT_DATE , CASING_CUT_METHOD_CD , CASING_CUT_DEPTH , CASING_CUT_MDL_IND |
| mv_eor_geomarkers |      [SN_EOR_FK] , [GEO_MARKER_NAME],[TOP_MD] |
| mv_eor_hcbearing_intvl_comps | [SN_EOR_WELL_COMP_FK] , [SN_HC_BEARING_INTVL_FK] |
| mv_hcbearing_intervals | SN_HC_BEARING_INTVL, SN_EOR_FK, INTERVAL_NAME, TOP_MD, BOTTOM_MD, HYDROCARBON_TYPE_CD |
| mv_eor_hydrobarbtypecodes | Reference Table [VALUE] , [VALUE_DESC] |
| mv_eor_mainquery | [SN_EOR] , [EOR_OPERATION_CD]
                                  ,[API_WELL_NUMBER]
                                  ,[WELL_NAME]
                                  ,[WELL_NM_ST_SFIX]
                                  ,[WELL_NM_BP_SFIX]
                                  ,[MMS_COMPANY_NUM]
                                  ,[BUS_ASC_NAME]
                                  ,[BOTM_LEASE_NUMBER]
                                  ,[BOTM_AREA_CODE]
                                  ,[BOTM_BLOCK_NUMBER]
                                  ,[SURF_LEASE_NUMBER]
                                  ,[SURF_AREA_CODE]
                                  ,[SURF_BLOCK_NUMBER]
                                  ,[BOREHOLE_STAT_CD]
                                  ,[BOREHOLE_STAT_DT]
                                  ,[OPERATIONAL_NARRATIVE]
                                  ,[SUBSEA_COMPLETION_FLAG]
                                  ,[SUBSEA_PROTECTION_FLAG]
                                  ,[SUBSEA_COMPLETION_BUOY_FLAG]
                                  ,[SUBSEA_TREE_HEIGHT_AML]
                                  ,[OBSTRUCTION_PROTECTION_FLAG]
                                  ,[OBSTRUCTION_TYPE_CD]
                                  ,[OBSTRUCTION_BUOY_FLAG]
                                  ,[OBSTRUCTION_HEIGHT_AML] |
| mv_eor_mainquery_prop | [SN_EOR] 
,[BOTM_LONGITUDE] 
,[BOTM_LATITUDE] 
,[BH_TOTAL_MD] 
,[WELL_BORE_TVD] 
,[WELL_BP_ST_KICKOFF_MD] |
| mv_eor_perf_intervals | [SN_EOR_WELL_COMP_FK]
                          ,[PERF_TOP_MD]
                          ,[PERF_BOTM_TVD]
                          ,[PERF_TOP_TVD]
                          ,[PERF_BASE_MD] |


