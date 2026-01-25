#!/usr/bin/env python3
"""
IMO GISIS Data Downloader with WebDriver Manager
Uses webdriver-manager to automatically download and configure Chrome driver
No sudo or manual browser installation required!
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Get credentials from user input
print("=" * 60)
print("IMO GISIS Data Downloader")
print("=" * 60)
print()

username = input("Enter your IMO username/email: ").strip()
password = input("Enter your IMO password: ").strip()

if not username or not password:
    print("❌ Username and password are required!")
    sys.exit(1)

print()
print(f"✅ Credentials configured")
print(f"   Username: {username}")
print()

# Setup output directory
output_dir = Path(__file__).parent.parent / "data/modules/marine_safety/raw/imo_gisis"
output_dir.mkdir(parents=True, exist_ok=True)

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

prefs = {
    "download.default_directory": str(output_dir.absolute()),
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
}
chrome_options.add_experimental_option("prefs", prefs)

print("🔧 Setting up Chrome WebDriver (this may take a moment)...")

try:
    # Use webdriver-manager to automatically download and setup chromedriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    print("✅ Chrome WebDriver initialized successfully!")
except Exception as e:
    print(f"❌ Failed to initialize WebDriver: {e}")
    print()
    print("Troubleshooting:")
    print("1. Ensure you have internet connection")
    print("2. Try installing Chrome manually: sudo apt install chromium-browser")
    print("3. Or download from: https://www.google.com/chrome/")
    sys.exit(1)

print()
print("🔐 Logging in to IMO GISIS...")

try:
    # Navigate to GISIS
    driver.get("https://gisis.imo.org/Public/MCIR/Search.aspx")
    time.sleep(5)

    # Wait for login redirect
    wait = WebDriverWait(driver, 20)

    # Find username field
    username_field = None
    for selector in [("ID", "username"), ("ID", "email"), ("NAME", "username"),
                     ("CSS_SELECTOR", "input[type='email']"), ("CSS_SELECTOR", "input[type='text']")]:
        try:
            if selector[0] == "ID":
                username_field = wait.until(EC.presence_of_element_located((By.ID, selector[1])))
            elif selector[0] == "NAME":
                username_field = wait.until(EC.presence_of_element_located((By.NAME, selector[1])))
            elif selector[0] == "CSS_SELECTOR":
                username_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector[1])))
            if username_field:
                print(f"   Found username field: {selector}")
                break
        except:
            continue

    if not username_field:
        print("❌ Could not find username field")
        driver.save_screenshot(str(output_dir / "login_error.png"))
        with open(output_dir / "login_page.html", "w") as f:
            f.write(driver.page_source)
        print("   Saved login_error.png and login_page.html for debugging")
        driver.quit()
        sys.exit(1)

    username_field.clear()
    username_field.send_keys(username)
    print("   ✓ Username entered")

    # Find password field
    password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_field.clear()
    password_field.send_keys(password)
    print("   ✓ Password entered")

    # Find and click login button
    login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    login_button.click()
    print("   ✓ Login button clicked")

    # Wait for redirect
    time.sleep(5)

    if "gisis.imo.org" in driver.current_url:
        print("✅ Successfully logged in!")
    else:
        print(f"⚠️  Unexpected URL: {driver.current_url}")
        driver.save_screenshot(str(output_dir / "post_login.png"))

except Exception as e:
    print(f"❌ Login failed: {e}")
    driver.save_screenshot(str(output_dir / "login_error.png"))
    driver.quit()
    sys.exit(1)

print()
print("📅 Starting yearly data download...")
print()

# Download data year by year
results = []
successful = 0

for year in range(2000, 2026):
    try:
        print(f"Year {year}:", end=" ", flush=True)

        # Navigate to search page
        driver.get("https://gisis.imo.org/Public/MCIR/Search.aspx")
        time.sleep(2)

        # Set date range
        from_date = f"{year}-01-01"
        to_date = f"{year}-12-31"

        # Find and fill date fields
        from_field = driver.find_element(By.XPATH, "//input[contains(@id, 'FromDate')]")
        from_field.clear()
        from_field.send_keys(from_date)

        to_field = driver.find_element(By.XPATH, "//input[contains(@id, 'ToDate')]")
        to_field.clear()
        to_field.send_keys(to_date)

        # Click search
        search_btn = driver.find_element(By.XPATH, "//input[@value='Search']")
        search_btn.click()
        time.sleep(3)

        # Check for results
        try:
            results_text = driver.find_element(By.XPATH, "//*[contains(text(), 'casualties found')]").text
            print(f"{results_text}", end="", flush=True)

            # Try to download
            try:
                export_btn = driver.find_element(By.XPATH, "//input[@value='Export']")
                export_btn.click()
                time.sleep(5)

                # Check if file downloaded
                csv_files = list(output_dir.glob("*.csv"))
                if csv_files:
                    latest = max(csv_files, key=lambda p: p.stat().st_mtime)
                    new_name = output_dir / f"imo_casualties_{year}.csv"
                    if new_name.exists():
                        new_name.unlink()
                    latest.rename(new_name)
                    print(f" ✅ Downloaded")
                    successful += 1
                    results.append({"year": year, "status": "success"})
                else:
                    print(f" ⚠️  No CSV file")
                    results.append({"year": year, "status": "no_file"})

            except NoSuchElementException:
                print(f" ⚠️  No export button")
                results.append({"year": year, "status": "no_export"})

        except NoSuchElementException:
            print("No results")
            results.append({"year": year, "status": "no_results"})

    except Exception as e:
        print(f"❌ Error: {e}")
        results.append({"year": year, "status": "error", "error": str(e)})

    time.sleep(2)

# Save summary
summary = {
    "download_date": datetime.now().isoformat(),
    "username": username,
    "successful_downloads": successful,
    "total_years": len(results),
    "results": results
}

summary_file = output_dir / "download_summary.json"
with open(summary_file, "w") as f:
    json.dump(summary, f, indent=2)

driver.quit()

print()
print("=" * 60)
print(f"✅ Download Complete!")
print("=" * 60)
print(f"Successful: {successful} years")
print(f"Output: {output_dir}")
print(f"Summary: {summary_file}")
print()
