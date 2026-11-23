#!/usr/bin/env python3
"""
Download IMO GISIS Marine Casualty and Incident Reports

This script iteratively downloads marine casualty data from IMO GISIS
by searching year-by-year to avoid hitting query limits.

Source: https://gisis.imo.org/Public/MCIR/Search.aspx
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
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
IMO_BASE_URL = "https://gisis.imo.org/Public/MCIR/Search.aspx"
OUTPUT_DIR = Path("/mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw/imo_gisis")
START_YEAR = 2010
END_YEAR = 2025


class IMOGISISDownloader:
    """Download marine casualty data from IMO GISIS iteratively"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.downloaded_count = 0
        self.failed_years = []

    async def download_year_data(self, page, year: int) -> Optional[Dict]:
        """
        Download casualty data for a specific year

        Args:
            page: Playwright page object
            year: Year to download data for

        Returns:
            Dict with results or None if failed
        """
        logger.info(f"Downloading data for year {year}...")

        try:
            # Navigate to search page
            await page.goto(IMO_BASE_URL, wait_until='networkidle', timeout=60000)
            logger.info(f"Loaded search page for {year}")

            # Wait for the page to load
            await page.wait_for_load_state('networkidle')

            # Look for date range inputs
            # IMO GISIS typically has "From Date" and "To Date" fields
            from_date = f"01/01/{year}"
            to_date = f"12/31/{year}"

            # Try to find and fill date inputs
            # This is a best guess - may need adjustment based on actual page structure
            try:
                # Look for date input fields
                date_inputs = await page.query_selector_all('input[type="text"]')
                logger.info(f"Found {len(date_inputs)} text input fields")

                # Try to identify date fields by labels or IDs
                from_field = None
                to_field = None

                # Common patterns for date field IDs in ASP.NET applications
                from_patterns = ['txtDateFrom', 'txtFromDate', 'FromDate', 'DateFrom']
                to_patterns = ['txtDateTo', 'txtToDate', 'ToDate', 'DateTo']

                for pattern in from_patterns:
                    from_field = await page.query_selector(f'input[id*="{pattern}"]')
                    if from_field:
                        logger.info(f"Found 'From Date' field with pattern: {pattern}")
                        break

                for pattern in to_patterns:
                    to_field = await page.query_selector(f'input[id*="{pattern}"]')
                    if to_field:
                        logger.info(f"Found 'To Date' field with pattern: {pattern}")
                        break

                if from_field and to_field:
                    await from_field.fill(from_date)
                    logger.info(f"Filled 'From Date': {from_date}")
                    await to_field.fill(to_date)
                    logger.info(f"Filled 'To Date': {to_date}")
                else:
                    logger.warning("Could not find date fields - attempting alternative approach")
                    # Save page content for debugging
                    content = await page.content()
                    debug_file = self.output_dir / f"page_structure_{year}.html"
                    debug_file.write_text(content)
                    logger.info(f"Saved page structure to {debug_file}")

                # Look for search/submit button
                search_button = await page.query_selector('input[type="submit"][value*="Search"]') or \
                               await page.query_selector('input[type="submit"][value*="Submit"]') or \
                               await page.query_selector('button:has-text("Search")')

                if search_button:
                    logger.info("Found search button, clicking...")
                    await search_button.click()
                    await page.wait_for_load_state('networkidle')
                    logger.info("Search completed")
                else:
                    logger.warning("Could not find search button")

                # Wait for results
                await asyncio.sleep(3)

                # Try to extract results
                # Look for results table or grid
                results_table = await page.query_selector('table.GridView') or \
                               await page.query_selector('table[id*="Grid"]') or \
                               await page.query_selector('table.results')

                results = []
                if results_table:
                    logger.info("Found results table")
                    # Extract table data
                    rows = await results_table.query_selector_all('tr')
                    logger.info(f"Found {len(rows)} rows")

                    # Get headers
                    header_row = rows[0] if rows else None
                    headers = []
                    if header_row:
                        header_cells = await header_row.query_selector_all('th')
                        headers = [await cell.inner_text() for cell in header_cells]
                        logger.info(f"Headers: {headers}")

                    # Get data rows
                    for row in rows[1:]:  # Skip header
                        cells = await row.query_selector_all('td')
                        if cells:
                            row_data = {}
                            for i, cell in enumerate(cells):
                                header = headers[i] if i < len(headers) else f"Column_{i}"
                                row_data[header] = await cell.inner_text()
                            results.append(row_data)

                    logger.info(f"Extracted {len(results)} records for {year}")

                    # Check if there are multiple pages
                    pagination = await page.query_selector('table[class*="Pager"]') or \
                                await page.query_selector('[class*="pagination"]')

                    if pagination:
                        logger.info("Multiple pages detected - downloading all pages...")
                        page_num = 2
                        while True:
                            # Look for next page link
                            next_link = await page.query_selector(f'a:has-text("{page_num}")') or \
                                       await page.query_selector('a:has-text("Next")')

                            if not next_link:
                                break

                            await next_link.click()
                            await page.wait_for_load_state('networkidle')
                            await asyncio.sleep(2)

                            # Extract data from current page
                            page_table = await page.query_selector('table.GridView') or \
                                        await page.query_selector('table[id*="Grid"]')

                            if page_table:
                                page_rows = await page_table.query_selector_all('tr')
                                for row in page_rows[1:]:  # Skip header
                                    cells = await row.query_selector_all('td')
                                    if cells:
                                        row_data = {}
                                        for i, cell in enumerate(cells):
                                            header = headers[i] if i < len(headers) else f"Column_{i}"
                                            row_data[header] = await cell.inner_text()
                                        results.append(row_data)

                            page_num += 1
                            logger.info(f"Downloaded page {page_num}, total records: {len(results)}")

                else:
                    logger.warning(f"No results table found for {year}")
                    # Save page for debugging
                    content = await page.content()
                    debug_file = self.output_dir / f"no_results_{year}.html"
                    debug_file.write_text(content)
                    logger.info(f"Saved page to {debug_file} for debugging")

                # Save results to JSON
                if results:
                    output_file = self.output_dir / f"imo_casualties_{year}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            'year': year,
                            'download_date': datetime.now().isoformat(),
                            'record_count': len(results),
                            'records': results
                        }, f, indent=2, ensure_ascii=False)
                    logger.info(f"Saved {len(results)} records to {output_file}")
                    self.downloaded_count += len(results)
                    return {'year': year, 'count': len(results), 'status': 'success'}
                else:
                    logger.warning(f"No results for {year}")
                    self.failed_years.append(year)
                    return {'year': year, 'count': 0, 'status': 'no_results'}

            except Exception as e:
                logger.error(f"Error processing search for {year}: {str(e)}")
                self.failed_years.append(year)
                return {'year': year, 'count': 0, 'status': 'error', 'error': str(e)}

        except PlaywrightTimeout:
            logger.error(f"Timeout loading page for {year}")
            self.failed_years.append(year)
            return {'year': year, 'count': 0, 'status': 'timeout'}
        except Exception as e:
            logger.error(f"Error downloading data for {year}: {str(e)}")
            self.failed_years.append(year)
            return {'year': year, 'count': 0, 'status': 'error', 'error': str(e)}

    async def download_all_years(self, start_year: int, end_year: int):
        """
        Download data for all years in range

        Args:
            start_year: Starting year
            end_year: Ending year (inclusive)
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()

            results = []
            for year in range(start_year, end_year + 1):
                result = await self.download_year_data(page, year)
                results.append(result)

                # Be polite - wait between requests
                await asyncio.sleep(2)

            await browser.close()

            # Save summary
            summary = {
                'download_date': datetime.now().isoformat(),
                'start_year': start_year,
                'end_year': end_year,
                'total_records': self.downloaded_count,
                'successful_years': len([r for r in results if r.get('status') == 'success']),
                'failed_years': self.failed_years,
                'results': results
            }

            summary_file = self.output_dir / 'download_summary.json'
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)

            logger.info(f"\n{'='*60}")
            logger.info(f"Download Summary:")
            logger.info(f"  Total records: {self.downloaded_count}")
            logger.info(f"  Successful years: {summary['successful_years']}")
            logger.info(f"  Failed years: {len(self.failed_years)}")
            if self.failed_years:
                logger.info(f"  Failed year list: {self.failed_years}")
            logger.info(f"  Summary saved to: {summary_file}")
            logger.info(f"{'='*60}\n")


async def main():
    """Main entry point"""
    logger.info("Starting IMO GISIS data download...")
    logger.info(f"Date range: {START_YEAR} to {END_YEAR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")

    downloader = IMOGISISDownloader(OUTPUT_DIR)
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
        sys.exit(1)
