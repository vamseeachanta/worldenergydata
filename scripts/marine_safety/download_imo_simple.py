#!/usr/bin/env python3
"""
Download IMO GISIS Marine Casualty Data - Simple Version

This script assumes you're already logged in to IMO GISIS and will
use your existing browser session to download data year by year.

Run this from a terminal where you can interact with the browser.

Source: https://gisis.imo.org/Public/MCIR/Search.aspx
"""

import asyncio
import csv
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Error: playwright not installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
IMO_SEARCH_URL = "https://gisis.imo.org/Public/MCIR/Search.aspx"
OUTPUT_DIR = Path("/mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw/imo_gisis")

# Date ranges to download (year by year)
DATE_RANGES = [
    ("2018-01-01", "2018-12-31"),
    ("2019-01-01", "2019-12-31"),
    ("2020-01-01", "2020-12-31"),
    ("2021-01-01", "2021-12-31"),
    ("2022-01-01", "2022-12-31"),
    ("2023-01-01", "2023-12-31"),
    ("2024-01-01", "2024-12-31"),
    ("2025-01-01", datetime.now().strftime("%Y-%m-%d")),
]


async def download_date_range(page, from_date: str, to_date: str) -> Dict:
    """Download data for one date range"""

    logger.info(f"Processing: {from_date} to {to_date}")

    try:
        # Go to search page
        await page.goto(IMO_SEARCH_URL, wait_until='load', timeout=30000)
        await asyncio.sleep(2)

        # Fill date fields - try multiple selectors
        from_selectors = [
            'input[id$="txtDateFrom"]',
            'input[name$="txtDateFrom"]',
            'input[placeholder*="From"]'
        ]

        to_selectors = [
            'input[id$="txtDateTo"]',
            'input[name$="txtDateTo"]',
            'input[placeholder*="Until"]'
        ]

        from_field = None
        for selector in from_selectors:
            from_field = await page.query_selector(selector)
            if from_field:
                break

        to_field = None
        for selector in to_selectors:
            to_field = await page.query_selector(selector)
            if to_field:
                break

        if not from_field or not to_field:
            logger.error("Could not find date fields")
            return {'from_date': from_date, 'to_date': to_date, 'status': 'field_not_found'}

        # Clear and fill dates
        await from_field.click(click_count=3)
        await from_field.type(from_date)
        logger.info(f"  Set from date: {from_date}")

        await to_field.click(click_count=3)
        await to_field.type(to_date)
        logger.info(f"  Set to date: {to_date}")

        # Click search
        search_selectors = [
            'input[id$="btnSearch"]',
            'input[value="Search"]',
            'button:has-text("Search")'
        ]

        search_btn = None
        for selector in search_selectors:
            search_btn = await page.query_selector(selector)
            if search_btn:
                break

        if not search_btn:
            logger.error("Could not find search button")
            return {'from_date': from_date, 'to_date': to_date, 'status': 'search_button_not_found'}

        logger.info("  Clicking search...")
        await search_btn.click()
        await page.wait_for_load_state('networkidle', timeout=30000)
        await asyncio.sleep(3)

        # Check results count
        results_pattern = await page.query_selector('text=/\\d+ results found/')
        result_count = 0
        if results_pattern:
            text = await results_pattern.inner_text()
            match = re.search(r'(\d+) results', text)
            if match:
                result_count = int(match.group(1))
                logger.info(f"  Found {result_count} results")

        if result_count == 0:
            logger.warning("  No results")
            return {'from_date': from_date, 'to_date': to_date, 'count': 0, 'status': 'no_results'}

        # Try to download if button exists
        download_selectors = [
            'img[title="Download"]',
            'a[id$="lnkDownload"]',
            '[class*="download"]'
        ]

        download_btn = None
        for selector in download_selectors:
            download_btn = await page.query_selector(selector)
            if download_btn:
                break

        if download_btn:
            logger.info("  Downloading CSV...")
            try:
                async with page.expect_download(timeout=60000) as download_info:
                    await download_btn.click()
                    download = await download_info.value

                    filename = f"imo_{from_date}_to_{to_date}.csv"
                    filepath = OUTPUT_DIR / filename
                    await download.save_as(filepath)

                    logger.info(f"  Saved: {filepath}")

                    # Count actual records
                    with open(filepath, 'r', encoding='utf-8-sig') as f:
                        reader = csv.reader(f)
                        actual_count = sum(1 for row in reader) - 1  # Exclude header

                    logger.info(f"  CSV has {actual_count} records")

                    return {
                        'from_date': from_date,
                        'to_date': to_date,
                        'count': actual_count,
                        'status': 'success',
                        'filename': filename
                    }
            except Exception as e:
                logger.error(f"  Download failed: {e}")
                return {'from_date': from_date, 'to_date': to_date, 'status': 'download_failed', 'error': str(e)}
        else:
            logger.warning("  No download button - would need to scrape table")
            return {'from_date': from_date, 'to_date': to_date, 'count': result_count, 'status': 'no_download_button'}

    except Exception as e:
        logger.error(f"  Error: {e}")
        return {'from_date': from_date, 'to_date': to_date, 'status': 'error', 'error': str(e)}


async def main():
    """Main entry point"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("IMO GISIS Downloader")
    logger.info("=" * 60)
    logger.info(f"Will download {len(DATE_RANGES)} date ranges")
    logger.info(f"Output: {OUTPUT_DIR}")
    logger.info("")
    logger.info("IMPORTANT: Make sure you're logged in to IMO GISIS")
    logger.info("  in your browser before running this script")
    logger.info("=" * 60)
    logger.info("")

    results = []
    total_records = 0

    async with async_playwright() as p:
        # Use chromium with persistent context to keep login
        browser = await p.chromium.launch(
            headless=False,  # Show browser
            channel='chromium'
        )

        context = await browser.new_context()
        page = await context.new_page()

        for from_date, to_date in DATE_RANGES:
            result = await download_date_range(page, from_date, to_date)
            results.append(result)

            if result.get('count'):
                total_records += result['count']

            # Wait between requests
            await asyncio.sleep(3)

        await browser.close()

    # Save summary
    summary = {
        'download_date': datetime.now().isoformat(),
        'total_records': total_records,
        'successful': len([r for r in results if r.get('status') == 'success']),
        'results': results
    }

    summary_file = OUTPUT_DIR / 'download_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total records: {total_records}")
    logger.info(f"Successful downloads: {summary['successful']}/{len(DATE_RANGES)}")
    logger.info(f"Summary: {summary_file}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
