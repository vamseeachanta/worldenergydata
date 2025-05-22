## Objective

this markdown is used to keep up some important notes for running analysis.

## SME, Chuck

## SME, Roy

## SME, Vamsee

### 2025-05-22



### Julia summary differences

some main points to look at:

- Roy used leases (Ex: G20351 ) for getting data - not a big deal
  - we used bottom blocks for fileds - julia ,stmalo, jack

- Roy utilized only war data
  - war: data/modules/bsee/bin/war/mv_war_main.bin
  - boreholes: data/modules/bsee/bin/war/mv_war_boreholes_view.bin
  - war_prop : data/modules/bsee/bin/war/mv_war_main_prop.bin
  - war_remarks: data/modules/bsee/bin/war/mv_war_main_prop_remark.bin

- WELL_SPUD_DATE , TOTAL_DEPTH_DATE from merged dataframe - war_df , boreholes_df etc..
  - WELL_SPUD_DATE is well's start date
  - TOTAL_DEPTH_DATE is well's end date
  
- Drilling Days = TOTAL_DEPTH_DATE - WELL_SPUD_DATE
