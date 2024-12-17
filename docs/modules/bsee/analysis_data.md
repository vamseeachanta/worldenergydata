## Filenames and columns 
### Columns required for preparing dataframes

### 1.  Well data 
   

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges |
| COMPANY_NAME                  | APIRawData_mv_api_list_all             |
| BOTM_FLD_NAME_CD              | APIRawData_mv_api_list_all             |
| WELL_NAME                     | APDRawdata_mv_apd_main_all             |
| WELL_NAME_SUFFIX (Sidetrack or bypass) | APDRawdata_mv_apd_main_all    |
| WELL_SPUD_DATE                | APIChangesRawData_mv_apichanges        |
| TOTAL_DEPTH_DATE              | APIRawdata, BoreholeRawdata, eWellWARRdata |
| BH_TOTAL_MD ( feet )          | APIChangesRawData_mv_apichanges, APIRawData_mv_api_list |
| WELL_BORE_TVD                 | BoreholeRawData_mv_boreholes_all , eWellEORRawData_mv_eor |
| WELL_BP_ST_KICKOFF_MD         | BoreholeRawData_mv_boreholes_all , eWellEORRawData_mv_eor |
| BOREHOLE_STAT_CD              | APIRawData_mv_api_list_all , BoreholeRawData_mv_boreholes_all |
| BOREHOLE_STAT_DT              | APIRawData_mv_api_list_all , BoreholeRawData_mv_boreholes_all |
| UNDWTR_COMP_STUB              | BoreholeRawData_mv_boreholes_all       | 
| Water depth (feet)            | APDRawdata ,  API_8                      |
| SURF_LATITUDE, SURF_LONGITUDE | API_number_1, num_2, APDRawdata, BoreholeRawdata |
| BOTM_LATITUDE, BOTM_LONGITUDE | BoreholeRawdata, eWELLEORRData         |
| CASING CUT CODE               | BoreholeRawData_mv_boreholes_all       |


### 2. all_bsee_blocks

BOTM_FLD_NAME_CD -  APIRawData_mv_api_list_all.csv 

### 3. ST_BP_and_tree_height

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges |
| WELL_NM_ST_SFIX               | APDRawdata_mv_apd_main_all , eWellAPDRawData_mv_apd_main |
| WELL_NM_BP_SFIX               | APDRawdata_mv_apd_main_all , eWellAPDRawData_mv_apd_main |
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
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges  |
| WELL_NAME                     | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges, APIRawData_mv_api_list_all |
| RIG_NAME                      | APDRawData_mv_apd_main_all , eWellAPDRawData_mv_apd_main , eWellAPMRawData_mv_rig_view , eWellWARRawData_mv_war_main |
| WAR_START_DT                  | eWellWARRawData_mv_war_main |
| WAR_END_DT                    | eWellWARRawData_mv_war_main |
| WELL_ACTIVITY_CD              | eWellEORRawData_mv_war_main_prop |
| DRILLING_MD                   | eWellEORRawData_mv_war_main_prop |
| DRILL_FLUID_WG                | eWellEORRawData_mv_war_main_prop |

### 12. well_activity_bop_tests

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges  |
| BOP_TEST_DATE                 | eWellWARRawData_mv_war_main |
| RAM_TST_PRSS                  | eWellWARRawData_mv_war_main |
| ANNULAR_TST_PRSS              | eWellWARRawData_mv_war_main |
| BUS_ASC_NAME                  | APDRawData_mv_apd_main_all , eWellAPDRawData_mv_apd_main , eWellEORRawData_mv_war_main_prop |

### 13. well_tubulars

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges  |
| WELL_NAME                     | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges, APIRawData_mv_api_list_all |
| WAR_START_DT                  | eWellWARRawData_mv_war_main |
| WAR_END_DT                    | eWellWARRawData_mv_war_main |
| CSNG_INTV_TYPE_CD             | eWellAPDRawData_mv_apd_casing_intervals , eWellWARRawData_mv_war_tabular_summaries |
| CSNG_HOLE_SIZE                | eWellWARRawData_mv_war_tabular_summaries |
| CSNG_SETTING_BOTM_MD          | eWellWARRawData_mv_war_tabular_summaries |
| CSNG_SETTING_TOP_MD           | eWellWARRawData_mv_war_tabular_summaries |
| CASING_SIZE                   | eWellAPDRawData_mv_apd_casing_sections , eWellEORRawData_mv_eor_cut_casings, eWellWARRawData_mv_war_tabular_summaries| 
| CASING_WEIGHT                 | eWellAPDRawData_mv_apd_casing_sections , eWellWARRawData_mv_war_tabular_summaries |
| CASING_GRADE                  | eWellAPDRawData_mv_apd_casing_sections , eWellWARRawData_mv_war_tabular_summaries |
| CSNG_LINER_TEST_PRSS          | eWellWARRawData_mv_war_tabular_summaries |
| CSNG_SHOE_TEST_PRSS           | eWellWARRawData_mv_war_tabular_summaries |
| CSNG_CEMENT_VOL               | eWellAPDRawData_mv_apd_casing_sections , , eWellWARRawData_mv_war_tabular_summaries|
| SN_WAR_CSNG_INTV              | eWellWARRawData_mv_war_tabular_summaries |

### 14. well_activity_open_hole

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges  |
| WELL_NAME                     | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges, APIRawData_mv_api_list_all |
| BUS_ASC_NAME                  | APDRawData_mv_apd_main_all , eWellAPDRawData_mv_apd_main , eWellEORRawData_mv_war_main_prop|
| OPERATIONS_COMPLETED_DATE     | eWellWARRawData_mv_war_open_hole_runs |
| LOG_TOOL_TYPE_CODE            | eWellWARRawData_mv_war_open_hole_tools|
| TOOL_LOGGING_METHOD_NAME      | eWellWARRawData_mv_war_open_hole_runs |
| LOG_INTV_TOP_MD               | eWellWARRawData_mv_war_open_hole_runs |
| LOG_INTV_BOTM_MD              | eWellWARRawData_mv_war_open_hole_runs |
| SN_OPEN_HOLE                  | eWellWARRawData_mv_war_open_hole_runs , eWellWARRawData_mv_war_open_hole_tools| 

### 15. well_activity_remarks

| Column Name                   | File Name                              |
|-------------------------------|----------------------------------------|
| API_WELL_NUMBER               | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges  |
| WELL_NAME                     | APDRawData_mv_apd_main_all , APIChangesRawData_mv_apichanges, APIRawData_mv_api_list_all |
| WAR_START_DT                  | eWellWARRawData_mv_war_main |
| SN_WAR                        | eWellWARRawData_mv_war_main_prop_remark  |
| TEXT_REMARK                   | eWellWARRawData_mv_war_main_prop_remark |

### 16. well_directional_surveys

NO COLUMNS FOUND