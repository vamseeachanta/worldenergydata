# BSEE Data Dictionary

> Comprehensive field definitions for BSEE datasets
> Version: 1.0.0
> Last Updated: 2025-08-21

## Table of Contents
1. [Production Data](#production-data)
2. [Wells Data](#wells-data)
3. [Completions Data](#completions-data)
4. [Operations Data](#operations-data)
5. [Geology Data](#geology-data)
6. [Infrastructure Data](#infrastructure-data)

---

## Production Data

### File: `current/production/production.csv`

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| WELL_API | String | Unique well identifier (API number) | "608174000100" |
| PRODUCTION_DATE | Date | Month and year of production | "2024-01-01" |
| OIL_BBL | Float | Oil production in barrels | 15234.5 |
| GAS_MCF | Float | Gas production in thousand cubic feet | 8921.3 |
| WATER_BBL | Float | Water production in barrels | 3421.0 |
| DAYS_ON | Integer | Days well was producing | 28 |
| FIELD_NAME | String | Field or area name | "Mars" |
| OPERATOR | String | Operating company name | "Shell Offshore Inc" |

---

## Wells Data

### File: `current/wells/well_data.csv`

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| API_WELL_NUMBER | String | API well number (unique ID) | "608174000100" |
| WELL_NAME | String | Common well name | "A-12" |
| WELL_NAME_SUFFIX | String | Additional well identifier | "ST01" |
| OPERATOR_NAME | String | Current operator | "BP Exploration" |
| FIELD_NAME | String | Field name | "Thunder Horse" |
| WATER_DEPTH | Float | Water depth in feet | 6050.0 |
| TOTAL_DEPTH | Float | Total measured depth in feet | 28500.0 |
| TVD | Float | True vertical depth in feet | 25800.0 |
| SPUD_DATE | Date | Date drilling began | "2023-03-15" |
| COMPLETION_DATE | Date | Date well completed | "2023-08-20" |
| WELL_STATUS | String | Current status | "ACTIVE", "P&A", "SHUT-IN" |
| WELL_TYPE | String | Type of well | "OIL", "GAS", "INJECTION" |
| BOTTOM_LATITUDE | Float | Bottom hole latitude | 28.1234 |
| BOTTOM_LONGITUDE | Float | Bottom hole longitude | -89.5678 |
| SURFACE_LATITUDE | Float | Surface location latitude | 28.1111 |
| SURFACE_LONGITUDE | Float | Surface location longitude | -89.5555 |
| BLOCK_NUMBER | String | Lease block number | "MC 778" |
| AREA_NAME | String | Area designation | "Mississippi Canyon" |
| DISTRICT | String | BSEE district | "New Orleans" |

### File: `current/wells/well_directional_surveys.csv`

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| API_WELL_NUMBER | String | API well number | "608174000100" |
| MEASURED_DEPTH | Float | Measured depth in feet | 15000.0 |
| INCLINATION | Float | Hole angle in degrees | 35.5 |
| AZIMUTH | Float | Direction in degrees | 245.3 |
| TVD | Float | True vertical depth | 14850.0 |
| NORTHING | Float | North coordinate | 1234.5 |
| EASTING | Float | East coordinate | 5678.9 |
| DOG_LEG_SEVERITY | Float | DLS in degrees/100ft | 2.3 |
| SURVEY_DATE | Date | Date of survey | "2023-05-10" |

### File: `current/wells/well_tubulars.csv`

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| API_WELL_NUMBER | String | API well number | "608174000100" |
| TUBULAR_TYPE | String | Type of tubular | "CASING", "TUBING" |
| SIZE_OD | Float | Outside diameter in inches | 9.625 |
| WEIGHT | Float | Weight in lbs/ft | 47.0 |
| GRADE | String | Steel grade | "P-110" |
| TOP_DEPTH | Float | Top of tubular in feet | 0.0 |
| BOTTOM_DEPTH | Float | Bottom depth in feet | 15000.0 |
| CEMENT_TOP | Float | Top of cement in feet | 12000.0 |

---

## Completions Data

### File: `current/completions/completion_summary.csv`

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| API_WELL_NUMBER | String | API well number | "608174000100" |
| COMPLETION_DATE | Date | Date of completion | "2023-08-20" |
| COMPLETION_TYPE | String | Type of completion | "GRAVEL PACK", "FRAC PACK" |
| COMPLETION_NUMBER | Integer | Completion sequence | 1 |
| TOP_MD | Float | Top measured depth | 24000.0 |
| BOTTOM_MD | Float | Bottom measured depth | 24500.0 |
| NET_PAY | Float | Net pay thickness in feet | 450.0 |
| SAND_CONTROL | String | Sand control method | "GRAVEL PACK" |

### File: `current/completions/completion_perforations.csv`

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| API_WELL_NUMBER | String | API well number | "608174000100" |
| PERFORATION_DATE | Date | Date perforated | "2023-08-15" |
| TOP_DEPTH | Float | Top perforation depth | 24100.0 |
| BOTTOM_DEPTH | Float | Bottom perforation depth | 24400.0 |
| SHOTS_PER_FOOT | Integer | Shot density | 12 |
| SHOT_SIZE | Float | Charge size in inches | 0.75 |
| PHASING | Integer | Degrees of phasing | 60 |

### File: `current/completions/completion_properties.csv`

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| API_WELL_NUMBER | String | API well number | "608174000100" |
| POROSITY | Float | Average porosity (%) | 28.5 |
| PERMEABILITY | Float | Permeability in mD | 850.0 |
| WATER_SATURATION | Float | Water saturation (%) | 22.0 |
| ARTIFICIAL_LIFT | String | Lift method | "ESP", "GAS LIFT" |
| PACKER_DEPTH | Float | Packer setting depth | 23800.0 |

---

## Operations Data

### File: `current/operations/well_activity_summary.csv`

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| API_WELL_NUMBER | String | API well number | "608174000100" |
| ACTIVITY_DATE | Date | Date of activity | "2023-07-15" |
| ACTIVITY_TYPE | String | Type of operation | "DRILLING", "WORKOVER" |
| ACTIVITY_CODE | String | Specific activity code | "DRL", "WO", "P&A" |
| RIG_NAME | String | Rig performing work | "Deepwater Horizon" |
| DURATION_DAYS | Integer | Duration in days | 45 |
| TOTAL_COST | Float | Cost in USD | 15000000.0 |
| REMARKS | String | Activity notes | "Sidetrack from 15000'" |

### File: `current/operations/well_activity_bop_tests.csv`

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| API_WELL_NUMBER | String | API well number | "608174000100" |
| TEST_DATE | Date | Date of BOP test | "2023-06-01" |
| TEST_TYPE | String | Type of test | "FUNCTION", "PRESSURE" |
| TEST_PRESSURE | Float | Test pressure in PSI | 15000.0 |
| DURATION_MINUTES | Integer | Test duration | 30 |
| RESULT | String | Test result | "PASS", "FAIL" |
| RAM_TYPE | String | Ram configuration | "BLIND SHEAR" |

### File: `current/operations/ST_BP_and_tree_height.csv`

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| API_WELL_NUMBER | String | API well number | "608174000100" |
| TREE_HEIGHT | Float | Subsea tree height in feet | 25.0 |
| BOP_STACK_HEIGHT | Float | BOP stack height in feet | 55.0 |
| TREE_MANUFACTURER | String | Tree manufacturer | "FMC Technologies" |
| TREE_MODEL | String | Tree model number | "Enhanced Vertical" |
| INSTALLATION_DATE | Date | Installation date | "2023-04-01" |

---

## Geology Data

### File: `current/geology/geology_markers.csv`

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| API_WELL_NUMBER | String | API well number | "608174000100" |
| FORMATION_NAME | String | Geological formation | "Miocene Sand A" |
| TOP_DEPTH_MD | Float | Top depth measured | 22000.0 |
| TOP_DEPTH_TVD | Float | Top true vertical depth | 21500.0 |
| FORMATION_AGE | String | Geological age | "Miocene" |
| LITHOLOGY | String | Rock type | "SANDSTONE" |

### File: `current/geology/hydrocarbon_bearing_interval.csv`

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| API_WELL_NUMBER | String | API well number | "608174000100" |
| ZONE_NAME | String | Pay zone name | "Main Pay Sand" |
| TOP_DEPTH | Float | Top of pay zone | 24000.0 |
| BOTTOM_DEPTH | Float | Bottom of pay zone | 24450.0 |
| NET_PAY | Float | Net pay thickness | 380.0 |
| POROSITY_AVG | Float | Average porosity (%) | 28.0 |
| PERMEABILITY_AVG | Float | Average permeability (mD) | 1200.0 |
| OIL_SATURATION | Float | Oil saturation (%) | 78.0 |
| GOR | Float | Gas-oil ratio (scf/bbl) | 650.0 |

---

## Infrastructure Data

### File: `current/infrastructure/all_bsee_blocks.csv`

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| BLOCK_NUMBER | String | Official block number | "MC 778" |
| AREA_CODE | String | Area code | "MC" |
| AREA_NAME | String | Full area name | "Mississippi Canyon" |
| BLOCK_LATITUDE | Float | Block center latitude | 28.1500 |
| BLOCK_LONGITUDE | Float | Block center longitude | -89.5000 |
| WATER_DEPTH_MIN | Float | Minimum water depth (ft) | 5800.0 |
| WATER_DEPTH_MAX | Float | Maximum water depth (ft) | 6200.0 |
| LEASE_NUMBER | String | Current lease number | "OCS-G-12345" |
| OPERATOR | String | Current operator | "BP America" |
| LEASE_DATE | Date | Lease effective date | "2020-01-01" |
| EXPIRATION_DATE | Date | Lease expiration | "2030-01-01" |
| ACREAGE | Float | Block area in acres | 5760.0 |
| ACTIVE_WELLS | Integer | Number of active wells | 8 |

---

## Data Type Definitions

### Common Data Types
- **String**: Text data, variable length
- **Float**: Decimal numbers
- **Integer**: Whole numbers
- **Date**: ISO format (YYYY-MM-DD)

### Common Abbreviations
- **API**: American Petroleum Institute
- **BBL**: Barrels
- **MCF**: Thousand Cubic Feet
- **MD**: Measured Depth
- **TVD**: True Vertical Depth
- **BOP**: Blowout Preventer
- **P&A**: Plugged and Abandoned
- **ESP**: Electric Submersible Pump
- **GOR**: Gas-Oil Ratio
- **DLS**: Dog Leg Severity

### Units of Measurement
- **Depth**: Feet (ft)
- **Pressure**: Pounds per Square Inch (PSI)
- **Temperature**: Degrees Fahrenheit (°F)
- **Volume (Oil/Water)**: Barrels (BBL)
- **Volume (Gas)**: Thousand Cubic Feet (MCF)
- **Permeability**: Millidarcies (mD)
- **Porosity**: Percentage (%)

## Data Quality Notes

### Missing Data Conventions
- Numeric fields: NULL or -999.0
- String fields: Empty string or "N/A"
- Date fields: NULL or "1900-01-01"

### Data Validation Rules
1. API numbers must be 10-14 characters
2. Depths must be positive values
3. Dates must be in valid ISO format
4. Coordinates must be within Gulf of Mexico bounds

---

*For field-specific questions or to report data issues, please submit a GitHub issue.*