## Filenames and columns 

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
|  |  |
|   |   |