## Filenames and columns 
### Columns required for preparing dataframes

### 1.  Well data 
   

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges_all |
| COMPANY_NAME                  | APIRawData_mv_api_list_all             |
| BOTM_FLD_NAME_CD              | APIRawData_mv_api_list_all             |
| WELL_NAME                     | APDRawData_mv_apd_main_all             |
| WELL_NAME_SUFFIX (Sidetrack or bypass) | APDRawData_mv_apd_main_all    |
| WELL_SPUD_DATE                | APIChangesRawData_mv_apichanges_all        |
| TOTAL_DEPTH_DATE              | APIRawData_mv_api_list_all , BoreholeRawData_mv_boreholes_all, eWellWARRdata_mv_war_boreholes_view |
| BH_TOTAL_MD ( feet )          | APIChangesRawData_mv_apichanges_all, APIRawData_mv_api_list_all |
| WELL_BORE_TVD                 | BoreholeRawData_mv_boreholes_all , eWellEORRawData_mv_eor_mainquery_prop |
| WELL_BP_ST_KICKOFF_MD         | BoreholeRawData_mv_boreholes_all , eWellEORRawData_mv_eor_mainquery_prop |
| BOREHOLE_STAT_CD              | APIRawData_mv_api_list_all , BoreholeRawData_mv_boreholes_all |
| BOREHOLE_STAT_DT              | APIRawData_mv_api_list_all , BoreholeRawData_mv_boreholes_all |
| UNDWTR_COMP_STUB              | BoreholeRawData_mv_boreholes_all       | 
| WATER_DEPTH                   | APDRawData_mv_apd_main_all             |
| SURF_LATITUDE, SURF_LONGITUDE | APDRawData_mv_apd_main_all, BoreholeRawData_mv_boreholes_all |
| BOTM_LATITUDE, BOTM_LONGITUDE | BoreholeRawData_mv_boreholes_all, eWellEORRawData_mv_eor_mainquery_prop    |
| CASING CUT CODE               | BoreholeRawData_mv_boreholes_all       |

**Way Forward:**
DF = 
APDRawData_mv_apd_main_all 
where API_WELL_NUMBER = 'Well_Number'
Merge/Joint with BoreHOLERAwData 
where API_WELL_NUMBER = 'Well_Number'

Minimum column renames. Anything broken in analysis code, we will refactor the code.


### 2. all_bsee_blocks

BOTM_FLD_NAME_CD -  APIRawData_mv_api_list_all.csv 

### 3. ST_BP_and_tree_height

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges |
| WELL_NM_ST_SFIX               | APDRawData_mv_apd_main_all , eWellAPDRawData_mv_apd_main |
| WELL_NM_BP_SFIX               | APDRawData_mv_apd_main_all , eWellAPDRawData_mv_apd_main |
| SUBSEA_TREE_HEIGHT_AML        | eWellEORRawData_mv_eor_mainquery       |
| SN_EOR                        | eWellEORRawData_mv_eor_mainquery , eWellEORRawData_mv_eor_mainquery_prop |

 ### 4. completion_summary

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| WELL_NAME               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges , APIRawData_mv_api_list_all |
| API_WELL_NUMBER              | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges |
| INTERVAL              | eWellEORRawData_mv_eor_completions |
| COMP_AREA_CODE        | eWellEORRawData_mv_eor_completions       |
| COMP_BLOCK_NUMBER                       |  eWellEORRawData_mv_eor_completions |
| COMP_STATUS_CD | eWellEORRawData_mv_eor_completions |
| VALUE , VALUE_DESC | eWellEORRawData_mv_eor_compstatcodes , eWellEORRawData_mv_eor_hydrobarbtypecodes |

### 5. hydrocarbon_bearing_interval

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| WELL_NAME                     | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges , APIRawData_mv_api_list_all |
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges |
| SN_HC_BEARING_INTVL           | eWellEORRawData_mv_eor_hcbearing_intvl_comps , eWellEORRawData_mv_eor_hcbearing_intervals |
| SN_EOR_FK                     | eWellEORRawData_mv_eor_completion ,eWellEORRawData_mv_eor_hcbearing_intervals  |
| INTERVAL_NAME                 | eWellEORRawData_mv_eor_hcbearing_intervals |
| TOP_MD                        | eWellEORRawData_mv_eor_geomarkers , eWellEORRawData_mv_eor_hcbearing_intervals  |
| BOTTOM_MD                     | eWellEORRawData_mv_eor_hcbearing_intervals|
| HYDROCARBON_TYPE_CD           | eWellEORRawData_mv_eor_hcbearing_intervals |

### 6. geology_markers

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges |
| WELL_NAME                     | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges, APIRawData_mv_api_list_all |
| GEO_MARKER_NAME               | eWellAPDRawData_mv_apd_geologic , eWellEORRawData_mv_eor_geomarkers|
| TOP_MD                        | eWellAPDRawData_mv_apd_geologic , eWellEORRawData_mv_eor_geomarkers , eWellEORRawData_mv_eor_hcbearing_intervals  |

### 7. cut_casings

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges  |
| WELL_NAME                     | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges, APIRawData_mv_api_list_all |
| CASING_SIZE                   | eWellAPDRawData_mv_apd_casing_sections , eWellEORRawData_mv_eor_cut_casings |
| CASING_CUT_DATE               | eWellEORRawData_mv_eor_cut_casings |
| CASING_CUT_METHOD_CD          | eWellEORRawData_mv_eor_cut_casings |
| CASING_CUT_DEPTH              | eWellEORRawData_mv_eor_cut_casings |
| CASING_CUT_MDL_IND            | eWellEORRawData_mv_eor_cut_casings |

### 8. completion_properties

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges  |
| COMP_LATITUDE                 | eWellEORRawData_mv_eor_completionsprop |
| COMP_LONGITUDE                | eWellEORRawData_mv_eor_completionsprop|
| COMP_RSVR_NAME                | eWellEORRawData_mv_eor_completionsprop |
| COMP_INTERVAL_NAME            | eWellEORRawData_mv_eor_completionsprop |

### 9. completion_perforations

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| WELL_NAME                     | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges, APIRawData_mv_api_list_all |
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges  |
| PERF_TOP_MD                   | eWellEORRawData_mv_eor_perf_intervals |
| PERF_BOTM_TVD                 | eWellEORRawData_mv_eor_perf_intervals |
| PERF_TOP_TVD                  | eWellEORRawData_mv_eor_perf_intervals |
| PERF_BASE_MD                  | eWellEORRawData_mv_eor_perf_intervals |

### 10. production

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges  |
| COMPLETION_NAME               | BHPSRawData_mv_bhpsurvey_all |
| PRODUCTION_DATE               | ProdPlanAreaRawData_mv_pbpadata |

|   |   |
|   |   | - MISSING COLUMNS

### 11. well_activity_summary

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | eWellWARRawData_mv_war_main|
| WELL_NAME                     | eWellWARRawData_mv_war_main |
| RIG_NAME                      | eWellWARRawData_mv_war_main|
| WAR_START_DT                  | eWellWARRawData_mv_war_main |
| WAR_END_DT                    | eWellWARRawData_mv_war_main |
| WELL_ACTIVITY_CD              | eWellEORRawData_mv_war_main_prop |
| DRILLING_MD                   | eWellEORRawData_mv_war_main_prop |
| DRILL_FLUID_WG                | eWellEORRawData_mv_war_main_prop |

### 12. well_activity_bop_tests

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | eWellWARRawData_mv_war_main  |
| BOP_TEST_DATE                 | eWellWARRawData_mv_war_main |
| RAM_TST_PRSS                  | eWellWARRawData_mv_war_main |
| ANNULAR_TST_PRSS              | eWellWARRawData_mv_war_main |
| BUS_ASC_NAME                  | eWellWARRawData_mv_war_main |

### 13. well_tubulars

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all  |
| WELL_NAME                     | APDRawData_mv_apd_main_all  |
| WAR_START_DT                  | eWellWARRawData_mv_war_main |
| WAR_END_DT                    | eWellWARRawData_mv_war_main |
| CSNG_INTV_TYPE_CD             | eWellWARRawData_mv_war_tabular_summaries |
| CSNG_HOLE_SIZE                | eWellWARRawData_mv_war_tabular_summaries |
| CSNG_SETTING_BOTM_MD          | eWellWARRawData_mv_war_tabular_summaries_prop |
| CSNG_SETTING_TOP_MD           | eWellWARRawData_mv_war_tabular_summaries_prop |
| CASING_SIZE                   | eWellWARRawData_mv_war_tabular_summaries| 
| CASING_WEIGHT                 | eWellAPDRawData_mv_apd_casing_sections , eWellWARRawData_mv_war_tabular_summaries |
| CASING_GRADE                  | eWellAPDRawData_mv_apd_casing_sections , eWellWARRawData_mv_war_tabular_summaries |
| CSNG_LINER_TEST_PRSS          | eWellWARRawData_mv_war_tabular_summaries |
| CSNG_SHOE_TEST_PRSS           | eWellWARRawData_mv_war_tabular_summaries |
| CSNG_CEMENT_VOL               | eWellAPDRawData_mv_apd_casing_sections , , eWellWARRawData_mv_war_tabular_summaries|
| SN_WAR_CSNG_INTV              | eWellWARRawData_mv_war_tabular_summaries |

### 14. well_activity_open_hole

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all   |
| WELL_NAME                     | APDRawData_mv_apd_main_all  |
| BUS_ASC_NAME                  | eWellWARRawData_mv_war_open_hole_runs|
| OPERATIONS_COMPLETED_DATE     | eWellWARRawData_mv_war_open_hole_runs |
| LOG_TOOL_TYPE_CODE            | eWellWARRawData_mv_war_open_hole_tools|
| TOOL_LOGGING_METHOD_NAME      | eWellWARRawData_mv_war_open_hole_runs |
| LOG_INTV_TOP_MD               | eWellWARRawData_mv_war_open_hole_runs |
| LOG_INTV_BOTM_MD              | eWellWARRawData_mv_war_open_hole_runs |
| SN_OPEN_HOLE                  | eWellWARRawData_mv_war_open_hole_runs , eWellWARRawData_mv_war_open_hole_tools| 

### 15. well_activity_remarks

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all  |
| WELL_NAME                     | APDRawData_mv_apd_main_all  |
| WAR_START_DT                  | eWellWARRawData_mv_war_main |
| SN_WAR                        | eWellWARRawData_mv_war_main_prop_remark  |
| TEXT_REMARK                   | eWellWARRawData_mv_war_main_prop_remark |

### 16. well_directional_surveys

[API_WELL_NUMBER],[INCL_ANG_DEG_VAL] ,[INCL_ANG_MIN_VAL],[SURVEY_POINT_MD],[WELL_N_S_CODE],[DIR_DEG_VAL],[DIR_MINS_VAL],[WELL_E_W_CODE],[SURVEY_POINT_TVD],[DELTA_X],[DELTA_Y],[SURF_LONGITUDE],[SURF_LATITUDE]

dsptsdelimit

# BoreHole COdes


| BOREHOLE_STAT_CD | BOREHOLE_STAT_DESC |
|------------------|--------------------|
| APD              | APPLICATION FOR PERMIT TO DRILL |
| AST              | APPROVED SIDETRACK |
| CNL              | BOREHOLE IS CANCELLED. THE REQUEST TO DRILL THE WELL IS CANCELLED AFTER THE APD OR SUNDRY HAS BEEN APPROVED. THE STATUS DATE IS THE DATE THE BOREHOLE WAS CANCELLED. |
| COM              | BOREHOLE COMPLETED |
| CT               | CORE TEST WELL |
| DRL              | DRILLING ACTIVE |
| DSI              | DRILLING SUSPENDED |
| PA               | PERMANENTLY ABANDONED |
| ST               | BOREHOLE SIDETRACKED |
| TA               | TEMPORARILY ABANDONED |
| VCW              | VOLUME CHAMBER WELL |

