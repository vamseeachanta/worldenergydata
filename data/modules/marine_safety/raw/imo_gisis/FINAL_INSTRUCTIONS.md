# IMO GISIS Download - Final Instructions

## Summary

After multiple automation attempts (Playwright MCP, Selenium, WebDriver Manager), the IMO GISIS website's complex authentication and dynamic form fields prevent automated downloads. 

**RECOMMENDATION: Manual download is the most reliable approach.**

## Your Credentials

- **URL:** https://gisis.imo.org/Public/MCIR/Search.aspx
- **Username:** vamseeachanta
- **Password:** rose109@Gudda

## FASTEST METHOD: Single Bulk Download

**Try this first - it may work!**

1. Login to https://gisis.imo.org/Public/MCIR/Search.aspx
2. Set date range:
   - From Date: **1990-01-01**
   - Until Date: **2025-12-31**
3. Check ALL casualty types:
   - ☑ Very serious marine casualty
   - ☑ Marine casualty  
   - ☑ Marine incident
4. Click **Search**
5. If results appear, click **Export** or **Download** button
6. Save as: `imo_casualties_1990_2025_full.csv`

**Expected result:** 1 file with ~7,000-10,000 records

If this times out or hits a limit, use the 5-year approach below.

## BACKUP METHOD: 5-Year Bulk Downloads

Download 7 files (10-15 minutes total):

| # | From Date | Until Date | Save As | Estimated Records |
|---|-----------|------------|---------|-------------------|
| 1 | 1990-01-01 | 1994-12-31 | `imo_1990_1994.csv` | ~1,000 |
| 2 | 1995-01-01 | 1999-12-31 | `imo_1995_1999.csv` | ~1,000 |
| 3 | 2000-01-01 | 2004-12-31 | `imo_2000_2004.csv` | ~1,000 |
| 4 | 2005-01-01 | 2009-12-31 | `imo_2005_2009.csv` | ~1,000 |
| 5 | 2010-01-01 | 2014-12-31 | `imo_2010_2014.csv` | ~1,000 |
| 6 | 2015-01-01 | 2019-12-31 | `imo_2015_2019.csv` | ~1,000 |
| 7 | 2020-01-01 | 2025-12-31 | `imo_2020_2025.csv` | ~1,200 |

For each download:
1. Set the date range
2. Check all casualty types
3. Search → Export → Save

## After Downloading

Move files to project directory:

```bash
# From your Downloads folder
cd ~/Downloads

# Move to project
mv imo_*.csv /mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw/imo_gisis/

# Verify
cd /mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw/imo_gisis
ls -lh imo_*.csv

# Count records
for file in imo_*.csv; do
    echo "$file: $(tail -n +2 "$file" | wc -l) records"
done
```

## Next Steps (After You Download)

Once you have the CSV files, let me know and I'll:

1. **Examine the data structure**
   ```bash
   head -1 imo_casualties_*.csv | head -1  # Check column headers
   ```

2. **Create IMO data importer**
   - Parse CSV columns
   - Map to database schema
   - Handle duplicates

3. **Import to database**
   ```bash
   python scripts/import_imo_data.py
   ```

4. **Generate statistics**
   - Casualties by year
   - By type and severity
   - Geographic distribution
   - Compare with existing USCG/MAIB/TSB data

## Why Automation Failed

1. **Complex authentication flow** - IMO uses multi-stage login with dynamic tokens
2. **Dynamic form field IDs** - Field selectors change between sessions
3. **Anti-automation measures** - Likely detects and blocks automated browsers
4. **Snap Chromium compatibility** - WebDriver issues with snap-installed browsers

**Bottom line:** Manual download is faster and more reliable than fixing automation.

## Time Estimate

- **Single bulk download:** 5 minutes (if it works)
- **7-file download:** 10-15 minutes
- **Year-by-year (36 files):** 30-45 minutes

---

**Created:** 2025-10-09  
**Status:** Ready for manual download  
**Expected Records:** 7,000-10,000 global marine casualties (1990-2025)
