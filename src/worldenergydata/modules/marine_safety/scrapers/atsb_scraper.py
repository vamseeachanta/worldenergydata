# ABOUTME: Australian Transport Safety Bureau (ATSB) marine investigation scraper.
# ABOUTME: Fetches marine incident data from atsb.gov.au with pagination and checkpointing.

"""
ATSB Marine Investigation Scraper

Scrapes marine investigation reports from the Australian Transport Safety Bureau
at https://www.atsb.gov.au/publications/investigation_reports/marine.

This scraper:
- Queries the ATSB publications page for marine investigations
- Handles pagination for large result sets
- Exports data in JSON format
- Supports checkpointing for resumable scraping
- Downloads PDF reports for detailed analysis
- Validates data using established validation patterns

Note: ATSB covers Australian waters and the Southern Hemisphere.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urljoin

from worldenergydata.modules.marine_safety.config import get_config
from worldenergydata.modules.marine_safety.constants import DataSource
from worldenergydata.modules.marine_safety.exceptions import HTTPError

# Import from split modules
from worldenergydata.modules.marine_safety.scrapers.atsb_checkpoint import (
    ATSBCheckpointManager,
)
from worldenergydata.modules.marine_safety.scrapers.atsb_constants import (
    ATSB_ID_PATTERN,
    AUSTRALIAN_STATES,
    BASE_URL,
    DEFAULT_MIN_DATE_DAY,
    DEFAULT_MIN_DATE_MONTH,
    DEFAULT_MIN_DATE_YEAR,
    DEFAULT_PAGE_SIZE,
    INCIDENT_TYPE_MAPPING,
    MARINE_URL,
    MAX_PAGES,
    PDF_BASE_URL,
    STATUS_MAPPING,
)
from worldenergydata.modules.marine_safety.scrapers.atsb_exceptions import (
    ATSBConnectionError,
    ATSBDataValidationError,
)
from worldenergydata.modules.marine_safety.scrapers.atsb_extractor import (
    extract_investigation_details,
    map_incident_type,
    normalize_australian_state,
    parse_casualty_count,
)
from worldenergydata.modules.marine_safety.scrapers.atsb_parser import (
    map_status,
    parse_date,
    parse_investigation_entry,
    parse_investigation_list,
)
from worldenergydata.modules.marine_safety.scrapers.atsb_transformer import (
    transform_investigation,
)
from worldenergydata.modules.marine_safety.scrapers.atsb_validator import (
    validate_atsb_id,
    validate_investigation_data,
)
from worldenergydata.modules.marine_safety.scrapers.base_scraper import BaseScraper

# Re-export for backward compatibility
__all__ = [
    "ATSBScraper",
    "ATSBDataValidationError",
    "ATSBConnectionError",
    "ATSB_ID_PATTERN",
    "AUSTRALIAN_STATES",
    "INCIDENT_TYPE_MAPPING",
    "STATUS_MAPPING",
]


class ATSBScraper(BaseScraper):
    """
    Scraper for ATSB Marine Investigation Reports.

    Queries the ATSB publications page at
    https://www.atsb.gov.au/publications/investigation_reports/marine
    for marine investigations.

    Features:
        - Scrapes ATSB marine investigation listings
        - Handles pagination for large result sets
        - Downloads PDF reports for detailed analysis
        - Checkpoint support for resumable scraping
        - Comprehensive data validation
        - Australian state code normalization

    Attributes:
        BASE_URL: Base URL for ATSB website
        MARINE_URL: URL for marine investigation reports
        PDF_BASE_URL: Base URL for PDF downloads
    """

    # Class-level constants for backward compatibility
    BASE_URL = BASE_URL
    MARINE_URL = MARINE_URL
    PDF_BASE_URL = PDF_BASE_URL
    ATSB_ID_PATTERN = ATSB_ID_PATTERN
    AUSTRALIAN_STATES = AUSTRALIAN_STATES
    INCIDENT_TYPE_MAPPING = INCIDENT_TYPE_MAPPING
    STATUS_MAPPING = STATUS_MAPPING

    def __init__(
        self,
        checkpoint_dir: Optional[Path] = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        min_date: Optional[date] = None,
        download_pdfs: bool = False,
    ) -> None:
        """
        Initialize ATSB scraper.

        Args:
            checkpoint_dir: Directory for checkpoint files. If None, uses
                the default cache path from configuration.
            page_size: Number of results per page for pagination.
                Default is 20 (ATSB's default).
            min_date: Minimum date for scraping. ATSB marine data is
                available from approximately 2003 onwards.
            download_pdfs: If True, download PDF reports.
        """
        super().__init__(
            source=DataSource.ATSB,
            base_url=BASE_URL,
            name="atsb_marine_scraper",
        )

        self.config_obj = get_config()
        checkpoint_path = checkpoint_dir or self.config_obj.storage.cache_path / "atsb"

        self.page_size = page_size
        self.min_date = min_date or date(
            DEFAULT_MIN_DATE_YEAR,
            DEFAULT_MIN_DATE_MONTH,
            DEFAULT_MIN_DATE_DAY,
        )
        self.download_pdfs = download_pdfs

        # Initialize checkpoint manager
        self._checkpoint = ATSBCheckpointManager(checkpoint_path)

        # PDF download directory
        self.pdf_dir = checkpoint_path / "pdfs"
        if download_pdfs:
            self.pdf_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            f"ATSB Scraper initialized (page_size={self.page_size}, "
            f"min_date={self.min_date}, download_pdfs={download_pdfs})"
        )

    # Backward compatibility properties
    @property
    def checkpoint_dir(self) -> Path:
        """Get checkpoint directory."""
        return self._checkpoint.checkpoint_dir

    @property
    def _processed_ids(self) -> set:
        """Get processed IDs for backward compatibility."""
        return self._checkpoint.processed_ids

    @property
    def _last_checkpoint_time(self) -> Optional[datetime]:
        """Get last checkpoint time for backward compatibility."""
        return self._checkpoint.last_checkpoint_time

    def _load_checkpoint(self) -> None:
        """Load checkpoint data from disk if available."""
        self._checkpoint.load()

    def _save_checkpoint(self, force: bool = False) -> None:
        """Save checkpoint data to disk."""
        self._checkpoint.save(force=force)

    def _normalize_australian_state(self, state: Optional[str]) -> Optional[str]:
        """Normalize Australian state names to standard codes."""
        return normalize_australian_state(state)

    def _fetch_investigation_list(self, page: int = 1) -> str:
        """
        Fetch investigation listing page from ATSB.

        Args:
            page: Page number (1-indexed)

        Returns:
            HTML content of the page

        Raises:
            HTTPError: If HTTP request fails
        """
        params = {
            "page": page,
            "items_per_page": self.page_size,
        }

        url = f"{MARINE_URL}?{urlencode(params)}"
        self.logger.debug(f"Fetching page {page}: {url}")

        try:
            response = self._make_request(url, method="GET")
            return response.text

        except Exception as e:
            raise HTTPError(
                url=urljoin(self.base_url, url),
                status_code=0,
                message=f"Failed to fetch ATSB page: {e}",
            )

    def _parse_investigation_list(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse investigation listing HTML to extract investigation metadata."""
        soup = self._parse_html(html_content)
        return parse_investigation_list(
            soup,
            extract_text_fn=self._extract_text,
            extract_attribute_fn=self._extract_attribute,
        )

    def _parse_investigation_entry(self, entry: Any) -> Optional[Dict[str, Any]]:
        """Parse a single investigation entry from HTML."""
        return parse_investigation_entry(
            entry,
            extract_text_fn=self._extract_text,
            extract_attribute_fn=self._extract_attribute,
        )

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string in various formats."""
        return parse_date(date_str)

    def _map_status(self, status_text: Optional[str]) -> str:
        """Map ATSB status text to IncidentStatus enum value."""
        return map_status(status_text)

    def _fetch_investigation_details(self, report_url: str) -> Dict[str, Any]:
        """Fetch detailed investigation data from report page."""
        try:
            response = self._make_request(report_url, method="GET")
            html_content = response.text
        except Exception as e:
            self.logger.warning(f"Failed to fetch investigation details: {e}")
            return {}

        soup = self._parse_html(html_content)
        return extract_investigation_details(soup, self._extract_text)

    def _map_incident_type(self, incident_type: str) -> str:
        """Map ATSB incident type to IncidentType enum value."""
        return map_incident_type(incident_type)

    def _parse_casualty_count(self, text: str) -> int:
        """Parse casualty count from text."""
        return parse_casualty_count(text)

    def _download_pdf(self, pdf_url: str, atsb_id: str) -> Optional[Path]:
        """
        Download PDF report.

        Args:
            pdf_url: URL of the PDF
            atsb_id: ATSB investigation ID for naming

        Returns:
            Path to downloaded PDF or None if failed
        """
        if not self.download_pdfs:
            return None

        filename = f"{atsb_id.replace('/', '-')}.pdf"
        pdf_path = self.pdf_dir / filename

        if pdf_path.exists():
            self.logger.debug(f"PDF already exists: {pdf_path}")
            return pdf_path

        try:
            response = self._make_request(pdf_url, method="GET")

            with open(pdf_path, "wb") as f:
                f.write(response.content)

            self.logger.info(f"Downloaded PDF: {pdf_path}")
            return pdf_path

        except Exception as e:
            self.logger.warning(f"Failed to download PDF {pdf_url}: {e}")
            return None

    def _parse_investigation(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw investigation data into standardized format."""
        return transform_investigation(raw_data)

    def scrape(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scrape marine investigations from ATSB website.

        Args:
            start_date: Start date for scraping. If None, uses min_date.
            end_date: End date for scraping. If None, uses today.

        Returns:
            List of investigation dictionaries

        Raises:
            HTTPError: If HTTP requests fail
            ATSBConnectionError: If connection to ATSB fails
            ParsingError: If response parsing fails
        """
        # Convert datetime to date if needed
        if start_date is None:
            start_date_obj = self.min_date
        elif isinstance(start_date, datetime):
            start_date_obj = start_date.date()
        else:
            start_date_obj = start_date

        if end_date is None:
            end_date_obj = date.today()
        elif isinstance(end_date, datetime):
            end_date_obj = end_date.date()
        else:
            end_date_obj = end_date

        # Validate date range
        if start_date_obj < self.min_date:
            self.logger.warning(
                f"Start date {start_date_obj} before min date {self.min_date}, "
                f"using min date"
            )
            start_date_obj = self.min_date

        if end_date_obj < start_date_obj:
            raise ValueError(
                f"End date {end_date_obj} before start date {start_date_obj}"
            )

        self.logger.info(f"Starting ATSB scrape: {start_date_obj} to {end_date_obj}")

        # Load checkpoint
        self._load_checkpoint()

        investigations: List[Dict[str, Any]] = []
        page = 1

        try:
            while page <= MAX_PAGES:
                self.logger.info(f"Fetching page {page}")

                try:
                    html_content = self._fetch_investigation_list(page)
                except HTTPError as e:
                    if e.details and e.details.get("status_code") == 404:
                        self.logger.warning("No more results (404)")
                        break
                    raise

                page_investigations = self._parse_investigation_list(html_content)

                if not page_investigations:
                    self.logger.debug(f"No investigations on page {page}")
                    break

                for raw_investigation in page_investigations:
                    atsb_id = raw_investigation.get("atsb_id")

                    if not atsb_id:
                        continue

                    # Skip if already processed
                    if self._checkpoint.is_processed(atsb_id):
                        self.logger.debug(f"Skipping processed: {atsb_id}")
                        continue

                    # Check date filter
                    occurrence_date = raw_investigation.get("occurrence_date")
                    if occurrence_date:
                        if occurrence_date < start_date_obj:
                            self.logger.debug(f"Skipping {atsb_id} - before start date")
                            continue
                        if occurrence_date > end_date_obj:
                            self.logger.debug(f"Skipping {atsb_id} - after end date")
                            continue

                    try:
                        # Fetch detailed information
                        if raw_investigation.get("report_url"):
                            details = self._fetch_investigation_details(
                                raw_investigation["report_url"]
                            )
                            raw_investigation.update(details)

                        # Download PDF if enabled
                        if self.download_pdfs and raw_investigation.get("pdf_url"):
                            pdf_path = self._download_pdf(
                                raw_investigation["pdf_url"], atsb_id
                            )
                            raw_investigation["pdf_path"] = pdf_path

                        # Parse and validate
                        parsed = self._parse_investigation(raw_investigation)

                        if self.validate_data(parsed):
                            investigations.append(parsed)
                            self._checkpoint.add_processed_id(atsb_id)
                        else:
                            self.logger.warning(f"Validation failed for {atsb_id}")

                    except Exception as e:
                        self.logger.error(f"Error processing {atsb_id}: {e}")
                        continue

                # Save checkpoint after each page
                self._save_checkpoint()

                page += 1

        except Exception as e:
            self.logger.error(f"Scraping error: {e}")
            # Save checkpoint on error
            self._save_checkpoint(force=True)
            raise

        finally:
            # Final checkpoint save
            self._save_checkpoint(force=True)

        self.logger.info(f"Scraping complete: {len(investigations)} new investigations")

        return investigations

    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate scraped investigation data.

        Args:
            data: Dictionary containing investigation data

        Returns:
            True if data is valid, False otherwise

        Raises:
            ATSBDataValidationError: If validation fails with critical errors
        """
        return validate_investigation_data(data, self.min_date)

    def _validate_atsb_id(self, atsb_id: str) -> bool:
        """Validate ATSB investigation ID format."""
        return validate_atsb_id(atsb_id)

    def clear_checkpoint(self) -> None:
        """Clear checkpoint data to start fresh."""
        self._checkpoint.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about scraped data.

        Returns:
            Dictionary of scraping statistics
        """
        stats = self._checkpoint.get_statistics()
        stats.update(
            {
                "source": DataSource.ATSB.value,
                "total_requests": self._request_count,
                "pdfs_downloaded": (
                    len(list(self.pdf_dir.glob("*.pdf")))
                    if self.pdf_dir.exists()
                    else 0
                ),
            }
        )
        return stats

    def export_to_json(
        self,
        data: List[Dict[str, Any]],
        output_path: Path,
        include_raw: bool = False,
    ) -> None:
        """
        Export scraped data to JSON file.

        Args:
            data: List of investigation dictionaries
            output_path: Path to output file
            include_raw: If True, include raw_data field in export
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        export_data = data
        if not include_raw:
            export_data = [
                {k: v for k, v in record.items() if k != "raw_data"} for record in data
            ]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)

        self.logger.info(f"Exported {len(data)} records to {output_path}")
