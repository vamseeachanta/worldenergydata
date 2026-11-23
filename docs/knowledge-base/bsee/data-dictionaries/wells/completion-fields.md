# Completion Data Fields

> **Dataset**: eWell Completion
> **Source**: https://www.data.bsee.gov/Well/Completion/Default.aspx
> **Raw Data**: https://www.data.bsee.gov/Well/Files/CompletionRawData.zip
> **Update Frequency**: Daily
> **Purpose**: Well completion details and production zone data

---

## Completion Type Codes

| Code | Description | Notes |
|------|-------------|-------|
| OC | Original Completion | First completion in wellbore |
| RC | Recompletion | Change to different zone |
| DC | Dual Completion | Multiple zones completed |
| SC | Single Completion | One production zone |
| CC | Commingled Completion | Multiple zones commingled |
| GI | Gas Injection | Injection well completion |
| WI | Water Injection | Water injection well |
| DI | Disposal Well | Saltwater disposal |
| OB | Observation Well | Monitoring/observation |
| SS | Subsea Completion | Subsea tree installed |

---

## Completion Identification Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Completion ID | VARCHAR(15) | Unique completion identifier | C177093400100-01 |
| API Well Number | VARCHAR(12) | Well API number | 177093400100 |
| Completion Number | INT | Completion sequence (1, 2, 3...) | 1 |
| Completion Type | CHAR(2) | Type code | OC |
| Completion Name | VARCHAR(50) | Completion zone name | M10A SAND |
| Lease Number | VARCHAR(10) | Associated lease | G00123 |

---

## Completion Date Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Completion Date | DATE | Date completion finished | 03/15/2024 |
| First Production Date | DATE | First production date | 04/01/2024 |
| Perforation Date | DATE | Date perforated | 03/10/2024 |
| Stimulation Date | DATE | Date stimulated (if done) | 03/12/2024 |
| Last Activity Date | DATE | Last completion activity | 03/15/2024 |
| Status Date | DATE | Current status date | 04/01/2024 |

---

## Perforation Interval Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Perf Top MD | DECIMAL(10,2) | Top of perforations (MD ft) | 15200.00 |
| Perf Bottom MD | DECIMAL(10,2) | Bottom of perforations (MD ft) | 15350.00 |
| Perf Top TVD | DECIMAL(10,2) | Top of perforations (TVD ft) | 12100.00 |
| Perf Bottom TVD | DECIMAL(10,2) | Bottom of perforations (TVD ft) | 12180.00 |
| Perf Interval | DECIMAL(6,2) | Total perforated interval (ft) | 150.00 |
| Shots Per Foot | INT | Perforation density | 6 |
| Total Shots | INT | Total perforations | 900 |
| Perf Gun Size | DECIMAL(4,2) | Perforating gun diameter (in) | 4.50 |
| Perf Charge Type | VARCHAR(30) | Charge description | Deep Penetrating |

---

## Multiple Perforation Zones

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Zone Number | INT | Zone sequence (1, 2, 3...) | 1 |
| Zone Name | VARCHAR(30) | Formation/sand name | M10A |
| Zone Top MD | DECIMAL(10,2) | Zone top depth (MD ft) | 15200.00 |
| Zone Bottom MD | DECIMAL(10,2) | Zone bottom depth (MD ft) | 15350.00 |
| Zone Status | VARCHAR(10) | Active/Isolated | Active |
| Gross Interval | DECIMAL(6,2) | Gross thickness (ft) | 150.00 |
| Net Pay | DECIMAL(6,2) | Net pay thickness (ft) | 85.00 |

---

## Production Zone Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Target Formation | VARCHAR(50) | Primary target formation | LOWER MIOCENE |
| Producing Formation | VARCHAR(50) | Producing interval name | M10 SAND |
| Reservoir Name | VARCHAR(50) | Reservoir designation | THUNDER HAWK M10 |
| Sand Name | VARCHAR(30) | Sand body identifier | M10A |
| Zone Code | VARCHAR(10) | Zone identifier code | LWR-MIO-M10 |
| Pay Zone Top | DECIMAL(10,2) | Pay zone top (TVD ft) | 12100.00 |
| Pay Zone Bottom | DECIMAL(10,2) | Pay zone bottom (TVD ft) | 12180.00 |
| Gross Pay | DECIMAL(6,2) | Gross pay interval (ft) | 80.00 |
| Net Pay | DECIMAL(6,2) | Net pay interval (ft) | 55.00 |

---

## Reservoir Properties

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Porosity | DECIMAL(4,2) | Average porosity (fraction) | 0.25 |
| Permeability | DECIMAL(8,2) | Average permeability (mD) | 250.00 |
| Water Saturation | DECIMAL(4,2) | Initial Sw (fraction) | 0.22 |
| Reservoir Pressure | DECIMAL(8,2) | Initial reservoir pressure (psi) | 8500.00 |
| Reservoir Temp | DECIMAL(6,2) | Reservoir temperature (F) | 185.00 |
| Formation Volume Factor | DECIMAL(6,4) | Oil FVF (rb/stb) | 1.2500 |
| GOR | INT | Initial gas-oil ratio (scf/bbl) | 850 |

---

## Tubing/Casing Details

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Production Casing Size | DECIMAL(4,2) | Production casing OD (in) | 7.000 |
| Production Casing Weight | DECIMAL(4,1) | Casing weight (lb/ft) | 32.0 |
| Casing Grade | VARCHAR(10) | Casing steel grade | P-110 |
| Casing Setting Depth | DECIMAL(10,2) | Casing shoe depth (MD ft) | 16500.00 |
| Tubing Size | DECIMAL(4,3) | Tubing OD (in) | 4.500 |
| Tubing Weight | DECIMAL(4,1) | Tubing weight (lb/ft) | 12.6 |
| Tubing Grade | VARCHAR(10) | Tubing grade | L-80 |
| Tubing Depth | DECIMAL(10,2) | Tubing setting depth (MD ft) | 15100.00 |
| Packer Depth | DECIMAL(10,2) | Production packer depth (MD ft) | 15050.00 |
| Packer Type | VARCHAR(30) | Packer description | Permanent |

---

## Artificial Lift

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Lift Type | VARCHAR(20) | Artificial lift method | ESP |
| Lift Install Date | DATE | Date lift installed | 06/15/2024 |
| ESP Depth | DECIMAL(10,2) | ESP setting depth (MD ft) | 12500.00 |
| ESP Size | VARCHAR(20) | ESP model/size | DN3100 |
| Gas Lift Depth | DECIMAL(10,2) | Gas lift valve depth (ft) | NULL |
| Gas Lift Rate | DECIMAL(8,2) | Gas lift injection rate (mcf/d) | NULL |

---

## Stimulation Data

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Stimulation Type | VARCHAR(20) | Treatment type | Hydraulic Fracture |
| Stim Date | DATE | Treatment date | 03/12/2024 |
| Frac Fluid Volume | DECIMAL(10,2) | Total fluid pumped (bbl) | 125000.00 |
| Proppant Volume | DECIMAL(10,2) | Total proppant (lbs) | 3500000.00 |
| Proppant Type | VARCHAR(30) | Proppant description | 40/70 White Sand |
| Max Treating Pressure | INT | Maximum pump pressure (psi) | 9500 |
| Avg Treating Rate | DECIMAL(6,2) | Average pump rate (bpm) | 65.00 |
| Acid Volume | DECIMAL(8,2) | Acid pumped (gal) | 15000.00 |
| Acid Type | VARCHAR(30) | Acid description | 15% HCl |
| Number of Stages | INT | Frac stages (if multi-stage) | 1 |

---

## Gravel Pack Data

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Gravel Pack Type | VARCHAR(20) | GP method | High Rate Water Pack |
| GP Date | DATE | Gravel pack date | 03/14/2024 |
| Screen Size | DECIMAL(4,3) | Screen OD (in) | 5.500 |
| Screen Length | DECIMAL(6,2) | Total screen length (ft) | 150.00 |
| Gravel Size | VARCHAR(20) | Gravel mesh size | 20/40 |
| Gravel Volume | DECIMAL(8,2) | Gravel placed (lbs) | 45000.00 |
| Pack Efficiency | DECIMAL(4,2) | Pack efficiency (%) | 95.00 |

---

## Initial Production Rates

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| IP Oil Rate | DECIMAL(10,2) | Initial oil rate (bbl/d) | 8500.00 |
| IP Gas Rate | DECIMAL(12,2) | Initial gas rate (mcf/d) | 12500.00 |
| IP Water Rate | DECIMAL(10,2) | Initial water rate (bbl/d) | 250.00 |
| IP Test Date | DATE | Date of IP test | 04/05/2024 |
| IP Test Duration | INT | Test duration (hours) | 24 |
| Choke Size | VARCHAR(10) | Test choke size | 32/64" |
| FTP | DECIMAL(8,2) | Flowing tubing pressure (psi) | 2500.00 |
| FCP | DECIMAL(8,2) | Flowing casing pressure (psi) | 2800.00 |
| SIBHP | DECIMAL(8,2) | Shut-in BHP (psi) | 8200.00 |
| SITHP | DECIMAL(8,2) | Shut-in THP (psi) | 3500.00 |

---

## Production Allocation

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Oil Allocation | DECIMAL(5,2) | Oil allocation factor (%) | 100.00 |
| Gas Allocation | DECIMAL(5,2) | Gas allocation factor (%) | 100.00 |
| Condensate Allocation | DECIMAL(5,2) | Condensate factor (%) | 100.00 |
| Water Allocation | DECIMAL(5,2) | Water allocation factor (%) | 100.00 |
| FMP Number | VARCHAR(10) | Facility measurement point | 12345 |

---

## Completion Status

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Completion Status | VARCHAR(20) | Current status | Producing |
| Status Code | CHAR(3) | BSEE status code | COM |
| Status Date | DATE | Status effective date | 04/01/2024 |
| Producing Status | VARCHAR(20) | Production status | Active |
| Days On Production | INT | Total days produced | 285 |

---

## Completion Status Values

| Status | Description | Notes |
|--------|-------------|-------|
| Producing | Currently producing | Active |
| Shut-In | Not producing, well capable | Active |
| Waiting on Completion | WOC for completion equipment | Pre-production |
| Suspended | Operations suspended | Inactive |
| Temporarily Abandoned | Zone isolated, may re-enter | Inactive |
| Permanently Abandoned | Zone P&A complete | Terminal |

---

## Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| API Well Number | Text | Well API number | 177093400100 |
| Completion Number | Int | Completion sequence | 1 |
| Completion Type | Dropdown | Type code | OC |
| Date Range | Date Range | Completion date range | 01/01/2024 - 12/31/2024 |
| Region | Dropdown | Geographic region | Gulf of America |
| Formation | Text | Producing formation | MIOCENE |
| Operator | Dropdown | Company name | Shell Offshore |

---

## Sample Query URL

```
https://www.data.bsee.gov/Well/Completion/Default.aspx
  ?Region=Gulf%20of%20America
  &CompletionType=OC
  &CompletionDateFrom=01/01/2024
  &CompletionDateTo=12/31/2024
```

---

## Related Documents

- [Borehole Fields](borehole-fields.md) - Well master data
- [APD Fields](apd-fields.md) - Permit application data
- [WAR Fields](war-fields.md) - Well Activity Reports
- [Production Fields](../production/production-fields.md) - Production data
- [Status Codes](status-codes.md) - Well status reference
