# IMO GISIS - Global Integrated Shipping Information System

**Status:** ⚠️ REGISTRATION REQUIRED - DATA NOT PUBLICLY ACCESSIBLE
**Source:** International Maritime Organization (IMO)
**Website:** https://gisis.imo.org/Public/MCIR/Search.aspx
**Attempted Download:** 2025-10-08

---

## Overview

IMO GISIS (Global Integrated Shipping Information System) contains comprehensive marine casualty and incident data reported by IMO member states. However, access requires **free registration** with IMO Web Accounts.

## Access Barrier Discovered

### What We Found:

When attempting to access the Marine Casualties and Incidents Reports (MCIR) module at:
- **URL:** https://gisis.imo.org/Public/MCIR/Search.aspx

The system redirects to:
- **Login Portal:** IMO Web Accounts authentication page
- **Access Type:** Free but requires account registration

### Error Message:
```
"IMO Web Accounts"
ReturnUrl=https://gisis.imo.org/Public/MCIR/Search.aspx
error_message=interaction_required
```

## Registration Process

### Step 1: Create IMO Web Account

1. **Visit:** https://webaccounts.imo.org/ (or redirected from GISIS)
2. **Register:** Create free account with email verification
3. **Wait:** Account approval may take 1-2 business days
4. **Purpose:** Select "Research" or "Academic" as account purpose

### Step 2: Access GISIS After Registration

Once registered and approved:
1. **Login:** https://gisis.imo.org/
2. **Navigate:** Marine Casualties and Incidents (MCIR) module
3. **Search:** Use advanced search filters
4. **Export:** Download results (CSV/Excel if available)

## Expected Data Coverage

### Marine Casualties and Incidents Reports (MCIR)

**Data Types:**
- **Very Serious Casualties** - Total loss, marine pollution, fatalities
- **Serious Casualties** - Significant damage, injuries
- **Less Serious Casualties** - Minor damage, incidents
- **Marine Incidents** - Near misses, potential casualties

**Fields Expected:**
- IMO Ship Number
- Ship name and flag state
- Casualty date and location
- Casualty type (collision, grounding, fire, etc.)
- Vessel type and tonnage
- Casualties (fatalities, injuries, missing)
- Damage assessment
- Investigation status
- Causal factors

**Geographic Scope:**
- **Global:** All IMO member states
- **Focus:** International waters and member state waters
- **Coverage:** Commercial vessels primarily

**Time Range:**
- **Historical:** Data from 1990s onwards (varies by member state)
- **Current:** Regular updates from member state reports
- **Quality:** Varies by reporting state compliance

## Estimated Record Count

Based on IMO reports and EMSA statistics:
- **Very Serious Casualties:** ~100-200 per year globally
- **Serious Casualties:** ~500-800 per year globally
- **Less Serious Casualties:** ~2,000-3,000 per year globally
- **Marine Incidents:** ~5,000-10,000 per year globally (if available)

**Total Estimate (2000-2024):**
- **Conservative:** 10,000-15,000 casualty records
- **Optimistic:** 50,000-100,000 records (if incidents included)

## Alternative Access Methods

### 1. IMO Statistics Publications

**Freely available annual summaries:**
- **URL:** https://www.imo.org/en/OurWork/MSAS/Pages/Casualties.aspx
- **Format:** PDF reports with casualty statistics
- **Coverage:** Summary data by year, casualty type, flag state
- **Limitation:** Aggregate statistics, not individual incident records

### 2. EMSA EMCIP Database

**Already Downloaded:**
- `/emsa_reports/` directory contains EMSA Annual Overview PDFs (2020-2023)
- EMSA data includes European casualties also reported to IMO
- **Overlap:** European incidents appear in both EMSA and IMO GISIS

### 3. Member State Reports

Individual IMO member states publish their own casualty data:
- **UK MAIB** - Already downloaded (5,877 records)
- **Canadian TSB** - Already downloaded (86,289 records)
- **US USCG** - Already downloaded (68,000+ records)
- **Australian ATSB** - No bulk download available

### 4. Classification Societies

**Alternative sources:**
- Lloyd's Register Intelligence (subscription required)
- IHS Markit Sea-web (subscription required)
- INTERCARGO casualty statistics (members only)

## Manual Download Process

### When You Have IMO Account Access:

1. **Login to GISIS:**
   ```
   https://gisis.imo.org/
   Navigate to: Public Access → Marine Casualties and Incidents
   ```

2. **Search Parameters:**
   ```
   Date Range: Select time period (e.g., 2010-2024)
   Casualty Type: All or specific (collision, fire, grounding, etc.)
   Flag State: All or specific countries
   Vessel Type: All or specific (cargo, passenger, tanker, etc.)
   Severity: All or specific (very serious, serious, less serious)
   ```

3. **Export Data:**
   - Look for "Export" or "Download" button
   - Format: CSV, Excel, or PDF
   - Save to: `data/modules/marine_safety/raw/imo_gisis/`

4. **Iterative Download (if query limits exist):**
   ```
   Year-by-year approach:
   - 2024: imo_casualties_2024.csv
   - 2023: imo_casualties_2023.csv
   - 2022: imo_casualties_2022.csv
   ...
   ```

5. **Expected Files:**
   ```
   imo_gisis/
   ├── imo_casualties_2024.csv
   ├── imo_casualties_2023.csv
   ├── imo_casualties_2022.csv
   ├── imo_casualties_2021.csv
   └── ... (by year or by casualty type)
   ```

## Data Quality Considerations

### Strengths:
- **Authoritative:** Official reports from IMO member states
- **Comprehensive:** Global coverage of commercial vessel casualties
- **Standardized:** IMO casualty reporting codes
- **Verified:** Investigated incidents with causal analysis

### Limitations:
- **Reporting Delays:** Member states may report months after incident
- **Completeness Varies:** Depends on member state compliance
- **Coverage Gaps:** Small vessels and non-member states may be underrepresented
- **Classification Changes:** Casualty definitions evolved over time

### Known Issues:
- Not all member states report consistently
- Incidents in territorial waters may be excluded
- Recreational vessels not included
- Fishing vessels underrepresented in some regions

## Related Datasets in Marine Safety Database

**Already Imported:**
- **USCG BARD** - Recreational boating (63,340 incidents)
- **NOAA OR&R** - Oil spills (4,797 incidents)
- **Canadian TSB** - Marine occurrences (86,289 records)
- **UK MAIB** - UK casualties (5,877 records)

**Overlap Expected:**
- UK MAIB casualties also reported to IMO
- Canadian TSB major casualties reported to IMO
- USCG reports to IMO for US-flagged vessels in international waters

**Complementary Data:**
- IMO would add non-US/UK/Canada casualties
- Focus on commercial vessels (vs recreational in BARD)
- International waters incidents
- Foreign-flagged vessel casualties

## Integration Priority

### If Access Obtained:

**HIGH PRIORITY** if:
- >10,000 unique casualty records available
- Individual incident details provided
- Coverage extends to regions not in current database (Asia, Africa, South America)
- Export to CSV/Excel is straightforward

**MEDIUM PRIORITY** if:
- 5,000-10,000 records
- Significant overlap with existing data
- Manual download is time-consuming

**LOW PRIORITY** if:
- Only summary statistics available
- Mostly duplicates existing USCG/MAIB/TSB data
- Export requires extensive manual work

## Automation Challenges

### Why Automated Download Failed:

1. **Authentication Required:**
   - Login session needed
   - Cannot access public search without credentials
   - Rate limiting for automated queries likely

2. **ASP.NET Application:**
   - Complex ViewState/EventValidation
   - Dynamic form controls
   - JavaScript-dependent interactions

3. **Potential Query Limits:**
   - Maximum results per search unknown
   - May require pagination or multiple queries
   - Export functionality unknown until logged in

### Future Automation Options:

**If credentials available:**
- Python Playwright with login automation
- Selenium with authenticated session
- API access (if IMO provides one - check after login)

**Script Location:**
- `/scripts/download_imo_gisis_data.py` (created but requires credentials)
- Update script with login credentials if registration successful

## Next Steps

### For User:

1. **Register for IMO Web Account:**
   - Visit: https://webaccounts.imo.org/
   - Complete registration form
   - Wait for email confirmation and approval

2. **Explore GISIS Interface:**
   - Login and navigate to MCIR module
   - Test search functionality
   - Check export options (CSV/Excel)
   - Assess data volume and fields

3. **Manual Download Strategy:**
   - If <1,000 records: Single export
   - If 1,000-10,000 records: Export by year or casualty type
   - If >10,000 records: Coordinate with research team for automation

4. **Report Findings:**
   - Document available fields
   - Estimate record count
   - Note export format options
   - Assess overlap with existing data

## Contact Information

**IMO Data Requests:**
- Website: https://www.imo.org/en/OurWork/MSAS/Pages/Casualties.aspx
- GISIS Support: gisis@imo.org
- Phone: +44 (0)20 7735 7611

**IMO Headquarters:**
- International Maritime Organization
- 4 Albert Embankment
- London SE1 7SR, United Kingdom

---

**README Created:** 2025-10-08
**Status:** Awaiting user registration with IMO Web Accounts
**Priority:** HIGH (if bulk export available), MEDIUM (if manual extraction required)
**Estimated Records:** 10,000-100,000 global casualties (2000-2024)
