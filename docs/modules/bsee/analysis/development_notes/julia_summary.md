### Julia Summary analysis


#### Some API12s from search by lease are missing in search by block. Find out what is the right way to search these wells?

reason should be:

- the data for field Julia as block 584 and lease G20351 ( Roy ) comes from " eWELLRawData_mv_war_main.csv " in our analysis.
  - please see the code in src\worldenergydata\modules\bsee\data\well.py - line 292 and check the csv data.

#### API12s missing in search by block 
- 608124011100

Missing API12 is 608124011100, which is exists in the eWELLRawData_mv_war_main.csv file but this API12 is not found in the output summary (well_summ_goa_julia.xlsx) search by block .

- Need to analyze the analysis code and fix this issue.

#### An example result for Julia:
 - By block: ?
 - By lease: ?


Roy did not got the data by lease he had just filtered downloaded data by lease from the .csv files.
 - so we do not need to get the data by lease
 - also lease data does not have the API12s required to do analysis.