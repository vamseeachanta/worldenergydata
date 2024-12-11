## Data Definitions

## Summary

- Investigate what data exists where with the new processess (by url, by zip, worstcase by manual download)
- Investigate what data is required for the analysis
- Load the required data from files as raw DFs (synonymous to sql tables in BSEE_analysis.yml i.e. Likely Filenames)
- Join the required data to create the final DFs for analysis (synonymous to sql queries in BSEE_analysis.yml)
- Provide these final DFs to the analysis module.

## BSEE Data | Tables and DataFrames

The BSEE data tables and dataframes are given in the following sections.

### DF Columns Required

<https://github.com/vamseeachanta/energydata/blob/bseedata/docs/modules/bsee/legacy/code/ong_field_development/BSEE_analysis.yml>

#### Well Data

**Columns:**
API12, [Company Name], [Field Name], [Well Name], [Sidetrack and Bypass]
            , [Spud Date], [Total Depth Date], [Well Purpose]
            , [Water Depth], [Total Measured Depth], [Total Vertical Depth], [Sidetrack KOP]
            , [Surface Latitude], [Surface Longitude], [Bottom Latitude], [Bottom Longitude]
            , [Wellbore Status], [Wellbore Status Date], [Completion Stub Code], [Casing Cut Code]

**Likely Filenames:**

- mv_api_list
- mv_boreholes

**Data Sources:**

https://github.com/vamseeachanta/energydata/blob/d9f30ee2583290a29045329a3b644c13e57b8f5c/tests/modules/bsee/results/Data/by_zip/APIRawData_mv_api_list_all_columns.csv

API_WELL_NUMBER
WELL_TYPE_CODE
WELL_NAME
WELL_NAME_SUFFIX
COMPANY_NAME
BOREHOLE_STAT_DT
BOREHOLE_STAT_CD
BOTM_FLD_NAME_CD
SURF_AREA_CODE
SURF_BLOCK_NUMBER
SURF_LEASE_NUMBER
BOTM_AREA_CODE
BOTM_BLOCK_NUMBER
BOTM_LEASE_NUMBER
WELL_SPUD_DATE
TOTAL_DEPTH_DATE
BH_TOTAL_MD
REGION_CODE

#### all_bsee_blocks

**Columns:**

BOTM_FLD_NAME_CD

**Likely Filenames:**

- mv_api_list

**Data Sources:**


#### ST_BP_and_tree_height

**Columns:**
SELECT API12, WELL_NM_ST_SFIX, WELL_NM_BP_SFIX, SUBSEA_TREE_HEIGHT_AML, SN_EOR

**Likely Filenames:**

- mv_api_list
- mv_eor_mainquery

#### completion_summary

- mv_api_list
- mv_eor_mainquery
- mv_eor_completions
- mv_eor_completionsprop
- mv_eor_compstatcodes

#### hydrocarbon_bearing_interval

- mv_api_list
- mv_eor_mainquery
- mv_eor_hcbearing_intvl_comps
- mv_hcbearing_intervals
- mv_eor_hydrobarbtypecodes


**Data Sources:**
https://github.com/vamseeachanta/energydata/blob/d9f30ee2583290a29045329a3b644c13e57b8f5c/tests/modules/bsee/results/Data/by_zip/BHPSRawData_mv_bhpsurvey_all_columns.csv

FIELD_NAME_CODE
LEASE_NUMBER
COMPLETION_NAME
API_WELL_NUMBER
RESERVOIR_NAME
BHTST_DATE
SI_TIME
BHTST_TEMP
BHTST_SI_PRSS
BHTST_MD
BHTST_TVD
BHTST_PRESSURE
REMARK
REGION_CODE



#### wellbore_survey

- mv_api_list
- mv_eor_mainquery
- mv_eor_mainquery_prop
- mv_eor_perf_intervals
- mv_eor_geomarkers

#### cut_casings

- mv_api_list
- mv_eor_mainquery
- mv_eor_cut_casings
- mv_eor_casingcutcodes

#### completion_properties

- mv_api_list
- mv_eor_mainquery
- mv_eor_completions
- mv_eor_completionsprop

#### completion_perforations

- mv_api_list
- mv_eor_mainquery
- mv_eor_completions
- mv_eor_completionsprop
- mv_eor_perf_intervals

#### production

**Columns :**

For joined table:
API12, COMPLETION_NAME, PRODUCTION_DATE, PRODUCT_CODE, DAYS_ON_PROD, MON_O_PROD_VOL, TYPE_CODE

For basic tables:
- yearly_production_data
API12, COMPLETION_NAME, PRODUCTION_DATE, PRODUCT_CODE, DAYS_ON_PROD, MON_O_PROD_VOL, TYPE_CODE

- mv_boreholes
WELLAPI, [WELL_TYPE_CODE]


**Likely Filenames:**

- mv_boreholes

**Data Sources:**

tests\modules\bsee\results\Data\by_API\production_data.csv

Lease Number (UID for Well_API12)
Production Month
Production Year
Lease Oil Production (BBL)
Lease Condensate Production (BBL)
Lease Gas-Well-Gas Production (MCF)
Lease Oil-Well-Gas Production (MCF)
Lease Water Production (BBL)
Producing Completions
Lease Max Water Depth (meters)

#### well_activity_summary

- mv_api_list
- mv_war_main
- mv_war_main_prop
- mv_war_tubular_summaries
- mv_war_tubular_summaries_prop
- mv_war_open_hole_tools
- mv_war_open_hole_runs

### by_API

<https://github.com/vamseeachanta/energydata/tree/bseedata/tests/modules/bsee/results/Data/by_API>

### by_zip_url

<https://github.com/vamseeachanta/energydata/tree/bseedata/tests/modules/bsee/results/Data/by_zip>
