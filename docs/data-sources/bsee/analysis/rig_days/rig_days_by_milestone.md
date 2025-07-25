## Rig Days

## Way forward:

- Utilize database numbers or add Roy's Calculation

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

---

*Last updated: 2025-07-24*
