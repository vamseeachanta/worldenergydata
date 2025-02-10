## Objective





## SME, Roy

Need the following well data

### Summary

- [ ] Identify and combine data sources, see data sources below
- [ ] Utilize the well data function "prepare_field_well_data", etc., in src\energydata\modules\bsee\analysis\bsee_analysis.py


| Data | Description | Source/Method
| --- | --- | --- |
Well Name |  | Well Name, by_block_well_data
Water Depth | | Water Depth (feet), by_block_well_data
Spud Date | | WELL_SPUD_DATE, APIRawData_mv_api_list_all
Rig Name  | | Rig Name, by_block_well_data
Rig Start Date |  | by_block_well_data
Rig Release Date | | calculated from by_block_well_data (last date)
TVD | | WELL_BORE_TVD, BoreholeRawData
TMD | | BH_TOTAL_MD, APIRawData_mv_api_list_all
TD Date | | TOTAL_DEPTH_DATE, APIRawData_mv_api_list_all
Number of sidetracks | | caculated
Well departure (step out) |  | caculated from well bore data, dsptsdelimit
Mud Weight at TD (max) | | 
Drilling Days | | calculated
Completion Days | | calculated
First oil date  | | calculated from production data
Production rate by month | by API | from yearly zip files, [#23](https://github.com/vamseeachanta/energydata/issues/23)


### Data Sources

by_block_well_data :  tests\modules\bsee\analysis\results\Data\julia_by_block\WR540.csv
BHPS: https://github.com/vamseeachanta/energydata/blob/2084250f6055a4f0dae7cafc3844f797bc8b624d/tests/modules/bsee/data/results/Data/by_zip/BHPSRawData_mv_bhpsurvey_all.csv
APIRawData_mv_api_list_all : https://github.com/vamseeachanta/energydata/blob/2084250f6055a4f0dae7cafc3844f797bc8b624d/tests/modules/bsee/data/results/Data/by_zip/APIRawData_mv_api_list_all.csv
BoreholeRawData: https://github.com/vamseeachanta/energydata/blob/1691a05e908c4a69876d821296e63e5e65277a73/tests/modules/bsee/data/results/Data/by_zip/BoreholeRawData_mv_boreholes_all.csv

dsptsdelimit: https://github.com/vamseeachanta/energydata/blob/2084250f6055a4f0dae7cafc3844f797bc8b624d/tests/modules/bsee/data/results/Data/by_zip/dsptsdelimit.csv




## PRoduction Data

  - [ ] https://www.data.bsee.gov/Main/Production.aspx, See OGOR-A (1996-Current) , OGOR-B (1996-Current), OGOR-C (1996-Current) 
  - [ ] https://www.data.bsee.gov/Main/OGOR-A.aspx
  - [ ] https://www.data.bsee.gov/Production/Files/ogoradelimit.zip
  - [ ] https://www.data.bsee.gov/Production/Files/ogora2023delimit.zip
  - [ ] https://www.data.bsee.gov/Production/Files/ogora2022delimit.zip
  - [ ] https://www.data.bsee.gov/Production/Files/ogora2021delimit.zip
  - [ ] ...
  - [ ] ...
  - [ ] https://www.data.bsee.gov/Production/Files/ogora1966delimit.zip
- [ ] TBA