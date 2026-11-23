# NOAA Oil Spill Incident Database

**Status:** ✅ DOWNLOADED
**Download Date:** October 5, 2025
**Source:** NOAA Office of Response and Restoration

---

## Overview

This directory contains the NOAA Incident News database, which tracks oil and chemical spill incidents in U.S. waters from 1957 to present.

## Source Information

- **Provider:** NOAA Office of Response and Restoration
- **URL:** https://incidentnews.noaa.gov/raw/index
- **Download URL:** https://incidentnews.noaa.gov/raw/incidents.csv
- **Format:** CSV (Comma-separated values)
- **Encoding:** UTF-8
- **Update Frequency:** Ongoing (near real-time)

## Files

### incidents.csv
- **Size:** 3.0 MB
- **Records:** 4,797 incidents
- **Coverage:** 1957-09-29 to 2025-09-29
- **Download Date:** 2025-10-05

## Data Schema

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique incident identifier |
| open_date | Date | Date incident was opened/reported |
| name | String | Incident name/description |
| location | String | Location description |
| lat | Float | Latitude coordinate |
| lon | Float | Longitude coordinate |
| threat | String | Threat classification (typically "Oil") |
| tags | String | Incident tags/categories |
| commodity | String | Type of material spilled |
| measure_skim | Boolean | Whether skimming operations used |
| measure_shore | Boolean | Whether shoreline cleanup conducted |
| measure_bio | Boolean | Whether bioremediation used |
| measure_disperse | Boolean | Whether dispersants used |
| measure_burn | Boolean | Whether in-situ burning used |
| max_ptl_release_gallons | Integer | Maximum potential release (gallons) |
| posts | Integer | Number of posts/updates |
| description | Text | Detailed incident description |

## Sample Record

```csv
11071,2025-09-29,"Derelict Fishing Vessel Sunk in Pamlico Sound; Buxton, North Carolina","7CRH+CM Buxton, NC, USA",35.29112241420674,-75.57083129882812,Oil,,,,,,,,,0,"At 1030 on September 29, 20205, U.S. Coast Guard (USCG) Sector North Carolina notified the NOAA Scientific Support Coordinator (SSC) about a derelict 30-foot commercial fishing vessel that was found on the morning of September 28, sunk in the Pamlico Sound offshore of Hatteras Island, North Carolina. Vessel had an estimated 150 gallons of diesel fuel on board. Sector North Carolina requested a trajectory."
```

## Data Quality Notes

- **Completeness:** Most fields populated for recent incidents (2000+)
- **Geographic Coverage:** Primarily U.S. waters and EEZ
- **Missing Values:** Commodity and response measures often blank for older incidents
- **Coordinate Precision:** Varies by incident; recent incidents have high precision
- **Release Volumes:** Often estimates or maximum potential (not actual)

## Known Issues

- Response measure fields (boolean) are often empty rather than explicitly false
- Date field in description sometimes contains typos (e.g., "20205" instead of "2025")
- Location strings use various formats (coordinates, place names, Plus Codes)

## Usage Notes

1. **Filtering:** Filter by `open_date` for temporal analysis
2. **Geocoding:** Use `lat`/`lon` for spatial analysis; validate against location string
3. **Response Analysis:** Check measure_* fields for response tactics
4. **Size Estimation:** `max_ptl_release_gallons` is often maximum potential, not actual spill size
5. **Descriptions:** Parse `description` field for additional details and context

## Citation

```
NOAA Office of Response and Restoration. (2025). Incident News Database.
Retrieved October 5, 2025, from https://incidentnews.noaa.gov/
```

## Related Datasets

- USCG MISLE Database (marine casualties)
- EPA Emergency Response Notification System (ERNS)
- Coast Guard National Response Center (NRC) reports

## Contact

For questions about this dataset, contact:
- NOAA Office of Response and Restoration: https://response.restoration.noaa.gov/

---

**README Generated:** 2025-10-05
**Data Steward:** Research Agent
