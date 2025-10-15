# IMO GISIS Marine Casualties Data - Summary Report

**Date:** 2025-10-11
**Status:** ✅ DATA SUCCESSFULLY DOWNLOADED AND COLLATED
**Source:** IMO Global Integrated Shipping Information System (GISIS)

---

## Executive Summary

Successfully downloaded and collated **13,160 marine casualty records** spanning **125 years** (1900-2025) from the IMO GISIS database. This represents comprehensive global marine casualty data from the authoritative international maritime safety organization.

---

## Data Coverage

### Temporal Coverage
- **Earliest Record:** 1900-01-01
- **Latest Record:** 2025-06-09
- **Total Span:** 125 years

### Records by Era
| Era | Records | Percentage |
|-----|---------|------------|
| 1900-1969 | 23 | 0.2% |
| 1970-1979 | 87 | 0.7% |
| 1980-1989 | 523 | 4.0% |
| 1990-1999 | 2,603 | 19.8% |
| 2000-2009 | 4,427 | 33.6% |
| 2010-2019 | 4,257 | 32.3% |
| 2020-2025 | 1,240 | 9.4% |

### Recent Years (2015-2025)
- 2015: 387 casualties
- 2016: 399 casualties
- 2017: 459 casualties
- 2018: 310 casualties
- 2019: 323 casualties
- 2020: 266 casualties
- 2021: 297 casualties
- 2022: 255 casualties
- 2023: 261 casualties
- 2024: 148 casualties
- 2025: 13 casualties (through June 9)

---

## Data Quality

### Completeness
| Field | Non-Null | Percentage |
|-------|----------|------------|
| Reference | 13,160 | 100.0% |
| Occurrence date and time | 13,160 | 100.0% |
| Casualty severity | 13,160 | 100.0% |
| Flag Administrations | 13,160 | 100.0% |
| Number of ships involved | 13,160 | 100.0% |
| Ships involved | 13,159 | 100.0% |
| Ship types | 11,591 | 88.1% |
| Place | 10,043 | 76.3% |
| Coordinates | 5,953 | 45.2% |
| Administrations submitting investigation reports | 5,401 | 41.0% |
| Location | 4,534 | 34.5% |
| Casualty event | 1,884 | 14.3% |

### Data Integrity
- **Unique References:** 13,160
- **Duplicates:** 0
- **Invalid Records:** 0 (all 6 files processed successfully)

---

## Casualty Statistics

### By Severity
| Severity | Records | Percentage |
|----------|---------|------------|
| Very serious marine casualty | 5,255 | 39.9% |
| Marine casualty | 5,088 | 38.7% |
| Marine incident | 2,817 | 21.4% |

### Top Casualty Event Types
| Event Type | Records | Percentage |
|------------|---------|------------|
| Collision - with other ship | 226 | 1.7% |
| Fire/explosion - fire | 178 | 1.4% |
| Grounding - while under power | 141 | 1.1% |
| Occupational accident - slipping, stumbling, falling overboard | 132 | 1.0% |
| Capsize/listing - capsize | 100 | 0.8% |
| Ship/equipment damage | 88 | 0.7% |
| Flooding/foundering - flooding | 77 | 0.6% |
| Flooding/foundering - foundering | 66 | 0.5% |

*Note: 85.7% of records have missing casualty event data*

### Top Ship Types Involved
| Ship Type | Records | Percentage |
|-----------|---------|------------|
| General Cargo | 2,614 | 19.9% |
| Bulk Dry | 1,342 | 10.2% |
| Fish Catching | 1,338 | 10.2% |
| Container | 702 | 5.3% |
| Oil Tanker | 601 | 4.6% |
| Non-ship structures | 523 | 4.0% |
| Passenger/Ro-Ro Cargo | 448 | 3.4% |
| Passenger | 420 | 3.2% |
| Chemical Tanker | 392 | 3.0% |
| Towing / Pushing | 228 | 1.7% |

---

## Geographic Distribution

### Top Locations
| Location | Records | Percentage |
|----------|---------|------------|
| Open sea | 1,179 | 9.0% |
| Coastal waters | 1,063 | 8.1% |
| Port | 734 | 5.6% |
| At berth | 401 | 3.0% |
| Anchorage | 319 | 2.4% |
| Port approach | 274 | 2.1% |
| River | 138 | 1.0% |
| Inland waters | 130 | 1.0% |

*Note: 65.5% of records have missing location data*

### Top Flag States
| Flag Administration | Records | Percentage |
|---------------------|---------|------------|
| Panama | 1,756 | 13.3% |
| United Kingdom | 582 | 4.4% |
| Liberia | 544 | 4.1% |
| Malta | 515 | 3.9% |
| Bahamas | 360 | 2.7% |
| Cyprus | 301 | 2.3% |
| United States | 291 | 2.2% |
| Hong Kong, China | 241 | 1.8% |
| Antigua and Barbuda | 236 | 1.8% |
| France | 232 | 1.8% |
| Russian Federation | 228 | 1.7% |
| Spain | 224 | 1.7% |
| Canada | 215 | 1.6% |
| Republic of Korea | 212 | 1.6% |

---

## Downloaded Files

| File | Period | Records | Size |
|------|--------|---------|------|
| GISIS-MCIR-19000101-19691231.csv | 1900-1969 | 23 | 4.0 KB |
| GISIS-MCIR-19700101-19891231.csv | 1970-1989 | 610 | 75 KB |
| GISIS-MCIR-19900101-19991231.csv | 1990-1999 | 2,603 | 412 KB |
| GISIS-MCIR-20001011-20091231.csv | 2000-2009 | 4,427 | 896 KB |
| GISIS-MCIR-20101011-20191231.csv | 2010-2019 | 4,257 | 988 KB |
| GISIS-MCIR-20200101-20251010.csv | 2020-2025 | 1,240 | 318 KB |

**Collated Output:**
- `imo_gisis_collated.csv` - 13,160 records, 2.38 MB

---

## Data Columns

1. **Reference** - Unique IMO casualty reference ID
2. **Number of ships involved** - Count of vessels in incident
3. **Ships involved** - Ship names and IMO numbers
4. **SOLAS status** - SOLAS convention compliance
5. **Flag Administrations** - Vessel flag state(s)
6. **Ship types** - Vessel classification
7. **Occurrence date and time** - Incident timestamp
8. **Casualty event** - Type of incident (sparse)
9. **Casualty severity** - Very serious / Marine casualty / Marine incident
10. **Coordinates** - Latitude/longitude (45% coverage)
11. **Place** - Location description (76% coverage)
12. **Location** - Location category (35% coverage)
13. **Number of investigation reports** - Count of investigation reports
14. **Administrations submitting investigation reports** - Reporting authorities

---

## Key Findings

### 1. Data Availability Increasing
- Modern era (2000-2025) represents 82% of all records
- Peak data availability: 2000-2019 (8,684 records / 66%)
- Indicates improved reporting standards and data capture

### 2. Severity Distribution
- 79% of casualties are serious or very serious
- Only 21% classified as marine incidents
- Suggests database focuses on significant events

### 3. Vessel Types
- Cargo vessels (General Cargo + Bulk) = 30% of casualties
- Fishing vessels = 10%
- Tankers (Oil + Chemical) = 7.5%

### 4. Geographic Patterns
- Open sea incidents = 9% (suggesting deep-water operations risk)
- Coastal waters = 8% (high-traffic areas)
- Port-related (Port + Berth + Anchorage) = 11%

### 5. Flag State Patterns
- Panama (flag of convenience) leads with 13.3%
- Major maritime nations well represented (UK, US, France, Canada)
- Top 15 flags account for 45% of all casualties

### 6. Missing Data Challenges
- Casualty event: 86% missing (major gap for event type analysis)
- Location category: 65% missing
- Coordinates: 55% missing
- Suggests varying reporting standards across administrations

---

## Data Limitations

1. **Sparse Event Data**: Only 14% of records include casualty event classification
2. **Geographic Gaps**: 65% missing location categories, 55% missing coordinates
3. **Historical Coverage**: Pre-1990 data is sparse (only 5% of total)
4. **Reporting Bias**: Likely underrepresents casualties from:
   - Non-IMO member states
   - Small vessels not subject to IMO reporting
   - Incidents in territorial waters with limited reporting

---

## Next Steps

### 1. Database Import
- Create database schema matching IMO data structure
- Import collated CSV into marine_safety database
- Add indexes on Reference, Date, Flag Administration, Ship Type

### 2. Data Enhancement
- Parse coordinates into separate lat/long fields
- Extract individual ship details from "Ships involved" field
- Categorize missing casualty events where possible from descriptions

### 3. Integration with Existing Data
- Cross-reference with USCG BARD data (US casualties)
- Compare with UK MAIB data (UK casualties)
- Identify overlaps and unique incidents

### 4. Analysis
- Time series analysis of casualty trends
- Geographic clustering of high-risk areas
- Flag state safety performance comparison
- Vessel type risk assessment

---

## Files Generated

**Raw Data:**
- Location: `/mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw/imo_gisis/`
- 6 original CSV files (2.7 MB total)

**Processed Data:**
- `imo_gisis_collated.csv` - Combined dataset (2.38 MB)
- `collation_summary.json` - Detailed statistics
- `DATA_SUMMARY.md` - This report

**Scripts:**
- `/scripts/collate_imo_data_robust.py` - Data collation script
- Ready for database import script development

---

## Data Source

**Organization:** International Maritime Organization (IMO)
**Database:** Global Integrated Shipping Information System (GISIS)
**Module:** Marine Casualties and Incidents Reports (MCIR)
**URL:** https://gisis.imo.org/Public/MCIR/Search.aspx
**Access:** Registered user account required
**Download Date:** 2025-10-10 to 2025-10-11
**Downloaded By:** vamseeachanta

---

## Summary

✅ **13,160 marine casualty records** successfully downloaded and collated
✅ **125-year** historical coverage (1900-2025)
✅ **Global coverage** from authoritative IMO source
✅ **High data quality** - zero duplicates, all files processed successfully
✅ Ready for database import and analysis

This dataset provides unprecedented global maritime casualty data for safety analysis, trend identification, and risk assessment across the international shipping industry.

---

**Report Generated:** 2025-10-11 17:36 UTC
**Report Version:** 1.0
**Status:** Complete
