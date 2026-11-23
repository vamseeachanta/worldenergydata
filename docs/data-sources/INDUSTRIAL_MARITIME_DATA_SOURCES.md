# Industrial Maritime Incident Data Sources

**Research Date:** October 6, 2025
**Repository:** WorldEnergyData
**Focus:** Industrial/Commercial Maritime Incidents (Non-Recreational)

---

## Executive Summary

This document catalogs publicly available data sources for industrial maritime incidents, complementing our existing recreational boating and oil spill databases. The research identified **50+ distinct data sources** across federal agencies, international organizations, industry bodies, and academic institutions.

### Coverage Highlights:
- ✅ **Offshore oil & gas incidents** - Comprehensive coverage via BSEE, USCG
- ✅ **Port/terminal operations** - OSHA, state agencies, RightShip data
- ✅ **Commercial vessel casualties** - USCG, EMSA, IMO GISIS, classification societies
- ✅ **Maritime labor/occupational safety** - OSHA, ILO, BLS
- ⚠️ **Marine construction** - Limited dedicated databases
- ⚠️ **Fishing industry** - NIOSH only (already documented)
- ⚠️ **Specialized operations** - DP vessels (IMCA), cybersecurity (SIPRI), offshore wind (G+)

---

## Priority Tier 1: Federal U.S. Sources (High Value, Free Access)

### 1.1 OSHA Maritime Industry Data
**Organization:** Occupational Safety and Health Administration
**URL:** https://www.osha.gov/data
**Data Coverage:** Workplace injuries/fatalities in maritime sector (all industries)

#### Key Databases:
- **Injury Tracking Application (ITA):** Establishment-specific injury/illness data
- **Fatality Inspection Data:** Work-related fatalities since 2017
- **OSHA Data Catalog:** Inspection case details with incident descriptions
- **Severe Injury Reports:** Hospitalization, amputation, eye loss cases

#### Technical Details:
- **Format:** Downloadable datasets (CSV, Excel)
- **Coverage Period:** 2017-present for fatalities; varies by database
- **Update Frequency:** Daily for fatality data; annual for ITA
- **Record Estimates:** 100,000+ inspection records annually
- **Filtering Required:** Use NAICS/SIC codes for maritime industries
  - 336611: Ship Building and Repairing
  - 483000: Water Transportation
  - 488300: Support Activities for Water Transportation
  - 237990: Marine Construction

#### Access:
- ✅ Free, no registration
- ✅ Bulk download available
- ⚠️ Website not updated since 10/1/2025 (government services suspension)

#### Complementarity:
Fills **occupational injury/fatality gap** - provides worker-level incident data not captured in vessel casualty databases. Critical for offshore platform workers, port terminal operations, shipyard incidents.

---

### 1.2 U.S. Coast Guard Marine Casualty Database
**Organization:** USCG Office of Investigations & Casualty Analysis
**URL:** https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/Marine-Casualty-and-Pollution-Data-for-Researchers/

#### Database Components:
- **MISLE (Marine Information for Safety and Law Enforcement)**
- **BARD (Boating Accident Report Database)** - recreational only
- **Marine Casualty Database** - commercial vessels

#### Technical Details:
- **Format:** Delimited text files, MS Access
- **Coverage Period:** 1982-present (casualties), 1973-present (pollution)
- **Update Frequency:** Quarterly
- **Record Estimates:** 500,000+ total records
- **Geographic Scope:** U.S. waters and U.S.-flagged vessels worldwide

#### Access:
- ✅ Free download for researchers
- ✅ Bulk download available
- ✅ Data dictionaries provided

#### Complementarity:
**PRIMARY SOURCE** for U.S. commercial vessel casualties. Already documented but critical foundation.

---

### 1.3 BSEE Offshore Incident Statistics
**Organization:** Bureau of Safety and Environmental Enforcement
**URL:** https://www.bsee.gov/stats-facts/offshore-incident-statistics

#### Data Categories:
- Platform fires and explosions
- Blowouts and well control incidents
- Injuries and fatalities (offshore workers)
- Collisions with offshore structures
- Loss of well control
- Hydrogen sulfide (H2S) releases

#### Technical Details:
- **Format:** Excel, PDF reports
- **Coverage Period:** 1996-present (some data older)
- **Update Frequency:** Annual
- **Record Estimates:** 10,000+ incidents
- **Geographic Scope:** U.S. Outer Continental Shelf

#### Access:
- ✅ Free, no registration
- ✅ Downloadable reports and datasets

#### Complementarity:
**ESSENTIAL** for offshore oil & gas platform incidents. Already documented; critical for industrial maritime safety.

---

### 1.4 EPA National Response Center (NRC) Database
**Organization:** Environmental Protection Agency / U.S. Coast Guard
**URL:** https://www.epa.gov/emergency-response/national-response-center

#### Data Coverage:
- Oil spills (all sources including maritime)
- Chemical spills and releases
- Hazardous substance discharges
- Radiological releases
- Maritime security incidents (suspicious activity)

#### Technical Details:
- **Format:** Online query system, downloadable reports
- **Coverage Period:** 1990s-present
- **Update Frequency:** Real-time (24/7 reporting)
- **Record Estimates:** 200,000+ incident reports
- **Hotline:** 1-800-424-8802

#### Access:
- ✅ Free public access
- ✅ Historical reports viewable online
- ⚠️ Bulk download may require FOIA request

#### Complementarity:
Complements NOAA oil spill data with **broader chemical/hazmat incidents**. Includes land-based and maritime pollution events.

---

### 1.5 DOE Offshore Pipeline & Energy Facility Incidents
**Organization:** Department of Energy / OSTI
**URL:** https://www.osti.gov/dataexplorer/biblio/dataset/2280823

#### Data Coverage:
- Offshore pipeline incidents
- Reported causes of pipeline failures
- Incident dates and locations (OCS lease blocks)
- Energy facility operational incidents

#### Technical Details:
- **Format:** Dataset (CSV/Excel)
- **Coverage Period:** 1986-2021
- **Record Count:** 900+ offshore pipeline incidents
- **Geographic Scope:** U.S. Outer Continental Shelf

#### Additional DOE Databases:
- **CAIRS (Computerized Accident/Incident Reporting System):** DOE contractor injuries/illnesses
- **ORPS (Occurrence Reporting and Processing System):** Events affecting worker safety/environment

#### Access:
- ✅ Free public download
- ✅ Hosted on DOE Data Explorer

#### Complementarity:
Specialized **offshore pipeline incident data** not available elsewhere. Complements BSEE platform data.

---

### 1.6 PHMSA Hazardous Materials Incident Database
**Organization:** Pipeline and Hazardous Materials Safety Administration
**URL:** https://hazmatonline.phmsa.dot.gov/IncidentReportsSearch/

#### Maritime Relevance:
- Dangerous goods cargo incidents (packaged)
- Marine hazmat transportation violations
- LNG carrier incidents (since 2011)
- Chemical spill incidents

#### Technical Details:
- **Format:** Searchable database, Excel export
- **Coverage Period:** 1971-present (varies by category)
- **Update Frequency:** Nightly updates
- **Form:** DOT Form 5800.1

#### Important Limitations:
- ⚠️ **Does NOT include bulk marine hazmat** (reported to USCG instead)
- Focuses on packaged/containerized dangerous goods

#### Access:
- ✅ Free public access
- ✅ Downloadable datasets
- ✅ Statistics dashboard

#### Complementarity:
Fills **containerized hazmat transport gap**. Use alongside IMO GISIS for comprehensive dangerous goods incident coverage.

---

### 1.7 BLS (Bureau of Labor Statistics) Occupational Injury Data
**Organization:** U.S. Department of Labor
**URL:** https://www.bls.gov/iif/

#### Databases:
- **Survey of Occupational Injuries and Illnesses (SOII)**
- **Census of Fatal Occupational Injuries (CFOI)**

#### Maritime Industry Coverage:
- Water transportation (NAICS 483)
- Support activities for water transportation (NAICS 4883)
- Ship and boat building (NAICS 3366)
- Marine cargo handling (NAICS 488320)

#### Technical Details:
- **Format:** Excel, PDF, online query tool
- **Coverage Period:** 1992-present (varies)
- **Update Frequency:** Annual
- **Geographic Scope:** All U.S. states

#### Access:
- ✅ Free public access
- ✅ Downloadable datasets
- ✅ Customizable queries

#### Complementarity:
Provides **industry-wide labor statistics** with maritime breakdowns. Complements OSHA incident-level data.

---

### 1.8 State Maritime Agency Incident Reporting

#### California Division of Boating and Waterways (DBW)
**URL:** https://dbw.parks.ca.gov/
**Data:** Boating accident reports (form DBW BAR-1)
- ⚠️ **Primarily recreational** but includes commercial vessels
- **Requirements:** Death, injury, $500+ damage
- **Timeframe:** 48 hours for death/serious injury

#### Federal Requirement:
All states receive boating accident reports per 46 CFR Part 4.05-1
- Form CG-3865 or state equivalent
- Compiled into USCG BARD database

#### Complementarity:
**Limited industrial value** - state agencies primarily track recreational boating. Commercial vessels report to USCG directly.

---

## Priority Tier 1: International Organizations (High Value)

### 2.1 IMO Global Integrated Shipping Information System (GISIS)
**Organization:** International Maritime Organization
**URL:** https://gisis.imo.org/

#### Modules:
- **Marine Casualties and Incidents (MCI):** Worldwide casualty database
- **Port State Control:** Inspection/deficiency records
- **Piracy and Armed Robbery:** Security incidents
- **Global Integrated Shipping Information:** Ship particulars
- **Dangerous Goods Incidents:** IMO DG transport accidents (2000-2023)

#### Technical Details:
- **Format:** Online database with export functions
- **Coverage:** Global - all IMO member states
- **Update Frequency:** Continuous
- **Record Estimates:** 100,000+ casualties and incidents

#### Access:
- ⚠️ **Registration required** (free for government/academic users)
- ⚠️ Some modules restricted to flag states
- ✅ Annual summaries publicly available

#### Complementarity:
**GLOBAL GOLD STANDARD** for international maritime casualties. Essential for non-U.S. incidents and worldwide trend analysis.

---

### 2.2 EMSA European Marine Casualty Information Platform (EMCIP)
**Organization:** European Maritime Safety Agency
**URL:** https://emsa.europa.eu/emcip.html

#### Database Details:
- Operational since June 2011
- Mandatory reporting for EU/EEA member states
- Stores marine casualties and incidents (all vessel types)
- Includes occupational accidents related to ship operations

#### Technical Details:
- **Format:** Database system (THETIS platform hosted by EMSA)
- **Coverage Period:** 2011-present (some historical data)
- **Coverage Region:** EU/EEA waters plus EU-flagged vessels worldwide
- **Record Estimates:** 26,595 casualties/incidents (2014-2023)

#### Public Access:
- ⚠️ **Direct database access restricted** to authorized national authorities
- ✅ **Annual Overview Reports** freely downloadable (PDF)
- ✅ **Safety Analysis Publications** available by vessel type
- ✅ Investigation reports published (anonymized)

#### Annual Reports Available:
- 2024 Edition: Latest statistics and trend analysis
- Detailed breakdowns by:
  - Navigation accidents
  - Container vessels
  - Fishing vessels
  - Ro-ro vessels
  - Bulk carriers

#### Access:
- ✅ Free public reports (https://www.emsa.europa.eu/accident-investigation-publications/)
- ⚠️ Raw data requires authorization

#### Complementarity:
**EUROPEAN AUTHORITY** on maritime casualties. Provides detailed regional analysis not available in global IMO data. Essential for European vessel/incident coverage.

---

### 2.3 ILO Maritime Worker Safety Data
**Organization:** International Labour Organization
**URL:** https://ilostat.ilo.org/

#### Databases:
- **Global Register on Seafarer Deaths:** Mandatory reporting since Dec 23, 2024
  - Experimental data collection for 2023 (403 deaths reported by 51 countries)
  - Disaggregated by: cause of death, ship type, size, location, seafarer demographics
- **ILO/IMO Joint Database on Abandonment of Seafarers:** Cases since Jan 1, 2004
- **ILOSTAT Occupational Safety & Health Database:** Includes maritime sector
- **WHO/ILO Joint Estimates:** Work-related burden of disease (2000-2016)

#### Technical Details:
- **Format:** Online database (ILOSTAT), downloadable reports
- **Coverage:** Global - ILO member states
- **Update Frequency:** Annual for seafarer deaths
- **First full data:** 2023 statistics published 2024

#### Key Statistics (2023):
- 403 seafarer deaths reported
- Leading cause: Illnesses and diseases (139 cases)
- Coverage: 51 countries (incomplete global coverage)

#### Access:
- ✅ Free public access to ILOSTAT
- ✅ Annual reports downloadable
- ✅ Abandonment database searchable

#### Complementarity:
**UNIQUE WORKER-FOCUSED DATA** - only international source for seafarer mortality by occupation. Fills labor safety gap in vessel-focused casualty databases.

---

### 2.4 Paris MOU Port State Control Database
**Organization:** Paris Memorandum of Understanding on Port State Control
**URL:** https://parismou.org/

#### Database Access:
- **Inspection Search Portal:** parismou.org/inspection-Database/inspection-search
- **THETIS System:** Hosted by EMSA, contains:
  - Ship particulars and certificates
  - Port call records
  - PSC inspection reports
  - Deficiency details (unique codes)

#### Coverage:
- **Region:** European waters, North Atlantic, Canadian Arctic
- **Member Authorities:** 27 maritime administrations
- **Data Period:** Historical records since 1982

#### Technical Details:
- **Format:** Interactive search portal, downloadable reports
- **Update Frequency:** Real-time inspection data
- **Annual Reports:** Comprehensive statistics (PDF)

#### Access:
- ✅ Free inspection search tool
- ✅ Annual reports downloadable
- ⚠️ Bulk data export may require request

#### Complementarity:
**PORT STATE CONTROL DEFICIENCIES** - reveals systemic vessel safety issues before casualties occur. Predictive value for incident prevention.

---

### 2.5 Tokyo MOU Port State Control Database
**Organization:** Tokyo Memorandum of Understanding on Port State Control
**URL:** https://www.tokyo-mou.org/

#### Database Systems:
- **PSC Database:** tokyo-mou.org/inspections-detentions/psc-database/
- **APCIS (Asia Pacific Computerized Information System):** https://apcis.tmou.org/public/
  - Hosted by Information and Coordinating Center (Russian Federation)
  - Real-time publication of PSC data

#### Coverage:
- **Region:** Asia-Pacific (22 member authorities)
- **Countries:** Australia, Canada, Chile, China, Fiji, Hong Kong, Indonesia, Japan, Korea, Malaysia, New Zealand, PNG, Philippines, Russia, Samoa, Singapore, Thailand, Vanuatu, Vietnam, others

#### Technical Details:
- **Format:** Searchable database, annual reports
- **Update Frequency:** Real-time via APCIS
- **Annual Reports:** PDF downloads with statistics

#### Access:
- ✅ Free public access to APCIS portal
- ✅ Annual reports downloadable
- ✅ Inspection search available

#### Complementarity:
**ASIA-PACIFIC PSC DATA** - complements Paris MOU for global port state control coverage. Critical for Asian vessel/trade route incidents.

---

## Priority Tier 2: Classification Societies & Industry (Medium Value)

### 3.1 DNV Maritime Safety Reports
**Organization:** Det Norske Veritas
**URL:** https://www.dnv.com/maritime/publications/

#### Publications:
- **Maritime Safety Trends 2014-2024:** Comprehensive 10-year analysis
  - Data from 866,000 inspections
  - 26,000 detentions
  - 22,000 casualty incidents
  - 1,000 total losses
- **Maritime Safety 2012-2021:** Decade of progress whitepaper

#### Key Findings:
- 42% increase in incidents (2018-2024) vs. 10% fleet growth
- 22% increase in incidents (2022-2024)
- Leading cause: Machinery failures and aging vessels (25+ years)
- 2,200+ recorded casualties per year since 2021

#### Data Source:
Lloyd's List Intelligence casualty database (partnership)

#### Access:
- ✅ Free report downloads
- ✅ Statistics and trend analysis
- ⚠️ Raw data not publicly available

#### Complementarity:
**COMMERCIAL INDUSTRY ANALYSIS** - provides business intelligence perspective on safety trends. Aging fleet analysis unique.

---

### 3.2 Lloyd's Register Foundation Casualty Returns
**Organization:** Lloyd's Register Foundation Heritage & Education Centre
**URL:** https://hec.lrfoundation.org.uk/archive-library/casualty-returns

#### Historical Database:
- **Casualty Returns (Wreck Returns):** Total losses of ocean-going merchant ships >100 GT
- **Coverage Period:** 1890-2000+ (historical archive)
- **Published:** Quarterly and annually

#### Data Includes:
- Losses by flag and cause
- Tonnage statistics (since 1928)
- Ship type (since 1939)
- Year of build (since 1928)
- Size, type, age analysis (since 1967)
- Geographic maps of losses (since 1970)

#### Access:
- ✅ **Free PDF downloads** by year
- ✅ Internet Archive mirror available
- ⚠️ Copyright restrictions (must cite Lloyd's Register Foundation)

#### Modern Data:
- **Lloyd's List Intelligence:** Current casualty database (subscription required)
- Commercial service - not freely accessible

#### Complementarity:
**HISTORICAL BENCHMARK** - essential for long-term trend analysis. Public access to century+ of maritime casualty data.

---

### 3.3 ABS (American Bureau of Shipping) Casualty Data
**Organization:** American Bureau of Shipping
**URL:** https://ww2.eagle.org/

#### Database:
- ABS maintains casualty survey data for classified vessels
- **Data Elements:** File number, survey date, ship particulars, damage descriptions, root cause analysis

#### Critical Limitation:
- ⚠️ **NOT PUBLICLY ACCESSIBLE**
- Services paid for by vessel owners
- **Written owner permission required** for data release
- Proprietary database

#### Alternative:
- **ABS Record Online Database:** Vessel information system (classification status)
- ✅ Publicly searchable for vessel particulars

#### Complementarity:
**LIMITED PUBLIC VALUE** - Classification society data is proprietary. Not usable for research without owner agreements.

---

### 3.4 Bureau Veritas
**Organization:** Bureau Veritas Marine & Offshore
**URL:** https://marine-offshore.bureauveritas.com/

#### Public Resources:
- **BV Fleet Database:** Searchable register of BV-classed ships
- Classification and certification information

#### Incident Data:
- ⚠️ **No public incident/casualty database identified**
- Classification societies maintain proprietary safety records
- Similar restrictions as ABS

#### Complementarity:
**NO INDEPENDENT VALUE** for incident research. Vessel registry only.

---

### 3.5 International Group of P&I Clubs
**Organization:** International Group of Protection & Indemnity Clubs
**URL:** https://www.igpandi.org/

#### Data Available:
- **Annual Summaries:** General statistics on pool claims
- **Pooling Statistics:** Claims sharing data (>$10M incidents)
- **Group Data Highlights:** Aggregate claim trends

#### Coverage:
- 90% of world's ocean-going tonnage insured
- 13 member clubs
- Pool claims threshold: $10M-$8.9B

#### Data Limitations:
- ⚠️ **Aggregated statistics only** - no incident-level data
- ⚠️ Privacy restrictions on individual claims
- ⚠️ Subscription/membership may be required for detailed reports

#### Access:
- ✅ Annual summaries public
- ⚠️ Detailed data restricted to members

#### Complementarity:
**HIGH-VALUE INCIDENTS ONLY** - provides financial severity perspective on major casualties. Complements physical casualty counts.

---

### 3.6 INTERCARGO Bulk Carrier Casualty Reports
**Organization:** International Association of Dry Cargo Shipowners
**URL:** https://www.intercargo.org/

#### Annual Publications:
- **Bulk Carrier Casualty Report** (annual since 2015)
- Latest: 2015-2024 analysis (published 2025)
- Historical: 2011-2020, 2009-2018 reports available

#### Recent Statistics:
- **2015-2024:** 20 bulk carriers lost (≥10,000 DWT), 89 seafarer fatalities
- **Average:** 2 vessels lost per year
- **2013-2022:** 26 bulk carriers lost, 104 deaths
- **2009-2018:** 48 bulk carriers lost

#### Data Quality:
- Focused exclusively on bulk carriers ≥10,000 DWT
- Detailed cause analysis
- Fatality trends tracked

#### Access:
- ⚠️ **Full reports require INTERCARGO membership**
- ✅ Summary statistics publicly available
- ✅ Press releases with key findings

#### Complementarity:
**BULK CARRIER SPECIALIST DATA** - only dedicated database for this vessel type. Critical for dry cargo incident analysis.

---

### 3.7 INTERTANKO Tanker Database (DISCONTINUED)
**Organization:** International Association of Independent Tanker Owners
**URL:** https://www.tankeraccidentdatabase.org/ (defunct)

#### Status:
- ⚠️ **DISCONTINUED as of July 17, 2023**
- Joint database with OCIMF (Oil Companies International Marine Forum)
- Original source data deleted
- Anonymized data archived (not publicly accessible)

#### Historical Value:
- Previously captured tanker accidents and incidents
- Used for industry safety analysis

#### Alternative Resources:
- INTERTANKO still provides member benchmarking tools
- No public tanker-specific incident database currently available

#### Complementarity:
**NO CURRENT VALUE** - database discontinued. Use IMO GISIS, EMCIP, or Lloyd's for tanker incidents.

---

## Priority Tier 2: Specialized Maritime Databases

### 4.1 IMCA Dynamic Positioning Incident Database
**Organization:** International Marine Contractors Association
**URL:** https://www.imca-int.com/resources/dp/dp-incidents/

#### Database Details:
- **Free access** to DP events and incidents (30+ years of data)
- Covers: DP events, incidents, observations, drill scenarios
- Individual entries downloadable as PDF

#### Annual Reports:
- **Dynamic Positioning Station Keeping Reviews** (published annually)
- Technical Library access: imca-int.com/resources/technical-library/

#### Data Submission:
- Members encouraged to report DP station keeping events
- Anonymous reporting supported

#### Access:
- ✅ Free public database search
- ✅ PDF downloads of individual incidents
- ✅ Annual review reports in Technical Library

#### Complementarity:
**SPECIALIZED DP OPERATIONS** - only dedicated database for dynamic positioning incidents. Critical for offshore construction, drilling, subsea operations.

---

### 4.2 National Ballast Information Clearinghouse (NBIC)
**Organization:** Smithsonian Environmental Research Center + USCG
**URL:** https://nbic.si.edu/

#### Database Coverage:
- Ballast water management practices (commercial ships in U.S. waters)
- Ballast water discharge data
- Compliance violations
- Species invasion risk data

#### Enforcement Data:
- USCG Letters of Warning (LOW)
- Notices of Violation (NOV)
- Civil Penalties (CP)
- Deficiencies for non-compliance

#### Technical Details:
- **Format:** Online database, downloadable reports
- **Coverage:** All commercial vessels operating in U.S. waters
- **Update Frequency:** Voyage-based reporting

#### Related Resources:
- **IMO GISIS Ballast Water Module:** International compliance tracking
- **INTERTANKO Ports with Challenging Water Quality Database:** Port-specific BWMS issues
- **EPA Enforcement Cases:** Ballast water violations ($81,474 in recent fines for MSC)

#### Access:
- ✅ Free public access
- ✅ Downloadable data
- ✅ Completion instructions available

#### Complementarity:
**ENVIRONMENTAL COMPLIANCE** - tracks ballast water violations before they become pollution incidents. Preventive intelligence.

---

### 4.3 Maritime Cyber Attack Database (MCAD)
**Organization:** NHL Stenden University of Applied Sciences (Netherlands)
**URL:** https://www.nhlstenden.com/en/maritime-cyber-attack-database

#### Database Details:
- **Launch Date:** 2023 (publicly available)
- **Historical Coverage:** 2001-present
- **Record Count:** 160+ cyber incidents
- **Scope:** Vessels, ports, maritime facilities worldwide

#### Incident Types:
- Location spoofing (GPS manipulation)
- Ransomware attacks
- Insider threats
- System compromises
- Port facility cyber attacks

#### Notable Cases:
- Russian spoofing of NATO ships (Black Sea, 2021)
- U.S. nuclear carrier insider attack (2014)
- Container ship ransomware preventing NY harbor entry (2019)

#### Research Publications:
- 46 incidents analyzed (2010-2020) in academic study
- Insurance claims data (anonymized)
- Two decades of risk factor analysis available

#### Access:
- ✅ Free public access online
- ✅ Research publications available
- Developed by Dr. Stephen McCombie (Professor of Maritime IT Security)

#### Complementarity:
**CYBERSECURITY INCIDENTS** - emerging threat category not captured in traditional maritime casualty databases. Critical for modern maritime security.

---

### 4.4 G+ Offshore Wind Health & Safety Database
**Organization:** G+ Global Offshore Wind Health & Safety Organisation
**URL:** https://www.gplusoffshorewind.com/

#### Database Requirements:
- **Mandatory reporting** for G+ members
- Covers offshore wind farms from development to decommissioning
- Data collected and published by Energy Institute

#### Recent Statistics:
- **2023:** 1,679 incidents worldwide (94% increase from 867 in 2022)
- **UK 2023:** 502 incidents (up from 348 in 2022)
- **Injuries 2023:** 65 lost workday, 70 medical treatment, 33 restricted workday, 31 emergency evacuation
- **Fatalities 2023:** 1 death globally (onshore turbine assembly, France)

#### Incident Categories:
- Vessel operations (jack-ups, barges): 169 incidents
- Service vessel incidents (construction phase): 139 (tripled from 35 in 2022)
- Substation incidents: 79 (doubled from 35 in 2022)
- Turbine-related incidents

#### Alternative Sources:
- **Scotland Against Spin Database:** Wind turbine accidents via press reports (June 2025 update)
- Acknowledged as "tip of the iceberg" - underreporting significant

#### Access:
- ⚠️ **G+ members only** for detailed data
- ✅ Annual reports publicly available
- ✅ Summary statistics published

#### Complementarity:
**OFFSHORE WIND INCIDENTS** - new industrial maritime sector. Vessel collision risks, construction accidents. Complements offshore oil/gas data.

---

### 4.5 SIPRI Vessel and Maritime Incident Database (VMID)
**Organization:** Stockholm International Peace Research Institute
**URL:** https://www.sipri.org/research/conflict-peace-and-security/transport-and-security/vessel-and-maritime-incident-database

#### Database Scope:
- **2,500+ incidents** (1980s-present)
- Focus on **illicit maritime activities:**
  - Destabilizing military equipment transfers
  - Dual-use goods smuggling
  - Narcotics trafficking
  - Untaxed/smuggled commodities (tobacco, oil, timber)
  - Illegal/unreported/undocumented fishing (IUU)
  - Undocumented migrant transport (unsafe vessels)

#### Data Sources:
- Open sources: books, journals, media
- NGO and government reports
- Freedom of information requests

#### Access:
- ✅ Free public database
- ✅ SIPRI publications reference data

#### Complementarity:
**MARITIME SECURITY FOCUS** - different from safety/casualty databases. Tracks illicit activities and smuggling. Limited industrial incident value but relevant for security analysis.

---

### 4.6 Divers Alert Network (DAN) Diving Incident Database
**Organization:** Divers Alert Network
**URL:** https://www.dansa.org/ (South Africa), https://dan.org/ (U.S.)

#### Database Details:
- **Maintained since 1989**
- Covers: Open-circuit scuba, breath-hold, rebreather incidents
- **Annual Diving Reports** published with anonymized data

#### Commercial Diving Coverage:
- **North Sea Fatalities:** 82 diving personnel deaths (1966-2016)
- Likely significant underreporting in earlier years
- ⚠️ **No comprehensive global commercial diving database exists**

#### Major Causes of Commercial Diving Fatalities:
- Differential Pressure (Delta P): Instant entrapment in underwater intakes
- Entanglement/entrapment: Ropes, nets, cables, structures
- Hydrogen sulfide exposure (subsea pipelines)

#### Access:
- ✅ Annual reports publicly available
- ✅ Anonymized incident summaries (Incident Insights)
- ✅ Free case summaries

#### Complementarity:
**SUBSEA OPERATIONS FATALITIES** - fills gap for commercial/industrial diving incidents. ROV operations data not systematically collected.

---

### 4.7 Dangerous Goods Maritime Incidents
**Primary Source:** IMO GISIS Marine Casualties and Incidents (MCI) Module
**Coverage:** 2000-2023

#### U.S. Data:
**PHMSA Incident Database:** https://hazmatonline.phmsa.dot.gov/
- **Maritime subset:** Packaged dangerous goods only
- ⚠️ **Excludes bulk marine hazmat** (reported to USCG)
- LNG incident data since 2011
- Updated nightly

#### European Data:
**EMSA Central Hazmat Database:** Directive 2002/59/EC compliance
- Dangerous and polluting goods notifications
- IMO FAL Form 7 integration

#### Research Findings:
- **LNG Carriers:** 158 known incidents documented
- **LNG Incident Types (1994-present):**
  - LNG leakage: 25% (18 cases)
  - Collisions: 15% (11 cases)
  - Equipment failure: 14% (10 events)
  - Vapor release: 8%
  - Fire/explosion: 8%
- **Notable:** No major cargo loss in LNG maritime transport history

#### Historical Database (Discontinued):
- **MHIDAS (Major Hazard Incident Data Service):** Stopped 2007

#### Complementarity:
**HAZMAT TRANSPORT INCIDENTS** - critical for containerized/packaged dangerous goods. Use IMO GISIS + PHMSA for comprehensive coverage.

---

### 4.8 Port and Terminal Incident Data

#### RightShip Global Port Incident Data
**Source:** RightShip commercial maritime intelligence
**Key Finding:** 50% of maritime incidents occur in ports/terminals (2022 data: 2,400 incidents)

#### OSHA Longshoring Fatal Facts
**URL:** https://www.osha.gov/maritime/longshoring
- **Fatality Risk:** 1 in 1,000 maritime crane operators
- **Leading Causes:** Struck by vehicles (trucks, loaders, forklifts), falls, drowning
- **Cargo Handling:** Improperly loaded forklifts, unstable cargo, falling loads

#### Academic Database:
**ISY PORT Project:** Vessel accidents in Mediterranean and worldwide port areas
- Developed for integrated risk mitigation systems

#### BLS Data:
- **3,700+ marine terminals** in U.S.
- **1,400 intermodal connections**
- CDC/NIOSH tracks injuries via Bureau of Labor Statistics

#### Complementarity:
**PORT OPERATIONS FOCUS** - fills gap between vessel casualties (at-sea) and shore-based industrial accidents. Critical for terminal worker safety.

---

### 4.9 Offshore Construction & Salvage Incidents

#### BSEE Ship-to-Platform Collision Database
**Coverage:** 1996-2015
**Incidents:** 176 collisions with offshore structures
- Platform Supply Vessels (PSVs)
- Anchor handling tugs
- Requires BSEE notification if damage >$25,000

#### IMCA Safety Flashes
**URL:** https://www.imca-int.com/resources/safety/
- Anchor handling incidents
- Close approach events
- Mooring line incidents
- Offshore construction safety matters

#### Access:
- ✅ BSEE data via research request
- ✅ IMCA Safety Flashes public

#### Complementarity:
**OFFSHORE CONSTRUCTION** - specialized vessel operations (AHTS, PSV). Complements DP incident data for offshore work.

---

### 4.10 LNG Carrier Safety Database

#### PHMSA LNG Incident Data
**URL:** https://www.phmsa.dot.gov/pipeline/liquified-natural-gas/lng-data-and-maps
- Data collection since 2011
- Downloadable datasets

#### Research Compilations:
- **158 documented LNG carrier accidents**
- **20+ accidents classified** (1994-present)
- **Incident categories:** Leakage, collision, equipment failure, vapor release, fire/explosion

#### Notable Safety Record:
- ✅ **No major cargo losses** in maritime LNG transport history
- Rare accidental spillage events

#### Major Land-Based Incident:
- Algeria LNG facility explosion (Jan 19, 2004): 27 deaths, 74 injuries

#### Complementarity:
**LNG-SPECIFIC DATA** - specialized cargo with unique risks. Limited incidents but high consequence potential.

---

## Priority Tier 3: Academic & Research Institutions

### 5.1 Woods Hole Oceanographic Institution (WHOI)
**URL:** https://www.whoi.edu/

#### Marine Accident Investigation Work:
- Deep submergence technology for wreck surveys
- **Notable investigations:**
  - M/V Derbyshire (1980 sinking, surveyed 1997)
  - R.M.S. Titanic (1985)
  - German battleship Bismarck (1989)

#### Research Contributions:
- Advanced deep-sea imaging
- Remotely operated vehicles (ROVs)
- Casualty investigation methodology

#### Data Access:
- ⚠️ **No public incident database**
- Research publications available through WHOI Library
- Case studies in academic journals

#### Complementarity:
**DEEP-SEA INVESTIGATION EXPERTISE** - contributes to understanding major sinkings but not a systematic database. Research library value.

---

### 5.2 MIT Sea Grant
**URL:** https://seagrant.mit.edu/

#### Research Areas:
- Marine safety technology
- Coastal engineering
- Maritime systems

#### Library:
- 1,400+ journal reprints, technical reports, brochures, manuals
- Conference proceedings from funded research

#### Data Availability:
- ⚠️ **No dedicated maritime accident database identified**
- Research publications may contain incident case studies
- Project-specific data in technical reports

#### Complementarity:
**RESEARCH PUBLICATIONS** - academic analysis of maritime safety but not a data repository.

---

### 5.3 Other Academic Databases

#### Shipping Accidents Dataset (MDPI):
- **Coverage:** 2019-2024 list of maritime disasters
- **Purpose:** Data-driven accident impact assessment
- Research publication, not ongoing database

#### Maritime Accident Investigation Research:
- **Bibliometric analysis** of marine accidents research
- Published in ScienceDirect (literature review)

#### Ship/Platform Collision Research Database:
- Academic study covering 1996-2015
- 176 documented collisions with offshore structures
- Research dataset, not publicly maintained

#### Complementarity:
**ACADEMIC RESEARCH VALUE** - use for methodology, analysis frameworks, but not primary data sources.

---

## Data Gaps Analysis

### Well-Covered Areas:
✅ **Offshore oil & gas incidents** - BSEE, USCG, EMCIP
✅ **Commercial vessel casualties** - USCG, IMO GISIS, EMSA EMCIP
✅ **Port State Control deficiencies** - Paris MOU, Tokyo MOU
✅ **Occupational injuries** - OSHA, BLS, ILO
✅ **DP vessel incidents** - IMCA database
✅ **Bulk carrier casualties** - INTERCARGO reports
✅ **Cybersecurity incidents** - MCAD database
✅ **Offshore wind** - G+ statistics (limited public access)

### Moderate Coverage:
⚠️ **Dangerous goods incidents** - IMO GISIS, PHMSA (fragmented)
⚠️ **Ballast water violations** - NBIC, USCG enforcement
⚠️ **LNG carriers** - PHMSA, research compilations
⚠️ **Diving incidents** - DAN (recreational focus), limited commercial data
⚠️ **Port/terminal operations** - OSHA, RightShip (not comprehensive)

### Significant Gaps:
❌ **Marine construction accidents** - No dedicated database, scattered across BSEE, USCG
❌ **Subsea ROV incidents** - No systematic tracking identified
❌ **Dredging vessel accidents** - USACE internal only, no public database
❌ **Anchor handling incidents** - Limited to IMCA Safety Flashes
❌ **Tanker incidents** - INTERTANKO database discontinued (use IMO GISIS)
❌ **Ship-to-ship transfer incidents** - No dedicated database
❌ **Autonomous vessel incidents** - Technology too new, no accidents yet
❌ **Maritime worker compensation claims** - Fragmented state/private systems
❌ **Salvage operation accidents** - No systematic collection

### Privacy/Access Barriers:
🔒 **Classification society data** - ABS, DNV, Bureau Veritas (proprietary)
🔒 **P&I Club claims** - Aggregated only, privacy restrictions
🔒 **Flag state registries** - Panama, Liberia, Marshall Islands (limited public access)
🔒 **Shipowner/operator records** - Private, liability concerns

---

## Complementarity with Existing WorldEnergyData Sources

### Current Repository Coverage:
1. **USCG MISLE** - Recreational + commercial vessel casualties (U.S.)
2. **NOAA Oil Spills** - Pollution incidents (U.S.)
3. **NTSB Major Investigations** - Significant casualty investigations (U.S.)
4. **BSEE Offshore Incidents** - Platform accidents, blowouts (U.S. OCS)
5. **NIOSH Commercial Fishing** - Fishing vessel fatalities (U.S.)
6. **Canadian TSB, UK MAIB** - National investigation reports

### New Sources Fill These Gaps:

#### Occupational Safety:
- **OSHA ITA/Fatality Data** → Worker injuries at ports, terminals, shipyards
- **BLS SOII/CFOI** → Industry-wide maritime labor statistics
- **ILO Seafarer Deaths** → International maritime worker fatalities

#### International Coverage:
- **IMO GISIS** → Global vessel casualties (non-U.S.)
- **EMSA EMCIP** → European casualties and incidents (detailed)
- **Paris MOU / Tokyo MOU** → Port state control deficiencies worldwide

#### Specialized Operations:
- **IMCA DP Database** → Dynamic positioning failures (offshore)
- **G+ Offshore Wind** → Wind farm construction/operation incidents
- **MCAD** → Cybersecurity incidents (modern threat)
- **NBIC** → Ballast water violations (environmental compliance)

#### Hazmat & Cargo:
- **PHMSA Hazmat** → Dangerous goods incidents (containerized)
- **IMO GISIS DG Module** → International dangerous goods transport
- **DOE Pipeline Data** → Offshore energy pipeline failures

#### Industry Analysis:
- **DNV Safety Reports** → Commercial fleet trends (aging vessels, machinery)
- **Lloyd's Casualty Returns** → Historical benchmark data (1890-2000+)
- **INTERCARGO Reports** → Bulk carrier specialist analysis
- **IG P&I Pooling Stats** → High-value casualty financial impact

---

## Import Feasibility Assessment

### High Feasibility (Bulk Download, Structured Data):
🟢 **OSHA Data Catalog** - CSV/Excel, data dictionaries
🟢 **USCG Marine Casualty** - Delimited text, MS Access
🟢 **BSEE Incidents** - Excel files
🟢 **DOE Offshore Pipeline** - OSTI dataset (CSV)
🟢 **PHMSA Hazmat** - Searchable DB, Excel export
🟢 **Lloyd's Casualty Returns** - Historical PDFs (structured)
🟢 **Paris MOU / Tokyo MOU** - Inspection search, downloadable reports

### Medium Feasibility (Reports, Aggregated Data):
🟡 **EMSA Annual Reports** - PDFs with statistics (tables extractable)
🟡 **ILO Seafarer Deaths** - Annual reports (structured tables)
🟡 **DNV Safety Reports** - PDF whitepapers (charts/tables)
🟡 **INTERCARGO Reports** - Members only, but summaries public
🟡 **IMCA DP Incidents** - Individual PDFs (requires scraping)
🟡 **G+ Offshore Wind** - Annual statistics (limited access)

### Low Feasibility (Restricted, Proprietary, or No Bulk Access):
🔴 **IMO GISIS** - Registration required, export limits
🔴 **EMCIP Database** - Direct access restricted (use annual reports)
🔴 **ABS/Bureau Veritas** - Proprietary, not public
🔴 **P&I Clubs** - Aggregated only, privacy restrictions
🔴 **MCAD** - Online database (may require scraping)

### Not Applicable (No Database/Discontinued):
⚫ **INTERTANKO** - Database discontinued 2023
⚫ **Woods Hole/MIT** - No systematic databases
⚫ **State agencies** - Recreational focus

---

## Recommendations for Data Acquisition

### Priority 1: Immediate High-Value Downloads
1. **OSHA Injury Tracking Application (ITA)** + Fatality Data
   - Filter for maritime NAICS codes
   - Provides worker-level incidents missing from vessel databases

2. **DOE Offshore Pipeline Incidents Dataset**
   - Direct download from OSTI
   - 900+ incidents (1986-2021) not in other sources

3. **PHMSA Hazardous Materials Database**
   - Maritime subset for dangerous goods
   - LNG incident data

4. **Lloyd's Register Casualty Returns**
   - Historical baseline (1890-2000)
   - Public domain PDFs

### Priority 2: Enhanced Coverage
5. **EMSA Annual Overview Reports** (2014-2024)
   - Parse tables from PDFs
   - European casualty trends

6. **DNV Maritime Safety Reports**
   - Extract statistics from whitepapers
   - Aging fleet analysis

7. **Paris MOU / Tokyo MOU Inspection Data**
   - Query inspection search tools
   - PSC deficiency trends

### Priority 3: Specialized Databases
8. **IMCA DP Incident Database**
   - Scrape individual incident PDFs
   - Critical for offshore operations

9. **NBIC Ballast Water Data**
   - Download compliance reports
   - Environmental violations

10. **G+ Offshore Wind Statistics**
    - Extract from annual reports
    - Emerging sector data

### Priority 4: Registration-Required Sources
11. **IMO GISIS** (if access granted)
    - Apply for academic/research access
    - Global casualty database

12. **ILO ILOSTAT**
    - Download seafarer death statistics
    - Maritime labor data

### Low Priority (Use Reports Only):
- INTERCARGO summaries (full reports require membership)
- IG P&I annual summaries (aggregated data only)
- Academic publications (reference materials)

### Not Recommended:
- Classification societies (proprietary)
- INTERTANKO (discontinued)
- State agencies (recreational focus)
- MCAD (manual scraping required)

---

## Data Integration Strategy

### Database Architecture Recommendations:

#### Core Tables:
1. **industrial_vessel_casualties** - Commercial vessel incidents
2. **offshore_platform_incidents** - Oil/gas platform accidents
3. **port_terminal_incidents** - Cargo handling, crane accidents
4. **maritime_worker_injuries** - Occupational safety (OSHA, ILO)
5. **hazmat_incidents** - Dangerous goods transport
6. **psc_deficiencies** - Port state control findings
7. **specialized_operations** - DP vessels, offshore wind, diving, etc.

#### Source Mapping:
- **USCG MISLE** → industrial_vessel_casualties (U.S. commercial subset)
- **BSEE** → offshore_platform_incidents
- **OSHA ITA** → maritime_worker_injuries
- **PHMSA** → hazmat_incidents
- **DOE Pipeline** → offshore_platform_incidents (pipeline subset)
- **Paris/Tokyo MOU** → psc_deficiencies
- **IMCA** → specialized_operations (DP subset)

#### Cross-Reference Fields:
- Vessel IMO number (link to multiple databases)
- Incident date/time/location (geographic correlation)
- Casualty type (standardized taxonomy)
- Vessel type (map across classification schemes)
- Incident severity (harmonize scales)

---

## Next Steps for WorldEnergyData Repository

1. **Download Priority 1 datasets** (OSHA, DOE, PHMSA, Lloyd's)
2. **Parse EMSA/DNV reports** for European statistics
3. **Query Paris/Tokyo MOU** inspection databases
4. **Apply for IMO GISIS access** (academic research status)
5. **Document data schema** for industrial maritime incidents
6. **Create ETL pipelines** for recurring data updates
7. **Validate against existing USCG/BSEE data** for U.S. overlap
8. **Publish data inventory** with source attribution

---

## Conclusion

This research identified **50+ data sources** for industrial maritime incidents, with **15 high-priority sources** offering bulk downloads or structured data suitable for the WorldEnergyData repository. Key findings:

- **U.S. Federal sources** (OSHA, DOE, PHMSA) provide excellent occupational safety and offshore pipeline data not currently in repository
- **International organizations** (IMO GISIS, EMSA, ILO) offer global coverage complementing U.S.-focused USCG data
- **Specialized databases** (IMCA DP, G+ Offshore Wind, MCAD) fill niche gaps in offshore operations and cybersecurity
- **Significant data gaps remain** in marine construction, subsea ROV operations, and salvage incidents
- **Classification society data** is largely proprietary and unavailable for public research

The recommended approach is to prioritize freely downloadable U.S. federal datasets, supplement with international organization reports, and pursue registration for IMO GISIS access to achieve comprehensive global industrial maritime incident coverage.

---

**Research conducted by:** Claude (Anthropic)
**Date:** October 6, 2025
**Repository:** github.com/worldenergydata
**Contact:** [Repository maintainer contact]
