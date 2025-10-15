# Canadian Transportation Safety Board (TSB) Marine Data

## Phase 2 Documentation Update

**Original Download:** August 2024
**Phase 2 Verification:** October 7, 2025
**Status:** ✅ VERIFIED AND DOCUMENTED

## Overview

The Transportation Safety Board of Canada (TSB) is an independent agency that investigates marine, pipeline, railway and aviation transportation occurrences. This dataset contains marine transportation occurrences from 1995 to present.

**Data Source:** https://www.tsb.gc.ca/eng/stats/marine/

## Download Information

**Original Download Date:** August 19, 2024
**Format:** CSV (6 relational tables)
**Update Frequency:** Monthly (on or after the 15th of each month)
**Date Range:** 1995 to the last day of the month before release

## Files Description

| File | Size | Records | Description |
|------|------|---------|-------------|
| `occurrence.csv` | 90 MB | 86,289 | Main occurrence/event records |
| `vessel.csv` | 72 MB | 72,071 | Vessel details for each occurrence |
| `navigation_equipment.csv` | 26 MB | 307,245 | Navigation equipment inventory |
| `lifesaving_equipment.csv` | 1.4 MB | 73,383 | Lifesaving appliances equipment |
| `recording_equipment.csv` | 4.0 MB | 75,868 | Recording equipment inventory |
| `injuries.csv` | 1.3 MB | 20,292 | Injury and fatality records |

**Total:** ~194 MB, 635,148 rows across 6 tables

## Schema Overview

### occurrence.csv

**Primary Key:** `OccID`

**Alternative Keys:** `OccNo` (occurrence number)

**Core Fields:**
- `OccID` - Unique occurrence identifier (integer)
- `OccNo` - Occurrence report number (string)
- `OccDate` - Date of occurrence (YYYY-MM-DD)
- `OccTime` - Time of occurrence (HH:MM:SS)
- `TimeZoneID` / `TimeZoneDisplayEng` / `TimeZoneDisplayFre` - Time zone information
- `Summary` - Narrative description of occurrence

**Classification:**
- `OccClassID` / `OccClassDisplayEng` / `OccClassDisplayFre` - TSB classification system
- `OccurrenceTypeID` / `OccTypeDisplayEng` / `OccTypeDisplayFre` - Occurrence type
- `AccIncTypeID` / `AccIncTypeDisplayEng` / `AccIncTypeDisplayFre` - Accident/Incident type
- `ImoClassLevelID` / `ImoClasslevelDisplayEng` / `ImoClassLevelDisplayFre` - IMO severity classification

**Location:**
- `ProvinceID` / `ProvinceDisplayEng` / `ProvinceDisplayFre` - Canadian province/territory
- `Latitude` / `LatEnum` / `LatEnum_Bearing_DisplayEng` - Latitude coordinates
- `Longitude` / `LongEnum` / `LongEnum_Bearing_DisplayEng` - Longitude coordinates
- `PositionEstimatedIND` - Flag if position is estimated
- `NearestLocationDistance_Nm` - Distance to nearest location (nautical miles)
- `NearestLocationDescription` - Description of nearest landmark
- `BearingID` / `BearingDisplay` - Bearing to nearest location
- `Position` - Position code
- `PositionInText` - Position in text format
- `PositionTypeEnum` - Type of position reference

**Area Type:**
- `AreaTypeID` / `AreaTypeDisplayEng` / `AreaTypeDisplayFre` - Waterway area type
- `RoutingID` / `RoutingDisplayEng` / `RoutingDisplayFre` - Traffic routing system
- `WithInPilotBoardingAreaEnum` - Flag if within pilot boarding area

**Indicators:**
- `InjuriesIND` - Injuries involved (Yes/No)
- `SearchAndRescueIND` - SAR deployment (Yes/No)
- `DamageIND` - Damage occurred (Yes/No)
- `SafetyCommIssuedIND` - Safety communication issued (Yes/No)
- `PollutionIND` - Pollution occurred (Yes/No)
- `DeployedIND` - TSB deployed to site (Yes/No)

**Environmental Conditions:**
- `EnvironmentalConditionID` - Environmental condition reference
- `VisibilityDistance_Nm` - Visibility in nautical miles
- `LightConditionID` / `LightConditionDisplayEng` - Light conditions
- `WeatherConditionID` / `WeatherConditionDisplayEng` - Weather conditions
- `WindDirectionID` / `WindDirection` - Wind direction
- `WindSpeedTypeID` / `WindSpeedTypeDisplayEng` - Wind speed type
- `BeaufortScaleID` / `BeaufortScaleDisplayEng` - Beaufort wind scale
- `WindSpeed_Knots` - Wind speed in knots
- `SeaStateID` / `SeaStateDisplayEng` - Sea state
- `SwellDirectionID` / `SwellDirection` - Swell direction
- `SwellHeight_Meters` - Swell height
- `AirTemp_Celsius` - Air temperature
- `SeatTemp_Celsius` - Sea temperature (note typo in field name)

**Ice Conditions:**
- `IceCoverage_ScaleOutOf1to10` - Ice coverage scale (1-10)
- `IcebergEnum` - Iceberg presence
- `BergyBitsEnum` - Bergy bits presence
- `GrowlersEnum` - Growlers presence
- `UnderIceRegimeEnum` - Under ice regime
- `VesselIcingPresentEnum` - Vessel icing present
- `VesselIcingQualificationID` - Vessel icing qualification

**Observed By:**
- `ObservedByID` / `ObservedByDisplayEng` - Who observed conditions

**Investigation Details:**
- `FatigueInvestEnum` - Fatigue investigated
- `FatigueContFactorEnum` - Fatigue contributing factor
- `WeatherFactorEnum` - Weather contributing factor
- `ReleasedDate` - Date released
- `OccClosedDate` - Date occurrence closed
- `RegionResponsibilityID` / `RegionResponsibilityDisplayEng` - TSB region responsible
- `RegionOfOccurrenceID` / `RegionOfOccurrenceDisplayEng` - Region where occurred

**Reporting:**
- `ReportSourceID` / `ReportSourceeDisplayEng` / `ReportSourceDisplayFre` - Report source
- `NotificationDetailID` - Notification details
- `ReportedDate` - Date reported
- `ReportedByID` / `ReportedByDisplayEng` - Who reported
- `SubstantiallyInsterestedStateIND` - Substantially interested state indicator
- `OtherStateInvestigatingID` / `OtherStateInvestigatingDisplayEng` - Other investigating state
- `SubstantiallyInterestedStateID` / `SubstantiallyInterestedStateDisplayEng` - Substantially interested state

**Casualty Summaries:**
- `TotalDeaths` - Total fatalities
- `TotalMinorInjuries` - Total minor injuries
- `TotalSeriousInjuries` - Total serious injuries
- `TotalMissingIndividuals` - Total missing persons
- `TotalPeopleInTheWater` - Total people in water

**Metadata:**
- `EntryDate` - Database entry date
- `MajorChangesIncludedInDaily` - Major changes flag
- `IncludedInDailyEnum` - Included in daily report

### vessel.csv

**Foreign Key:** Links to `occurrence.csv` via `OccID`

**Key Fields:**
- Vessel identification (name, official number, IMO number)
- Vessel type and classification
- Vessel specifications (length, tonnage, gross tonnage)
- Build year and builder
- Flag state and registration
- Ownership information
- Vessel activity at time of occurrence
- Damage assessment

### navigation_equipment.csv

**Foreign Key:** Links to `occurrence.csv` and `vessel.csv`

**Key Fields:**
- Equipment type and classification
- Equipment manufacturer and model
- Installation date
- Operational status
- Equipment involvement in occurrence

### lifesaving_equipment.csv

**Foreign Key:** Links to `occurrence.csv` and `vessel.csv`

**Key Fields:**
- Lifesaving appliance type
- Capacity and specifications
- Deployment details
- Serviceability status

### recording_equipment.csv

**Foreign Key:** Links to `occurrence.csv` and `vessel.csv`

**Key Fields:**
- Voyage Data Recorder (VDR) details
- Audio recording equipment
- Data recovery status
- Equipment maintenance records

### injuries.csv

**Foreign Key:** Links to `occurrence.csv`

**Key Fields:**
- Person type (crew, passenger, other)
- Injury severity (fatal, serious, minor)
- Injury type and cause
- Age and gender
- Medical treatment
- Person activity at time of injury

## Data Quality

**Strengths:**
- Comprehensive 30-year historical coverage
- Bilingual field labels (English/French)
- Detailed environmental conditions including ice data
- Six normalized relational tables
- Monthly updates ensure current data
- Extensive equipment inventories
- Links to IMO classification standards

**Considerations:**
- Field names use bilingual approach (Eng/Fre suffixes)
- UTF-8 BOM encoding (starts with `\ufeff`)
- Some field naming inconsistencies (e.g., "SeatTemp" instead of "SeaTemp")
- Large file sizes require proper parsing
- Complex relational structure

## Import Priority

**Priority Level:** HIGH

**Rationale:**
- Largest single-country dataset (86,289 occurrences)
- Excellent historical coverage (1995-present)
- Comprehensive structured data
- Regular monthly updates
- Strong data quality
- Detailed equipment inventories unique to this dataset

## Field Mapping Notes

### To Unified Marine Safety Schema

**Occurrence Mapping:**
- `OccID` → `external_id` (with 'TSB-' prefix)
- `OccNo` → `report_number`
- `OccDate` + `OccTime` → `incident_datetime`
- `OccClassDisplayEng` + `OccTypeDisplayEng` + `AccIncTypeDisplayEng` → `incident_type`
- `ImoClasslevelDisplayEng` → `severity_level`
- `Summary` → `narrative`

**Location Mapping:**
- `Latitude` / `Longitude` → `latitude`, `longitude`
- `ProvinceDisplayEng` → `state_province`
- `NearestLocationDescription` → `location_description`
- `AreaTypeDisplayEng` → `waterway_type`

**Environmental Mapping:**
- `LightConditionDisplayEng` → `light_conditions`
- `WeatherConditionDisplayEng` → `weather_conditions`
- `VisibilityDistance_Nm` → `visibility`
- `WindSpeed_Knots` + `BeaufortScaleDisplayEng` → `wind_speed`
- `SeaStateDisplayEng` → `sea_state`
- `AirTemp_Celsius` → `air_temperature`

**Casualties Mapping:**
- `TotalDeaths` → `fatalities`
- `TotalSeriousInjuries` → `serious_injuries`
- `TotalMinorInjuries` → `minor_injuries`
- `TotalMissingIndividuals` → `missing_persons`
- Join `injuries.csv` for detailed person-level data

**Vessels Mapping:**
- Join `vessel.csv` on `OccID`
- Extract primary vessel details
- Store additional vessels as related records

**Equipment Mapping:**
- Join equipment tables for detailed inventories
- Store in separate equipment tables

## Data Relationships

```
occurrence (1) ←→ (many) vessel
occurrence (1) ←→ (many) navigation_equipment
occurrence (1) ←→ (many) lifesaving_equipment
occurrence (1) ←→ (many) recording_equipment
occurrence (1) ←→ (many) injuries

vessel (1) ←→ (many) navigation_equipment
vessel (1) ←→ (many) lifesaving_equipment
vessel (1) ←→ (many) recording_equipment
```

## Sample Queries

### Count occurrences by year:
```sql
SELECT YEAR(OccDate) as Year, COUNT(*) as Occurrences
FROM occurrence
GROUP BY YEAR(OccDate)
ORDER BY Year;
```

### Get fatal accidents with environmental conditions:
```sql
SELECT o.OccNo, o.OccDate, o.Summary, o.TotalDeaths,
       o.WeatherConditionDisplayEng, o.SeaStateDisplayEng,
       o.BeaufortScaleDisplayEng
FROM occurrence o
WHERE o.TotalDeaths > 0
ORDER BY o.TotalDeaths DESC;
```

### Vessel type involvement:
```sql
SELECT v.VesselTypeDisplayEng, COUNT(*) as Incidents
FROM occurrence o
JOIN vessel v ON o.OccID = v.OccID
GROUP BY v.VesselTypeDisplayEng
ORDER BY Incidents DESC;
```

## Additional Resources

- **TSB Marine Statistics:** https://www.tsb.gc.ca/eng/stats/marine/index.html
- **TSB Investigation Reports:** https://www.tsb.gc.ca/eng/enquetes-investigations/marine/index.html
- **Data Dictionary:** Available at data download page
- **Annual Reports:** https://www.tsb.gc.ca/eng/rapports-reports/index.html

## Citation

When using this data, please cite:

> Transportation Safety Board of Canada (2024). Marine Occurrence Database 1995-Present. Retrieved from https://www.tsb.gc.ca/eng/stats/marine/

## Data License

This data is made available under the Open Government Licence - Canada. See: https://open.canada.ca/en/open-government-licence-canada

## Contact

For questions about this data:
- TSB Information: info@tsb.gc.ca
- Data Inquiries: communications@tsb.gc.ca

---

*README Last Updated: October 7, 2025*
*Data Version: 1995-August 2024 (monthly updates)*
*Phase 2 Documentation*
