# NTSB CAROL Marine Investigation Database

**Status:** ❌ WEB QUERY REQUIRED
**Expected Coverage:** 1967-present (focus on 2010+)
**Expected Records:** 1,000+ major marine investigations

---

## Source Information

- **Provider:** National Transportation Safety Board (NTSB)
- **CAROL Database:** https://data.ntsb.gov/carol-main-public/
- **Developer Portal:** https://developer.ntsb.gov/
- **Expected Format:** JSON or CSV exports from query builder

## Download Status

**❌ API Access Failed**
- Public API endpoints return 404 errors
- API documentation outdated
- Manual web query interface required

## Manual Download Instructions

### Option 1: CAROL Query Builder (Recommended)

1. **Visit CAROL Database:**
   ```
   https://data.ntsb.gov/carol-main-public/query-builder
   ```

2. **Build Query:**
   - **Mode:** Select "Marine"
   - **Event Date From:** 2010-01-01 (or earlier)
   - **Event Date To:** 2025-12-31
   - **Investigation Type:** All types
   - Optional filters:
     - Vessel type
     - Accident type
     - Location
     - Severity

3. **Execute and Export:**
   - Click "Search"
   - Review results
   - Click "Export" or "Download"
   - Save as CSV or JSON
   - Save to this directory

### Option 2: NTSB API (If Registration Available)

1. **Register for API Access:**
   ```
   https://developer.ntsb.gov/
   ```

2. **Obtain API Key:**
   - Complete registration
   - Verify email
   - Generate API key

3. **Query Marine Investigations:**
   ```python
   import requests

   api_key = "YOUR_API_KEY"
   url = "https://data.ntsb.gov/api/investigations"
   params = {
       "mode": "Marine",
       "event_date_from": "2010-01-01",
       "api_key": api_key
   }
   response = requests.get(url, params=params)
   ```

4. **Save Results:**
   - Export to JSON or CSV
   - Save to this directory

### Option 3: Bulk Download (If Available)

Check NTSB download center for bulk marine data:
```
https://www.ntsb.gov/safety/data/Pages/Data_Stats.aspx
```

## Expected Data Schema

### Investigation Records
- **NTSB Case Number:** Unique identifier
- **Event Date:** When accident occurred
- **Investigation Date:** When investigation started
- **Location:** Lat/lon, waterway, port
- **Vessel Information:**
  - Name, IMO number, flag
  - Type, length, tonnage
  - Owner, operator
- **Accident Type:**
  - Collision, grounding, fire, explosion
  - Capsizing, flooding, structural failure
  - Personnel casualty, pollution event
- **Casualties:**
  - Fatalities, injuries (serious, minor)
  - Missing persons
- **Investigation Details:**
  - Probable cause determination
  - Contributing factors
  - Safety recommendations
  - Report publication status

## Data Quality Considerations

- **Scope:** NTSB investigates major marine casualties
- **Completeness:** Detailed investigations with root cause analysis
- **Coverage:** U.S. waters and U.S.-flagged vessels globally
- **Temporal Lag:** Investigations take 12-24 months; final reports lag events
- **Selective:** Not all marine accidents; focuses on significant casualties

## Query Strategy

### Recommended Query Parameters

1. **Comprehensive Marine Dataset:**
   - Mode: Marine
   - Date Range: 1980-present (or specific years needed)
   - Investigation Status: All (including preliminary)

2. **Major Casualties Only:**
   - Mode: Marine
   - Fatalities: > 0
   - Investigation Type: Accident investigation

3. **Vessel Type Specific:**
   - Passenger vessels
   - Commercial vessels
   - Recreational vessels
   - Fishing vessels

## Known Limitations

- NTSB doesn't investigate all marine accidents (USCG primary investigator for most)
- Focus on major casualties with significant safety implications
- Investigations are lengthy; recent events may not have final reports
- Some preliminary reports available before final determination

## Related Datasets

- **USCG MISLE:** Broader coverage of marine casualties
- **NOAA Oil Spills:** Environmental incidents
- **IMO GISIS:** International marine casualties
- **MAIB (UK):** Similar investigation depth for UK incidents

## API Documentation

If API access obtained, reference:
- **Swagger Docs:** https://developer.ntsb.gov/swagger/
- **API Guide:** Check developer portal for latest documentation
- **Rate Limits:** Document any rate limiting encountered

## Contact

**NTSB:**
- Office of Research and Engineering
- Email: See NTSB website contact page
- Phone: 202-314-6000

**Data/API Questions:**
- Developer Portal: https://developer.ntsb.gov/

---

## Status Updates

### 2025-10-05
- **Status:** API endpoints not functional
- **Action Required:** Use CAROL web query builder
- **Priority:** MEDIUM (Tier 2 source)
- **Alternative:** Manual query and export from web interface

### Next Steps
1. Visit CAROL query builder
2. Execute marine investigations query (2010-present)
3. Export results to JSON/CSV
4. Validate record counts
5. Document actual schema received
6. Update this README with final dataset details

---

**README Generated:** 2025-10-05
**Data Steward:** Research Agent
