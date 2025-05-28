## Julia Summary analysis

### Missing API12s in online query
- Some search_by_lease API12s are missing in search by block API12s. 
- Find out what is the right way to search these wells. If online search is not consistent, we change to csv route.

reason should be:
-
- the major data for Julia summary by block 584 (by lease G20351) comes from " eWellWARRawData_mv_war_main.csv " , "BoreholeRawData_mv_boreholes_all" in our analysis.
  - From "eWellWARRawData_mv_war_main.csv"
    - SURF_LEASE_NUM,SURF_AREA_CODE,SURF_BLOCK_NUM,BOTM_LEASE_NUM,BOTM_AREA_CODE,BOTM_BLOCK_NUM
 
Test Observations:

- API12s missing in search by block 
  - 608124011100

Missing API12 is 608124011100, which comes from 'eWELLRawData_mv_war_main.csv' , 'BoreholeRawData_mv_boreholes_all' files and it is exists in the both files but it is not found in the output summary (well_summ_goa_julia.xlsx) .

- Need to analyze the analysis code and fix this issue.
  - api12_array from cfg groups through online query (scrapy) does not contain the missing API12.

 - By block: ?
 - By lease: ?

Roy did not got the data by lease he had just filtered downloaded war data by lease from the .csv files.
 - so we do not need to get the data by lease
 - also lease data does not have the API12s required to do analysis.


The key point to consider from this analysis is ,

- We are filtering the analysis data by api12 data which comes from by block online query (scrapy) and it does not include the API12 608124011100.
- Roy is filtering his analysis data by API12s which comes from the downloaded WAR data and it includes the API12 608124011100.

### Conclusion

- The API12s missing in search by block is due to the fact that the online query (scrapy) does not include this API12, while the downloaded WAR data does.
- To resolve this issue, we may need to go with what roy has doing, which is filtering the analysis data by API12s from the downloaded WAR data instead of the online query.

## Way forward:
- Keep legacy and unsed code clean
  - Csv route (Use this going forward)
  - scrapy query route
- Test
  - Compare Julia csv vs. scrapy. 
 - proceed with CSV/bin and try to get Roy's results
  - convert to bin (DONE)
  - Read from bin file
