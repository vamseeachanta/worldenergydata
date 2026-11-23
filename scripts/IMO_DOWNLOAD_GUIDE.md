# IMO GISIS Data Download Guide

## Quick Start

### 1. Install Dependencies

```bash
cd /mnt/github/workspace-hub/worldenergydata

# Install Python requirements
pip install -r scripts/requirements_imo_download.txt

# Install Chrome/Chromium and chromedriver
sudo apt update
sudo apt install chromium-browser chromium-chromedriver
```

### 2. Set Up Credentials

**Option A: Environment Variables (Recommended)**
```bash
export IMO_USERNAME="your_email@domain.com"
export IMO_PASSWORD="your_password"
```

**Option B: Command Line Arguments**
```bash
# Pass credentials directly (less secure)
python scripts/download_imo_gisis_authenticated.py \
    --username "your_email@domain.com" \
    --password "your_password"
```

### 3. Run Download

**Download all years (2000-2025):**
```bash
python scripts/download_imo_gisis_authenticated.py
```

**Download specific year range:**
```bash
python scripts/download_imo_gisis_authenticated.py \
    --start-year 2015 \
    --end-year 2025
```

**Run with visible browser (for debugging):**
```bash
python scripts/download_imo_gisis_authenticated.py --visible
```

## Prerequisites

### IMO Web Account Registration

If you don't have IMO credentials yet:

1. **Visit:** https://webaccounts.imo.org/
2. **Register:** Click "Create Account" or "Register"
3. **Fill Form:**
   - Email address
   - Password
   - Organization/Institution
   - Purpose: "Research" or "Academic"
4. **Verify:** Check email for verification link
5. **Wait:** Account approval may take 1-2 business days
6. **Test:** Login at https://gisis.imo.org/

### System Requirements

- **Python:** 3.8+
- **Chrome/Chromium:** Latest stable version
- **Chromedriver:** Matching Chrome version
- **Disk Space:** ~500MB for data + 1GB for browser
- **Internet:** Stable connection (downloads may take 30-60 minutes)

## Download Options

### Command Line Arguments

```bash
python scripts/download_imo_gisis_authenticated.py --help
```

**Available options:**

| Argument | Short | Description | Default |
|----------|-------|-------------|---------|
| `--username` | `-u` | IMO username/email | `$IMO_USERNAME` |
| `--password` | `-p` | IMO password | `$IMO_PASSWORD` |
| `--start-year` | - | First year to download | `2000` |
| `--end-year` | - | Last year to download | Current year |
| `--output-dir` | `-o` | Download directory | `data/modules/marine_safety/raw/imo_gisis/` |
| `--headless` | - | Run browser hidden | `True` |
| `--visible` | - | Show browser window | `False` |

### Examples

**Download only recent years:**
```bash
python scripts/download_imo_gisis_authenticated.py \
    --start-year 2020 \
    --end-year 2025
```

**Download to custom directory:**
```bash
python scripts/download_imo_gisis_authenticated.py \
    --output-dir /path/to/custom/directory
```

**Debug mode (visible browser):**
```bash
python scripts/download_imo_gisis_authenticated.py \
    --visible \
    --start-year 2024 \
    --end-year 2024
```

## Expected Output

### File Structure

```
data/modules/marine_safety/raw/imo_gisis/
├── imo_casualties_2000.csv
├── imo_casualties_2001.csv
├── imo_casualties_2002.csv
...
├── imo_casualties_2024.csv
├── imo_casualties_2025.csv
├── download_summary.json
└── [debug HTML files if errors occur]
```

### Download Summary

After each run, a `download_summary.json` file is created:

```json
{
  "download_date": "2025-10-09T10:30:00",
  "username": "your_email@domain.com",
  "total_files": 26,
  "successful_downloads": 24,
  "failed_downloads": 2,
  "results": [
    {
      "year": 2000,
      "from_date": "2000-01-01",
      "to_date": "2000-12-31",
      "status": "success",
      "records": 245
    },
    {
      "year": 2001,
      "from_date": "2001-01-01",
      "to_date": "2001-12-31",
      "status": "no_results"
    }
  ]
}
```

### Expected Data Volume

Based on IMO GISIS coverage:

- **Per Year:** 100-300 casualties (varies by year)
- **2000-2025:** Estimated 3,000-5,000 total records
- **File Size:** 50-200KB per CSV (uncompressed)
- **Total Size:** ~5-10MB for all years

## Troubleshooting

### Browser Issues

**Error: "Chromium distribution not found"**

```bash
# Install Chromium
sudo apt install chromium-browser chromium-chromedriver

# Or use Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt install -f
```

**Error: "chromedriver not found"**

```bash
# Option 1: Install system chromedriver
sudo apt install chromium-chromedriver

# Option 2: Use webdriver-manager (automatic)
pip install webdriver-manager
```

### Authentication Issues

**Error: "Could not find username field"**

The IMO login page structure may have changed. The script will:
1. Save the HTML page to `login_page_error.html`
2. You can inspect it to find the correct field IDs
3. Update the selectors in the script if needed

**Error: "Login failed"**

1. **Check credentials:** Verify username/password are correct
2. **Test manually:** Try logging in at https://gisis.imo.org/ in a browser
3. **Account status:** Ensure your account is approved and active
4. **Run visible:** Use `--visible` flag to watch the login process

### Download Issues

**Error: "Could not find download button"**

The results page structure may have changed:
1. Script saves `results_page_YEAR.html` for inspection
2. Login manually and check if export/download button exists
3. Update the button selectors in the script if needed

**Error: "No CSV file found after download"**

1. Check the output directory manually
2. Browser download settings may need adjustment
3. Download may require manual save dialog interaction (use `--visible`)

### Rate Limiting

If you get errors after several successful downloads:

```bash
# Add delays between years (modify script)
# Or download in batches:

# Batch 1: 2000-2010
python scripts/download_imo_gisis_authenticated.py \
    --start-year 2000 --end-year 2010

# Wait 5 minutes, then batch 2: 2011-2020
python scripts/download_imo_gisis_authenticated.py \
    --start-year 2011 --end-year 2020
```

## Manual Fallback

If automated download fails completely, use manual download:

1. **Login:** https://gisis.imo.org/
2. **Navigate:** Public Access → Marine Casualties and Incidents (MCIR)
3. **For each year:**
   - Set "From Date": YYYY-01-01
   - Set "Until Date": YYYY-12-31
   - Check all casualty types
   - Click "Search"
   - Click "Export" or "Download" button
   - Save as: `imo_casualties_YYYY.csv`
4. **Move files:** Copy CSVs to `data/modules/marine_safety/raw/imo_gisis/`

## Data Validation

After download, verify the data:

```bash
cd data/modules/marine_safety/raw/imo_gisis

# Count downloaded files
ls -1 imo_casualties_*.csv | wc -l

# Check file sizes
ls -lh imo_casualties_*.csv

# Count total records (excluding headers)
for file in imo_casualties_*.csv; do
    echo "$file: $(tail -n +2 "$file" | wc -l) records"
done

# View column headers
head -1 imo_casualties_2024.csv
```

## Next Steps

After successful download:

1. **Examine Data Structure:**
   ```bash
   head -20 data/modules/marine_safety/raw/imo_gisis/imo_casualties_2024.csv
   ```

2. **Create IMO Importer:**
   - Parse CSV files
   - Map columns to database schema
   - Handle duplicates with existing data

3. **Import to Database:**
   ```bash
   python scripts/import_imo_data.py
   ```

4. **Generate Statistics:**
   - Total casualties by year
   - Casualties by type (collision, fire, grounding, etc.)
   - Geographic distribution
   - Comparison with existing data sources

## Security Notes

- **Never commit credentials** to git
- Use environment variables for sensitive data
- The script does not log passwords
- Downloaded data is stored locally only

## Support

**IMO GISIS Support:**
- Email: gisis@imo.org
- Website: https://gisis.imo.org/
- Phone: +44 (0)20 7735 7611

**Script Issues:**
- Check `download_summary.json` for detailed status
- Inspect saved HTML files in output directory
- Run with `--visible` flag to watch the process

## Advanced Usage

### Retry Failed Downloads

```bash
# Check which years failed
cat data/modules/marine_safety/raw/imo_gisis/download_summary.json | \
    jq '.results[] | select(.status != "success") | .year'

# Retry specific years
for year in 2005 2012 2018; do
    python scripts/download_imo_gisis_authenticated.py \
        --start-year $year --end-year $year
    sleep 10
done
```

### Parallel Downloads (Not Recommended)

```bash
# Download in parallel (may trigger rate limiting)
for year in {2020..2025}; do
    python scripts/download_imo_gisis_authenticated.py \
        --start-year $year --end-year $year \
        --output-dir data/imo_temp_$year/ &
done
wait
```

### Custom Modifications

The script is designed to be easily modified:

1. **Change date ranges per query:** Modify `search_year()` method
2. **Add filters:** Modify casualty type checkboxes in `search_year()`
3. **Change file format:** Modify download button selection logic
4. **Add pagination:** Implement page iteration in `download_results()`

---

**Last Updated:** 2025-10-09
**Script Version:** 1.0.0
**IMO GISIS URL:** https://gisis.imo.org/Public/MCIR/Search.aspx
