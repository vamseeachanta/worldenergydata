"""
Simple verification script for Task 10.1.3
Verify all files from zip archives are processed and written to .bin files
"""

import os
import sys
from pathlib import Path
import zipfile
from io import BytesIO

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.worldenergydata.modules.bsee.data.scrapers.bsee_web_scraper import BSEEWebScraper
from src.worldenergydata.modules.bsee.data.processors.memory_processor import MemoryProcessor

def check_well_data():
    """Check well data processing"""
    print("\n" + "="*60)
    print("Task 10.1.3.1: Verifying WELL data processing")
    print("="*60)
    
    # Download well data
    scraper = BSEEWebScraper()
    url = 'https://www.data.bsee.gov/Well/Files/APDRawData.zip'
    print(f"Downloading from {url}...")
    
    zip_data = scraper.download_zip_to_memory(url)
    if not zip_data:
        print("ERROR: Failed to download")
        return False
    
    # Check zip contents
    print("\nExpected files from zip archive:")
    expected_files = []
    with zipfile.ZipFile(BytesIO(zip_data), 'r') as zf:
        for filename in zf.namelist():
            if not filename.endswith('/'):
                base_name = Path(filename).stem
                expected_files.append(base_name)
                print(f"  - {filename} -> {base_name}.bin")
    
    # Check actual output files
    output_dir = 'data/modules/bsee/bin/apd'
    print(f"\nActual files in {output_dir}:")
    actual_files = []
    if os.path.exists(output_dir):
        for file in os.listdir(output_dir):
            if file.endswith('.bin'):
                actual_files.append(file.replace('.bin', ''))
                print(f"  - {file}")
    
    # Compare
    print("\nVerification:")
    print(f"Expected: {sorted(expected_files)}")
    print(f"Actual:   {sorted(actual_files)}")
    
    missing = set(expected_files) - set(actual_files)
    if missing:
        print(f"MISSING: {missing}")
        return False
    else:
        print("SUCCESS: All expected files are present\!")
        return True

if __name__ == "__main__":
    success = check_well_data()
    print("\n" + "="*60)
    if success:
        print("✅ Task 10.1.3.1 PASSED: Well data files verified")
    else:
        print("❌ Task 10.1.3.1 FAILED: Some files missing")
    print("="*60)
