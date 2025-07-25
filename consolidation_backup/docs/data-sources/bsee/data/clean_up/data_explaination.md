#### Objective

* For a given API well or block, get data from BSEE website and perform analysis that we have done back in 2022.

* Then progress further to drilling statistics, well plans, risk, safety events etc.

* Then I believe will allow people to use AI .

a/ data method :

legacy: download ,
worldenergydata:

* Online query (Latest data)
* Read ZIP file directly (Latest data)
* downloading files, loading in database (chance of stale data)
hybrid (online primary, download secondary).

b/ data transformation:

 (Extract-Transform-Load): automate (no manual interruption - all mapping/transformation from data website)

c/ analysis (eg: drilling statistics, well duration, production data, ). A mapped and organized output (json, yaml format ready to unleash AI)

d/ you can run your AI bot on it

# Summary

Key rules:

- Data can be either queried online (data.bsee.com) or downloaded in bulk. First preference is online query.
- When data is read from disk files, a seperate process should be utilized.

# Usage

To run BSEE data smoothly, clone the below repository.

# Sources

## Drill Down By Block

- Example
- Cascade Chinook

## API Number

test - 10 APIs
<https://www.data.bsee.gov/Well/APD/Default.aspx>

## Borehole data

### Borehole data
Online query
<https://www.data.boem.gov/Well/Borehole/Default.aspx/>

### Bottomhole pressure

https://www.data.bsee.gov/Well/BHPS/Default.aspx

## Production Data

online query:
<https://www.data.bsee.gov/Production/ProductionData/Default.aspx>

Lease Number: G03237
Production Month/year : 01/2024 to 02/2024

- Metadata for the files is given below:
<https://www.data.bsee.gov/Main/OGOR-A.aspx>

- Download all the files from below location
<https://www.data.bsee.gov/Main/OGOR-A.aspx>

- Filter the files by API number as necessary

- Label them with well name

- Plot the production data

## References


### URLS to download data

