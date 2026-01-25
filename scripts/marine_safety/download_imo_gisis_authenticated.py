#!/usr/bin/env python3
"""
IMO GISIS Marine Casualties Data Downloader (Authenticated)

This script automates downloading yearly marine casualty data from
the IMO GISIS database (https://gisis.imo.org/Public/MCIR/Search.aspx)

Requirements:
- Valid IMO Web Accounts credentials
- Selenium with Chrome/Chromium webdriver
- Internet connection

Usage:
    python download_imo_gisis_authenticated.py --username YOUR_EMAIL --password YOUR_PASSWORD

Or set environment variables:
    export IMO_USERNAME="your_email@domain.com"
    export IMO_PASSWORD="your_password"
    python download_imo_gisis_authenticated.py
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class IMOGISISDownloader:
    """Automated downloader for IMO GISIS marine casualty data"""

    def __init__(self, username, password, output_dir=None, headless=True):
        self.username = username
        self.password = password
        self.base_url = "https://gisis.imo.org/Public/MCIR/Search.aspx"
        self.login_url = "https://webaccounts.imo.org/"
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent.parent / "data/modules/marine_safety/raw/imo_gisis"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.driver = None
        self.download_summary = {
            "download_date": datetime.now().isoformat(),
            "username": username,
            "total_files": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "results": []
        }

    def setup_driver(self):
        """Initialize Chrome webdriver with appropriate options"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Set download directory
        prefs = {
            "download.default_directory": str(self.output_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            print("✅ Chrome webdriver initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize Chrome webdriver: {e}")
            print("\nTroubleshooting:")
            print("1. Install Chrome/Chromium: sudo apt install chromium-browser")
            print("2. Install chromedriver: sudo apt install chromium-chromedriver")
            print("3. Or use pip: pip install webdriver-manager")
            return False

    def login(self):
        """Authenticate with IMO Web Accounts"""
        try:
            print(f"\n🔐 Logging in to IMO Web Accounts...")
            print(f"   Username: {self.username}")

            # Navigate to GISIS (will redirect to login)
            self.driver.get(self.base_url)
            time.sleep(3)

            # Wait for login form
            wait = WebDriverWait(self.driver, 20)

            # Try to find username/email field (various possible selectors)
            username_selectors = [
                (By.ID, "username"),
                (By.ID, "email"),
                (By.NAME, "username"),
                (By.NAME, "email"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[type='text']")
            ]

            username_field = None
            for selector_type, selector_value in username_selectors:
                try:
                    username_field = wait.until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    print(f"   Found username field: {selector_type}={selector_value}")
                    break
                except TimeoutException:
                    continue

            if not username_field:
                print("❌ Could not find username/email input field")
                self.save_page_source("login_page_error.html")
                return False

            # Enter username
            username_field.clear()
            username_field.send_keys(self.username)
            print("   ✓ Username entered")

            # Find password field
            password_selectors = [
                (By.ID, "password"),
                (By.NAME, "password"),
                (By.CSS_SELECTOR, "input[type='password']")
            ]

            password_field = None
            for selector_type, selector_value in password_selectors:
                try:
                    password_field = self.driver.find_element(selector_type, selector_value)
                    print(f"   Found password field: {selector_type}={selector_value}")
                    break
                except NoSuchElementException:
                    continue

            if not password_field:
                print("❌ Could not find password input field")
                self.save_page_source("login_page_error.html")
                return False

            # Enter password
            password_field.clear()
            password_field.send_keys(self.password)
            print("   ✓ Password entered")

            # Find and click login button
            login_button_selectors = [
                (By.ID, "submit"),
                (By.ID, "login"),
                (By.NAME, "submit"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Sign in')]"),
                (By.XPATH, "//button[contains(text(), 'Login')]"),
                (By.XPATH, "//input[@value='Sign in']"),
                (By.XPATH, "//input[@value='Login']")
            ]

            login_button = None
            for selector_type, selector_value in login_button_selectors:
                try:
                    login_button = self.driver.find_element(selector_type, selector_value)
                    print(f"   Found login button: {selector_type}={selector_value}")
                    break
                except NoSuchElementException:
                    continue

            if not login_button:
                print("❌ Could not find login button")
                self.save_page_source("login_page_error.html")
                return False

            # Click login
            login_button.click()
            print("   ✓ Login button clicked")

            # Wait for redirect back to GISIS
            time.sleep(5)

            # Check if we're back at GISIS search page
            if "MCIR/Search.aspx" in self.driver.current_url or "gisis.imo.org" in self.driver.current_url:
                print("✅ Successfully logged in to IMO GISIS")
                return True
            else:
                print(f"⚠️  Unexpected URL after login: {self.driver.current_url}")
                self.save_page_source("post_login_page.html")
                return False

        except Exception as e:
            print(f"❌ Login failed: {e}")
            self.save_page_source("login_error.html")
            return False

    def save_page_source(self, filename):
        """Save current page HTML for debugging"""
        try:
            filepath = self.output_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print(f"   💾 Page source saved to: {filepath}")
        except Exception as e:
            print(f"   ⚠️  Could not save page source: {e}")

    def search_year(self, year):
        """Search for casualties in a specific year"""
        try:
            print(f"\n📅 Searching for casualties in {year}...")

            # Navigate to search page
            self.driver.get(self.base_url)
            time.sleep(2)

            wait = WebDriverWait(self.driver, 15)

            # Find date fields (they might be textboxes or date pickers)
            from_date = f"{year}-01-01"
            to_date = f"{year}-12-31"

            # Try to find "From" date field
            from_date_selectors = [
                (By.ID, "ctl00_MainContent_txtFromDate"),
                (By.ID, "txtFromDate"),
                (By.NAME, "ctl00$MainContent$txtFromDate"),
                (By.XPATH, "//input[contains(@id, 'FromDate')]")
            ]

            from_date_field = None
            for selector_type, selector_value in from_date_selectors:
                try:
                    from_date_field = wait.until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    break
                except TimeoutException:
                    continue

            if not from_date_field:
                print(f"   ⚠️  Could not find 'From Date' field")
                self.save_page_source(f"search_page_error_{year}.html")
                return None

            # Clear and set from date
            from_date_field.clear()
            from_date_field.send_keys(from_date)
            print(f"   ✓ From date set: {from_date}")

            # Find "To" date field
            to_date_selectors = [
                (By.ID, "ctl00_MainContent_txtToDate"),
                (By.ID, "txtToDate"),
                (By.NAME, "ctl00$MainContent$txtToDate"),
                (By.XPATH, "//input[contains(@id, 'ToDate')]")
            ]

            to_date_field = None
            for selector_type, selector_value in to_date_selectors:
                try:
                    to_date_field = self.driver.find_element(selector_type, selector_value)
                    break
                except NoSuchElementException:
                    continue

            if not to_date_field:
                print(f"   ⚠️  Could not find 'To Date' field")
                self.save_page_source(f"search_page_error_{year}.html")
                return None

            # Clear and set to date
            to_date_field.clear()
            to_date_field.send_keys(to_date)
            print(f"   ✓ To date set: {to_date}")

            # Ensure all casualty types are selected
            casualty_checkboxes = [
                "ctl00_MainContent_chkVerySeriousMarineCasualty",
                "ctl00_MainContent_chkMarineCasualty",
                "ctl00_MainContent_chkMarineIncident"
            ]

            for checkbox_id in casualty_checkboxes:
                try:
                    checkbox = self.driver.find_element(By.ID, checkbox_id)
                    if not checkbox.is_selected():
                        checkbox.click()
                        print(f"   ✓ Checked: {checkbox_id}")
                except NoSuchElementException:
                    print(f"   ⚠️  Checkbox not found: {checkbox_id}")

            # Find and click search button
            search_button_selectors = [
                (By.ID, "ctl00_MainContent_btnSearch"),
                (By.ID, "btnSearch"),
                (By.XPATH, "//input[@value='Search']"),
                (By.XPATH, "//button[contains(text(), 'Search')]")
            ]

            search_button = None
            for selector_type, selector_value in search_button_selectors:
                try:
                    search_button = self.driver.find_element(selector_type, selector_value)
                    break
                except NoSuchElementException:
                    continue

            if not search_button:
                print(f"   ⚠️  Could not find Search button")
                self.save_page_source(f"search_page_error_{year}.html")
                return None

            # Click search
            search_button.click()
            print(f"   ✓ Search initiated")

            # Wait for results
            time.sleep(3)

            # Check for results count
            try:
                results_text = self.driver.find_element(By.XPATH, "//*[contains(text(), 'casualties found')]").text
                print(f"   ✅ Results: {results_text}")
                return True
            except NoSuchElementException:
                print(f"   ℹ️  No results found for {year}")
                return False

        except Exception as e:
            print(f"   ❌ Search failed for {year}: {e}")
            self.save_page_source(f"search_error_{year}.html")
            return None

    def download_results(self, year):
        """Download search results as CSV"""
        try:
            print(f"\n💾 Downloading data for {year}...")

            # Find download/export button
            download_button_selectors = [
                (By.ID, "ctl00_MainContent_btnExport"),
                (By.ID, "btnExport"),
                (By.XPATH, "//input[@value='Export']"),
                (By.XPATH, "//button[contains(text(), 'Export')]"),
                (By.XPATH, "//a[contains(text(), 'Export')]"),
                (By.XPATH, "//a[contains(@title, 'Export')]"),
                (By.CSS_SELECTOR, "a.export-button"),
                (By.XPATH, "//img[contains(@title, 'Export')]/..")
            ]

            download_button = None
            for selector_type, selector_value in download_button_selectors:
                try:
                    download_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    print(f"   Found download button: {selector_type}={selector_value}")
                    break
                except TimeoutException:
                    continue

            if not download_button:
                print(f"   ⚠️  Could not find download/export button")
                self.save_page_source(f"results_page_{year}.html")
                return False

            # Click download
            download_button.click()
            print(f"   ✓ Download initiated")

            # Wait for download to complete
            time.sleep(5)

            # Verify download
            downloaded_files = list(self.output_dir.glob("*.csv"))
            if downloaded_files:
                latest_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)
                new_filename = self.output_dir / f"imo_casualties_{year}.csv"
                latest_file.rename(new_filename)
                print(f"   ✅ Downloaded: {new_filename}")
                return True
            else:
                print(f"   ⚠️  No CSV file found after download")
                return False

        except Exception as e:
            print(f"   ❌ Download failed for {year}: {e}")
            return False

    def download_year_range(self, start_year, end_year):
        """Download data for a range of years"""
        print(f"\n{'='*60}")
        print(f"IMO GISIS DATA DOWNLOAD")
        print(f"Year range: {start_year} - {end_year}")
        print(f"Output directory: {self.output_dir}")
        print(f"{'='*60}\n")

        successful = 0
        failed = 0

        for year in range(start_year, end_year + 1):
            result = {
                "year": year,
                "from_date": f"{year}-01-01",
                "to_date": f"{year}-12-31",
                "status": "unknown",
                "records": 0
            }

            # Search for year
            search_result = self.search_year(year)

            if search_result is True:
                # Results found, try to download
                if self.download_results(year):
                    result["status"] = "success"
                    successful += 1
                else:
                    result["status"] = "download_failed"
                    failed += 1
            elif search_result is False:
                # No results found
                result["status"] = "no_results"
            else:
                # Search failed
                result["status"] = "search_failed"
                failed += 1

            self.download_summary["results"].append(result)

            # Brief pause between downloads
            time.sleep(2)

        self.download_summary["total_files"] = successful + failed
        self.download_summary["successful_downloads"] = successful
        self.download_summary["failed_downloads"] = failed

        # Save summary
        self.save_download_summary()

        print(f"\n{'='*60}")
        print(f"DOWNLOAD COMPLETE")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"{'='*60}\n")

        return successful > 0

    def save_download_summary(self):
        """Save download summary to JSON file"""
        summary_file = self.output_dir / "download_summary.json"
        with open(summary_file, "w") as f:
            json.dump(self.download_summary, f, indent=2)
        print(f"\n📊 Download summary saved: {summary_file}")

    def cleanup(self):
        """Close browser and cleanup"""
        if self.driver:
            self.driver.quit()
            print("\n✅ Browser closed")

def main():
    parser = argparse.ArgumentParser(
        description="Download IMO GISIS marine casualty data"
    )
    parser.add_argument(
        "--username", "-u",
        help="IMO Web Accounts username/email",
        default=os.getenv("IMO_USERNAME")
    )
    parser.add_argument(
        "--password", "-p",
        help="IMO Web Accounts password",
        default=os.getenv("IMO_PASSWORD")
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2000,
        help="Start year (default: 2000)"
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=datetime.now().year,
        help="End year (default: current year)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory for downloaded files",
        default=None
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)"
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run browser in visible mode (overrides --headless)"
    )

    args = parser.parse_args()

    # Validate credentials
    if not args.username or not args.password:
        print("❌ Error: IMO credentials required")
        print("\nProvide credentials via:")
        print("1. Command line: --username YOUR_EMAIL --password YOUR_PASSWORD")
        print("2. Environment variables: IMO_USERNAME and IMO_PASSWORD")
        sys.exit(1)

    # Determine headless mode
    headless = args.headless and not args.visible

    # Initialize downloader
    downloader = IMOGISISDownloader(
        username=args.username,
        password=args.password,
        output_dir=args.output_dir,
        headless=headless
    )

    try:
        # Setup driver
        if not downloader.setup_driver():
            sys.exit(1)

        # Login
        if not downloader.login():
            print("\n❌ Login failed. Please check your credentials.")
            sys.exit(1)

        # Download data
        success = downloader.download_year_range(args.start_year, args.end_year)

        if success:
            print("\n✅ Download completed successfully!")
        else:
            print("\n⚠️  Download completed with errors. Check the summary for details.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        downloader.cleanup()

if __name__ == "__main__":
    main()
