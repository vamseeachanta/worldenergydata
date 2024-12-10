## Data Definitions

## Summary

- Investigate what data exists where with the new processess (by url, by zip, worstcase by manual download)
- Investigate what data is required for the analysis
- Load the required data from files as raw DFs (synonymous to sql tables in BSEE_analysis.yml i.e. Likely Filenames)
- Join the required data to create the final DFs for analysis (synonymous to sql queries in BSEE_analysis.yml)
- Provide these final DFs to the analysis module.

## Energydata Repo

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

#### all_bsee_blocks

**Columns:**

BOTM_FLD_NAME_CD

**Likely Filenames:**

- mv_api_list

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

- yearly_production_data
- mv_boreholes

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
