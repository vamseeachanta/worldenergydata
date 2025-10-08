# Manual Download Guide for Marine Safety Data

**Purpose:** Instructions for data sources requiring manual browser downloads
**Date:** October 7, 2025

---

## 🎯 High-Priority Manual Downloads (50,000+ Records)

### 1. BSEE Offshore Incident Data (~50,000 records)

**WHERE TO FIND BSEE YEARLY FILES:**

**Primary Source - BSEE Statistics Page:**
- **URL:** https://www.bsee.gov/stats-facts/offshore-incident-statistics
- **What you'll find:** Annual PDF reports and Excel files by year
- **Files to download:** Incident statistics by fiscal year (1996-2024)

**Step-by-Step Instructions:**

1. **Visit:** https://www.bsee.gov/stats-facts/offshore-incident-statistics

2. **Look for sections:**
   - "Calendar Year Statistics" (2018-present)
   - "Fiscal Year Statistics" (2001-2017)
   - "Historical Data" (1996-2000)

3. **Download options:**
   - **Option A:** Excel files by year (preferred)
     - Click on year links (e.g., "CY 2023", "FY 2016")
     - Download Excel (.xlsx) files
     - Save to: `data/modules/marine_safety/raw/bsee_offline/`
   
   - **Option B:** PDF reports (if Excel unavailable)
     - Download annual PDF reports
     - Will require PDF extraction

4. **Alternative - BSEE Data Center:**
   - **URL:** https://www.data.bsee.gov/
   - Navigate to "Incidents" section
   - Use query builder to export data
   - Filter by: Incident type, date range, location
   - Export to CSV/Excel

5. **What to download:**
   ```
   Priority years (most recent):
   - 2024 (partial year)
   - 2023
   - 2022
   - 2021
   - 2020
   
   Historical (if time permits):
   - 2010-2019
   - 2000-2009
   - 1996-1999
   ```

6. **Save to:**
   ```
   data/modules/marine_safety/raw/bsee_offline/
   ├── CY2024_Incidents.xlsx
   ├── CY2023_Incidents.xlsx
   ├── FY2017_Incidents.xlsx
   └── ... (one file per year)
   ```

**Expected Data:**
- Platform fires and explosions
- Injuries and fatalities
- Blowouts and well control incidents
- Collisions with offshore structures
- H2S releases
- Loss of well control

---

### 2. PHMSA Hazardous Materials Data (~500-1,000 records)

**WHERE TO FIND:**

**Primary Source - PHMSA Hazmat Portal:**
- **URL:** https://hazmatonline.phmsa.dot.gov/IncidentReportsSearch/
- **Requires:** Free registration (one-time)

**Step-by-Step Instructions:**

1. **Register (if needed):**
   - Visit: https://hazmatonline.phmsa.dot.gov/
   - Click "Register" or "Create Account"
   - Complete registration form
   - Wait for email confirmation

2. **Login and Search:**
   - Navigate to "Incident Reports Search"
   - **Filter by:**
     - Transportation Mode: **Water** (select)
     - Date Range: 2000-2025 (or specific years)
     - Hazard Class: All (or specific classes)
   - Click "Search"

3. **Export Data:**
   - Click "Export" or "Download Results"
   - Choose format: CSV (preferred) or Excel
   - Save to: `data/modules/marine_safety/raw/phmsa_hazmat/`

4. **Files to create:**
   ```
   data/modules/marine_safety/raw/phmsa_hazmat/
   ├── hazmat_water_transport_2000-2010.csv
   ├── hazmat_water_transport_2011-2020.csv
   └── hazmat_water_transport_2021-2025.csv
   ```

---

### 3. IMO GISIS - Global Marine Casualties (~10,000 records)

**WHERE TO FIND:**

**Primary Source - IMO GISIS Portal:**
- **URL:** https://gisis.imo.org/
- **Requires:** Free IMO account registration

**Step-by-Step Instructions:**

1. **Register for IMO Account:**
   - Visit: https://gisis.imo.org/
   - Click "Register" or create account
   - **Registration URL:** https://webaccounts.imo.org/
   - Fill out registration form (requires email verification)
   - Wait for approval (may take 1-2 business days)

2. **Login to GISIS:**
   - Navigate to: https://gisis.imo.org/Public/
   - Login with your IMO credentials

3. **Access Marine Casualties Module:**
   - Click on "Marine Casualties and Incidents" module
   - Navigate to "Search" or "Query" section

4. **Export Data:**
   - Set filters:
     - Date range: 2010-2025 (or broader)
     - Casualty type: All
     - Flag state: All (or specific countries)
   - Look for "Export" or "Download" option
   - Choose format: CSV/Excel (if available)
   - Save to: `data/modules/marine_safety/raw/imo_gisis/`

5. **Alternative - Manual Queries:**
   - If bulk download not available, run multiple queries:
     - By year (2010, 2011, 2012, etc.)
     - Export each year's results separately
     - Combine later

**Expected Data:**
- International vessel casualties
- Investigation reports
- Flag state data
- Ship particulars
- Casualties and pollution incidents

---

## 📥 Medium-Priority Manual Downloads

### 4. USCG MISLE 2013-2015 Data

**WHERE TO FIND:**

**Primary Source - USCG Homeport:**
- **URL:** https://homeport.uscg.mil/missions/investigations/marine-casualty-pollution-investigations
- Or: https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/Marine-Casualty-and-Pollution-Data-for-Researchers/

**Step-by-Step Instructions:**

1. **Visit USCG Homeport:**
   - Navigate to: Missions → Investigations → Marine Casualty Pollution Investigations

2. **Look for "Data for Researchers" section**

3. **Download files:**
   - Look for: "MISLE_DATA.zip" or similar files
   - Download File #2: MISLE Database (2002-2015+)
   - May have multiple ZIP files for different years

4. **Save and Extract:**
   - Save to: `data/modules/marine_safety/raw/uscg_misle/`
   - Extract ZIP files
   - Look for database files or CSV exports

**Note:** We already have 1995-2012 via Data Liberation Project, so focus on 2013-2024 if available.

---

### 5. State-Level OSHA Maritime Data

**WHERE TO FIND:**

**California:**
- **URL:** https://www.dir.ca.gov/dosh/fatalworkplaceinjuries.html
- Filter by NAICS codes: 336611, 483000, 488300

**Washington:**
- **URL:** https://fortress.wa.gov/lni/oshafatcasesrch/
- Search for maritime industry codes

**New York:**
- **URL:** https://www.labor.ny.gov/stats/fatal.shtm
- Look for maritime/shipping fatalities

**Instructions:**
1. Visit each state's OSHA portal
2. Search/filter for maritime industries
3. Export available data (usually CSV or Excel)
4. Save to: `data/modules/marine_safety/raw/osha_maritime/`

---

## 📄 PDF Extraction Tasks (12,000+ Records)

### 6. EMSA Annual Reports (Already Downloaded)

**Location:** `data/modules/marine_safety/raw/emsa_reports/`

**Files:**
- EMSA_Annual_Overview_2020.pdf (2.3 MB)
- EMSA_Annual_Overview_2021.pdf (3.3 MB)
- EMSA_Annual_Overview_2022.pdf (135 KB)
- EMSA_Annual_Overview_2023.pdf (87 KB)

**Task:** Extract casualty statistics tables from PDFs

**Tools to use:**
- Online: https://www.ilovepdf.com/pdf_to_excel
- Python: `tabula-py` or `pdfplumber`
- Desktop: Adobe Acrobat, Preview (Mac)

**What to extract:**
- Annual casualty counts by type
- Vessel type breakdowns
- Flag state statistics
- Casualty severity classifications
- Fatality and injury counts

**Save as:**
- `emsa_reports/emsa_casualties_2020-2023.csv`

---

## 🗂️ Organization Tips

**Create folder structure:**
```bash
cd data/modules/marine_safety/raw/

mkdir -p bsee_offline/{calendar_year,fiscal_year,historical}
mkdir -p phmsa_hazmat
mkdir -p imo_gisis
mkdir -p uscg_misle_2013_2024
mkdir -p osha_maritime/{california,washington,new_york}
```

**Naming conventions:**
- Use descriptive names: `CY2023_Incidents.xlsx` not `download.xlsx`
- Include date ranges: `hazmat_2000-2010.csv`
- Keep source prefixes: `bsee_`, `phmsa_`, `imo_`

**Document downloads:**
Create a README.md in each folder with:
- Download date
- Source URL
- File descriptions
- Record counts (estimate)
- Any notes or observations

---

## ⏱️ Estimated Time Requirements

| Task | Priority | Time | Records |
|------|----------|------|---------|
| BSEE yearly files | HIGH | 30-60 min | 50,000+ |
| PHMSA Hazmat | HIGH | 20-30 min | 500-1,000 |
| IMO GISIS | HIGH | 45-90 min* | 10,000+ |
| USCG MISLE | MEDIUM | 15-30 min | Variable |
| State OSHA | MEDIUM | 30-60 min | 1,000+ |
| EMSA PDF extraction | MEDIUM | 20-40 min | 12,000+ |

*IMO GISIS includes registration wait time (1-2 days)

---

## 📋 Checklist Format

Copy this checklist and mark as you complete:

```
BSEE Offshore Incidents:
- [ ] Downloaded 2020-2024 files
- [ ] Downloaded 2010-2019 files
- [ ] Downloaded 2000-2009 files
- [ ] Saved to bsee_offline/ folder
- [ ] Created README.md with metadata

PHMSA Hazmat:
- [ ] Registered for PHMSA portal
- [ ] Filtered by Water transport mode
- [ ] Downloaded 2000-2025 data
- [ ] Saved to phmsa_hazmat/ folder
- [ ] Created README.md

IMO GISIS:
- [ ] Registered for IMO account
- [ ] Account approved (wait 1-2 days)
- [ ] Logged into GISIS portal
- [ ] Downloaded casualty data
- [ ] Saved to imo_gisis/ folder
- [ ] Created README.md

EMSA PDF Extraction:
- [ ] Extracted tables from 2020 PDF
- [ ] Extracted tables from 2021 PDF
- [ ] Extracted tables from 2022 PDF
- [ ] Extracted tables from 2023 PDF
- [ ] Combined into emsa_casualties_2020-2023.csv
```

---

## 🚀 After You Download

**Once files are saved:**

1. **Create a download log:**
   ```
   File: MANUAL_DOWNLOADS_LOG.txt
   
   Date: 2025-10-07
   Downloaded by: [Your Name]
   
   BSEE:
   - CY2023_Incidents.xlsx (downloaded, 1,234 records)
   - CY2022_Incidents.xlsx (downloaded, 1,456 records)
   ...
   
   PHMSA:
   - hazmat_water_2000-2025.csv (downloaded, 567 records)
   ...
   ```

2. **Notify when ready:**
   - Let me know which files you've downloaded
   - I'll create importers for the new datasets
   - We'll import everything together

3. **Priority order:**
   - Do BSEE first (largest dataset)
   - Then PHMSA (quick registration)
   - IMO GISIS last (registration wait time)

---

**Questions? Issues?**

If you encounter:
- Broken links → Document in README, try alternative URLs
- Access denied → Check if registration required
- Large files → Download in chunks by year
- Format issues → Note file format, we'll handle during import

---

**This guide provides everything you need to manually acquire 50,000+ additional marine safety incidents!**
