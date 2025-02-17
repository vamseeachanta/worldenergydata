## Objective



## SME, Chuck

Vamsee, it would really be great to know what’s really been happening at / for JSM. The attached 2019 news article about “Stage 4” indicates that the big FPS acts as the hub for 43 (FORTY-THREE!) wells. The initial big brochure by CVX and O&GJ (published in 2016???) indicated that “Phase 1” had 9 wells (4@ Jack & 5@ St. Malo)… and, says that “Stage 2” adds just 2 wells at Jack and 2 at St. Malo with 1st oil from Stage 2 expected in 2017.

The 2019 article about the $2B waterflood says that Stage 4 adds just 2 producers and 3 injectors (plus topside facilities). The “D&C+tieback, etc” for Stage 4 project averages out to about $400M/well tied back… which lines up reasonably well with the cost per tied back well for the 20 wells cited in the 2015 EIA/HIS report data on JSM. Therein, 20 wells were reported to be D&C’d+tied back for $9.7B.

How does one get from 13 wells to 43 tied back?

Also, the big CVX brochure on JSM says that the 2 fields provide an estimated oil-equivalent recoverable resource exceeding 500Mboe. The 2019 article might be saying that Stage 4 adds 175Mbbls to the project… or that JSM’s total recoverable is now estimated to be just 175Mbbls. That would be a huge drop if CVX really spent $12B for initial stages and $20B to bring the total well count to FORTY-THREE!  

https://github.com/vamseeachanta/energydata/blob/202501/docs/modules/bsee/JStM-CVX-sanctions-$2B-waterflood-20190919.pdf

https://github.com/vamseeachanta/energydata/blob/202501/docs/modules/bsee/JStM-key-info-EIA-Cost-Study-2016_IHS.pdf


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


### Communications

#### 2025-02-12

Attached are the well data for Julia and Jack & St. Malo. Stones is pending. Production data for these are pending.

As mentioned, BSEE data download is not straightforward and need some hand-holding. AI for analysis will also need some handholding when you get your hands on the fields we provide. 
FYI, In all our coding, we leveraging AI even for everything but convert them to codes where possible for repeatability and reusability and traceability. Of courese, feel free to use your own independent judgement on how to use AI.

For Jack & St. Malo wells, we got the data directly from BSEE. The blocks for jack are WR 758, WR 759. THe blocks for St. Malo are WR 678. The well data is attached and the number of API12 wells are given below. Status of these wells is to be determined.:
- Jack, WR758: 40
- Jack, WR759: 8
- St. Malo, WR678: 20 

From production data from blocks WR540 and 584, we got API12s from notes and articles as follows:

| Stage | Field | Purpose | Well Count | Total Wells | First Oil Year |
| --- | --- | --- | --- | --- | --- |
| 1 | Jack | Production | 4 | 4 | 2014 |
| 1 | St. Malo | Production | 5 | 9 | 2014 |
| 2 | Jack | Production | 2 | 11 | 2017 |
| 2 | St. Malo | Production | 2 | 13 | 2017 |
| 3 | Jack | Production | 0 | 13 | |
| 3 | St. Malo | Production | 0 | 13 | |
| 3 | ? | Injectors | 0 | 13 | |
| 4 | ? | Production | 2 |  15 | 2019 |
| 4 | ? | Injection | 3 | 18 | 2019 |


References:
https://jpt.spe.org/chevron-sanctions-waterflood-project-st-malo
https://www.offshore-technology.com/projects/jackstmalodeepwaterp/?cf-view

Thank you,
Vamsee

#### 2025-02-11

Roy, 

Short answer: We are already using AI to download data. AI still needs immense human intelligence especially for BSEE Data download.

Will respond this morning with details in our dedicated thread limited audience thread. 

Vamsee


On Wed, Feb 12, 2025 at 6:59 AM <roy.shilling@frontierdeepwater.com> wrote:
Vamsee is it possible to just download all the data associated with Julia into multiple files.  We may be able to feed those into ai and get faster processing rather than trying to generate more complicated python scripts?


r


From: Vamsee Achanta <vamsee.achanta@aceengineer.com>
Sent: Tuesday, February 11, 2025 9:00 PM
To: roy.shilling@frontierdeepwater.com
Cc: chuck.white@frontierdeepwater.com; terrance.ivers@gmail.com; Howard Day <howardday7777@gmail.com>; paul.hyatt@tdsolutions.com.au
Subject: Re: Average DAILY OIL PRODUCTION data for WILCOX fields

 

Yes, I (and my assistant programmer, Samdan) are working on Julia first. 

 

Will get some preliminary answers on well count tomorrow.
