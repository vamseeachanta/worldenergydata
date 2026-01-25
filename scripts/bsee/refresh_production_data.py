#!/usr/bin/env python3
# ABOUTME: Download and refresh BSEE OGOR-A production data from data.bsee.gov
# ABOUTME: Uses browser automation (Playwright) since BSEE site requires JavaScript

"""
BSEE Production Data Refresh Script

Downloads OGOR-A (Oil and Gas Operations Report - Part A) production data
from the BSEE Data Center. Supports downloading specific years or refreshing
the latest available data.

Usage:
    python refresh_production_data.py                    # Download current + previous year
    python refresh_production_data.py --years 2024 2025  # Download specific years
    python refresh_production_data.py --all              # Download all years (1996-current)
    python refresh_production_data.py --list             # List available files without downloading

Data Source: https://www.data.bsee.gov/Main/OGOR-A.aspx
"""

import argparse
import os
import sys
import zipfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Ensure playwright is available
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Installing playwright...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright", "-q"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


# Configuration
BSEE_OGOR_URL = "https://www.data.bsee.gov/Main/OGOR-A.aspx"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent / "data/modules/bsee/zip/historical_production_yearly"
DOWNLOAD_TIMEOUT = 60000  # 60 seconds


def get_script_dir() -> Path:
    """Get the directory containing this script."""
    return Path(__file__).parent.resolve()


def get_project_root() -> Path:
    """Get the project root directory."""
    return get_script_dir().parent.parent


def log(message: str, level: str = "INFO"):
    """Print a log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    colors = {
        "INFO": "\033[0;34m",    # Blue
        "SUCCESS": "\033[0;32m", # Green
        "WARNING": "\033[1;33m", # Yellow
        "ERROR": "\033[0;31m",   # Red
    }
    reset = "\033[0m"
    color = colors.get(level, "")
    print(f"{color}[{timestamp}] [{level}] {message}{reset}")


def verify_zip_file(filepath: Path) -> bool:
    """Verify that a file is a valid ZIP archive."""
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            # Check if it has at least one file
            if len(zf.namelist()) > 0:
                return True
    except (zipfile.BadZipFile, Exception):
        pass
    return False


def get_available_files(page) -> List[Dict]:
    """
    Parse the BSEE OGOR-A page to find available download files.

    Returns list of dicts with: year, last_updated, fixed_url, delimit_url, description
    """
    files = []

    # Find all table rows with OGOR-A Production files
    rows = page.query_selector_all('tr')

    for row in rows:
        try:
            # Look for rows containing "OGOR-A Production"
            text = row.inner_text()
            if "OGOR-A Production" not in text:
                continue

            cells = row.query_selector_all('td')
            if len(cells) < 5:
                continue

            # Extract year from file name (e.g., "OGOR-A Production 2024")
            file_name = cells[0].inner_text().strip()
            year_str = file_name.replace("OGOR-A Production", "").strip()

            try:
                year = int(year_str)
            except ValueError:
                continue

            # Get last updated
            last_updated = cells[1].inner_text().strip()

            # Get download links
            fixed_link = cells[2].query_selector('a')
            delimit_link = cells[3].query_selector('a')

            fixed_url = fixed_link.get_attribute('href') if fixed_link else None
            delimit_url = delimit_link.get_attribute('href') if delimit_link else None

            # Get description
            description = cells[4].inner_text().strip() if len(cells) > 4 else ""

            files.append({
                'year': year,
                'last_updated': last_updated,
                'fixed_url': fixed_url,
                'delimit_url': delimit_url,
                'description': description,
            })

        except Exception as e:
            continue

    return sorted(files, key=lambda x: x['year'], reverse=True)


def download_file(page, url: str, download_dir: Path, timeout: int = DOWNLOAD_TIMEOUT) -> Optional[Path]:
    """
    Download a file by clicking its link.

    Returns the path to the downloaded file, or None if download failed.
    """
    try:
        # Set up download handling
        with page.expect_download(timeout=timeout) as download_info:
            # Navigate to the download URL (triggers download)
            page.goto(f"https://www.data.bsee.gov{url}" if url.startswith('/') else url)

        download = download_info.value

        # Save to download directory
        dest_path = download_dir / download.suggested_filename
        download.save_as(dest_path)

        return dest_path

    except PlaywrightTimeout:
        log(f"Download timed out for {url}", "ERROR")
        return None
    except Exception as e:
        log(f"Download failed for {url}: {e}", "ERROR")
        return None


def download_via_click(page, link_ref: str, download_dir: Path, timeout: int = DOWNLOAD_TIMEOUT) -> Optional[Path]:
    """
    Download a file by clicking a link element.

    Returns the path to the downloaded file, or None if download failed.
    """
    try:
        link = page.query_selector(f'a[href*="{link_ref}"]')
        if not link:
            log(f"Link not found: {link_ref}", "ERROR")
            return None

        with page.expect_download(timeout=timeout) as download_info:
            link.click()

        download = download_info.value
        dest_path = download_dir / download.suggested_filename
        download.save_as(dest_path)

        return dest_path

    except PlaywrightTimeout:
        log(f"Download timed out for {link_ref}", "ERROR")
        return None
    except Exception as e:
        log(f"Download failed for {link_ref}: {e}", "ERROR")
        return None


def refresh_production_data(
    years: Optional[List[int]] = None,
    output_dir: Optional[Path] = None,
    download_all: bool = False,
    list_only: bool = False,
    file_type: str = "delimit",
) -> Dict:
    """
    Main function to refresh BSEE production data.

    Args:
        years: List of years to download. If None, downloads current + previous year.
        output_dir: Directory to save files. Defaults to BSEE zip directory.
        download_all: If True, download all available years.
        list_only: If True, only list available files without downloading.
        file_type: Type of file to download: "delimit" or "fixed"

    Returns:
        Dict with download results: {'downloaded': [...], 'failed': [...], 'available': [...]}
    """
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create temp download directory
    temp_dir = output_dir / ".temp_downloads"
    temp_dir.mkdir(exist_ok=True)

    results = {
        'downloaded': [],
        'failed': [],
        'available': [],
        'skipped': [],
    }

    log("Starting BSEE Production Data Refresh")
    log(f"Output directory: {output_dir}")

    with sync_playwright() as p:
        # Launch browser
        log("Launching browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        # Navigate to OGOR-A page
        log(f"Navigating to {BSEE_OGOR_URL}")
        page.goto(BSEE_OGOR_URL, timeout=60000)
        page.wait_for_load_state('networkidle')

        # Get available files
        log("Parsing available files...")
        available_files = get_available_files(page)
        results['available'] = available_files

        if not available_files:
            log("No files found on BSEE page", "ERROR")
            browser.close()
            return results

        log(f"Found {len(available_files)} years of data available", "SUCCESS")

        # List mode
        if list_only:
            log("\nAvailable OGOR-A Production Files:")
            print("-" * 100)
            print(f"{'Year':<6} {'Last Updated':<22} {'Description':<50}")
            print("-" * 100)
            for f in available_files:
                print(f"{f['year']:<6} {f['last_updated']:<22} {f['description'][:50]:<50}")
            print("-" * 100)
            browser.close()
            return results

        # Determine which years to download
        if download_all:
            target_years = [f['year'] for f in available_files]
        elif years:
            target_years = years
        else:
            # Default: current year + previous year
            current_year = datetime.now().year
            target_years = [current_year, current_year - 1]

        log(f"Target years: {target_years}")

        # Download each year
        for year in target_years:
            # Find file info for this year
            file_info = next((f for f in available_files if f['year'] == year), None)

            if not file_info:
                log(f"Year {year} not available", "WARNING")
                results['failed'].append({'year': year, 'reason': 'not available'})
                continue

            url_key = f"{file_type}_url"
            download_url = file_info.get(url_key)

            if not download_url:
                log(f"No {file_type} URL for year {year}", "WARNING")
                results['failed'].append({'year': year, 'reason': f'no {file_type} URL'})
                continue

            log(f"Downloading {year} ({file_type})...")

            # Download via clicking the link
            downloaded_path = download_via_click(page, download_url.split('/')[-1], temp_dir)

            if downloaded_path and downloaded_path.exists():
                # Verify it's a valid ZIP
                if verify_zip_file(downloaded_path):
                    # Determine target filename
                    if year == datetime.now().year:
                        # Current year file might be named without year
                        target_name = f"ogora{year}delimit.zip" if file_type == "delimit" else f"ogora{year}fixed.zip"
                    else:
                        target_name = downloaded_path.name
                        # Ensure year is in filename
                        if str(year) not in target_name:
                            target_name = f"ogora{year}delimit.zip" if file_type == "delimit" else f"ogora{year}fixed.zip"

                    target_path = output_dir / target_name

                    # Move file to final location
                    shutil.move(str(downloaded_path), str(target_path))

                    # Get file info
                    file_size = target_path.stat().st_size
                    with zipfile.ZipFile(target_path, 'r') as zf:
                        uncompressed_size = sum(f.file_size for f in zf.filelist)

                    log(f"✓ Downloaded {year}: {target_name} ({file_size:,} bytes)", "SUCCESS")
                    results['downloaded'].append({
                        'year': year,
                        'path': str(target_path),
                        'size': file_size,
                        'uncompressed_size': uncompressed_size,
                        'last_updated': file_info['last_updated'],
                        'description': file_info['description'],
                    })
                else:
                    log(f"Downloaded file for {year} is not a valid ZIP", "ERROR")
                    downloaded_path.unlink(missing_ok=True)
                    results['failed'].append({'year': year, 'reason': 'invalid ZIP'})
            else:
                log(f"Failed to download {year}", "ERROR")
                results['failed'].append({'year': year, 'reason': 'download failed'})

        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

        browser.close()

    # Print summary
    log("\n" + "=" * 60)
    log("BSEE Production Data Refresh Summary")
    log("=" * 60)
    log(f"Downloaded: {len(results['downloaded'])} files", "SUCCESS")

    for item in results['downloaded']:
        log(f"  • {item['year']}: {Path(item['path']).name} ({item['size']:,} bytes)")

    if results['failed']:
        log(f"Failed: {len(results['failed'])} files", "ERROR")
        for item in results['failed']:
            log(f"  • {item['year']}: {item['reason']}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Refresh BSEE OGOR-A production data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Download current + previous year
  %(prog)s --years 2024 2025    # Download specific years
  %(prog)s --all                # Download all years (1996-current)
  %(prog)s --list               # List available files
  %(prog)s --output /path/to/dir  # Custom output directory
        """
    )

    parser.add_argument(
        '--years', '-y',
        type=int,
        nargs='+',
        help='Specific years to download'
    )

    parser.add_argument(
        '--all', '-a',
        action='store_true',
        dest='download_all',
        help='Download all available years'
    )

    parser.add_argument(
        '--list', '-l',
        action='store_true',
        dest='list_only',
        help='List available files without downloading'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f'Output directory (default: {DEFAULT_OUTPUT_DIR})'
    )

    parser.add_argument(
        '--type', '-t',
        choices=['delimit', 'fixed'],
        default='delimit',
        help='File type to download (default: delimit)'
    )

    args = parser.parse_args()

    results = refresh_production_data(
        years=args.years,
        output_dir=args.output,
        download_all=args.download_all,
        list_only=args.list_only,
        file_type=args.type,
    )

    # Exit with error if any downloads failed
    if results['failed'] and not args.list_only:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
