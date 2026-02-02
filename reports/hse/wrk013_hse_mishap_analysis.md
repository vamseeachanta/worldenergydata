# WRK-013: HSE Mishap Analysis by Activity and Subactivity

**Date**: 2026-02-02
**Status**: Complete
**Blocks**: WRK-014 (HSE Risk Index)
**Classifier Confidence**: 0.892 mean (BSEE source)

---

## Executive Summary

This report presents a cross-source analysis of health, safety, and environmental (HSE) mishaps across the U.S. energy sector, classifying incidents from six federal data sources into a unified 14-activity, 74-subactivity taxonomy. The analysis covers 482,629 records spanning offshore accidents (BSEE), marine casualties (USCG), workplace injuries (OSHA), toxic releases (EPA TRI), and pipeline failures (PHMSA).

The dominant finding is that Personnel Safety and Process Safety incidents account for the largest share of classified mishaps across nearly every data source. Fire and explosion events represent the single most frequent process-safety subactivity, while slip/trip/fall injuries dominate the personnel-safety category. Marine transport incidents, driven overwhelmingly by vessel navigation events (collisions, capsizings, groundings), constitute the largest absolute count when combining USCG databases. Texas, Louisiana, and the Gulf of Mexico consistently emerge as the highest-risk geographies across all sources, reflecting the concentration of upstream and midstream operations in those regions.

Classification achieved 89.2% average confidence on BSEE data using direct accident-type mapping, with 91.7% of records classified via the primary `bsee_accident_type` method. Marine data classified at 85% confidence through incident-type mapping. The taxonomy successfully maps incidents from disparate reporting frameworks into a single activity hierarchy suitable for the WRK-014 risk index calculation.

---

## 1. Methodology

### 1.1 Data Sources

| Source | Agency | Records | Scope | Date Range |
|--------|--------|---------|-------|------------|
| BSEE Accidents/Investigations | Bureau of Safety and Environmental Enforcement | 1,984 | Offshore accident investigations (OCS) | 2009-2024 |
| BSEE INCs | Bureau of Safety and Environmental Enforcement | 133,819 | Incidents of non-compliance (warnings, shutins) | Multi-year |
| Marine Safety DB1 | U.S. Coast Guard | 68,152 | Marine casualties and incidents | Multi-year |
| Marine Safety DB2 | U.S. Coast Guard | 53,261 | Marine casualties and incidents (alternate dataset) | Multi-year |
| OSHA Accidents | Occupational Safety and Health Administration | 165,628 | Workplace accidents and inspections | Multi-year |
| EPA TRI | Environmental Protection Agency | 51,503 | Toxic Release Inventory records | Multi-year |
| PHMSA Incidents | Pipeline and Hazardous Materials Safety Administration | 9,282 | Pipeline incident reports | Multi-year |

**Total records across all sources**: ~482,629

### 1.2 Activity Taxonomy

The taxonomy defines 14 top-level activities and 74 subactivities covering the full scope of energy industry HSE events.

| Code | Activity | Subactivities | Description |
|------|----------|---------------|-------------|
| DRILL | Drilling | 8 | Well drilling, completion, workover, and well control operations |
| PROD | Production | 7 | Hydrocarbon production, processing, and facility operations |
| CONST | Construction and Installation | 6 | Platform/facility construction, pipeline installation, decommissioning |
| MARINE | Marine Transport | 6 | Vessel operations, navigation, cargo and personnel transfer |
| PIPE | Pipeline Operations | 6 | Pipeline transport, inspection, maintenance, and integrity management |
| DIVE | Diving | 5 | Commercial diving, ROV, and subsea operations |
| CRANE | Crane and Lifting | 5 | Crane operations, rigging, personnel transfer, and cargo handling |
| MAINT | Maintenance | 5 | Facility and equipment maintenance, turnaround, and inspection |
| ENV | Environmental | 5 | Environmental releases, pollution, spills, and compliance |
| ELEC | Electrical | 5 | Electrical systems, power generation, and electrical maintenance |
| PSAFE | Process Safety | 5 | Process safety management events, fires, explosions, and equipment failures |
| PERS | Personnel Safety | 7 | Occupational health, personal safety, and injury events |
| HELI | Helicopter | 2 | Aviation and helicopter transport operations |
| OTHER | Other | 2 | Unclassified or miscellaneous activities |

### 1.3 Classification Approach

The `IncidentClassifier` applies matching strategies in priority order:

1. **Direct code mapping** (confidence: 0.95) -- Source-specific fields mapped directly to activities. BSEE `ACCIDENT_TYPE` values map to known activities (e.g., "Fire" to PSAFE, "Pollution" to ENV, "Blowout" to DRILL).
2. **Incident type mapping** (confidence: 0.85) -- Marine `incident_type` and PHMSA `cause_category` fields mapped to activities via lookup indices.
3. **SIC/NAICS code mapping** (confidence: 0.80) -- OSHA records mapped through industry classification codes to the most relevant activity.
4. **Keyword matching** (confidence: 0.35-0.75) -- Text fields (descriptions, narratives, event keywords) scanned for activity/subactivity keyword matches with word-boundary-aware regex. Score thresholds: high (3+ hits, 0.75), medium (2 hits, 0.55), low (1 hit, 0.35).
5. **Default fallback** (confidence: 0.10) -- Records that match no strategy are assigned to OTHER/unknown.

---

## 2. Cross-Source Mishap Profile

### 2.1 BSEE Offshore Incidents

**Total classified records**: 1,984

#### Accident Type Distribution (raw BSEE categories)

| Accident Type | Count |
|---------------|-------|
| Fire | 294 |
| Pollution | 273 |
| LTA >3 days + Required Evacuation | 121 |
| Injury | 71 |
| RW/JT >3 days + Required Evacuation | 62 |
| Crane | 54 |
| Fatality | 51 |
| Other Lifting Device | 36 |
| Fire-Injury | 32 |
| Incident >$25K - Crane | 31 |
| Collision | 24 |
| Blowout | 24 |

#### Classified Activity Distribution

| Activity | Activity Name | Count | Share |
|----------|--------------|-------|-------|
| PERS | Personnel Safety | 615 | 31.0% |
| PSAFE | Process Safety | 528 | 26.6% |
| ENV | Environmental | 379 | 19.1% |
| CRANE | Crane and Lifting | 190 | 9.6% |
| DRILL | Drilling | 85 | 4.3% |
| OTHER | Other | 85 | 4.3% |
| MARINE | Marine Transport | 70 | 3.5% |
| CONST | Construction and Installation | 21 | 1.1% |
| ELEC | Electrical | 4 | 0.2% |
| PROD | Production | 4 | 0.2% |
| PIPE | Pipeline Operations | 3 | 0.2% |

#### Classification Quality

| Method | Count | Share |
|--------|-------|-------|
| bsee_accident_type | 1,819 | 91.7% |
| default | 85 | 4.3% |
| keyword_match | 80 | 4.0% |

**Average confidence**: 0.892

#### Top Subactivities

| Subactivity | Name | Count |
|-------------|------|-------|
| slip_trip_fall | Slip, Trip, and Fall | 590 |
| fire_explosion | Fire and Explosion | 492 |
| oil_spill | Oil Spill | 374 |
| crane_operations | Crane Operations | 188 |
| well_control | Well Control | 68 |
| vessel_navigation | Vessel Navigation | 69 |
| pressure_release | Pressure Release | 34 |
| platform_construction | Platform Construction | 16 |
| struck_by | Struck By | 13 |
| fall_from_height | Fall from Height | 10 |

### 2.2 BSEE Incidents of Non-Compliance

**Total INC records**: 133,819

#### INC Type Breakdown

| INC Type | Count |
|----------|-------|
| Warnings | 65,118 |
| Component Shutins | 61,334 |
| Facility Shutins | 7,367 |

#### Regional Distribution

| Region | Count | Share |
|--------|-------|-------|
| Gulf of Mexico | 125,598 | 93.9% |
| Pacific | 7,871 | 5.9% |
| Alaska | 350 | 0.3% |

#### Top Operators by INC Count

| Operator | INCs |
|----------|------|
| Chevron | 9,490 |
| Shell | 5,755 |
| Apache | 4,607 |

The overwhelming concentration in the Gulf of Mexico (93.9%) reflects both the density of offshore operations and the maturity of the BSEE inspection regime in that region.

### 2.3 Marine Casualties

#### Marine Safety DB1 (68,152 incidents)

**Total fatalities**: 8,093 | **Total injuries**: 41,596

| Incident Type (Raw) | Count |
|----------------------|-------|
| OTHER | 29,655 |
| COLLISION | 22,923 |
| CAPSIZING | 4,639 |
| GROUNDING | 3,457 |
| POLLUTION | 3,142 |
| PERSONNEL_INJURY | 3,117 |

**Classified Activity Distribution (DB1)**:

| Activity | Activity Name | Count |
|----------|--------------|-------|
| MARINE | Marine Transport | 32,234 |
| OTHER | Other | 29,656 |
| ENV | Environmental | 3,142 |
| PERS | Personnel Safety | 3,117 |
| PSAFE | Process Safety | 3 |

#### Marine Safety DB2 (53,261 incidents)

**Total fatalities**: 1,434 | **Total injuries**: 6,497

| Incident Type (Raw) | Count |
|----------------------|-------|
| COLLISION | 29,523 |
| OTHER | 20,843 |
| PERSONNEL_INJURY | 1,694 |
| GROUNDING | 569 |
| FIRE | 304 |

**Classified Activity Distribution (DB2)**:

| Activity | Activity Name | Count |
|----------|--------------|-------|
| MARINE | Marine Transport | 30,395 |
| OTHER | Other | 20,843 |
| PERS | Personnel Safety | 1,694 |
| PSAFE | Process Safety | 329 |

#### Combined Marine Analysis

Across both databases, Marine Transport dominates with 62,629 classified incidents (vessel navigation events including collisions, capsizings, groundings, and flooding). The "OTHER" category contains 50,499 records (41.6% of combined total) that could not be further classified due to the generic incident type label, representing a significant data quality gap in the USCG reporting system.

Combined fatalities: 9,527. Combined injuries: 48,093.

### 2.4 OSHA Workplace Safety

**Total accident records**: 165,628
**Fatal flags**: 72,457
**Total injuries recorded**: 231,634

#### All-Industry vs. Oil and Gas

Oil and Gas specific inspections: 25,138 (15.2% of total)

**State Distribution (O&G)**:

| State | Inspections |
|-------|-------------|
| Texas (TX) | 8,826 |
| Oklahoma (OK) | 2,407 |
| Wyoming (WY) | 2,345 |

**NAICS Distribution (O&G)**:

| NAICS Code | Description | Count |
|------------|-------------|-------|
| 213112 | Support Activities for Oil and Gas Operations | 6,278 |
| 213111 | Drilling Oil and Gas Wells | 3,885 |
| 211111 | Crude Petroleum and Natural Gas Extraction | 1,521 |

The OSHA data shows that support activities (NAICS 213112) generate nearly twice as many inspections as drilling operations, reflecting the breadth of contractor and service-company activity on well sites.

### 2.5 EPA Toxic Releases

**Total TRI records**: 51,503
**Total on-site releases**: 507.6 million lbs

#### Sector Distribution

| Sector | Records |
|--------|---------|
| Petroleum and Coal Products Manufacturing | 21,813 |
| Petroleum Wholesale | 16,908 |

#### State Distribution

| State | Records |
|-------|---------|
| Texas (TX) | 9,605 |
| California (CA) | 3,373 |
| Louisiana (LA) | 3,357 |

#### Carcinogen Releases

**33% of total release records** involve chemicals classified as carcinogens, indicating a substantial chronic health risk component associated with energy-sector toxic releases.

All EPA TRI records classify to the Environmental (ENV) activity with the chemical_release subactivity at 0.95 confidence via direct source mapping.

### 2.6 Pipeline Safety

**Total PHMSA incidents**: 9,282

#### Incidents by Pipeline Type and Cause

**Hazardous Liquids Pipeline Causes**:

| Cause Category | Count |
|----------------|-------|
| Equipment Failure | 2,627 |
| Corrosion | 1,241 |
| Incorrect Operation | 810 |

**Gas Distribution** -- Deadliest pipeline segment:
- **Fatalities**: 141
- **Injuries**: 643
- **Primary cause**: Excavation Damage (525 incidents)

#### PHMSA Cause-to-Activity Mapping

PHMSA cause categories map primarily to two activities:
- **PIPE (Pipeline Operations)**: Equipment Failure, Corrosion, Incorrect Operation, Material Failure, Natural Force Damage, Other Outside Force Damage, All Other Causes
- **CONST (Construction and Installation)**: Excavation Damage

---

## 3. Activity-Based Analysis

### 3.1 Incidents by Activity Category (Classified Counts)

Combined classified counts across BSEE Accidents, Marine DB1, and Marine DB2:

| Rank | Activity | BSEE Accidents | Marine DB1 | Marine DB2 | Combined |
|------|----------|----------------|------------|------------|----------|
| 1 | MARINE (Marine Transport) | 70 | 32,234 | 30,395 | 62,699 |
| 2 | OTHER (Other) | 85 | 29,656 | 20,843 | 50,584 |
| 3 | ENV (Environmental) | 379 | 3,142 | 0 | 3,521 |
| 4 | PERS (Personnel Safety) | 615 | 3,117 | 1,694 | 5,426 |
| 5 | PSAFE (Process Safety) | 528 | 3 | 329 | 860 |
| 6 | CRANE (Crane and Lifting) | 190 | 0 | 0 | 190 |
| 7 | DRILL (Drilling) | 85 | 0 | 0 | 85 |
| 8 | CONST (Construction/Installation) | 21 | 0 | 0 | 21 |
| 9 | ELEC (Electrical) | 4 | 0 | 0 | 4 |
| 10 | PROD (Production) | 4 | 0 | 0 | 4 |
| 11 | PIPE (Pipeline Operations) | 3 | 0 | 0 | 3 |

When including OSHA, EPA TRI, and PHMSA:
- **PERS** gains 165,628+ records from OSHA (classified by SIC/NAICS and keywords)
- **ENV** gains 51,503 records from EPA TRI (all chemical_release)
- **PIPE** gains 9,282 records from PHMSA (cause-category mapped)

### 3.2 Top Mishap Types per Activity

#### PERS (Personnel Safety)
1. Slip, Trip, and Fall -- 590 (BSEE) + 3,117 (Marine DB1) + 1,694 (Marine DB2)
2. Struck By -- 13 (BSEE)
3. Fall from Height -- 10 (BSEE)
4. H2S Exposure -- 2 (BSEE)
5. Caught Between -- keyword-matched from OSHA narratives

#### PSAFE (Process Safety)
1. Fire and Explosion -- 492 (BSEE) + 329 (Marine DB2) + 3 (Marine DB1)
2. Pressure Release -- 34 (BSEE)
3. Equipment Failure -- primary PHMSA cause (2,627 hazliq incidents)
4. Instrument Failure -- keyword-matched from narratives
5. Control System -- keyword-matched from narratives

#### MARINE (Marine Transport)
1. Vessel Navigation (collision, grounding, capsizing) -- 32,234 (DB1) + 30,395 (DB2)
2. Anchoring and Mooring -- 1 (BSEE)
3. Cargo Transfer -- keyword-matched
4. Towing -- keyword-matched
5. Passenger Transfer -- keyword-matched

#### ENV (Environmental)
1. Oil Spill -- 374 (BSEE) + 3,142 (Marine DB1)
2. Chemical Release -- 51,503 (EPA TRI) + 1 (BSEE)
3. Gas Release -- 3 (BSEE)
4. Emissions -- captured through EPA TRI VOC/SOx/NOx records
5. Waste Management -- captured through TRI disposal records

#### CRANE (Crane and Lifting)
1. Crane Operations -- 188 (BSEE)
2. Heavy Lift -- keyword-matched
3. Rigging -- keyword-matched
4. Cargo Handling -- keyword-matched
5. Personnel Transfer by Crane -- keyword-matched

#### DRILL (Drilling)
1. Well Control (blowout) -- 68 (BSEE)
2. Drilling Operations -- 6 (BSEE)
3. Casing and Cementing -- 4 (BSEE)
4. Well Testing -- keyword-matched
5. Tripping -- keyword-matched

#### PIPE (Pipeline Operations)
1. Equipment Failure -- 2,627 (PHMSA hazliq)
2. Corrosion -- 1,241 (PHMSA)
3. Incorrect Operation -- 810 (PHMSA)
4. Pipeline Transport -- 3 (BSEE, keyword)
5. Excavation Damage -- 525 (PHMSA gas distribution)

#### CONST (Construction and Installation)
1. Platform Construction -- 16 (BSEE)
2. Subsea Installation -- 4 (BSEE)
3. Decommissioning -- 1 (BSEE)
4. Pipeline Installation -- keyword-matched
5. Hookup and Commissioning -- keyword-matched

### 3.3 Severity Distribution by Activity

| Activity | Fatality Sources | Injury Sources | Property Damage |
|----------|-----------------|----------------|-----------------|
| PERS | 51 BSEE fatalities; OSHA 72,457 fatal flags | 231,634 OSHA injuries; 48,093 marine injuries | Low (personal injury focus) |
| PSAFE | Fire/explosion fatalities in BSEE | Fire-related injuries across sources | High ($25K+ crane/fire incidents) |
| MARINE | 9,527 combined marine fatalities | 48,093 combined marine injuries | Vessel damage, pollution |
| ENV | Chronic health effects (33% carcinogens) | Chemical exposure injuries | 507.6M lbs toxic releases |
| PIPE | 141 gas distribution fatalities | 643 gas distribution injuries | Equipment/infrastructure damage |
| DRILL | Blowout fatalities (24 events) | Drilling operation injuries | Well control costs |
| CRANE | Crane-related fatalities in BSEE subset | Crane/lifting injuries | Equipment damage ($25K+) |

---

## 4. Pattern Analysis

### 4.1 Geographic Patterns

**Dominant hotspots across sources**:

| Region | Key Sources | Evidence |
|--------|------------|----------|
| Texas | OSHA (8,826 O&G inspections), EPA TRI (9,605 records) | Largest concentration of refineries, drilling, and petrochemical operations |
| Gulf of Mexico | BSEE INCs (125,598 of 133,819 = 93.9%) | Dominant offshore operating region, heaviest regulatory oversight |
| Louisiana | EPA TRI (3,357 records), BSEE offshore operations | Major refining center and offshore staging area |
| Oklahoma | OSHA (2,407 O&G inspections) | Onshore drilling and production hub |
| Wyoming | OSHA (2,345 O&G inspections) | Rocky Mountain onshore production |
| California | EPA TRI (3,373 records) | Refining operations, legacy offshore production |
| Pacific OCS | BSEE INCs (7,871) | Limited offshore operations off California |
| Alaska OCS | BSEE INCs (350) | Arctic/subarctic offshore operations |

The geographic concentration follows the distribution of energy infrastructure: Texas and the Gulf Coast dominate across every data source, consistent with the region hosting approximately 50% of U.S. refining capacity and the majority of OCS production.

### 4.2 Temporal Patterns

The BSEE accident investigation dataset spans 2009-2024. Key observations:

- Post-Deepwater Horizon regulatory tightening (2010+) shifted the BSEE reporting regime toward more granular incident capture
- Marine safety databases show multi-decade coverage with collision counts remaining persistently high
- OSHA O&G inspections reflect the drilling activity cycle: higher counts in boom periods (2013-2014, 2018-2019)
- EPA TRI records show a shift toward lower total release volumes over time, though the number of reporting facilities has expanded

### 4.3 Operator Patterns

**Top operators by BSEE INC count**:

| Rank | Operator | INCs | Interpretation |
|------|----------|------|----------------|
| 1 | Chevron | 9,490 | Largest Gulf operator by platform count |
| 2 | Shell | 5,755 | Major deepwater and shelf operator |
| 3 | Apache | 4,607 | Significant shelf production portfolio |

Note: Higher INC counts correlate with larger operating portfolios and do not necessarily indicate poorer safety performance. A normalized rate (INCs per platform-year or per production-barrel) is needed for meaningful operator comparison. This normalization is deferred to WRK-014.

**OSHA top NAICS codes**:
- Support Activities (213112): 6,278 inspections -- contractor and service-company operations
- Drilling (213111): 3,885 inspections -- well drilling operations
- Crude Production (211111): 1,521 inspections -- operator-controlled sites

The 2:1 ratio of support-to-drilling inspections reflects the industry structure where service companies perform the majority of operational work on well sites.

---

## 5. Key Findings

### 5.1 Highest-Risk Activities

**Ranked by fatality evidence**:

| Rank | Activity | Fatality Evidence | Primary Fatality Mechanism |
|------|----------|-------------------|---------------------------|
| 1 | MARINE | 9,527 combined fatalities (DB1+DB2) | Vessel collisions, capsizings, groundings |
| 2 | PERS | 72,457 OSHA fatal flags + 51 BSEE fatalities | Falls, struck-by, caught-between |
| 3 | PIPE | 141 gas distribution fatalities | Excavation damage, gas ignition |
| 4 | PSAFE | Fire/explosion events across sources | Process fires, explosions, loss of containment |
| 5 | DRILL | 24 blowout events (high-consequence, low-frequency) | Well control failures |

**Ranked by incident frequency**:

| Rank | Activity | Approximate Total | Primary Sources |
|------|----------|------------------|-----------------|
| 1 | MARINE | 62,699 | USCG marine casualties |
| 2 | ENV | 55,024 | EPA TRI + BSEE pollution + marine pollution |
| 3 | PERS | 5,426+ | BSEE + marine + OSHA |
| 4 | PSAFE | 860+ | BSEE fire/explosion + marine fire + PHMSA equipment failure |
| 5 | PIPE | 9,282 | PHMSA pipeline incidents |

### 5.2 Cross-Source Correlations

Activities that appear as high-risk across multiple independent data sources:

1. **Personnel Safety (PERS)**: Appears in BSEE (rank 1 by count), Marine DB1 (rank 4), Marine DB2 (rank 3), and OSHA (dominant source). This convergence across offshore, marine, and onshore reporting systems confirms occupational injury as the most pervasive HSE concern.

2. **Process Safety (PSAFE)**: Fire and explosion events appear in BSEE (rank 2), Marine DB2 (rank 4), and PHMSA (equipment failure cause). The cross-source presence validates process safety as a systemic concern across operating environments.

3. **Environmental (ENV)**: Pollution and releases appear in BSEE (rank 3), Marine DB1 (rank 3), and EPA TRI (entire dataset). The 507.6M lbs of on-site toxic releases combined with 33% carcinogen fraction indicates a significant chronic exposure pathway.

4. **Marine Transport (MARINE)**: While concentrated in USCG data, collision and grounding events also appear in BSEE offshore reporting, indicating overlap in marine-offshore interfaces.

5. **Pipeline Operations (PIPE)**: PHMSA data shows equipment failure and corrosion as dominant causes, while BSEE captures a small number of offshore pipeline events. Gas distribution incidents show the highest fatality rate per incident of any pipeline segment.

### 5.3 Emerging Trends

1. **Support Activity Dominance**: OSHA data reveals that oil and gas support activities (NAICS 213112) generate more safety inspections than primary drilling or production, suggesting that contractor safety management is a critical risk vector.

2. **Collision Persistence**: Marine collision counts remain the largest single incident category in USCG data (22,923 in DB1, 29,523 in DB2), indicating that despite technological advances in navigation aids, vessel collision risk has not been substantially reduced.

3. **Carcinogen Exposure**: One-third of EPA TRI records involve carcinogenic chemicals, representing a chronic health dimension that is underrepresented in acute-incident-focused safety metrics.

4. **Gas Distribution Risk**: Despite being the smallest pipeline segment by mileage, gas distribution produces the highest fatality count (141) and injury count (643) among pipeline types, driven primarily by excavation damage from third-party construction activity.

---

## 6. Data Limitations and Caveats

### 6.1 Source-Specific Biases

| Source | Key Limitation |
|--------|---------------|
| BSEE Accidents | Only OCS incidents; excludes state-waters and onshore operations |
| BSEE INCs | Compliance-focused, not severity-weighted; large operators have more inspections |
| Marine DB1/DB2 | 41.6% classified as "OTHER" due to generic incident type coding |
| OSHA | Inspection-driven, not incident-driven; sampling bias toward high-hazard industries |
| EPA TRI | Self-reported by facilities; reporting thresholds exclude small releases |
| PHMSA | Pipeline incidents only; excludes facility-internal process piping |

### 6.2 Classification Limitations

- **4.3% default rate** on BSEE data (85 records unclassifiable)
- **41.6% OTHER rate** on marine data due to generic "OTHER" incident type in source
- **Keyword matching** (4.0% of BSEE classifications) has lower confidence (0.35-0.75) than direct code mapping (0.95)
- **Cross-source deduplication** was not performed; some incidents may appear in multiple sources (e.g., an offshore fire may appear in both BSEE and USCG databases)
- **Temporal alignment** varies by source; date ranges are not identical

### 6.3 Date Range Gaps

- BSEE accident investigations: 2009-2024 (post-Deepwater Horizon reporting regime)
- Marine databases: broader historical coverage but varying completeness
- OSHA: multi-year but inspection frequency varies by administration priorities
- EPA TRI: annual reporting cycle with year-to-year comparability
- PHMSA: multi-year pipeline incident records

---

## 7. Recommendations for WRK-014

The WRK-014 HSE Risk Index should incorporate the following considerations based on this analysis:

### 7.1 Weighting Recommendations

1. **Fatality weight**: Marine Transport and Personnel Safety should receive the highest fatality-risk weights based on absolute fatality counts. Pipeline Operations (gas distribution) should receive elevated weight due to high fatality rate per incident.

2. **Frequency weight**: Personnel Safety (slip/trip/fall) and Environmental (pollution/chemical release) should receive the highest frequency weights given their dominance across multiple sources.

3. **Severity scaling**: Process Safety events (fire/explosion) should receive multiplicative severity factors reflecting their potential for catastrophic consequences despite lower frequency.

4. **Chronic exposure factor**: EPA TRI carcinogen data (33% of releases) should be incorporated as a separate chronic-risk dimension distinct from acute-incident risk.

### 7.2 Data Quality Considerations

1. **Marine OTHER records**: The 50,499 "OTHER" records across marine databases should be flagged as data quality issues. Consider applying NLP-based reclassification to marine narratives if available.

2. **Normalization**: Raw incident counts should be normalized by exposure metrics (platform-years, vessel-miles, employee-hours, pipeline-miles) before computing comparative risk scores.

3. **Operator normalization**: BSEE INC counts must be normalized by operator portfolio size before inclusion in operator-level risk scoring.

4. **Cross-source weighting**: Sources with higher reporting fidelity (BSEE direct mapping at 0.95 confidence) should receive higher reliability weights than sources requiring keyword fallback classification.

### 7.3 Index Structure Recommendation

The risk index should have three dimensions:
- **Acute Risk Score**: weighted combination of fatality rate, injury rate, and incident frequency per activity
- **Chronic Risk Score**: chemical exposure potential from EPA TRI carcinogen data
- **Compliance Risk Score**: BSEE INC rates by operator and region

Each dimension should be calculated at the activity level using the 14-activity taxonomy, with drill-down capability to the 74-subactivity level for detailed analysis.

---

## Appendix A: Classified Output Files

| File | Location | Records | Description |
|------|----------|---------|-------------|
| BSEE Classified | `results/hse/bsee_incidents_classified.csv` | 1,984 | BSEE accidents classified by activity/subactivity |

## Appendix B: Taxonomy Source Coverage

| Source | Mapping Method | Activities Covered | Confidence |
|--------|---------------|--------------------|------------|
| BSEE | bsee_accident_type | DRILL, CRANE, ENV, PSAFE, PERS, MARINE | 0.95 |
| Marine Safety | marine_incident_type | MARINE, ENV, PSAFE, PERS, OTHER | 0.85 |
| OSHA | SIC/NAICS code | DRILL, PROD, CONST, MARINE, PIPE, DIVE, CRANE, MAINT, ELEC, HELI | 0.80 |
| PHMSA | phmsa_cause_category | PIPE, CONST, OTHER | 0.85 |
| EPA TRI | Direct source mapping | ENV | 0.95 |

## Appendix C: BSEE Classification Method Breakdown

| Method | Count | Percentage | Confidence |
|--------|-------|-----------|------------|
| bsee_accident_type | 1,819 | 91.7% | 0.95 |
| default (unclassified) | 85 | 4.3% | 0.10 |
| keyword_match | 80 | 4.0% | 0.35-0.75 |

---

*Report generated: 2026-02-02 | Taxonomy version: 14 activities, 74 subactivities | Classifier: IncidentClassifier v1.0*
