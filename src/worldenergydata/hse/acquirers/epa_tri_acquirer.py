# ABOUTME: Acquirer for EPA Toxics Release Inventory (TRI) basic data files.
# ABOUTME: Downloads annual TRI CSVs filtered for oil & gas industry SIC/NAICS codes.

"""
EPA TRI (Toxics Release Inventory) Data Acquirer

Downloads TRI basic data files from the EPA for oil & gas industry facilities.
TRI data includes annual facility-level reporting of chemical releases to air,
water, and land as required under the Emergency Planning and Community
Right-to-Know Act (EPCRA) Section 313.

Data sources:
- EPA TRI Basic Data Files: https://www.epa.gov/toxics-release-inventory-tri-program
- EPA Envirofacts REST API: https://data.epa.gov/efservice/

Usage:
    uv run python -m worldenergydata.hse.acquirers.epa_tri_acquirer \
        --output-dir data/modules/hse/raw/epa_tri [--years 2020-2024] [--force]
"""

import argparse
import io
import logging
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# EPA TRI data download URLs
# Pattern for individual year basic data downloads
TRI_BASIC_DOWNLOAD_URL = (
    "https://data.epa.gov/efservice/MV_TRI_BASIC_DOWNLOAD/YEAR/{year}/CSV"
)

# Alternative URL pattern (direct file download)
TRI_FILE_DOWNLOAD_URL = (
    "https://enviro.epa.gov/triexplorer/release_fac?p_view=USFAC"
    "&triession=TRIDB&sort=_VIEW_&sort_fmt=1&state=All+states"
    "&county=All+counties&chemical=All+chemicals"
    "&industry={sic_code}&year={year}&tab_rpt=1&fld=RELLBY"
    "&fld=TSFDSP&fld=E1&fld=E2&fld=E3&fld=E4&fld=E5&fld=E51"
    "&fld=RECYC&fld=ENRGY&fld=TREAT&fld=TSDSP"
)

# Envirofacts API base (for larger datasets)
ENVIROFACTS_BASE_URL = "https://data.epa.gov/efservice"

# Oil & gas industry SIC codes
OIL_GAS_SIC_CODES = [
    "1311",  # Crude Petroleum and Natural Gas
    "1381",  # Drilling Oil and Gas Wells
    "1382",  # Oil and Gas Field Services, NEC
    "1389",  # Services Allied to Oil and Gas Extraction
    "2911",  # Petroleum Refining
    "4612",  # Crude Petroleum Pipelines
    "4613",  # Refined Petroleum Pipelines
    "4922",  # Natural Gas Distribution
    "4923",  # Natural Gas Transmission and Distribution
    "4924",  # Natural Gas Distribution
    "4925",  # Mixed, Manufactured, or Liquefied Petroleum Gas
    "5171",  # Petroleum and Petroleum Products Wholesalers
]

# Oil & gas industry NAICS codes (3-digit prefixes)
OIL_GAS_NAICS_PREFIXES = [
    "211",  # Oil and Gas Extraction
    "213",  # Support Activities for Mining
    "324",  # Petroleum and Coal Products Manufacturing
    "424",  # Petroleum and Petroleum Products Merchant Wholesalers
    "486",  # Pipeline Transportation
]

# Default parameters
DEFAULT_START_YEAR = 2020
DEFAULT_END_YEAR = 2024
REQUEST_TIMEOUT = 120
RETRY_DELAY_SECONDS = 5
MAX_RETRIES = 3


class EPATRIAcquirer:
    """
    Acquirer for EPA Toxics Release Inventory data.

    Downloads TRI basic data files by year from the EPA Envirofacts
    REST API and filters for oil & gas industry facilities.

    Attributes:
        output_dir: Directory to save downloaded data
        years: List of years to download
        force: If True, overwrite existing files
        filter_industry: If True, filter for oil & gas SIC/NAICS codes
    """

    def __init__(
        self,
        output_dir: Path,
        years: Optional[List[int]] = None,
        force: bool = False,
        filter_industry: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.years = years or list(range(DEFAULT_START_YEAR, DEFAULT_END_YEAR + 1))
        self.force = force
        self.filter_industry = filter_industry
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "WorldEnergyData/1.0 (research; environmental-analysis)",
                "Accept": "text/csv, application/csv, */*",
            }
        )

    def acquire(self) -> List[Path]:
        """
        Execute the full acquisition pipeline.

        Downloads TRI data for each requested year, optionally filters
        for oil & gas industry, and saves CSV files.

        Returns:
            List of paths to downloaded/processed CSV files
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_files = []

        logger.info(f"Starting EPA TRI data acquisition for years: {self.years}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(
            f"Industry filter: {'enabled' if self.filter_industry else 'disabled'}"
        )

        for year in self.years:
            try:
                output_file = self._acquire_year(year)
                if output_file:
                    output_files.append(output_file)
            except Exception as e:
                logger.error(f"Failed to acquire TRI data for {year}: {e}")

        # Write combined file if multiple years
        if len(output_files) > 1:
            combined_file = self._combine_years(output_files)
            if combined_file:
                output_files.append(combined_file)

        logger.info(f"Acquisition complete: {len(output_files)} files")
        return output_files

    def _acquire_year(self, year: int) -> Optional[Path]:
        """
        Acquire TRI data for a single year.

        Tries the Envirofacts API first, then falls back to alternative
        download methods.

        Args:
            year: Calendar year to download

        Returns:
            Path to the downloaded CSV file, or None on failure
        """
        suffix = "_oil_gas" if self.filter_industry else "_all"
        output_file = self.output_dir / f"tri_basic_{year}{suffix}.csv"

        if output_file.exists() and not self.force:
            logger.info(
                f"Skipping {year}: {output_file} exists (use --force to overwrite)"
            )
            return output_file

        logger.info(f"Acquiring TRI data for year {year}...")

        # Strategy 1: Envirofacts REST API with pagination
        df = self._download_from_envirofacts(year)

        if df is None or df.empty:
            # Strategy 2: Try direct CSV download
            df = self._download_direct_csv(year)

        if df is None or df.empty:
            logger.warning(f"No TRI data acquired for year {year}")
            return None

        # Filter for oil & gas industry if requested
        if self.filter_industry:
            df = self._filter_oil_gas(df, year)

        if df.empty:
            logger.warning(f"No oil & gas TRI records found for year {year}")
            return None

        # Save to CSV
        df.to_csv(output_file, index=False, encoding="utf-8")
        logger.info(f"Saved {len(df)} records for {year} to {output_file}")

        return output_file

    def _download_from_envirofacts(self, year: int) -> Optional[pd.DataFrame]:
        """
        Download TRI data from EPA Envirofacts REST API.

        The Envirofacts API returns data in paginated chunks of up to
        10,000 rows per request.

        Args:
            year: Calendar year

        Returns:
            DataFrame of TRI records or None on failure
        """
        logger.info(f"Downloading from Envirofacts API for year {year}...")

        all_frames = []
        batch_size = 10000
        offset = 0
        max_iterations = 100  # Safety limit

        for iteration in range(max_iterations):
            # Envirofacts REST API URL with row range
            url = (
                f"{ENVIROFACTS_BASE_URL}/MV_TRI_BASIC_DOWNLOAD"
                f"/YEAR/{year}"
                f"/rows/{offset}:{offset + batch_size}/CSV"
            )

            try:
                response = self._make_request(url)
                if response is None:
                    break

                # Check content type and size
                content = response.text
                if not content.strip() or len(content) < 50:
                    if iteration == 0:
                        logger.warning(f"Empty response from Envirofacts for {year}")
                        return None
                    break

                # Parse CSV from response text
                try:
                    df_chunk = pd.read_csv(io.StringIO(content), low_memory=False)
                except pd.errors.EmptyDataError:
                    if iteration == 0:
                        return None
                    break

                if df_chunk.empty:
                    break

                all_frames.append(df_chunk)
                rows_received = len(df_chunk)
                offset += rows_received
                logger.debug(
                    f"Batch {iteration + 1}: {rows_received} rows (total: {offset})"
                )

                # If we received fewer than batch_size rows, we've reached the end
                if rows_received < batch_size:
                    break

                time.sleep(0.5)  # Rate limiting

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else None
                if status_code == 404 and iteration == 0:
                    logger.warning(f"Envirofacts API returned 404 for year {year}")
                    return None
                break
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as e:
                logger.warning(f"Envirofacts connection error for {year}: {e}")
                if iteration == 0:
                    return None
                break

        if not all_frames:
            return None

        df = pd.concat(all_frames, ignore_index=True)
        logger.info(
            f"Downloaded {len(df)} total TRI records for {year} from Envirofacts"
        )
        return df

    def _download_direct_csv(self, year: int) -> Optional[pd.DataFrame]:
        """
        Try downloading TRI data as a direct CSV file.

        Uses the simple Envirofacts CSV endpoint without pagination.

        Args:
            year: Calendar year

        Returns:
            DataFrame or None on failure
        """
        url = TRI_BASIC_DOWNLOAD_URL.format(year=year)
        logger.info(f"Trying direct CSV download for {year}: {url}")

        try:
            response = self._make_request(url, timeout=180)
            if response is None:
                return None

            content = response.text
            if not content.strip() or len(content) < 50:
                logger.warning(f"Empty direct CSV response for {year}")
                return None

            df = pd.read_csv(io.StringIO(content), low_memory=False)
            logger.info(f"Direct download: {len(df)} records for {year}")
            return df

        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            pd.errors.EmptyDataError,
        ) as e:
            logger.warning(f"Direct CSV download failed for {year}: {e}")
            return None

    def _filter_oil_gas(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """
        Filter DataFrame for oil & gas industry facilities.

        Uses SIC codes, NAICS codes, and industry sector descriptions to
        identify oil & gas sector facilities. Handles the lowercase column
        names returned by the Envirofacts API.

        Args:
            df: Full TRI DataFrame
            year: Year (for logging)

        Returns:
            Filtered DataFrame
        """
        original_count = len(df)

        # Normalize column names for matching (uppercase)
        col_map = {c: c.upper().strip() for c in df.columns}
        df_upper = df.rename(columns=col_map)

        # Find SIC code column (Envirofacts uses "PRIMARY SIC")
        sic_col = None
        for candidate in [
            "PRIMARY SIC",
            "PRIMARY_SIC",
            "SIC CODE",
            "SIC_CODE",
            "PRIMARY SIC CODE",
            "PRIMARY_SIC_CODE",
        ]:
            if candidate in df_upper.columns:
                sic_col = candidate
                break

        # Find NAICS code column (Envirofacts uses "PRIMARY NAICS")
        naics_col = None
        for candidate in [
            "PRIMARY NAICS",
            "PRIMARY_NAICS",
            "NAICS",
            "NAICS CODE",
            "NAICS_CODE",
            "PRIMARY NAICS CODE",
            "PRIMARY_NAICS_CODE",
        ]:
            if candidate in df_upper.columns:
                naics_col = candidate
                break

        # Find industry sector code column
        industry_code_col = None
        for candidate in ["INDUSTRY SECTOR CODE", "INDUSTRY_SECTOR_CODE"]:
            if candidate in df_upper.columns:
                industry_code_col = candidate
                break

        # Find industry sector description column
        industry_desc_col = None
        for candidate in [
            "INDUSTRY SECTOR",
            "INDUSTRY_SECTOR",
            "INDUSTRY",
            "SIC_DESCRIPTION",
            "SIC DESCRIPTION",
        ]:
            if candidate in df_upper.columns:
                industry_desc_col = candidate
                break

        logger.debug(
            f"Filter columns found - SIC: {sic_col}, NAICS: {naics_col}, "
            f"Industry code: {industry_code_col}, Industry desc: {industry_desc_col}"
        )

        mask = pd.Series([False] * len(df_upper), index=df_upper.index)

        # Filter by SIC code
        if sic_col:
            sic_values = df_upper[sic_col].astype(str).str.strip()
            for sic_code in OIL_GAS_SIC_CODES:
                mask = mask | sic_values.str.startswith(sic_code)
            sic_matches = mask.sum()
            logger.debug(f"SIC filter matches: {sic_matches}")

        # Filter by NAICS code
        if naics_col:
            naics_values = df_upper[naics_col].astype(str).str.strip()
            for prefix in OIL_GAS_NAICS_PREFIXES:
                mask = mask | naics_values.str.startswith(prefix)
            naics_matches = mask.sum()
            logger.debug(f"SIC+NAICS filter matches: {naics_matches}")

        # Also filter by industry sector description for broader coverage
        if industry_desc_col:
            industry_values = df_upper[industry_desc_col].astype(str).str.upper()
            oil_gas_keywords = [
                "PETROLEUM",
                "OIL AND GAS",
                "CRUDE",
                "REFIN",
                "PIPELINE",
                "DRILLING",
                "EXTRACTION",
            ]
            for keyword in oil_gas_keywords:
                mask = mask | industry_values.str.contains(keyword, na=False)
            desc_matches = mask.sum()
            logger.debug(f"Total filter matches (with industry desc): {desc_matches}")

        # If no structured columns found, try broader keyword search
        if sic_col is None and naics_col is None and industry_desc_col is None:
            logger.warning(
                f"No SIC/NAICS/Industry columns found. Available columns: "
                f"{list(df_upper.columns[:20])}"
            )

        filtered = df[mask]
        logger.info(
            f"Year {year}: filtered {original_count} -> {len(filtered)} oil & gas records"
        )

        return filtered

    def _combine_years(self, files: List[Path]) -> Optional[Path]:
        """
        Combine multiple year files into a single CSV.

        Args:
            files: List of per-year CSV paths

        Returns:
            Path to combined file, or None on failure
        """
        try:
            frames = []
            for f in files:
                if f.exists() and f.suffix == ".csv":
                    df = pd.read_csv(f, low_memory=False)
                    frames.append(df)

            if not frames:
                return None

            combined = pd.concat(frames, ignore_index=True)
            suffix = "_oil_gas" if self.filter_industry else "_all"
            years_str = f"{min(self.years)}-{max(self.years)}"
            output_file = (
                self.output_dir / f"tri_basic_{years_str}{suffix}_combined.csv"
            )
            combined.to_csv(output_file, index=False, encoding="utf-8")
            logger.info(f"Combined {len(combined)} records into {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Failed to combine year files: {e}")
            return None

    def _make_request(
        self,
        url: str,
        timeout: int = REQUEST_TIMEOUT,
    ) -> Optional[requests.Response]:
        """
        Make an HTTP GET request with retry logic.

        Args:
            url: Request URL
            timeout: Request timeout in seconds

        Returns:
            Response object or None if all retries failed
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                return response

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else None
                if status_code in (429, 503) and attempt < MAX_RETRIES:
                    delay = RETRY_DELAY_SECONDS * attempt
                    logger.warning(
                        f"HTTP {status_code} on attempt {attempt}, retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue
                raise
            except requests.exceptions.Timeout:
                if attempt < MAX_RETRIES:
                    logger.warning(f"Timeout on attempt {attempt}, retrying...")
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue
                raise
            except requests.exceptions.ConnectionError:
                if attempt < MAX_RETRIES:
                    logger.warning(
                        f"Connection error on attempt {attempt}, retrying..."
                    )
                    time.sleep(RETRY_DELAY_SECONDS * attempt)
                    continue
                raise

        return None


def parse_years(years_str: str) -> List[int]:
    """
    Parse a year range string into a list of years.

    Supports formats:
    - "2020" -> [2020]
    - "2020-2024" -> [2020, 2021, 2022, 2023, 2024]
    - "2020,2022,2024" -> [2020, 2022, 2024]

    Args:
        years_str: Year range string

    Returns:
        Sorted list of years
    """
    years = set()

    for part in years_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            for y in range(int(start.strip()), int(end.strip()) + 1):
                years.add(y)
        else:
            years.add(int(part))

    return sorted(years)


def main():
    """CLI entry point for EPA TRI data acquisition."""
    parser = argparse.ArgumentParser(
        description="Acquire EPA TRI toxic release inventory data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download TRI data for 2020-2024 (oil & gas only)
  uv run python -m worldenergydata.hse.acquirers.epa_tri_acquirer \\
    --output-dir data/modules/hse/raw/epa_tri --years 2020-2024

  # Download all industries
  uv run python -m worldenergydata.hse.acquirers.epa_tri_acquirer \\
    --output-dir data/modules/hse/raw/epa_tri --years 2023 --no-filter-industry

  # Force re-download
  uv run python -m worldenergydata.hse.acquirers.epa_tri_acquirer \\
    --output-dir data/modules/hse/raw/epa_tri --years 2020-2024 --force
        """,
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory to save downloaded data",
    )
    parser.add_argument(
        "--years",
        type=str,
        default=f"{DEFAULT_START_YEAR}-{DEFAULT_END_YEAR}",
        help=(
            f"Year(s) to download (e.g., '2020', '2020-2024',"
            f" '2020,2022'). Default: {DEFAULT_START_YEAR}-{DEFAULT_END_YEAR}"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )
    parser.add_argument(
        "--filter-industry",
        action="store_true",
        default=True,
        help="Filter for oil & gas industry (default: enabled)",
    )
    parser.add_argument(
        "--no-filter-industry",
        action="store_true",
        help="Download all industries (disable oil & gas filter)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    years = parse_years(args.years)
    filter_industry = not args.no_filter_industry

    acquirer = EPATRIAcquirer(
        output_dir=Path(args.output_dir),
        years=years,
        force=args.force,
        filter_industry=filter_industry,
    )

    output_files = acquirer.acquire()

    print("\nAcquisition summary:")
    print(f"  Years requested: {years}")
    print(f"  Files created: {len(output_files)}")
    for f in output_files:
        if f and f.exists():
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  - {f} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
