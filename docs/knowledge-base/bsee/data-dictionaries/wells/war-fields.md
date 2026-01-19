# WAR (Well Activity Report) Fields

> **Dataset**: eWell WAR
> **Source**: https://www.data.bsee.gov/Well/WAR/Default.aspx
> **Raw Data**: https://www.data.bsee.gov/Well/Files/WARRawData.zip
> **Update Frequency**: Daily
> **Purpose**: Ongoing well activity documentation

---

## WAR Types

| Type | Description | When Filed |
|------|-------------|------------|
| Drilling | Initial drilling operations | During drilling phase |
| Completion | Well completion activities | During completion operations |
| Workover | Well workover operations | During workover activities |
| Sidetrack | Sidetrack drilling operations | When sidetracking |
| Plugback | Plugback operations | During plugback |
| Abandonment | Well abandonment activities | During P&A operations |
| Recompletion | Recompletion operations | During zone change |
| Stimulation | Stimulation treatments | During frac/acidizing |

---

## Report Identification Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| WAR Number | VARCHAR(12) | Unique report identifier | W2400001234 |
| API Well Number | VARCHAR(12) | Well API number | 177093400100 |
| Report Type | VARCHAR(20) | Type of activity report | Drilling |
| Report Period | VARCHAR(10) | Reporting period | Weekly |
| Sequence Number | INT | Report sequence for well | 15 |
| Supersedes | VARCHAR(12) | Previous WAR replaced (if any) | W2400001200 |

---

## Activity Codes

| Code | Description | Category |
|------|-------------|----------|
| DR | Drilling | Drilling |
| CS | Casing/Cementing | Drilling |
| CG | Coring | Drilling |
| TD | Total Depth | Drilling |
| LG | Logging | Evaluation |
| TT | Testing | Evaluation |
| PF | Perforating | Completion |
| GV | Gravel Pack | Completion |
| TB | Tubing | Completion |
| ST | Stimulation | Completion |
| WO | Workover | Workover |
| WL | Wireline | Service |
| PB | Plugback | Abandonment |
| PA | Plug/Abandon | Abandonment |
| TA | Temp Abandon | Abandonment |
| SI | Shut-In | Status |
| PR | Producing | Status |
| SU | Suspended | Status |

---

## Report Period Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Report Date | DATE | Date report submitted | 01/20/2024 |
| Period Start | DATE | Activity period start | 01/13/2024 |
| Period End | DATE | Activity period end | 01/19/2024 |
| Days in Period | INT | Number of days | 7 |
| Report Frequency | VARCHAR(10) | Weekly/Monthly/Final | Weekly |

---

## Rig Information Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Rig Name | VARCHAR(50) | Drilling unit name | DEEPWATER NAUTILUS |
| Rig Type | VARCHAR(30) | Rig classification | Semi-submersible |
| Rig Owner | VARCHAR(100) | Rig owning company | Transocean |
| Contractor | VARCHAR(100) | Drilling contractor | Noble Corp |
| Rig Status | VARCHAR(20) | Current rig status | Drilling |
| Rig Arrival Date | DATE | Date rig arrived | 01/01/2024 |
| Rig Release Date | DATE | Date rig released | NULL |

---

## Depth Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Start MD | DECIMAL(10,2) | Measured depth at period start (ft) | 12500.00 |
| End MD | DECIMAL(10,2) | Measured depth at period end (ft) | 15800.00 |
| Current MD | DECIMAL(10,2) | Current measured depth (ft) | 15800.00 |
| Start TVD | DECIMAL(10,2) | TVD at period start (ft) | 10200.00 |
| End TVD | DECIMAL(10,2) | TVD at period end (ft) | 12100.00 |
| Current TVD | DECIMAL(10,2) | Current true vertical depth (ft) | 12100.00 |
| Water Depth | DECIMAL(8,2) | Water depth (ft) | 4500.00 |
| RKB Elevation | DECIMAL(6,2) | Rotary Kelly Bushing (ft) | 85.00 |
| Footage Drilled | DECIMAL(10,2) | Footage this period (ft) | 3300.00 |

---

## Depth Reference Points

| Field | Reference | Notes |
|-------|-----------|-------|
| MD (Measured Depth) | RKB | Along wellbore path |
| TVD (True Vertical Depth) | RKB | Vertical projection |
| TVD Subsea | Mean Sea Level | TVD minus RKB |
| Water Depth | Sea Floor | Water column depth |

---

## Status Update Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Current Activity | VARCHAR(50) | Activity in progress | Drilling 12-1/4" hole |
| Previous Activity | VARCHAR(50) | Last completed activity | Set 13-3/8" casing |
| Next Planned Activity | VARCHAR(50) | Upcoming operations | Run 9-5/8" casing |
| Well Status | CHAR(3) | Current well status code | DRL |
| Status Change Date | DATE | Date status changed | 01/19/2024 |
| Operational Status | VARCHAR(20) | Operational condition | On Schedule |

---

## Casing/Hole Information

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Hole Size | DECIMAL(4,2) | Current hole diameter (in) | 12.25 |
| Casing Size | DECIMAL(4,2) | Last casing set (in) | 13.375 |
| Casing Depth | DECIMAL(10,2) | Casing shoe depth (ft) | 12000.00 |
| Casing Weight | DECIMAL(4,1) | Casing weight (lb/ft) | 68.0 |
| Cement Top | DECIMAL(10,2) | Top of cement (ft) | 9500.00 |
| Cement Volume | INT | Cement pumped (sacks) | 1200 |

---

## Formation Information

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Current Formation | VARCHAR(50) | Formation being drilled | LOWER MIOCENE |
| Formation Top MD | DECIMAL(10,2) | Formation top depth (ft) | 14500.00 |
| Target Formation | VARCHAR(50) | Target zone | M10 SAND |
| Target Depth MD | DECIMAL(10,2) | Planned target depth (ft) | 18500.00 |
| Shows | VARCHAR(200) | Hydrocarbon shows | Gas show 15200-15350 |

---

## Daily Operations Summary

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Operations Summary | TEXT | Narrative of activities | Drilled 12-1/4" hole... |
| Problems Encountered | TEXT | Issues during period | Lost circulation at 14800 |
| NPT Hours | DECIMAL(6,2) | Non-productive time (hrs) | 24.5 |
| NPT Reason | VARCHAR(200) | Reason for NPT | Weather delay |
| Productive Hours | DECIMAL(6,2) | Productive time (hrs) | 143.5 |

---

## Safety/Environmental Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Incidents | INT | Number of safety incidents | 0 |
| Spills | INT | Number of spill events | 0 |
| Spill Volume | DECIMAL(8,2) | Total spill volume (bbl) | 0.00 |
| JSA Count | INT | Job safety analyses performed | 45 |
| H2S Detected | BIT | H2S encountered (1=Yes) | 0 |
| H2S Concentration | INT | H2S level if detected (ppm) | NULL |

---

## Mud/Fluid Information

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Mud Type | VARCHAR(30) | Drilling fluid type | Synthetic Oil-Based |
| Mud Weight | DECIMAL(4,1) | Current mud weight (ppg) | 12.5 |
| Viscosity | INT | Funnel viscosity (sec) | 45 |
| PV | INT | Plastic viscosity (cp) | 22 |
| YP | INT | Yield point (lb/100sqft) | 15 |
| Fluid Loss | DECIMAL(4,1) | API fluid loss (ml) | 2.5 |

---

## BOP/Safety Equipment

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| BOP Stack | VARCHAR(50) | BOP configuration | 18-3/4" 15K |
| Last BOP Test | DATE | Last BOP pressure test | 01/18/2024 |
| BOP Test Result | VARCHAR(10) | Test result | Pass |
| Diverter Status | VARCHAR(20) | Diverter system status | Operational |
| LMRP Status | VARCHAR(20) | LMRP status (deepwater) | Connected |

---

## Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| API Well Number | Text | Well API number | 177093400100 |
| WAR Number | Text | Specific WAR number | W2400001234 |
| Report Type | Dropdown | Activity type | Drilling |
| Date Range | Date Range | Report period | 01/01/2024 - 12/31/2024 |
| Region | Dropdown | Geographic region | Gulf of America |
| Operator | Dropdown | Company name | Shell Offshore |
| Rig Name | Text | Drilling unit | DEEPWATER NAUTILUS |

---

## WAR to Borehole Linkage

| WAR Field | Borehole Field | Notes |
|-----------|----------------|-------|
| API Well Number | API Well Number | Primary key |
| Current MD | BH Total MD | Final WAR = borehole MD |
| Current TVD | True Vertical Depth | Final WAR = borehole TVD |
| Well Status | Status Code | Should match |
| Spud Date | Spud Date | From first drilling WAR |

---

## Sample Query URL

```
https://www.data.bsee.gov/Well/WAR/Default.aspx
  ?Region=Gulf%20of%20America
  &ReportType=Drilling
  &DateFrom=01/01/2024
  &DateTo=12/31/2024
```

---

## Related Documents

- [Borehole Fields](borehole-fields.md) - Well master data
- [APD Fields](apd-fields.md) - Permit application data
- [Completion Fields](completion-fields.md) - Completion data
- [Status Codes](status-codes.md) - Well status reference
