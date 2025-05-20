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


## Production Data

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


### Communications (Roy, Vamsee, Chuck, Samdan)


### 2025-05-15

Vamsee, I have been taking the spud date – the td date as drilling days.  Anything after reaching TD is called appraisal or completion, but for our purposes we will call all those days completion days.  Even electric logging after reaching TD is considered part of completion.  Perhaps this will help you guys with your scripts.  I have been looking through the mv_war_main_prop_remark.txt file and it seems like the operations that come up there are after reaching TD and hence should be considered completion.  I am still reviewing this to make sure, you actually have to read through what they are doing to figure it out!


Here an example of what I am talking about – the data in the attached spreadsheets

**summary_file**
| SN_WAR  | API_WELL_NUMBER | Spud Date  | Total Depth Date | Drilling Days | TMD     | TVD     | Max Mud Weight (ppg) | Bottom Hole Pressure |
|---------|------------------|------------|-------------------|----------------|---------|---------|------------------------|-----------------------|
| -262552 | 608124009500     | 7/24/2014  | 12/26/2014        | 155            | 31,225  | 28,307  | 14.0                   | 20,607                |




**remarks_of_API**
| API_WELL_NUMBER | Date       | Activity                                                                                                                                                                                                                                                                                                                                                                     |
|------------------|------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 608124009500     | 10/15/15   | FIRST REPORT - INITIAL COMPLETION - Moved rig on location. Installed storm sheave/mux lines on slip jt. Landed/latched BOP's w/100K down. Unlocked slip jt/scope out inner barrel/set on gimble. Performed rig maintenance while waiting on approval for testing for BOP stack hop.                                                                                                 |
| 608124009500     | 10/16/15   | Performed rig maintenance while waiting on approval for testing for BOP stack hop/approved/approved. Performed conn/auto shear/deadman test to 1000 psi/OK.                                                                                                                                                                                                                  |
| 608124009500     | 10/17/15   | Performed rig maintenance while LOOP CURRENT.                                                                                                                                                                                                                                                                                                                               |
| 608124009500     | 10/18/15   | Performed general rig maintenance rig - waiting on loop current. Scoped in slip jt/latched in w/locking dogs. Break circ down KL/performed line test to 2500 psi/OK. Performed conn/auto shear/deadman test to 1000 psi/OK.                                                                                                                                                |
| 608124009500     | 10/19/15   | Performed general rig maintenance rig - waiting on loop current. TIH to 9848'MD. Commence testing BOP's to 250/8800 psi. Changed out saver sub. WOW. Monitored well on TT/riser static.                                                                                                                                                                                      |
| 608124009500     | 10/20/15   | WOW. TIH to 9987'MD. Commence testing BOP's to 250/8800 psi.                                                                                                                                                                                                                                                                                                                 |
| 608124009500     | 10/21/15   | Completed testing BOP's. Function tested BOP's. Performed accu drawdown test/OK.                                                                                                                                                                                                                                                                                             |
| 608124009500     | 10/22/15   | Tested BSR's to 250/8800 psi/OK (APM step 1.4a/b). WOW. Performed EDS function test/OK. Performed 1000 psi test against BSR's to verify closure/OK.                                                                                                                                                                                                                          |
| 608124009500     | 10/23/15   | TIH w/CO assy to 1724'MD. Performed riser conn w/ROV intervention. ROV stabbed into performed riser conn test/unlocked riser conn/function back lock on blue pod F/RF. Function riser conn unlock/locked back on blue pod F/RF. TIH to 9057'MD. Performed auto shear function test using ROV intervention test BSR/conn to 250/8800 psi/OK. Continued ROV intervention testin/function test BOP on yellow pod F/RF/blue pod F/RMP. |
| 608124009500     | 10/24/15   | TIH to 10038'MD. Break circulation down KL w/8.6# SW. Tested riser connector against upper annular on 5 7/8" drill pipe w/250/7000 psi on blue pod R/RF. TIH to 10425'MD/TOC w/30K down. Displaced well/riser/ck kl lines F/8.6# SW to 14# SBM (APM step 2a). Pumped 100 bbl of 14# SBM/ROV performed clear btm survey on well #9 umbilical came into contact w/marker buoy on well #4. While attempting to release buoy F/umbilical buoy detached F/clump wt. Washed to top of cmt F/10386-10430'MD. Drilled out cm |
| 608124009500     | 10/25/15   | Drilled out cmt to 10652'MD. Performed derrick inspection/OK. Drilled out cmt to 10830'MD. Function diverter F/RMP.                                                                                                                                                                                                                                                           |
| 608124009500     | 10/26/15   | Drilled out cmt to 10921'MD. Performed diverter function F/RMP. Reamed to 11079'MD. Pumped/circ out 100 bbl hi-vis sweep. Pumped slug. POOH/LD CO assy. Cleaned/cleared RF. TIH w/CO assy to 5928'MD.                                                                                                                                                                           |
| 608124009500     | 10/27/15   | TIH to 9057'MD. Function BSR/CSR's on blue pod F/RMP. TIH to 13259'MD. Washed to 13358'MD. TIH to 15000'MD.                                                                                                                                                                                                                                                                  |
| 608124009500     | 10/28/15   | TIH to 22849'MD/CBU. Flow check well/OK.                                                                                                                                                                                                                                                                                                                                      |
| 608124009500     | 10/29/15   | TIH to 23731'MD. Washed down to 23858'MD. TIH to 24237'MD. Washed/reamed to 26939'MD. CBU. Flushed ch/kl lines w/14# SBM. Drilled cmt to 26997'MD.                                                                                                                                                                                                                            |
| 608124009500     | 10/30/15   | Reamed to 27309'MD. Pumped 100 bbl hi-vis spacer/circ to surface. Washed to 30904'/BP/btm w/15k down (APM step 2b). CBU.                                                                                                                                                                                                                                                      |
93 days of date column ,

So the completion days for this well = 93 days, making the total drill and complete days 155 + 93 = 248

What a coinkydink!  That is about what we have been predicting through all of our previous papers and studies going back 10+ years!



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
