#!/usr/bin/env python3
"""
Industrial Maritime Dataset Downloader
Downloads high-priority industrial maritime incident datasets
"""

import os
import requests
import json
from datetime import datetime
from pathlib import Path
import time

BASE_DIR = Path("/mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw")
DOWNLOAD_LOG = []

def log_download(source, status, details):
    """Log download attempt"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "status": status,
        "details": details
    }
    DOWNLOAD_LOG.append(entry)
    print(f"[{status}] {source}: {details}")

def download_file(url, filepath, timeout=60):
    """Download a file with error handling"""
    try:
        print(f"Downloading: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = os.path.getsize(filepath)
        return True, f"Downloaded {file_size:,} bytes"
    except Exception as e:
        return False, str(e)

def download_osha_data():
    """Download OSHA Maritime Fatality Data"""
    source = "OSHA Maritime"
    target_dir = BASE_DIR / "osha_maritime"

    # OSHA Enforcement Data API
    urls = [
        {
            "name": "OSHA_Fatality_Inspection_Data.json",
            "url": "https://www.osha.gov/fatalities/export",
            "type": "json"
        },
        {
            "name": "OSHA_Maritime_Inspections.json",
            "url": "https://enforcedata.dol.gov/views/data_summary.php",
            "type": "api"
        }
    ]

    for url_info in urls:
        filepath = target_dir / url_info["name"]
        success, details = download_file(url_info["url"], filepath)
        log_download(source, "SUCCESS" if success else "FAILED",
                    f"{url_info['name']}: {details}")
        time.sleep(2)

def download_phmsa_pipeline_data():
    """Download DOE/PHMSA Offshore Pipeline Incidents"""
    source = "PHMSA Pipelines"
    target_dir = BASE_DIR / "doe_pipelines"

    # PHMSA Data Download URLs
    urls = [
        {
            "name": "offshore_pipeline_incidents.zip",
            "url": "https://www.phmsa.dot.gov/sites/phmsa.dot.gov/files/2024-01/offshore_incident_data.zip"
        },
        {
            "name": "distribution_transmission_gathering.zip",
            "url": "https://www.phmsa.dot.gov/sites/phmsa.dot.gov/files/2024-01/distribution_transmission_gathering.zip"
        }
    ]

    for url_info in urls:
        filepath = target_dir / url_info["name"]
        success, details = download_file(url_info["url"], filepath)
        log_download(source, "SUCCESS" if success else "FAILED",
                    f"{url_info['name']}: {details}")
        time.sleep(2)

def download_phmsa_hazmat_data():
    """Download PHMSA Hazardous Materials Incidents"""
    source = "PHMSA Hazmat"
    target_dir = BASE_DIR / "phmsa_hazmat"

    # PHMSA Hazmat incident data
    urls = [
        {
            "name": "hazmat_incidents_10_years.csv",
            "url": "https://portal.phmsa.dot.gov/analytics/saw.dll?Download"
        }
    ]

    for url_info in urls:
        filepath = target_dir / url_info["name"]
        success, details = download_file(url_info["url"], filepath)
        log_download(source, "SUCCESS" if success else "FAILED",
                    f"{url_info['name']}: {details}")

def download_epa_nrc_data():
    """Download EPA National Response Center Data"""
    source = "EPA NRC"
    target_dir = BASE_DIR / "epa_nrc"

    log_download(source, "INFO",
                "NRC data requires FOIA request or web scraping. Already have NOAA INC data.")

def download_imca_dp_reports():
    """Download IMCA DP Incident Database Reports"""
    source = "IMCA DP"
    target_dir = BASE_DIR / "imca_dp"

    # Annual DP incident reports (public PDFs)
    years = [2020, 2021, 2022, 2023, 2024]
    base_url = "https://www.imca-int.com/wp-content/uploads/2024/01/"

    for year in years:
        filename = f"IMCA_DP_Annual_Summary_{year}.pdf"
        url = f"{base_url}{filename}"
        filepath = target_dir / filename
        success, details = download_file(url, filepath)
        log_download(source, "SUCCESS" if success else "FAILED",
                    f"{filename}: {details}")
        time.sleep(1)

def download_ilo_seafarer_data():
    """Download ILO Seafarer Deaths Register"""
    source = "ILO Seafarer Deaths"
    target_dir = BASE_DIR / "ilo_seafarer_deaths"

    # ILO Statistics Database
    log_download(source, "INFO",
                "ILO data requires database query at https://ilostat.ilo.org/. Manual access needed.")

def download_emsa_reports():
    """Download EMSA Annual Reports"""
    source = "EMSA Reports"
    target_dir = BASE_DIR / "emsa_reports"

    # EMSA Annual Overview Reports
    years = [2020, 2021, 2022, 2023]

    for year in years:
        filename = f"EMSA_Annual_Overview_{year}.pdf"
        url = f"https://www.emsa.europa.eu/publications/item/4000-annual-overview-of-marine-casualties-{year}.html"
        filepath = target_dir / filename
        log_download(source, "INFO",
                    f"{filename}: Manual download required from EMSA website")

def download_paris_mou_data():
    """Download Paris MOU Port State Control Data"""
    source = "Paris MOU"
    target_dir = BASE_DIR / "paris_mou"

    log_download(source, "INFO",
                "Paris MOU inspection database requires registration at https://www.parismou.org/")

def download_imo_gisis_data():
    """Download IMO GISIS Data"""
    source = "IMO GISIS"
    target_dir = BASE_DIR / "imo_gisis"

    log_download(source, "INFO",
                "IMO GISIS requires registration at https://gisis.imo.org/")

def create_readme(source_dir, content):
    """Create README.md for data source"""
    readme_path = source_dir / "README.md"
    with open(readme_path, 'w') as f:
        f.write(content)

def main():
    """Main download orchestrator"""
    print("=" * 80)
    print("INDUSTRIAL MARITIME DATASET DOWNLOADER")
    print("=" * 80)
    print(f"Base directory: {BASE_DIR}")
    print(f"Start time: {datetime.now().isoformat()}")
    print("=" * 80)

    # Priority Tier 1 Downloads
    print("\n[TIER 1] OSHA Maritime Data")
    download_osha_data()

    print("\n[TIER 1] PHMSA Pipeline Data")
    download_phmsa_pipeline_data()

    print("\n[TIER 1] PHMSA Hazmat Data")
    download_phmsa_hazmat_data()

    print("\n[TIER 1] EPA NRC Data")
    download_epa_nrc_data()

    print("\n[TIER 1] IMCA DP Reports")
    download_imca_dp_reports()

    print("\n[TIER 1] ILO Seafarer Data")
    download_ilo_seafarer_data()

    # Lower Priority
    print("\n[TIER 2] EMSA Reports")
    download_emsa_reports()

    print("\n[TIER 2] Paris MOU Data")
    download_paris_mou_data()

    print("\n[TIER 2] IMO GISIS Data")
    download_imo_gisis_data()

    # Save download log
    log_file = BASE_DIR / "download_log.json"
    with open(log_file, 'w') as f:
        json.dump(DOWNLOAD_LOG, f, indent=2)

    print("\n" + "=" * 80)
    print(f"Download log saved to: {log_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
