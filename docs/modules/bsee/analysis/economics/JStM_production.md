
read and extract necessary details from excel - ✔️
create an input file - ✔️

perform necessary calculations
 - get same numbers

calculate NPV calculation rate %
 - get same as in the excel file

Tests :
  - analysis/query_field_jack_759_test.py 
  - analysis/query_field_stmalo_678_test.py


### Analysis Summary:

  - JStM production analysis
  - NPV calculation
    - costs (Wells, facilities)... 
    - revenue (oil price, production).. monthly

#### AI Journal Summary :

Hey , you are an pro expert dealing with Microsoft excel files , I want you to read and analyze the formulas and calculation is done in the excel file that I have attached to you. 
after successful study , you have to create a python function and write code for the calculations which you have understood from the excel file. 

The Excel sheet appears to summarize production data (bopd = barrels of oil per day) for multiple wells over time. Here's a breakdown:

- Rows 3 to 13 (0-based index) contain production values per well per month.

- The sheet spans multiple years from 2015 to 2019, with columns grouped by months.

- There is a summary row:

  - "AVG bopd/well" = average barrels per day per well.

  - "St. Malo" = likely a field or group average.

  - "PEAK" and "AVG" columns at the end reflect performance indicators.

**Detected Logic & Calculations:**

- Monthly Production: Each row under a well code (e.g., WR678 PN001) shows monthly production in barrels per day.

- AVG bopd/well = sum of production values from wells for a given month ÷ number of wells producing.

- St. Malo Total = total of all well productions for a given month.

- PEAK = the maximum monthly production per well over the years.

- AVG = the average production per well across all months.

✅ Based on this logic, we can create a Python function that:

- Parses monthly production for each well.

- Calculates average production per well.

- Finds the peak production per well.

- Computes total monthly production (St. Malo).

- Computes average production per well per month.


