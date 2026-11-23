# PHMSA Pipeline Safety Data

**Status:** ⚠️ REQUIRES INTERACTIVE DATA PORTAL ACCESS
**Provider:** Pipeline and Hazardous Materials Safety Administration (PHMSA), U.S. Department of Transportation
**Coverage:** 1970-present (varies by dataset)
**Data Types:** Incidents, Annual Reports, Performance Metrics

---

## Overview

PHMSA collects and maintains comprehensive pipeline safety data including:
- **Gas Distribution** pipelines
- **Gas Gathering** systems
- **Gas Transmission** pipelines
- **Hazardous Liquids** pipelines
- **Liquefied Natural Gas (LNG)** facilities
- **Underground Natural Gas Storage (UNGS)** facilities

---

## Data Access Methods

### ⚠️ Website Access Issues (2025-10-08)

The PHMSA website (www.phmsa.dot.gov) is experiencing connectivity issues with automated downloads. Direct file downloads are timing out.

**Alternative Access Methods:**

1. **PHMSA Data Portal (Interactive)**
   - URL: https://portal.phmsa.dot.gov/analytics
   - Requires interactive browser session
   - Custom query builder available

2. **Main Data Pages:**
   - Annual Reports: https://www.phmsa.dot.gov/data-and-statistics/pipeline/gas-distribution-gas-gathering-gas-transmission-hazardous-liquids
   - Incident Data: https://www.phmsa.dot.gov/data-and-statistics/pipeline/distribution-transmission-gathering-lng-and-liquid-accident-and-incident-data
   - Source Data: https://www.phmsa.dot.gov/data-and-statistics/pipeline/source-data

3. **National Pipeline Mapping System (NPMS)**
   - URL: https://www.npms.phmsa.dot.gov
   - Geographic pipeline data
   - Interactive mapping tools

---

## Available Datasets

### 1. Incident/Accident Data

**Coverage:** 1970-present
**Update Frequency:** Monthly
**File Format:** ZIP files containing CSV data + data dictionary

#### Gas Distribution Incidents
- Reportable incidents on gas distribution pipelines
- Includes: leaks, explosions, fires, fatalities, injuries
- Fields: Operator, location, cause, consequences, equipment involved

#### Gas Transmission & Gathering Incidents
- Incidents on transmission and gathering systems
- Interstate and intrastate pipelines
- Significant incidents (≥$50,000 or serious injuries)

#### Hazardous Liquids Incidents
- Crude oil, petroleum products, chemicals
- Spill volumes, environmental impacts
- Response and cleanup details

#### LNG Facility Incidents
- Liquefied natural gas facility events
- Import/export terminals, peak shaving plants

---

### 2. Annual Report Data

**Coverage:** Varies by system type (typically 2010-present for detailed data)
**Update Frequency:** Annually (reports submitted by March 15)
**File Format:** ZIP files with multiple CSV tables

#### Gas Distribution Annual Reports
- **49 CFR Part 191** reporting
- Mileage by pipe material, diameter
- Leaks detected and repaired
- Odorization, leak survey programs
- Service lines, meters

#### Gas Transmission Annual Reports
- **49 CFR Part 191** reporting
- Pipeline mileage, materials, operating pressures
- Valves, corrosion control
- Integrity management programs
- Inline inspection tools

#### Hazardous Liquids Annual Reports
- **49 CFR Part 195** reporting
- Pipeline systems by commodity type
- Breakout tanks, pumping stations
- Leak detection systems
- SCADA and control systems

---

### 3. Performance Metrics

- Miles of pipeline by system type
- Incident rates (per mile, per year)
- Serious incidents trend data
- Regulatory compliance metrics
- Enforcement actions

---

## Data Schema Overview

### Incident Reports

**Common Fields:**
- **Report Number:** Unique identifier
- **Operator ID & Name**
- **Incident Date/Time**
- **Location:** City, county, state, coordinates
- **Commodity:** Gas, crude oil, HVL, CO2, etc.
- **Cause:** Primary and contributing factors
- **Consequences:**
  - Fatalities (public, employees, contractors)
  - Injuries requiring hospitalization
  - Property damage ($)
  - Volume released/spilled
  - Environmental impacts
- **Equipment Involved:** Pipe, valve, fitting, etc.
- **System Type:** Transmission, distribution, gathering
- **Pipe Specifications:** Material, diameter, age, pressure
- **Investigation Status:** Open, closed, findings

### Annual Reports

**System Attributes:**
- Total pipeline miles
- Miles by material (steel, plastic, cast iron)
- Miles by diameter class
- Operating pressures (MAOP)
- Installation dates/age distribution
- Geographic distribution
- Regulatory classification

**Safety Programs:**
- Leak survey frequency and methods
- Corrosion control programs
- Integrity management plans
- Emergency response procedures
- Public awareness programs

---

## Download Instructions

### Method 1: Interactive Portal (Recommended)

1. **Access PHMSA Data Portal:**
   ```
   https://portal.phmsa.dot.gov/analytics
   ```

2. **Navigate to Datasets:**
   - Click "Public" folder
   - Select data category:
     - "Pipeline Incident 20 Year Trend" (incident data)
     - "Annual Report" (system data)
     - "All Reported Incidents" (comprehensive)

3. **Run Query:**
   - Select time range
   - Choose filters (state, operator, cause, etc.)
   - Click "Export" → Excel or CSV

4. **Save Files:**
   ```
   phmsa_pipelines/
   ├── incidents/
   │   ├── gas_distribution_YYYY-YYYY.csv
   │   ├── gas_transmission_YYYY-YYYY.csv
   │   └── hazardous_liquids_YYYY-YYYY.csv
   └── annual_reports/
       ├── gas_distribution_annual_YYYY.csv
       ├── gas_transmission_annual_YYYY.csv
       └── hazardous_liquids_annual_YYYY.csv
   ```

### Method 2: Direct Download Page

1. **Visit Source Data Page:**
   ```
   https://www.phmsa.dot.gov/data-and-statistics/pipeline/source-data
   ```

2. **Download ZIP Files:**
   - Incident data (updated monthly)
   - Annual report data (updated annually after March 15)
   - Each ZIP contains:
     - Data file (CSV)
     - Data dictionary (field definitions)

3. **Extract and Organize:**
   - Unzip files
   - Rename for clarity
   - Document version/date

---

## Known Data Quality Issues

1. **Operator Reporting Variability:**
   - Not all operators use consistent terminology
   - Cause codes may be interpreted differently
   - Investigation findings evolve over time

2. **Historical Data Limitations:**
   - Pre-2010 data less detailed
   - Reporting requirements changed over time
   - Some fields added in recent years

3. **Geographic Precision:**
   - Older incidents may have approximate locations
   - Coordinates not always provided
   - Address geocoding quality varies

4. **Economic Data:**
   - Property damage estimates are operator-reported
   - Not adjusted for inflation
   - May be updated during investigation

5. **Environmental Impact:**
   - Spill volume estimates can be revised
   - Cleanup costs not always final
   - Long-term impacts not captured

---

## Regulatory Context

### Key Regulations

- **49 CFR Part 191:** Gas pipeline incident and annual reporting
- **49 CFR Part 195:** Hazardous liquid pipeline reporting
- **49 CFR Part 192:** Gas pipeline safety standards
- **49 CFR Part 199:** Drug and alcohol testing

### Reporting Requirements

**Incidents must be reported within:**
- Telephonic: Immediately for serious incidents
- Written: 30 days for detailed report
- Supplemental: As investigation concludes

**Annual reports due:**
- March 15 of following year
- Covers calendar year data
- Verified by operator management

---

## Related Datasets

### Complementary Data Sources

1. **USCG Marine Casualties** (offshore platforms connected to pipelines)
2. **EPA CERCLA** (environmental cleanup sites)
3. **OSHA** (worker safety violations)
4. **State Pipeline Agencies** (intrastate pipeline data)
5. **NTSB** (major accident investigations)

### Academic & Research

- **Pipeline Safety Trust** - Advocacy and analysis
- **Interstate Natural Gas Association (INGAA)** - Industry data
- **American Petroleum Institute (API)** - Technical standards

---

## Analysis Opportunities

### High-Value Research Questions

1. **Temporal Trends:**
   - Incident rates over time
   - Impact of regulatory changes
   - Seasonal patterns
   - Regional variations

2. **Cause Analysis:**
   - Leading causes by system type
   - Equipment failure patterns
   - Human factors
   - External force damage (3rd party, natural)

3. **Risk Modeling:**
   - High consequence areas
   - Age-related failure rates
   - Material performance (steel vs. plastic)
   - Pressure class correlations

4. **Economic Impact:**
   - Total property damage trends
   - Cost per incident by type
   - Regional economic exposure
   - Insurance implications

5. **Safety Effectiveness:**
   - Integrity management program impacts
   - Inline inspection effectiveness
   - Leak detection system performance
   - Emergency response improvements

---

## Citation

```
Pipeline and Hazardous Materials Safety Administration. (2024).
Pipeline Incident and Annual Report Data [Data files].
U.S. Department of Transportation.
Retrieved October 8, 2025, from https://www.phmsa.dot.gov/data-and-statistics
```

---

## Contact

**PHMSA Information Resources:**
- **General:** information@phmsa.dot.gov
- **Data Requests:** phmsa.dataaccess@dot.gov
- **Phone:** 202-366-4595
- **Portal Support:** https://portal.phmsa.dot.gov/support

**Regional Offices:**
- Eastern: 609-989-2171
- Central: 816-329-3800
- Southern: 713-272-2859
- Western: 720-963-3160

---

## Status Updates

### 2025-10-08 - ⚠️ AUTOMATED DOWNLOAD FAILED

**Issue:** PHMSA website connectivity problems
- Web scraping attempts timed out
- Direct file downloads failed (HTTP/2 stream errors)
- Interactive portal requires browser session

**Recommended Actions:**
1. Use interactive portal with manual download
2. Request bulk data from phmsa.dataaccess@dot.gov
3. Check data.gov for PHMSA dataset mirrors
4. Retry automated download in 24-48 hours

**Priority:** HIGH - Pipeline safety data critical for marine safety correlation analysis

---

**README Created:** 2025-10-08
**Status:** Awaiting manual download or API access resolution
**Data Steward:** Research Agent
