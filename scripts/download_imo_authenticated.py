#!/usr/bin/env python3
"""
Download IMO GISIS Marine Casualty Data (Authenticated)

This script connects to an existing authenticated browser session to download
IMO GISIS data iteratively by date ranges.

Prerequisites:
- User must be logged in to IMO GISIS in a browser
- Playwright must have access to browser storage/cookies

Source: https://gisis.imo.org/Public/MCIR/Search.aspx
"""

import asyncio
import csv
import json
import logging
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Error: playwright not installed. Install with: pip install playwright")
    print("Then run: playwright install chromium")
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
START_YEAR = 2018
END_YEAR = 2025


class IMOAuthenticatedDownloader:
    """Download marine casualty data from IMO GISIS using authenticated session"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.downloaded_count = 0
        self.failed_ranges = []
        self.all_records = []

    async def search_and_download(self, page, from_date: str, to_date: str) -> Optional[Dict]:
        """
        Search and download data for a specific date range

        Args:
            page: Playwright page object (already authenticated)
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format

        Returns:
            Dict with results or None if failed
        """
        logger.info(f"Searching for casualties from {from_date} to {to_date}...")

        try:
            # Navigate to search page
            await page.goto(IMO_SEARCH_URL, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(2)

            # Fill in date fields
            # From the screenshot, the date format appears to be YYYY-MM-DD
            from_input = await page.query_selector('input[id*="txtDateFrom"]') or \
                         await page.query_selector('input[placeholder*="From"]')
            to_input = await page.query_selector('input[id*="txtDateTo"]') or \
                       await page.query_selector('input[placeholder*="Until"]')

            if from_input and to_input:
                # Clear existing dates
                await from_input.click(click_count=3)
                await from_input.fill(from_date)
                logger.info(f"  Set 'From' date: {from_date}")

                await to_input.click(click_count=3)
                await to_input.fill(to_date)
                logger.info(f"  Set 'To' date: {to_date}")

                # Ensure all severity checkboxes are checked (from screenshot: Very serious, Marine casualty, Marine incident)
                checkboxes = await page.query_selector_all('input[type="checkbox"]')
                for checkbox in checkboxes:
                    is_checked = await checkbox.is_checked()
                    if not is_checked:
                        await checkbox.check()

                # Click Search button
                search_button = await page.query_selector('input[id*="btnSearch"]') or \
                               await page.query_selector('input[value="Search"]') or \
                               await page.query_selector('button:has-text("Search")')

                if search_button:
                    logger.info("  Clicking search button...")
                    await search_button.click()
                    await page.wait_for_load_state('networkidle', timeout=60000)
                    await asyncio.sleep(3)
                else:
                    logger.error("  Could not find search button!")
                    return None

                # Check for results
                results_text = await page.query_selector('text=/\\d+ results found/')
                if results_text:
                    text_content = await results_text.inner_text()
                    result_count = int(re.search(r'(\d+) results', text_content).group(1))
                    logger.info(f"  Found {result_count} results")
                else:
                    logger.warning("  Could not find results count")
                    result_count = 0

                if result_count == 0:
                    logger.warning(f"  No results for {from_date} to {to_date}")
                    return {'from_date': from_date, 'to_date': to_date, 'count': 0, 'status': 'no_results'}

                # Check if download button is available
                download_button = await page.query_selector('a[id*="lnkDownload"]') or \
                                 await page.query_selector('img[title="Download"]') or \
                                 await page.query_selector('[class*="download"]')

                if download_button:
                    logger.info("  Found download button, initiating download...")

                    # Set up download handling
                    async with page.expect_download(timeout=120000) as download_info:
                        await download_button.click()
                        download = await download_info.value

                        # Save the downloaded file
                        filename = f"imo_casualties_{from_date}_to_{to_date}.csv"
                        filepath = self.output_dir / filename
                        await download.save_as(filepath)
                        logger.info(f"  Downloaded to: {filepath}")

                        # Parse the CSV to count records
                        try:
                            with open(filepath, 'r', encoding='utf-8-sig') as f:
                                reader = csv.DictReader(f)
                                records = list(reader)
                                actual_count = len(records)
                                logger.info(f"  CSV contains {actual_count} records")
                                self.all_records.extend(records)
                                self.downloaded_count += actual_count
                        except Exception as e:
                            logger.error(f"  Error parsing CSV: {e}")
                            actual_count = result_count

                        return {
                            'from_date': from_date,
                            'to_date': to_date,
                            'count': actual_count,
                            'status': 'success',
                            'filename': filename
                        }
                else:
                    logger.warning("  No download button found - scraping table instead...")
                    # Extract data from HTML table
                    records = await self.scrape_results_table(page)

                    if records:
                        # Save to CSV
                        filename = f"imo_casualties_{from_date}_to_{to_date}.csv"
                        filepath = self.output_dir / filename

                        with open(filepath, 'w', encoding='utf-8', newline='') as f:
                            if records:
                                writer = csv.DictWriter(f, fieldnames=records[0].keys())
                                writer.writeheader()
                                writer.writerows(records)

                        logger.info(f"  Scraped {len(records)} records to {filepath}")
                        self.all_records.extend(records)
                        self.downloaded_count += len(records)

                        return {
                            'from_date': from_date,
                            'to_date': to_date,
                            'count': len(records),
                            'status': 'success',
                            'filename': filename
                        }
                    else:
                        logger.error("  Failed to scrape table data")
                        return {'from_date': from_date, 'to_date': to_date, 'count': 0, 'status': 'scrape_failed'}

            else:
                logger.error("  Could not find date input fields")
                return None

        except PlaywrightTimeout:
            logger.error(f"  Timeout for {from_date} to {to_date}")
            self.failed_ranges.append((from_date, to_date))
            return {'from_date': from_date, 'to_date': to_date, 'count': 0, 'status': 'timeout'}
        except Exception as e:
            logger.error(f"  Error for {from_date} to {to_date}: {str(e)}")
            self.failed_ranges.append((from_date, to_date))
            return {'from_date': from_date, 'to_date': to_date, 'count': 0, 'status': 'error', 'error': str(e)}

    async def scrape_results_table(self, page) -> List[Dict]:
        """
        Scrape results from the HTML table on the page

        Args:
            page: Playwright page object

        Returns:
            List of dictionaries with casualty data
        """
        records = []

        try:
            # Look for results table - from screenshot it's a standard HTML table
            table = await page.query_selector('table[id*="gv"]') or \
                   await page.query_selector('table.GridView') or \
                   await page.query_selector('table[class*="grid"]')

            if not table:
                logger.warning("  No results table found")
                return records

            # Get headers
            header_row = await table.query_selector('tr:first-child')
            if not header_row:
                return records

            header_cells = await header_row.query_selector_all('th')
            headers = []
            for cell in header_cells:
                text = await cell.inner_text()
                headers.append(text.strip())

            logger.info(f"  Table headers: {headers}")

            # Get all data rows
            data_rows = await table.query_selector_all('tr:not(:first-child)')
            logger.info(f"  Found {len(data_rows)} data rows")

            for row in data_rows:
                cells = await row.query_selector_all('td')
                if len(cells) > 0:
                    row_data = {}
                    for i, cell in enumerate(cells):
                        header = headers[i] if i < len(headers) else f"Column_{i}"
                        text = await cell.inner_text()
                        row_data[header] = text.strip()
                    records.append(row_data)

            # Check for pagination and get additional pages
            current_page = 1
            while True:
                # Look for next page link
                next_link = await page.query_selector(f'a:has-text("{current_page + 1}")') or \
                           await page.query_selector('a[title="Next Page"]')

                if not next_link:
                    break

                current_page += 1
                logger.info(f"  Loading page {current_page}...")

                await next_link.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)

                # Scrape current page
                page_table = await page.query_selector('table[id*="gv"]') or \
                            await page.query_selector('table.GridView')

                if page_table:
                    page_rows = await page_table.query_selector_all('tr:not(:first-child)')
                    for row in page_rows:
                        cells = await row.query_selector_all('td')
                        if len(cells) > 0:
                            row_data = {}
                            for i, cell in enumerate(cells):
                                header = headers[i] if i < len(headers) else f"Column_{i}"
                                text = await cell.inner_text()
                                row_data[header] = text.strip()
                            records.append(row_data)

                logger.info(f"  Total records scraped: {len(records)}")

        except Exception as e:
            logger.error(f"  Error scraping table: {e}")

        return records

    async def download_all_years(self, start_year: int, end_year: int):
        """
        Download data for all years in range

        Args:
            start_year: Starting year
            end_year: Ending year (inclusive)
        """
        async with async_playwright() as p:
            # Use persistent context to maintain login session
            browser = await p.chromium.launch(
                headless=False,  # Set to False to see browser and maintain session
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )

            # Try to use existing browser state or create new context
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )

            page = await context.new_page()

            # Navigate to IMO GISIS
            logger.info("Navigating to IMO GISIS...")
            await page.goto(IMO_SEARCH_URL, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)

            # Check if we're logged in
            page_content = await page.content()
            if 'login' in page_content.lower() or 'sign in' in page_content.lower():
                logger.warning("=" * 60)
                logger.warning("NOT LOGGED IN!")
                logger.warning("Please log in to IMO GISIS in the browser window that opened.")
                logger.warning("After logging in, press ENTER here to continue...")
                logger.warning("=" * 60)
                input()
                await page.goto(IMO_SEARCH_URL, wait_until='domcontentloaded')
                await asyncio.sleep(2)

            results = []

            # Download year by year
            for year in range(start_year, end_year + 1):
                from_date = f"{year}-01-01"
                to_date = f"{year}-12-31"

                # For current year, use today's date
                if year == datetime.now().year:
                    to_date = datetime.now().strftime("%Y-%m-%d")

                result = await self.search_and_download(page, from_date, to_date)
                if result:
                    results.append(result)

                # Be polite - wait between requests
                await asyncio.sleep(3)

            await browser.close()

            # Save combined CSV with all records
            if self.all_records:
                combined_file = self.output_dir / 'imo_casualties_combined.csv'
                with open(combined_file, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=self.all_records[0].keys())
                    writer.writeheader()
                    writer.writerows(self.all_records)
                logger.info(f"Saved combined file: {combined_file} ({len(self.all_records)} records)")

            # Save summary
            summary = {
                'download_date': datetime.now().isoformat(),
                'start_year': start_year,
                'end_year': end_year,
                'total_records': self.downloaded_count,
                'successful_downloads': len([r for r in results if r and r.get('status') == 'success']),
                'failed_ranges': self.failed_ranges,
                'results': results
            }

            summary_file = self.output_dir / 'download_summary.json'
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)

            logger.info(f"\n{'='*60}")
            logger.info(f"Download Summary:")
            logger.info(f"  Total records: {self.downloaded_count}")
            logger.info(f"  Successful downloads: {summary['successful_downloads']}")
            logger.info(f"  Failed ranges: {len(self.failed_ranges)}")
            if self.failed_ranges:
                logger.info(f"  Failed range list: {self.failed_ranges}")
            logger.info(f"  Summary saved to: {summary_file}")
            logger.info(f"  Combined CSV: {self.output_dir / 'imo_casualties_combined.csv'}")
            logger.info(f"{'='*60}\n")


async def main():
    """Main entry point"""
    logger.info("Starting IMO GISIS authenticated data download...")
    logger.info(f"Date range: {START_YEAR} to {END_YEAR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")

    downloader = IMOAuthenticatedDownloader(OUTPUT_DIR)
    await downloader.download_all_years(START_YEAR, END_YEAR)

    logger.info("Download complete!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nDownload interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
