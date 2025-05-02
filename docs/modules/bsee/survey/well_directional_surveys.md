# Extracting Full Directional Surveys Data

This guide explains how to extract full directional surveys data by modifying and running the required scripts.

---

## Steps to Extract Data

### 1. Enable the Required Data Source
Edit the test configuration file:  
```
tests/modules/bsee/data/dwnld_from_zipurl.yml
```
- **Uncomment** the `dsptsdelimit` link in yaml file

---

### 2. Run the Test
Once the configuration is updated, execute the test to download the ZIP file.

---

### 3. Load the ZIP File
Modify and run the script:  
```
src/worldenergydata/modules/zip_data_dwnld/dwnld_from_zipurl.py
```

- Ensure the ZIP file is loaded correctly.  
- If columns exist, **pass `None` as the column names parameter**.  

---

### 4. Pass Data to ZIP Template
After loading the ZIP file, pass the extracted data to the ZIP template in:  
```
Asset Utilities Module (assetutilities)
```

---

## Code guide for Loading ZIP File


```python
from assetutilities.modules.zip_utilities.read_zip_to_df import ReadZiptoDf

rziptodf = ReadZiptoDf()

# Read ZIP file as bytes
with open(zip_filepath, "rb") as f:
    zip_bytes = f.read()

# Set column names to None if columns exist
column_names = None
df = rziptodf.zip_to_dataframes(zip_bytes, column_names)

```

---
