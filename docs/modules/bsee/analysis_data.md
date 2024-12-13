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