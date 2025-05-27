### Julia Summary analysis


#### Some API12s from search by lease are missing in search by block. Find out what is the right way to search these wells?

reason should be:

- the major data for Julia summary by block 584 (by lease G20351) comes from " eWellRawData_mv_war_main.csv " , "BoreholeRawData_mv_boreholes_all" in our analysis.

#### API12s missing in search by block 
- 608124011100

Missing API12 is 608124011100, which comes from 'eWELLRawData_mv_war_main.csv' , 'BoreholeRawData_mv_boreholes_all' files and it is exists in the both files but it is not found in the output summary (well_summ_goa_julia.xlsx) .

- Need to analyze the analysis code and fix this issue.
  - api12_array from cfg groups through online query (scrapy) does not contain the missing API12.

#### An example result for Julia:
 - By block: ?
 - By lease: ?

Roy did not got the data by lease he had just filtered downloaded war data by lease from the .csv files.
 - so we do not need to get the data by lease
 - also lease data does not have the API12s required to do analysis.


The key point to consider from this analysis is ,

- We are filtering the analysis data by api12 data which comes from by block online query (scrapy) and it does not include the API12 608124011100.
- Roy is filtering his analysis data by API12s which comes from the downloaded WAR data and it includes the API12 608124011100.

#### Conclusion

- The API12s missing in search by block is due to the fact that the online query (scrapy) does not include this API12, while the downloaded WAR data does.
- To resolve this issue, we may need to go with what roy has doing, which is filtering the analysis data by API12s from the downloaded WAR data instead of the online query.