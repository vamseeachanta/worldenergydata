# NTSB CAROL Manual Export Guide

The automated NTSB CAROL API acquisition was unable to connect.
Follow these steps to manually export marine investigation data.

## Steps

1. **Open CAROL Query Builder**
   Navigate to: https://data.ntsb.gov/carol-main-public/query-builder

2. **Set Search Criteria**
   - Mode: **Marine**
   - Date Range: 2001-01-01 to present
   - Leave other fields empty for all results

3. **Execute Search**
   Click "Submit" to run the query

4. **Export Results**
   - Click "Export" or "Download" button
   - Select CSV format
   - Save as `ntsb_marine_investigations.csv`

5. **Place File**
   Copy the downloaded CSV to:
   `data/modules/marine_safety/raw/ntsb/ntsb_marine_investigations.csv`

6. **Process the Export**
   Run the processing command:
   ```bash
   uv run python -c "
   from worldenergydata.marine_safety.acquirers.ntsb_carol_acquirer import NTSBCAROLAcquirer
   acquirer = NTSBCAROLAcquirer(output_dir='data/modules/marine_safety/raw/ntsb')
   acquirer.process_export('data/modules/marine_safety/raw/ntsb/ntsb_marine_investigations.csv')
   "
   ```

## Expected CAROL CSV Columns

The CAROL export typically includes:
- NTSB Number / MKEY
- Event Date
- City, State, Country
- Mode (should be "Marine")
- Event Type / Accident Type
- Vessel Name, Vessel Type
- Fatalities, Injuries
- Status
- Probable Cause / Synopsis

## Alternative: NTSB Data Download

NTSB also provides downloadable datasets at:
https://data.ntsb.gov/avdata

While primarily aviation-focused, check for marine data availability.
