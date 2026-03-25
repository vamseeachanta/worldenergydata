# ABOUTME: Acquirer for NTSB CAROL marine investigation data.
# ABOUTME: Downloads marine mode investigations from NTSB CAROL API with pagination and CSV export.

"""
NTSB CAROL Marine Data Acquirer

Downloads marine accident investigation data from the NTSB CAROL
(Case Analysis and Reporting Online) system at https://data.ntsb.gov.

The CAROL system provides public access to NTSB investigation data.
This acquirer attempts the API endpoint first, then falls back to
the report generation endpoint, and finally provides instructions
for manual CSV export if automated access is unavailable.

Usage:
    uv run python -m worldenergydata.marine_safety.acquirers.ntsb_carol_acquirer \
        --output-dir data/modules/marine_safety/raw/ntsb [--force] [--max-pages 100]
"""

import argparse
import csv
import json
import logging
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# NTSB CAROL endpoints
CAROL_BASE_URL = "https://data.ntsb.gov"
CAROL_SEARCH_URL = f"{CAROL_BASE_URL}/carol-main-public/api/Query/GetSearchResults"
CAROL_REPORT_URL = f"{CAROL_BASE_URL}/carol-repgen-api/api/Reports/GetReport"
CAROL_QUERY_URL = f"{CAROL_BASE_URL}/carol-main-public/api/query"

# Default parameters
DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 200
DEFAULT_MIN_DATE = "2001-01-01"
REQUEST_TIMEOUT = 60
RETRY_DELAY_SECONDS = 5
MAX_RETRIES = 3

# CSV output columns for standardized export
CSV_COLUMNS = [
    "ntsb_id",
    "event_date",
    "city",
    "state",
    "country",
    "location_description",
    "latitude",
    "longitude",
    "mode",
    "event_type",
    "vessel_name",
    "vessel_type",
    "fatalities",
    "injuries",
    "status",
    "probable_cause",
    "report_url",
    "scraped_at",
]


class NTSBCAROLAcquirer:
    """
    Acquirer for NTSB CAROL marine investigation data.

    Attempts multiple API strategies to download marine investigation data:
    1. CAROL GetSearchResults API (POST with JSON body)
    2. CAROL query API (GET with query parameters)
    3. Report generation API
    4. Falls back to documenting manual export steps

    Attributes:
        output_dir: Directory to save downloaded data
        force: If True, overwrite existing files
        max_pages: Maximum number of result pages to fetch
        page_size: Number of results per page
        min_date: Earliest date for investigation search
    """

    def __init__(
        self,
        output_dir: Path,
        force: bool = False,
        max_pages: int = DEFAULT_MAX_PAGES,
        page_size: int = DEFAULT_PAGE_SIZE,
        min_date: str = DEFAULT_MIN_DATE,
    ):
        self.output_dir = Path(output_dir)
        self.force = force
        self.max_pages = max_pages
        self.page_size = page_size
        self.min_date = min_date
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "WorldEnergyData/1.0 (research; marine-safety-analysis)",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        self._records: List[Dict[str, Any]] = []

    def acquire(self) -> Path:
        """
        Execute the full acquisition pipeline.

        Tries API endpoints in order of preference. If all automated
        approaches fail, generates a manual export guide.

        Returns:
            Path to the output CSV file
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_file = self.output_dir / "ntsb_marine_investigations.csv"

        if output_file.exists() and not self.force:
            logger.info(
                f"Output file exists, skipping (use --force to overwrite): {output_file}"
            )
            return output_file

        logger.info("Starting NTSB CAROL marine data acquisition...")
        logger.info(f"Output directory: {self.output_dir}")

        # Strategy 1: Try the GetSearchResults POST API
        success = self._try_search_api()

        # Strategy 2: Try the query GET API
        if not success:
            success = self._try_query_api()

        # Strategy 3: Try the report generation API
        if not success:
            success = self._try_report_api()

        if success and self._records:
            output_file = self._write_csv(output_file)
            logger.info(
                f"Acquisition complete: {len(self._records)} records saved to {output_file}"
            )
        else:
            # Strategy 4: Generate manual export guide
            logger.warning(
                "Automated API access unavailable. Generating manual export guide."
            )
            guide_path = self._write_manual_guide()
            logger.info(f"Manual export guide written to: {guide_path}")

            # Still write any partial data collected
            if self._records:
                output_file = self._write_csv(output_file)
                logger.info(f"Partial data saved: {len(self._records)} records")

        return output_file

    def _try_search_api(self) -> bool:
        """
        Try the CAROL GetSearchResults POST API.

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Trying CAROL Search API: {CAROL_SEARCH_URL}")

        # Build search payload for marine mode
        payload = {
            "QueryGroups": [
                {
                    "QueryRules": [
                        {
                            "FieldName": "Mode",
                            "RuleOperator": "Equals",
                            "RuleValue": "Marine",
                        }
                    ],
                    "GroupOperator": "And",
                }
            ],
            "ResultSort": {"SortFieldName": "EventDate", "SortDescending": True},
            "ResultsPage": {"PageNumber": 1, "PageSize": self.page_size},
        }

        page = 1
        total_fetched = 0

        while page <= self.max_pages:
            payload["ResultsPage"]["PageNumber"] = page

            try:
                response = self._make_request(
                    CAROL_SEARCH_URL, method="POST", json_data=payload
                )

                if response is None:
                    return total_fetched > 0

                data = response.json()

                # Extract results - CAROL API may use various response formats
                results = self._extract_results(data)
                if not results:
                    if page == 1:
                        logger.warning("No results from Search API on first page")
                        return False
                    break

                for record in results:
                    parsed = self._parse_carol_record(record)
                    if parsed:
                        self._records.append(parsed)
                        total_fetched += 1

                logger.info(
                    f"Page {page}: fetched {len(results)} records (total: {total_fetched})"
                )

                # Check if there are more pages
                total_count = self._extract_total_count(data)
                if total_count and total_fetched >= total_count:
                    break

                if len(results) < self.page_size:
                    break

                page += 1
                time.sleep(1)  # Rate limiting

            except requests.exceptions.HTTPError as e:
                if page == 1:
                    logger.warning(f"Search API returned HTTP error: {e}")
                    return False
                break
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as e:
                logger.warning(f"Search API connection error: {e}")
                return total_fetched > 0
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Search API response parsing error: {e}")
                return total_fetched > 0

        return total_fetched > 0

    def _try_query_api(self) -> bool:
        """
        Try the CAROL query GET API.

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Trying CAROL Query API: {CAROL_QUERY_URL}")

        params = {
            "mode": "Marine",
            "startDate": self.min_date,
            "endDate": date.today().isoformat(),
            "page": 1,
            "pageSize": self.page_size,
            "sortBy": "eventDate",
            "sortOrder": "desc",
        }

        page = 1
        total_fetched = 0

        while page <= self.max_pages:
            params["page"] = page

            try:
                response = self._make_request(
                    CAROL_QUERY_URL, method="GET", params=params
                )

                if response is None:
                    return total_fetched > 0

                data = response.json()
                results = self._extract_results(data)

                if not results:
                    if page == 1:
                        logger.warning("No results from Query API on first page")
                        return False
                    break

                for record in results:
                    parsed = self._parse_carol_record(record)
                    if parsed:
                        self._records.append(parsed)
                        total_fetched += 1

                logger.info(
                    f"Page {page}: fetched {len(results)} records (total: {total_fetched})"
                )

                total_count = self._extract_total_count(data)
                if total_count and total_fetched >= total_count:
                    break

                if len(results) < self.page_size:
                    break

                page += 1
                time.sleep(1)

            except requests.exceptions.HTTPError as e:
                if page == 1:
                    logger.warning(f"Query API returned HTTP error: {e}")
                    return False
                break
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as e:
                logger.warning(f"Query API connection error: {e}")
                return total_fetched > 0
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Query API response parsing error: {e}")
                return total_fetched > 0

        return total_fetched > 0

    def _try_report_api(self) -> bool:
        """
        Try the CAROL report generation API.

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Trying CAROL Report API: {CAROL_REPORT_URL}")

        payload = {
            "ReportType": "Marine",
            "StartDate": self.min_date,
            "EndDate": date.today().isoformat(),
            "Format": "json",
        }

        try:
            response = self._make_request(
                CAROL_REPORT_URL, method="POST", json_data=payload
            )

            if response is None:
                return False

            data = response.json()
            results = self._extract_results(data)

            if not results:
                logger.warning("No results from Report API")
                return False

            for record in results:
                parsed = self._parse_carol_record(record)
                if parsed:
                    self._records.append(parsed)

            logger.info(f"Report API: fetched {len(self._records)} records")
            return True

        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            json.JSONDecodeError,
            KeyError,
            ValueError,
        ) as e:
            logger.warning(f"Report API error: {e}")
            return False

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> Optional[requests.Response]:
        """
        Make an HTTP request with retry logic.

        Args:
            url: Request URL
            method: HTTP method (GET or POST)
            params: Query parameters for GET requests
            json_data: JSON body for POST requests

        Returns:
            Response object or None if all retries failed
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if method.upper() == "POST":
                    response = self.session.post(
                        url, json=json_data, timeout=REQUEST_TIMEOUT
                    )
                else:
                    response = self.session.get(
                        url, params=params, timeout=REQUEST_TIMEOUT
                    )

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

        return None

    def _extract_results(self, data: Any) -> List[Dict[str, Any]]:
        """
        Extract result records from various CAROL API response formats.

        Args:
            data: Parsed JSON response

        Returns:
            List of record dictionaries
        """
        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            # Try common response envelope keys
            for key in [
                "Results",
                "results",
                "Data",
                "data",
                "Items",
                "items",
                "Records",
                "records",
                "Investigations",
                "investigations",
            ]:
                if key in data and isinstance(data[key], list):
                    return data[key]

        return []

    def _extract_total_count(self, data: Any) -> Optional[int]:
        """
        Extract total record count from API response.

        Args:
            data: Parsed JSON response

        Returns:
            Total count or None
        """
        if not isinstance(data, dict):
            return None

        for key in [
            "TotalCount",
            "totalCount",
            "Total",
            "total",
            "TotalRecords",
            "totalRecords",
            "ResultCount",
            "resultCount",
        ]:
            if key in data:
                try:  # noqa: SIM105
                    return int(data[key])
                except (ValueError, TypeError):
                    pass

        # Check nested pagination object
        pagination = data.get("Pagination", data.get("pagination", {}))
        if isinstance(pagination, dict):
            for key in ["TotalRecords", "totalRecords", "Total", "total"]:
                if key in pagination:
                    try:  # noqa: SIM105
                        return int(pagination[key])
                    except (ValueError, TypeError):
                        pass

        return None

    def _parse_carol_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a CAROL API record into standardized format.

        Handles multiple possible field name conventions from the CAROL API.

        Args:
            record: Raw API record

        Returns:
            Parsed record dict or None if invalid
        """
        # Extract NTSB ID
        ntsb_id = self._get_field(
            record,
            [
                "NtsbNumber",
                "ntsb_number",
                "NTSB_NUMBER",
                "NtsbId",
                "ntsb_id",
                "Id",
                "id",
                "MKEY",
            ],
        )

        if not ntsb_id:
            return None

        # Extract event date
        event_date = self._get_field(
            record,
            ["EventDate", "event_date", "EVENT_DATE", "Date", "date", "AccidentDate"],
        )
        if event_date:
            event_date = self._normalize_date(event_date)

        parsed = {
            "ntsb_id": str(ntsb_id).strip(),
            "event_date": event_date,
            "city": self._get_field(record, ["City", "city", "CITY"]),
            "state": self._get_field(record, ["State", "state", "STATE"]),
            "country": self._get_field(
                record, ["Country", "country", "COUNTRY"], default="USA"
            ),
            "location_description": self._get_field(
                record,
                [
                    "Location",
                    "location",
                    "LOCATION",
                    "LocationDescription",
                    "locationDescription",
                ],
            ),
            "latitude": self._get_float(record, ["Latitude", "latitude", "LAT", "Lat"]),
            "longitude": self._get_float(
                record, ["Longitude", "longitude", "LON", "Lon", "Long"]
            ),
            "mode": self._get_field(record, ["Mode", "mode", "MODE"], default="Marine"),
            "event_type": self._get_field(
                record,
                [
                    "EventType",
                    "event_type",
                    "EVENT_TYPE",
                    "AccidentType",
                    "accident_type",
                    "ACCIDENT_TYPE",
                    "Type",
                    "type",
                ],
            ),
            "vessel_name": self._get_field(
                record, ["VesselName", "vessel_name", "VESSEL_NAME", "Vessel"]
            ),
            "vessel_type": self._get_field(
                record, ["VesselType", "vessel_type", "VESSEL_TYPE"]
            ),
            "fatalities": self._get_int(
                record, ["Fatalities", "fatalities", "FATALITIES", "Fatal"]
            ),
            "injuries": self._get_int(
                record, ["Injuries", "injuries", "INJURIES", "Injured"]
            ),
            "status": self._get_field(
                record,
                [
                    "Status",
                    "status",
                    "STATUS",
                    "InvestigationStatus",
                    "investigation_status",
                ],
            ),
            "probable_cause": self._get_field(
                record,
                [
                    "ProbableCause",
                    "probable_cause",
                    "PROBABLE_CAUSE",
                    "Synopsis",
                    "synopsis",
                ],
            ),
            "report_url": self._build_report_url(ntsb_id),
            "scraped_at": datetime.utcnow().isoformat(),
        }

        return parsed

    def _get_field(
        self,
        record: Dict[str, Any],
        keys: List[str],
        default: Optional[str] = None,
    ) -> Optional[str]:
        """Extract a string field trying multiple key names."""
        for key in keys:
            value = record.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return default

    def _get_float(self, record: Dict[str, Any], keys: List[str]) -> Optional[float]:
        """Extract a float field trying multiple key names."""
        for key in keys:
            value = record.get(key)
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    continue
        return None

    def _get_int(self, record: Dict[str, Any], keys: List[str]) -> Optional[int]:
        """Extract an integer field trying multiple key names."""
        for key in keys:
            value = record.get(key)
            if value is not None:
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    continue
        return None

    def _normalize_date(self, date_str: Any) -> Optional[str]:
        """Normalize a date value to YYYY-MM-DD format."""
        if date_str is None:
            return None

        date_str = str(date_str).strip()

        # Try common date formats
        for fmt in (
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%m/%d/%Y",
            "%m/%d/%Y %H:%M:%S",
            "%d-%b-%Y",
        ):
            try:
                return datetime.strptime(
                    date_str.split("T")[0] if "T" in date_str else date_str,
                    fmt.split("T")[0],
                ).strftime("%Y-%m-%d")
            except ValueError:
                continue

        # Return as-is if no format matched
        return date_str[:10] if len(date_str) >= 10 else date_str

    def _build_report_url(self, ntsb_id: str) -> str:
        """Build a CAROL landing page URL for an investigation."""
        return f"{CAROL_BASE_URL}/carol-main-public/landing-page?ntsb_number={ntsb_id}"

    def _write_csv(self, output_file: Path) -> Path:
        """
        Write collected records to CSV.

        Args:
            output_file: Path to output CSV file

        Returns:
            Path to the written file
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self._records)

        logger.info(f"Wrote {len(self._records)} records to {output_file}")

        # Also save raw JSON for debugging
        json_file = output_file.with_suffix(".json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self._records, f, indent=2, default=str)

        return output_file

    def _write_manual_guide(self) -> Path:
        """
        Write manual export guide when API access is unavailable.

        Returns:
            Path to the guide file
        """
        guide_path = self.output_dir / "NTSB_CAROL_MANUAL_EXPORT_GUIDE.md"

        guide_content = """# NTSB CAROL Manual Export Guide

The automated NTSB CAROL API acquisition was unable to connect.
Follow these steps to manually export marine investigation data.

## Steps

1. **Open CAROL Query Builder**
   Navigate to: https://data.ntsb.gov/carol-main-public/query-builder

2. **Set Search Criteria**
   - Mode: **Marine**
   - Date Range: 2001-01-01 to present
   - Leave other fields empty for all results

3. **Execute Search**
   Click "Submit" to run the query

4. **Export Results**
   - Click "Export" or "Download" button
   - Select CSV format
   - Save as `ntsb_marine_investigations.csv`

5. **Place File**
   Copy the downloaded CSV to:
   `{output_dir}/ntsb_marine_investigations.csv`

6. **Process the Export**
   Run the processing command:
   ```bash
   uv run python -c "
   from worldenergydata.marine_safety.acquirers.ntsb_carol_acquirer import NTSBCAROLAcquirer
   acquirer = NTSBCAROLAcquirer(output_dir='{output_dir}')
   acquirer.process_export('{output_dir}/ntsb_marine_investigations.csv')
   "
   ```

## Expected CAROL CSV Columns

The CAROL export typically includes:
- NTSB Number / MKEY
- Event Date
- City, State, Country
- Mode (should be "Marine")
- Event Type / Accident Type
- Vessel Name, Vessel Type
- Fatalities, Injuries
- Status
- Probable Cause / Synopsis

## Alternative: NTSB Data Download

NTSB also provides downloadable datasets at:
https://data.ntsb.gov/avdata

While primarily aviation-focused, check for marine data availability.
""".format(
            output_dir=self.output_dir
        )

        guide_path.write_text(guide_content, encoding="utf-8")
        return guide_path

    def process_export(self, input_file: str, output_dir: Optional[str] = None) -> Path:
        """
        Process a manually exported CAROL CSV file.

        Reads the exported CSV, normalizes field names, filters for marine
        mode, and writes a standardized output CSV.

        Args:
            input_file: Path to the manually exported CSV
            output_dir: Optional output directory (defaults to self.output_dir)

        Returns:
            Path to the processed CSV file
        """
        import pandas as pd

        input_path = Path(input_file)
        out_dir = Path(output_dir) if output_dir else self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Processing CAROL export: {input_path}")

        df = pd.read_csv(input_path, encoding="utf-8-sig")
        logger.info(f"Read {len(df)} records from export file")

        # Normalize column names to uppercase for matching
        df.columns = [col.upper().strip() for col in df.columns]

        # Filter for marine mode if mode column exists
        mode_col = None
        for col in ["MODE", "TRANSPORTATION_MODE"]:
            if col in df.columns:
                mode_col = col
                break

        if mode_col:
            original_count = len(df)
            df = df[df[mode_col].str.upper().str.strip().isin(["MARINE", "MAR"])]
            logger.info(
                f"Filtered to {len(df)} marine records (from {original_count} total)"
            )

        # Map columns to standardized names
        column_mapping = {
            "NTSB_NUMBER": "ntsb_id",
            "NTSBID": "ntsb_id",
            "NTSB_ID": "ntsb_id",
            "NTSB_NO": "ntsb_id",
            "MKEY": "ntsb_id",
            "EVENT_DATE": "event_date",
            "EVENTDATE": "event_date",
            "ACCIDENT_DATE": "event_date",
            "DATE": "event_date",
            "CITY": "city",
            "STATE": "state",
            "COUNTRY": "country",
            "LOCATION": "location_description",
            "LOCATION_DESCRIPTION": "location_description",
            "LATITUDE": "latitude",
            "LAT": "latitude",
            "LONGITUDE": "longitude",
            "LON": "longitude",
            "MODE": "mode",
            "TRANSPORTATION_MODE": "mode",
            "EVENT_TYPE": "event_type",
            "EVENTTYPE": "event_type",
            "ACCIDENT_TYPE": "event_type",
            "TYPE": "event_type",
            "VESSEL_NAME": "vessel_name",
            "VESSELNAME": "vessel_name",
            "VESSEL_TYPE": "vessel_type",
            "VESSELTYPE": "vessel_type",
            "FATALITIES": "fatalities",
            "FATAL": "fatalities",
            "INJURIES": "injuries",
            "INJURED": "injuries",
            "STATUS": "status",
            "INVESTIGATION_STATUS": "status",
            "PROBABLE_CAUSE": "probable_cause",
            "PROBABLECAUSE": "probable_cause",
            "SYNOPSIS": "probable_cause",
        }

        # Apply first matching column mapping
        renamed = {}
        for old_col in df.columns:
            if old_col in column_mapping:
                new_name = column_mapping[old_col]
                if new_name not in renamed.values():
                    renamed[old_col] = new_name

        df = df.rename(columns=renamed)

        # Add metadata columns
        if "scraped_at" not in df.columns:
            df["scraped_at"] = datetime.utcnow().isoformat()

        if "report_url" not in df.columns and "ntsb_id" in df.columns:
            df["report_url"] = df["ntsb_id"].apply(
                lambda x: self._build_report_url(str(x)) if pd.notna(x) else ""
            )

        # Select and reorder columns (only those that exist)
        available_cols = [c for c in CSV_COLUMNS if c in df.columns]
        df_out = df[available_cols]

        output_file = out_dir / "ntsb_marine_investigations.csv"
        df_out.to_csv(output_file, index=False, encoding="utf-8")
        logger.info(f"Processed export saved to: {output_file} ({len(df_out)} records)")

        return output_file


def main():
    """CLI entry point for NTSB CAROL data acquisition."""
    parser = argparse.ArgumentParser(
        description="Acquire NTSB CAROL marine investigation data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download NTSB marine data
  uv run python -m worldenergydata.marine_safety.acquirers.ntsb_carol_acquirer \\
    --output-dir data/modules/marine_safety/raw/ntsb

  # Force re-download with limited pages
  uv run python -m worldenergydata.marine_safety.acquirers.ntsb_carol_acquirer \\
    --output-dir data/modules/marine_safety/raw/ntsb --force --max-pages 10

  # Process a manually exported CSV
  uv run python -m worldenergydata.marine_safety.acquirers.ntsb_carol_acquirer \\
    --output-dir data/modules/marine_safety/raw/ntsb \\
    --process-export /path/to/manual_export.csv
        """,
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory to save downloaded data",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help=f"Maximum pages to fetch (default: {DEFAULT_MAX_PAGES})",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help=f"Results per page (default: {DEFAULT_PAGE_SIZE})",
    )
    parser.add_argument(
        "--min-date",
        type=str,
        default=DEFAULT_MIN_DATE,
        help=f"Earliest date for search (default: {DEFAULT_MIN_DATE})",
    )
    parser.add_argument(
        "--process-export",
        type=str,
        default=None,
        help="Process a manually exported CSV file instead of querying API",
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

    acquirer = NTSBCAROLAcquirer(
        output_dir=Path(args.output_dir),
        force=args.force,
        max_pages=args.max_pages,
        page_size=args.page_size,
        min_date=args.min_date,
    )

    if args.process_export:
        output = acquirer.process_export(args.process_export)
        print(f"Processed export: {output}")
    else:
        output = acquirer.acquire()
        print(f"Output: {output}")


if __name__ == "__main__":
    main()
