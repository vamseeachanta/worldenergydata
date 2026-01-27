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
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlencode, urljoin

from worldenergydata.modules.marine_safety.config import get_config
from worldenergydata.modules.marine_safety.constants import (
    DataSource,
    IncidentStatus,
    IncidentType,
    SeverityLevel,
)
from worldenergydata.modules.marine_safety.exceptions import (
    HTTPError,
    ParsingError,
    RateLimitError,
    ScraperError,
    TimeoutError,
    ValidationError,
)
from worldenergydata.modules.marine_safety.scrapers.base_scraper import BaseScraper
from worldenergydata.modules.marine_safety.utils.logger import get_logger


class ATSBDataValidationError(ValidationError):
    """Raised when ATSB data fails validation."""

    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
        atsb_id: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """
        Initialize ATSB data validation error.

        Args:
            field: Name of the field that failed validation
            value: The invalid value
            reason: Reason for validation failure
            atsb_id: Optional ATSB investigation ID
            message: Optional custom message
        """
        if message is None:
            id_info = f" (ATSB ID: {atsb_id})" if atsb_id else ""
            message = f"Invalid ATSB data for '{field}'{id_info}: {reason}"
        super().__init__(
            message=message,
            error_code="ATSB_VALIDATION_ERROR",
            details={
                "field": field,
                "value": value,
                "reason": reason,
                "atsb_id": atsb_id,
            },
        )


class ATSBConnectionError(ScraperError):
    """Raised when connection to ATSB website fails."""

    def __init__(
        self,
        message: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize ATSB connection error.

        Args:
            message: Optional custom message
            cause: Optional original exception
        """
        if message is None:
            message = "Failed to connect to ATSB website"
        super().__init__(
            message=message,
            error_code="ATSB_CONNECTION_ERROR",
            details={"cause": str(cause) if cause else None},
            cause=cause,
        )


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

    BASE_URL = "https://www.atsb.gov.au"
    MARINE_URL = "/publications/investigation_reports/marine"
    PDF_BASE_URL = "https://www.atsb.gov.au/publications"

    # ATSB Investigation ID pattern: e.g., MO-2022-001, 342-MO-2021-001
    ATSB_ID_PATTERN = re.compile(
        r"^(?:\d{3}-)?(?:MO|MR)-?\d{4}-?\d{3}$",
        re.IGNORECASE,
    )

    # Australian state codes
    AUSTRALIAN_STATES: Dict[str, str] = {
        "nsw": "NSW",
        "new south wales": "NSW",
        "vic": "VIC",
        "victoria": "VIC",
        "qld": "QLD",
        "queensland": "QLD",
        "wa": "WA",
        "western australia": "WA",
        "sa": "SA",
        "south australia": "SA",
        "tas": "TAS",
        "tasmania": "TAS",
        "nt": "NT",
        "northern territory": "NT",
        "act": "ACT",
        "australian capital territory": "ACT",
    }

    # Incident type mapping from ATSB categories
    INCIDENT_TYPE_MAPPING: Dict[str, IncidentType] = {
        "collision": IncidentType.COLLISION,
        "contact": IncidentType.COLLISION,
        "striking": IncidentType.COLLISION,
        "grounding": IncidentType.GROUNDING,
        "stranding": IncidentType.GROUNDING,
        "fire": IncidentType.FIRE,
        "explosion": IncidentType.EXPLOSION,
        "capsizing": IncidentType.CAPSIZING,
        "capsize": IncidentType.CAPSIZING,
        "flooding": IncidentType.FLOODING,
        "foundering": IncidentType.FLOODING,
        "sinking": IncidentType.CAPSIZING,
        "structural failure": IncidentType.STRUCTURAL_FAILURE,
        "hull failure": IncidentType.STRUCTURAL_FAILURE,
        "equipment failure": IncidentType.EQUIPMENT_FAILURE,
        "machinery failure": IncidentType.EQUIPMENT_FAILURE,
        "loss of propulsion": IncidentType.LOSS_OF_PROPULSION,
        "propulsion failure": IncidentType.LOSS_OF_PROPULSION,
        "loss of steering": IncidentType.LOSS_OF_CONTROL,
        "loss of control": IncidentType.LOSS_OF_CONTROL,
        "man overboard": IncidentType.PERSONNEL_INJURY,
        "person overboard": IncidentType.PERSONNEL_INJURY,
        "fall overboard": IncidentType.PERSONNEL_INJURY,
        "injury": IncidentType.PERSONNEL_INJURY,
        "fatality": IncidentType.FATALITY,
        "death": IncidentType.FATALITY,
        "pollution": IncidentType.POLLUTION,
        "oil spill": IncidentType.POLLUTION,
        "environmental": IncidentType.ENVIRONMENTAL,
        "weather": IncidentType.WEATHER_RELATED,
        "heavy weather": IncidentType.WEATHER_RELATED,
        "storm": IncidentType.WEATHER_RELATED,
        "cyclone": IncidentType.WEATHER_RELATED,
    }

    # Status mapping from ATSB investigation status
    STATUS_MAPPING: Dict[str, IncidentStatus] = {
        "active": IncidentStatus.UNDER_INVESTIGATION,
        "open": IncidentStatus.UNDER_INVESTIGATION,
        "preliminary": IncidentStatus.PRELIMINARY_REPORT,
        "interim": IncidentStatus.PRELIMINARY_REPORT,
        "final": IncidentStatus.FINAL_REPORT,
        "completed": IncidentStatus.FINAL_REPORT,
        "closed": IncidentStatus.CLOSED,
    }

    def __init__(
        self,
        checkpoint_dir: Optional[Path] = None,
        page_size: int = 20,
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
            base_url=self.BASE_URL,
            name="atsb_marine_scraper",
        )

        self.config_obj = get_config()
        self.checkpoint_dir = (
            checkpoint_dir or self.config_obj.storage.cache_path / "atsb"
        )
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.page_size = page_size
        self.min_date = min_date or date(2003, 1, 1)
        self.download_pdfs = download_pdfs

        # PDF download directory
        self.pdf_dir = self.checkpoint_dir / "pdfs"
        if download_pdfs:
            self.pdf_dir.mkdir(parents=True, exist_ok=True)

        # Checkpointing state
        self._checkpoint_file = self.checkpoint_dir / "atsb_scraper_checkpoint.json"
        self._processed_ids: Set[str] = set()
        self._last_checkpoint_time: Optional[datetime] = None

        self.logger.info(
            f"ATSB Scraper initialized (page_size={self.page_size}, "
            f"min_date={self.min_date}, download_pdfs={download_pdfs})"
        )

    def _load_checkpoint(self) -> None:
        """Load checkpoint data from disk if available."""
        if not self._checkpoint_file.exists():
            self.logger.debug("No checkpoint file found")
            return

        try:
            with open(self._checkpoint_file, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)

            self._processed_ids = set(checkpoint.get("processed_ids", []))
            last_time = checkpoint.get("last_checkpoint_time")
            if last_time:
                self._last_checkpoint_time = datetime.fromisoformat(last_time)

            self.logger.info(
                f"Loaded checkpoint: {len(self._processed_ids)} processed IDs, "
                f"last checkpoint: {self._last_checkpoint_time}"
            )

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to load checkpoint: {e}")

    def _save_checkpoint(self, force: bool = False) -> None:
        """
        Save checkpoint data to disk.

        Args:
            force: If True, save regardless of time since last checkpoint.
                Otherwise, saves at most once per minute.
        """
        now = datetime.utcnow()
        if (
            not force
            and self._last_checkpoint_time
            and (now - self._last_checkpoint_time).total_seconds() < 60
        ):
            return

        checkpoint = {
            "processed_ids": list(self._processed_ids),
            "last_checkpoint_time": now.isoformat(),
            "total_processed": len(self._processed_ids),
        }

        try:
            with open(self._checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, indent=2)

            self._last_checkpoint_time = now
            self.logger.debug(
                f"Checkpoint saved: {len(self._processed_ids)} processed IDs"
            )

        except IOError as e:
            self.logger.error(f"Failed to save checkpoint: {e}")

    def _normalize_australian_state(self, state: Optional[str]) -> Optional[str]:
        """
        Normalize Australian state names to standard codes.

        Args:
            state: State name or code

        Returns:
            Normalized state code (e.g., NSW, VIC) or original if not recognized
        """
        if not state:
            return None

        state_lower = state.lower().strip()
        return self.AUSTRALIAN_STATES.get(state_lower, state.upper())

    def _fetch_investigation_list(
        self,
        page: int = 1,
    ) -> str:
        """
        Fetch investigation listing page from ATSB.

        Args:
            page: Page number (1-indexed)

        Returns:
            HTML content of the page

        Raises:
            HTTPError: If HTTP request fails
        """
        # ATSB uses query parameters for pagination
        params = {
            "page": page,
            "items_per_page": self.page_size,
        }

        url = f"{self.MARINE_URL}?{urlencode(params)}"

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
        """
        Parse investigation listing HTML to extract investigation metadata.

        Args:
            html_content: HTML content of investigation listing page

        Returns:
            List of investigation metadata dictionaries
        """
        soup = self._parse_html(html_content)
        investigations: List[Dict[str, Any]] = []

        # Find investigation entries
        # ATSB uses various CSS classes for investigation listings
        entries = soup.select(
            ".view-content .views-row, .investigation-item, .report-item"
        )

        if not entries:
            # Try alternative selectors
            entries = soup.select("article, .node--type-investigation")

        for entry in entries:
            try:
                investigation = self._parse_investigation_entry(entry)
                if investigation:
                    investigations.append(investigation)
            except Exception as e:
                self.logger.warning(f"Failed to parse investigation entry: {e}")
                continue

        return investigations

    def _parse_investigation_entry(self, entry: Any) -> Optional[Dict[str, Any]]:
        """
        Parse a single investigation entry from HTML.

        Args:
            entry: BeautifulSoup element for the investigation

        Returns:
            Dictionary of investigation metadata or None
        """
        # Extract ATSB ID (report number)
        atsb_id = None
        id_selectors = [
            ".field--name-field-report-number",
            ".report-number",
            ".investigation-id",
            "h2 a",
            "h3 a",
        ]
        for selector in id_selectors:
            atsb_id = self._extract_text(entry, selector)
            if atsb_id:
                # Clean up the ID
                atsb_id = re.sub(r"[^\w-]", "", atsb_id.strip())
                break

        if not atsb_id:
            return None

        # Extract title
        title = self._extract_text(entry, "h2, h3, .title, .field--name-title")

        # Extract report URL
        report_url = self._extract_attribute(entry, "h2 a, h3 a, .title a", "href")
        if report_url:
            report_url = urljoin(self.base_url, report_url)

        # Extract date
        date_str = self._extract_text(
            entry, ".date, .field--name-field-occurrence-date, .occurrence-date"
        )
        occurrence_date = self._parse_date(date_str)

        # Extract location
        location = self._extract_text(entry, ".location, .field--name-field-location")

        # Extract vessel name
        vessel_name = self._extract_text(
            entry, ".vessel-name, .field--name-field-vessel-name"
        )

        # Extract status
        status_text = self._extract_text(
            entry, ".status, .field--name-field-investigation-status"
        )
        status = self._map_status(status_text)

        # Extract PDF link if available
        pdf_url = self._extract_attribute(entry, "a[href*='.pdf'], .pdf-link a", "href")
        if pdf_url:
            pdf_url = urljoin(self.base_url, pdf_url)

        return {
            "atsb_id": atsb_id,
            "title": title,
            "report_url": report_url,
            "occurrence_date": occurrence_date,
            "location": location,
            "vessel_name": vessel_name,
            "status": status,
            "pdf_url": pdf_url,
        }

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """
        Parse date string in various formats.

        Args:
            date_str: Date string

        Returns:
            Parsed date or None
        """
        if not date_str:
            return None

        date_str = date_str.strip()

        # Try common Australian date formats
        formats = [
            "%d %B %Y",  # 15 January 2022
            "%d %b %Y",  # 15 Jan 2022
            "%d/%m/%Y",  # 15/01/2022
            "%Y-%m-%d",  # 2022-01-15
            "%B %d, %Y",  # January 15, 2022
            "%b %d, %Y",  # Jan 15, 2022
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        self.logger.warning(f"Could not parse date: {date_str}")
        return None

    def _map_status(self, status_text: Optional[str]) -> str:
        """
        Map ATSB status text to IncidentStatus enum value.

        Args:
            status_text: Status text from ATSB

        Returns:
            IncidentStatus value as string
        """
        if not status_text:
            return IncidentStatus.REPORTED.value

        status_lower = status_text.lower().strip()

        for key, value in self.STATUS_MAPPING.items():
            if key in status_lower:
                return value.value

        return IncidentStatus.REPORTED.value

    def _fetch_investigation_details(self, report_url: str) -> Dict[str, Any]:
        """
        Fetch detailed investigation data from report page.

        Args:
            report_url: URL of the investigation report page

        Returns:
            Dictionary of detailed investigation data
        """
        try:
            response = self._make_request(report_url, method="GET")
            html_content = response.text
        except Exception as e:
            self.logger.warning(f"Failed to fetch investigation details: {e}")
            return {}

        soup = self._parse_html(html_content)
        details: Dict[str, Any] = {}

        # Extract incident type/category
        incident_type = self._extract_text(
            soup, ".field--name-field-occurrence-type, .occurrence-type"
        )
        if incident_type:
            details["incident_type"] = self._map_incident_type(incident_type)

        # Extract narrative/description
        narrative = self._extract_text(soup, ".field--name-body, .narrative, .summary")
        if narrative:
            details["description"] = narrative[:5000]  # Limit length

        # Extract casualties
        fatalities_text = self._extract_text(
            soup, ".field--name-field-fatalities, .fatalities"
        )
        if fatalities_text:
            details["fatalities"] = self._parse_casualty_count(fatalities_text)

        injuries_text = self._extract_text(
            soup, ".field--name-field-injuries, .injuries"
        )
        if injuries_text:
            details["injuries"] = self._parse_casualty_count(injuries_text)

        # Extract vessel details
        vessel_type = self._extract_text(
            soup, ".field--name-field-vessel-type, .vessel-type"
        )
        if vessel_type:
            details["vessel_type"] = vessel_type

        flag_state = self._extract_text(
            soup, ".field--name-field-flag-state, .flag-state"
        )
        if flag_state:
            details["flag_state"] = flag_state

        gross_tonnage = self._extract_text(
            soup, ".field--name-field-gross-tonnage, .gross-tonnage"
        )
        if gross_tonnage:
            try:
                details["gross_tonnage"] = float(
                    gross_tonnage.replace(",", "").replace(" ", "")
                )
            except ValueError:
                pass

        # Extract coordinates if available
        lat = self._extract_text(soup, ".field--name-field-latitude, .latitude")
        lon = self._extract_text(soup, ".field--name-field-longitude, .longitude")

        if lat:
            try:
                details["latitude"] = float(lat.replace(",", "."))
            except ValueError:
                pass

        if lon:
            try:
                details["longitude"] = float(lon.replace(",", "."))
            except ValueError:
                pass

        # Extract state/region
        state = self._extract_text(soup, ".field--name-field-state, .state-territory")
        if state:
            details["state"] = self._normalize_australian_state(state)

        # Extract probable cause if available
        probable_cause = self._extract_text(
            soup, ".field--name-field-probable-cause, .probable-cause, .findings"
        )
        if probable_cause:
            details["probable_cause"] = probable_cause[:5000]

        return details

    def _map_incident_type(self, incident_type: str) -> str:
        """
        Map ATSB incident type to IncidentType enum value.

        Args:
            incident_type: Incident type string from ATSB

        Returns:
            IncidentType value as string
        """
        incident_lower = incident_type.lower().strip()

        # Try exact match first
        if incident_lower in self.INCIDENT_TYPE_MAPPING:
            return self.INCIDENT_TYPE_MAPPING[incident_lower].value

        # Try partial match
        for key, value in self.INCIDENT_TYPE_MAPPING.items():
            if key in incident_lower or incident_lower in key:
                return value.value

        self.logger.warning(f"Unknown ATSB incident type: {incident_type}")
        return IncidentType.OTHER.value

    def _parse_casualty_count(self, text: str) -> int:
        """
        Parse casualty count from text.

        Args:
            text: Text containing casualty information

        Returns:
            Casualty count as integer
        """
        if not text:
            return 0

        # Try to extract number from text
        match = re.search(r"(\d+)", text)
        if match:
            return int(match.group(1))

        # Check for keywords
        text_lower = text.lower()
        if "none" in text_lower or "no " in text_lower:
            return 0

        return 0

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

        # Clean filename
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
        """
        Parse raw investigation data into standardized format.

        Args:
            raw_data: Raw investigation data from scraping

        Returns:
            Standardized investigation dictionary
        """
        atsb_id = raw_data.get("atsb_id", "")

        # Parse location into components
        location_text = raw_data.get("location", "")
        city = None
        state = None

        if location_text:
            # Try to extract state from location
            parts = location_text.split(",")
            if len(parts) >= 2:
                city = parts[0].strip()
                state_part = parts[-1].strip()
                state = self._normalize_australian_state(state_part)
            else:
                city = location_text

        # Use details state if available
        if raw_data.get("state"):
            state = raw_data["state"]

        # Build location dict
        location = {
            "latitude": raw_data.get("latitude"),
            "longitude": raw_data.get("longitude"),
            "city": city,
            "state": state,
            "country": "Australia",
            "description": location_text,
        }

        # Build vessel dict
        vessel = {
            "name": raw_data.get("vessel_name"),
            "type": raw_data.get("vessel_type"),
            "flag": raw_data.get("flag_state"),
            "gross_tonnage": raw_data.get("gross_tonnage"),
        }

        # Build casualties dict
        casualties = {
            "fatalities": raw_data.get("fatalities", 0),
            "injuries": raw_data.get("injuries", 0),
            "missing": 0,
        }

        # Build report URL
        report_url = raw_data.get("report_url")

        return {
            "source": DataSource.ATSB.value,
            "source_id": atsb_id,
            "event_date": (
                raw_data.get("occurrence_date").isoformat()
                if raw_data.get("occurrence_date")
                else None
            ),
            "incident_type": raw_data.get("incident_type", IncidentType.OTHER.value),
            "status": raw_data.get("status", IncidentStatus.REPORTED.value),
            "title": raw_data.get("title", ""),
            "description": raw_data.get("description", ""),
            "location": location,
            "vessel": vessel,
            "casualties": casualties,
            "probable_cause": raw_data.get("probable_cause"),
            "report_url": report_url,
            "pdf_url": raw_data.get("pdf_url"),
            "pdf_path": (
                str(raw_data.get("pdf_path")) if raw_data.get("pdf_path") else None
            ),
            "scraped_at": datetime.utcnow().isoformat(),
            "raw_data": raw_data,
        }

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
        max_pages = 100  # Safety limit

        try:
            while page <= max_pages:
                self.logger.info(f"Fetching page {page}")

                try:
                    html_content = self._fetch_investigation_list(page)
                except HTTPError as e:
                    if e.details and e.details.get("status_code") == 404:
                        self.logger.warning("No more results (404)")
                        break
                    raise

                # Parse investigation list
                page_investigations = self._parse_investigation_list(html_content)

                if not page_investigations:
                    self.logger.debug(f"No investigations on page {page}")
                    break

                for raw_investigation in page_investigations:
                    atsb_id = raw_investigation.get("atsb_id")

                    if not atsb_id:
                        continue

                    # Skip if already processed
                    if atsb_id in self._processed_ids:
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
                            self._processed_ids.add(atsb_id)
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
        atsb_id = data.get("source_id", "")

        # Required fields
        required_fields = ["source_id", "source"]
        for field in required_fields:
            if not data.get(field):
                self.logger.warning(f"Missing required field: {field}")
                return False

        # Validate ATSB ID format
        if atsb_id and not self._validate_atsb_id(atsb_id):
            self.logger.warning(f"Invalid ATSB ID format: {atsb_id}")
            # Don't fail validation for ID format, just warn

        # Validate date if present
        event_date = data.get("event_date")
        if event_date:
            try:
                if isinstance(event_date, str):
                    parsed_date = datetime.fromisoformat(event_date).date()
                else:
                    parsed_date = event_date

                if parsed_date < self.min_date:
                    self.logger.warning(
                        f"Event date {parsed_date} before min date {self.min_date}"
                    )
                if parsed_date > date.today():
                    self.logger.warning(f"Event date {parsed_date} is in the future")
                    return False

            except (ValueError, TypeError) as e:
                self.logger.warning(f"Invalid event date format: {event_date} - {e}")

        # Validate casualties (non-negative)
        casualties = data.get("casualties", {})
        for key in ["fatalities", "injuries", "missing"]:
            value = casualties.get(key, 0)
            if isinstance(value, (int, float)) and value < 0:
                self.logger.warning(f"Negative casualty count for {key}: {value}")
                return False

        # Validate coordinates if present
        location = data.get("location", {})
        lat = location.get("latitude")
        lon = location.get("longitude")

        if lat is not None:
            try:
                lat = float(lat)
                if not -90 <= lat <= 90:
                    self.logger.warning(f"Invalid latitude: {lat}")
                    return False
            except (ValueError, TypeError):
                pass

        if lon is not None:
            try:
                lon = float(lon)
                if not -180 <= lon <= 180:
                    self.logger.warning(f"Invalid longitude: {lon}")
                    return False
            except (ValueError, TypeError):
                pass

        return True

    def _validate_atsb_id(self, atsb_id: str) -> bool:
        """
        Validate ATSB investigation ID format.

        Args:
            atsb_id: ATSB ID to validate

        Returns:
            True if valid format
        """
        if not atsb_id:
            return False

        clean_id = atsb_id.strip().upper()

        # Check against pattern
        if self.ATSB_ID_PATTERN.match(clean_id):
            return True

        # Accept more flexible patterns (e.g., MO2022001)
        if re.match(r"^(?:MO|MR)\d{7,}$", clean_id):
            return True

        return False

    def clear_checkpoint(self) -> None:
        """Clear checkpoint data to start fresh."""
        self._processed_ids.clear()
        self._last_checkpoint_time = None

        if self._checkpoint_file.exists():
            self._checkpoint_file.unlink()
            self.logger.info("Checkpoint cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about scraped data.

        Returns:
            Dictionary of scraping statistics
        """
        return {
            "source": DataSource.ATSB.value,
            "total_processed_ids": len(self._processed_ids),
            "last_checkpoint": (
                self._last_checkpoint_time.isoformat()
                if self._last_checkpoint_time
                else None
            ),
            "total_requests": self._request_count,
            "checkpoint_file": str(self._checkpoint_file),
            "pdfs_downloaded": (
                len(list(self.pdf_dir.glob("*.pdf"))) if self.pdf_dir.exists() else 0
            ),
        }

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
