#!/usr/bin/env python3
"""
Download marine safety datasets from various government sources.
"""

import requests
import json
import csv
import time
import os
from pathlib import Path

# Base directories
BASE_DIR = Path("/mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw")

def download_canadian_tsb():
    """Download Canadian TSB marine statistics data."""
    print("\n=== Downloading Canadian TSB Data ===")
    tsb_dir = BASE_DIR / "canadian_tsb"

    # TSB provides data through their statistics portal
    # Try to access the data API or CSV exports
    base_url = "https://www.tsb.gc.ca"

    # Known CSV endpoints (these may need to be verified)
    csv_files = [
        "/eng/stats/marine/data/occurrences.csv",
        "/eng/stats/marine/data/vessels.csv",
        "/eng/stats/marine/data/consequences.csv",
    ]

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    })

    for csv_file in csv_files:
        try:
            url = base_url + csv_file
            print(f"Trying: {url}")
            response = session.get(url, timeout=30)
            if response.status_code == 200:
                filename = csv_file.split('/')[-1]
                filepath = tsb_dir / filename
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"  ✓ Downloaded: {filename} ({len(response.content)} bytes)")
            else:
                print(f"  ✗ Failed: {response.status_code}")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")

    return True

def download_ntsb_marine():
    """Download NTSB marine investigation data via API."""
    print("\n=== Downloading NTSB Marine Data ===")
    ntsb_dir = BASE_DIR / "ntsb_marine"

    # NTSB CAROL database query API
    # Public access endpoint for marine investigations
    base_url = "https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/GenerateExcelReport"

    # Alternative: Try the public data API
    api_url = "https://data.ntsb.gov/carol-main-public/api/Query"

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0',
        'Content-Type': 'application/json'
    })

    # Query for marine mode investigations
    query_params = {
        "Mode": "Marine",
        "EventDateFrom": "2010-01-01",
        "EventDateTo": "2025-12-31",
        "PageSize": 1000,
        "PageNumber": 1
    }

    try:
        print(f"Querying NTSB API...")
        response = session.post(api_url, json=query_params, timeout=60)
        if response.status_code == 200:
            data = response.json()
            filepath = ntsb_dir / "ntsb_marine_query.json"
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"  ✓ Downloaded: {len(data)} records")
        else:
            print(f"  ✗ API returned: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")

    return True

def download_bsee_offshore():
    """Download BSEE offshore incident data."""
    print("\n=== Downloading BSEE Offshore Data ===")
    bsee_dir = BASE_DIR / "bsee_offshore"

    # BSEE Data Center - try known data export endpoints
    # The data.bsee.gov portal may have direct download links

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0'
    })

    # Try accessing the public data portal
    data_urls = [
        "https://www.data.bsee.gov/api/search/type/dataset",
        "https://www.data.bsee.gov/api/3/action/package_search?q=incidents",
    ]

    for url in data_urls:
        try:
            print(f"Trying: {url}")
            response = session.get(url, timeout=30)
            if response.status_code == 200:
                filename = f"bsee_data_{url.split('/')[-1].replace('?', '_')[:30]}.json"
                filepath = bsee_dir / filename
                with open(filepath, 'w') as f:
                    f.write(response.text)
                print(f"  ✓ Downloaded metadata")

                # Parse to find actual data download links
                try:
                    data = response.json()
                    print(f"  Found {len(data)} items")
                except:
                    pass
            else:
                print(f"  ✗ Failed: {response.status_code}")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")

    return True

def download_niosh_cfid_github():
    """Try alternative GitHub repositories for NIOSH CFID data."""
    print("\n=== Downloading NIOSH CFID Data ===")
    niosh_dir = BASE_DIR / "niosh_cfid"

    # Try the actual Data Liberation Project releases
    github_urls = [
        "https://raw.githubusercontent.com/data-liberation-project/niosh-commercial-fishing-incident-database/main/data/cfid_persons.csv",
        "https://raw.githubusercontent.com/data-liberation-project/niosh-commercial-fishing-incident-database/main/data/cfid_incidents.csv",
        "https://raw.githubusercontent.com/data-liberation-project/niosh-commercial-fishing-incident-database/main/data/cfid_vessels.csv",
    ]

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0'
    })

    for url in github_urls:
        try:
            print(f"Trying: {url}")
            response = session.get(url, timeout=30)
            if response.status_code == 200:
                filename = url.split('/')[-1]
                filepath = niosh_dir / filename
                with open(filepath, 'wb') as f:
                    f.write(response.content)

                # Count records if CSV
                if filename.endswith('.csv'):
                    lines = response.content.decode('utf-8').count('\n')
                    print(f"  ✓ Downloaded: {filename} ({lines} records)")
                else:
                    print(f"  ✓ Downloaded: {filename}")
            else:
                print(f"  ✗ Failed: {response.status_code}")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")

    return True

def main():
    """Run all download functions."""
    print("=" * 70)
    print("MARINE SAFETY DATA ACQUISITION")
    print("=" * 70)

    # Run downloads
    download_canadian_tsb()
    time.sleep(2)

    download_niosh_cfid_github()
    time.sleep(2)

    download_ntsb_marine()
    time.sleep(2)

    download_bsee_offshore()

    print("\n" + "=" * 70)
    print("Download process complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
