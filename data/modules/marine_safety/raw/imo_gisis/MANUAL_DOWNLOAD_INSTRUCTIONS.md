# IMO GISIS Manual Download Instructions

**Based on your logged-in session screenshot**

Since automated download is encountering field detection issues, here's how to manually download the data year by year.

---

## What We See in Your Screenshot

**Current search showing:**
- Date range: 2018-09-01 to 2025-10-08
- Results: **1,668 casualties found**
- Checkboxes: ✓ Very serious marine casualty, ✓ Marine casualty, ✓ Marine incident
- Download button: Available (📥 icon visible in results)

## Manual Download Process

### Step 1: Download Full Dataset (2018-2025)

**Already set up in your browser:**
1. Your current search (2018-09-01 to 2025-10-08) shows 1,668 results
2. Click the **Download** button (📥 icon above results table)
3. Save as: `imo_2018_2025_full.csv`
4. Move to: `/mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw/imo_gisis/`

### Step 2: Download Historical Data (if available)

Try extending the date range backwards:

**2010-2017:**
1. Change "From" date: `2010-01-01`
2. Change "Until" date: `2017-12-31`
3. Click **Search**
4. If results found, click **Download**
5. Save as: `imo_2010_2017.csv`

**2000-2009:**
1. Change "From" date: `2000-01-01`
2. Change "Until" date: `2009-12-31`
3. Click **Search**
4. If results found, click **Download**
5. Save as: `imo_2000_2009.csv`

**Pre-2000 (if available):**
1. Try: `1990-01-01` to `1999-12-31`
2. Save as: `imo_1990_1999.csv`

### Step 3: Verify Download

After downloading, check files:

```bash
ls -lh /mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw/imo_gisis/*.csv
```

Each CSV should contain:
- Reference column
- Date of occurrence
- Severity (Very serious/Marine casualty/Marine incident)
- Ships involved
- Location
- Investigation reports count
- Reporting administrations

---

## Alternative: Year-by-Year Download

If the full download fails or times out, download year by year:

### 2025:
- From: `2025-01-01` | Until: `2025-10-08`
- Expected: ~200 results
- Save as: `imo_2025.csv`

### 2024:
- From: `2024-01-01` | Until: `2024-12-31`
- Expected: ~200-250 results
- Save as: `imo_2024.csv`

### 2023:
- From: `2023-01-01` | Until: `2023-12-31`
- Expected: ~200-250 results
- Save as: `imo_2023.csv`

### 2022:
- From: `2022-01-01` | Until: `2022-12-31`
- Expected: ~200-250 results
- Save as: `imo_2022.csv`

### 2021:
- From: `2021-01-01` | Until: `2021-12-31`
- Expected: ~200-250 results
- Save as: `imo_2021.csv`

### 2020:
- From: `2020-01-01` | Until: `2020-12-31`
- Expected: ~200-250 results
- Save as: `imo_2020.csv`

### 2019:
- From: `2019-01-01` | Until: `2019-12-31`
- Expected: ~200-250 results
- Save as: `imo_2019.csv`

### 2018:
- From: `2018-01-01` | Until: `2018-12-31`
- Expected: ~200-250 results
- Save as: `imo_2018.csv`

---

## After Download

### Verify Files

```bash
cd /mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw/imo_gisis

# Check file sizes
ls -lh *.csv

# Count records in each file
for file in *.csv; do
    echo "$file: $(wc -l < "$file") rows"
done
```

### Expected Total

Based on your screenshot:
- **Minimum:** 1,668 casualties (2018-2025 shown)
- **Possible:** 3,000-5,000+ if historical data available (2000-2017)
- **Optimistic:** 10,000+ if data goes back to 1990s

---

## Quick Download Commands

If you prefer command-line file moving:

```bash
# From your Downloads folder to project
cp ~/Downloads/imo_*.csv /mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw/imo_gisis/

# Or if files have different names
mv ~/Downloads/gisis_export.csv /mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw/imo_gisis/imo_2018_2025_full.csv
```

---

## What to Download

**Columns visible in your screenshot:**
1. Reference (e.g., C1000784)
2. Date of occurrence
3. Severity
4. Ships involved (with IMO numbers)
5. Location
6. Investigation Reports (count)
7. Reporting Administrations

**Expected CSV headers:**
- Reference
- Date_of_occurrence
- Severity
- Ship_name
- IMO_number
- Ship_type
- Flag_state
- Location
- Latitude
- Longitude
- Occurrence_category
- Investigation_status
- Reporting_administration
- (Additional columns may vary)

---

## After You Download

Once you have the CSV files, let me know and I'll:
1. Examine the file structure
2. Create an IMO importer
3. Import all records to the marine safety database
4. Generate statistics on the new data

---

**Estimated Time:** 5-15 minutes (depending on file size and download speed)
**Priority:** HIGH - IMO data provides global coverage we don't have yet
**Expected Records:** 1,668+ (confirmed from your search)
