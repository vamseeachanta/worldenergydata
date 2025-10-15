# How to Download Marine Casualty Data

**Quick Reference Guide**

---

## 🎯 Option 1: USCG MISLE Database (RECOMMENDED)

### What You'll Get:
- **40+ years** of marine casualty data (1982-2015+)
- **50,000-100,000+** incident records
- **Official USCG** investigation data
- **Comprehensive** coverage of US waters

### Download Steps:

**Step 1:** Open your web browser and navigate to:
```
https://homeport.uscg.mil/missions/investigations/marine-casualty-pollution-investigations
```

**Step 2:** On the page, look for section titled:
"Marine Casualty and Pollution Data for Researchers"

**Step 3:** Download these files:
- ☐ **File 1:** Historical data (pre-2002) - 64 MB
- ☐ **File 2:** **MISLE_DATA.zip** ⭐ PRIMARY FILE (2002-2015)
- ☐ **File 3:** Additional data (if available)

**Step 4:** Save files to your computer in this directory structure:
```
worldenergydata/
└── data/
    └── modules/
        └── marine_safety/
            └── raw/
                └── uscg/
                    ├── MISLE_DATA.zip
                    └── [other files]
```

**Step 5:** Extract the ZIP file:
```bash
cd data/modules/marine_safety/raw/uscg/
unzip MISLE_DATA.zip
```

You should now have CSV or database files that can be imported.

---

## 🎯 Option 2: NTSB CAROL Database

### What You'll Get:
- **Recent data** (2010-2024)
- **Detailed investigations** by NTSB
- **Major incidents** with full reports
- **CSV export** capability

### Download Steps:

**Step 1:** Navigate to NTSB CAROL:
```
https://data.ntsb.gov/carol-main-public/basic-search
```

**Step 2:** Set search parameters:
- **Investigation Type:** Marine
- **Date Range:** 2010-01-01 to [today's date]
- **Location:** United States (or select specific states)

**Step 3:** Click "Search" button

**Step 4:** Review results and click "Download Summary (CSV)"

**Step 5:** Save file as:
```
data/modules/marine_safety/raw/ntsb/ntsb_marine_[date].csv
```

---

## 🚀 After Downloading: Import to Database

### For USCG MISLE Data:

**Preview the data first:**
```bash
python scripts/import_misle_data.py data/modules/marine_safety/raw/uscg/[FILENAME].csv --preview
```

**Import first 100 records (test):**
```bash
python scripts/import_misle_data.py data/modules/marine_safety/raw/uscg/[FILENAME].csv --limit 100
```

**Import all data:**
```bash
python scripts/import_misle_data.py data/modules/marine_safety/raw/uscg/[FILENAME].csv
```

### Expected Output:
```
================================================================================
USCG MISLE DATA IMPORT
================================================================================

Source file: data/modules/marine_safety/raw/uscg/MISLE_DATA.csv
File size: 125,456,789 bytes

Database: data/modules/marine_safety/database/marine_safety.db

IMPORT MODE
--------------------------------------------------------------------------------
Limit: None (importing all records)
Batch size: 100

Starting import...

================================================================================
IMPORT COMPLETE
================================================================================

Statistics:
  Total records processed: 75,432
  Successfully imported: 75,129
  Skipped (invalid): 203
  Duplicates: 100
  Errors: 0

Success rate: 99.6%

Database totals:
  Incidents: 75,129
  Locations: 45,678
  Vessels: 38,945
```

---

## 📊 Verify Import Success

**Check total incident count:**
```bash
python -c "
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd() / 'src'))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session
from worldenergydata.modules.marine_safety.database.models import Incident, Vessel, Location

db_path = Path('data/modules/marine_safety/database/marine_safety.db')
engine = create_engine(f'sqlite:///{db_path}', echo=False)
session = Session(engine)

incidents = session.query(func.count(Incident.incident_id)).scalar()
vessels = session.query(func.count(Vessel.vessel_id)).scalar()
locations = session.query(func.count(Location.location_id)).scalar()

print(f'✅ Database contains:')
print(f'   Incidents: {incidents:,}')
print(f'   Vessels: {vessels:,}')
print(f'   Locations: {locations:,}')

session.close()
"
```

---

## ❓ Troubleshooting

### Problem: Can't access USCG Homeport website

**Solution 1:** Try Data.gov portal instead:
```
https://data.gov/maritime/safety-at-sea-us-coast-guard-marine-casualty-and-pollution-data-for-researchers/
```

**Solution 2:** Contact USCG directly for data:
- Email Office of Investigations and Casualty Analysis
- Request updated MISLE data extract

**Solution 3:** File FOIA request:
- Submit via USCG FOIA portal
- Request "Marine casualty data from MISLE database 2015-2024"

### Problem: Import script shows errors

**Check:**
1. Is the CSV file in the correct format?
   ```bash
   head -n 5 data/modules/marine_safety/raw/uscg/[FILENAME].csv
   ```

2. Are field names uppercase?
   - MISLE importer expects uppercase field names
   - First row should be headers

3. Is the file comma-delimited?
   - Script auto-detects comma or tab delimiters
   - Other formats not supported

**Solution:**
If format is wrong, you may need to preprocess the file or adjust the importer.

### Problem: Many records skipped or errors

**Common causes:**
1. Missing required fields (CASENUMBER, ACTIVITY_DATE)
2. Invalid dates or coordinates
3. Unknown incident/vessel types

**View logs:**
The import script logs warnings for each skipped record. Review to see patterns.

### Problem: Import is very slow

**Expected times:**
- **10,000 records:** ~2 minutes
- **50,000 records:** ~10 minutes
- **100,000 records:** ~20 minutes

**Speed up:**
- Increase batch size: `--batch-size 500`
- Use faster storage (SSD vs HDD)
- Close other applications

---

## ✅ Success Checklist

After downloading and importing data, you should have:

- [ ] Downloaded MISLE_DATA.zip from USCG Homeport
- [ ] Extracted CSV/database files
- [ ] Previewed data to verify format
- [ ] Imported data with 95%+ success rate
- [ ] Verified database contains expected number of incidents
- [ ] Checked sample incidents look correct
- [ ] (Optional) Downloaded NTSB data for 2015-2024
- [ ] (Optional) Set up quarterly update schedule

---

## 📞 Need Help?

1. **Check logs:** Import script displays detailed error messages
2. **Review field mappings:** See `src/worldenergydata/modules/marine_safety/importers/misle_importer.py`
3. **Test with sample:** We have 15 test records in `data/modules/marine_safety/raw/misle/sample_misle_data.csv`

---

**The import system is production-ready. You just need to get the data files!** 🚀

**Estimated total time:** 30-60 minutes (including download, extract, import, verify)
