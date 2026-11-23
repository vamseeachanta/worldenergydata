# ABOUTME: NTSB Marine Investigation Scraper for the CAROL query system.
# ABOUTME: Fetches marine incident data from data.ntsb.gov with pagination and checkpointing.

"""
NTSB Marine Investigation Scraper

Scrapes marine investigation reports from the NTSB CAROL (Case Analysis and
Reporting Online) system at https://data.ntsb.gov/carol-main-public.

This scraper:
- Queries the CAROL system for marine mode investigations
- Handles pagination for large result sets
- Exports data in JSON format
- Supports checkpointing for resumable scraping
- Validates data using the established validation patterns

Note: The NTSB Marine API is "Coming Soon" as of 2024. This scraper uses
the web interface with JSON export as a workaround.
"""

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlencode

from worldenergydata.marine_safety.config import get_config
from worldenergydata.marine_safety.constants import (
    DataSource,
    IncidentStatus,
    IncidentType,
)
from worldenergydata.marine_safety.exceptions import (
    HTTPError,
    ParsingError,
    ScraperError,
    ValidationError,
)
from worldenergydata.marine_safety.scrapers.base_scraper import BaseScraper


class NTSBDataValidationError(ValidationError):
    """Raised when NTSB data fails validation."""

    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
        ntsb_id: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """
        Initialize NTSB data validation error.

        Args:
            field: Name of the field that failed validation
            value: The invalid value
            reason: Reason for validation failure
            ntsb_id: Optional NTSB investigation ID
            message: Optional custom message
        """
        if message is None:
            id_info = f" (NTSB ID: {ntsb_id})" if ntsb_id else ""
            message = f"Invalid NTSB data for '{field}'{id_info}: {reason}"
        super().__init__(
            message=message,
            error_code="NTSB_VALIDATION_ERROR",
            details={
                "field": field,
                "value": value,
                "reason": reason,
                "ntsb_id": ntsb_id,
            },
        )


class NTSBConnectionError(ScraperError):
    """Raised when connection to NTSB CAROL system fails."""

    def __init__(
        self,
        message: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize NTSB connection error.

        Args:
            message: Optional custom message
            cause: Optional original exception
        """
        if message is None:
            message = "Failed to connect to NTSB CAROL system"
        super().__init__(
            message=message,
            error_code="NTSB_CONNECTION_ERROR",
            details={"cause": str(cause) if cause else None},
            cause=cause,
        )


class NTSBScraper(BaseScraper):
    """
    Scraper for NTSB Marine Investigation Reports.

    Queries the NTSB CAROL (Case Analysis and Reporting Online) system
    at https://data.ntsb.gov/carol-main-public for marine investigations.

    Features:
        - Queries CAROL basic search with marine mode filter
        - Handles pagination for large result sets
        - Supports JSON export from search results
        - Checkpoint support for resumable scraping
        - Comprehensive data validation

    Attributes:
        BASE_URL: Base URL for NTSB CAROL system
        SEARCH_ENDPOINT: Endpoint for basic search queries
        EXPORT_ENDPOINT: Endpoint for JSON export
        MARINE_MODE: Mode identifier for marine investigations
    """

    BASE_URL = "https://data.ntsb.gov/carol-main-public"
    SEARCH_ENDPOINT = "/api/query"
    EXPORT_ENDPOINT = "/api/export"
    MARINE_MODE = "Marine"

    # NTSB ID pattern: e.g., MAR-22-01, DCA22MM001
    NTSB_ID_PATTERN = re.compile(
        r"^(?:MAR|DCA|MAB)\d{2}[A-Z]{2,3}\d{3}$|^MAR-\d{2}-\d{2}$",
        re.IGNORECASE,
    )

    # Incident type mapping from NTSB categories
    INCIDENT_TYPE_MAPPING: Dict[str, IncidentType] = {
        "collision": IncidentType.COLLISION,
        "allision": IncidentType.COLLISION,
        "grounding": IncidentType.GROUNDING,
        "fire": IncidentType.FIRE,
        "explosion": IncidentType.EXPLOSION,
        "capsizing": IncidentType.CAPSIZING,
        "flooding": IncidentType.FLOODING,
        "sinking": IncidentType.CAPSIZING,
        "material failure": IncidentType.EQUIPMENT_FAILURE,
        "equipment failure": IncidentType.EQUIPMENT_FAILURE,
        "loss of propulsion": IncidentType.LOSS_OF_PROPULSION,
        "loss of steering": IncidentType.LOSS_OF_CONTROL,
        "personnel casualty": IncidentType.PERSONNEL_INJURY,
        "fatality": IncidentType.FATALITY,
        "pollution": IncidentType.POLLUTION,
    }

    # Status mapping from NTSB investigation status
    STATUS_MAPPING: Dict[str, IncidentStatus] = {
        "open": IncidentStatus.UNDER_INVESTIGATION,
        "active": IncidentStatus.UNDER_INVESTIGATION,
        "preliminary": IncidentStatus.PRELIMINARY_REPORT,
        "final": IncidentStatus.FINAL_REPORT,
        "closed": IncidentStatus.CLOSED,
        "archived": IncidentStatus.ARCHIVED,
    }

    def __init__(
        self,
        checkpoint_dir: Optional[Path] = None,
        page_size: int = 100,
        min_date: Optional[date] = None,
    ) -> None:
        """
        Initialize NTSB scraper.

        Args:
            checkpoint_dir: Directory for checkpoint files. If None, uses
                the default cache path from configuration.
            page_size: Number of results per page for pagination.
                Default is 100, max is typically 500.
            min_date: Minimum date for scraping. NTSB marine data is
                available from 2010 onwards. Defaults to 2010-01-01.
        """
        super().__init__(
            source=DataSource.NTSB,
            base_url=self.BASE_URL,
            name="ntsb_marine_scraper",
        )

        self.config_obj = get_config()
        self.checkpoint_dir = (
            checkpoint_dir or self.config_obj.storage.cache_path / "ntsb"
        )
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.page_size = min(page_size, 500)  # Cap at 500
        self.min_date = min_date or date(2010, 1, 1)

        # Checkpointing state
        self._checkpoint_file = self.checkpoint_dir / "ntsb_scraper_checkpoint.json"
        self._processed_ids: Set[str] = set()
        self._last_checkpoint_time: Optional[datetime] = None

        self.logger.info(
            f"NTSB Scraper initialized (page_size={self.page_size}, "
            f"min_date={self.min_date})"
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

    def _build_search_query(
        self,
        start_date: date,
        end_date: date,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Build search query parameters for CAROL API.

        Args:
            start_date: Start date for search range
            end_date: End date for search range
            page: Page number (1-indexed)

        Returns:
            Dictionary of query parameters
        """
        return {
            "mode": self.MARINE_MODE,
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "page": page,
            "pageSize": self.page_size,
            "sortBy": "eventDate",
            "sortOrder": "desc",
        }

    def _fetch_search_results(
        self,
        start_date: date,
        end_date: date,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Fetch search results from CAROL API.

        Args:
            start_date: Start date for search range
            end_date: End date for search range
            page: Page number (1-indexed)

        Returns:
            Dictionary containing search results with 'data' and 'pagination' keys

        Raises:
            HTTPError: If HTTP request fails
            ParsingError: If response cannot be parsed
        """
        query_params = self._build_search_query(start_date, end_date, page)
        url = f"{self.SEARCH_ENDPOINT}?{urlencode(query_params)}"

        self.logger.debug(f"Fetching page {page}: {url}")

        try:
            response = self._make_request(url, method="GET")
            data = response.json()

            if not isinstance(data, dict):
                raise ParsingError(
                    source="NTSB CAROL",
                    reason="Expected JSON object, got something else",
                )

            return data

        except json.JSONDecodeError as e:
            raise ParsingError(
                source="NTSB CAROL",
                reason=f"Invalid JSON response: {e}",
            )

    def _parse_investigation(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse raw investigation data into standardized format.

        Args:
            raw_data: Raw investigation data from CAROL

        Returns:
            Standardized investigation dictionary
        """
        ntsb_id = raw_data.get("ntsb_number", raw_data.get("id", ""))

        # Parse event date
        event_date = None
        date_str = raw_data.get("event_date", raw_data.get("eventDate"))
        if date_str:
            try:
                if isinstance(date_str, str):
                    # Handle various date formats
                    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
                        try:
                            event_date = datetime.strptime(
                                date_str.split("T")[0], fmt
                            ).date()
                            break
                        except ValueError:
                            continue
            except (ValueError, AttributeError):
                self.logger.warning(f"Could not parse date: {date_str}")

        # Map incident type
        raw_type = raw_data.get("event_type", raw_data.get("type", "")).lower().strip()
        incident_type = self.INCIDENT_TYPE_MAPPING.get(raw_type, IncidentType.OTHER)

        # Map status
        raw_status = raw_data.get("status", "").lower().strip()
        status = self.STATUS_MAPPING.get(raw_status, IncidentStatus.REPORTED)

        # Extract location
        location = {
            "latitude": raw_data.get("latitude"),
            "longitude": raw_data.get("longitude"),
            "city": raw_data.get("city"),
            "state": raw_data.get("state"),
            "country": raw_data.get("country", "USA"),
            "description": raw_data.get(
                "location", raw_data.get("locationDescription")
            ),
        }

        # Extract vessel information
        vessel = {
            "name": raw_data.get("vessel_name", raw_data.get("vesselName")),
            "type": raw_data.get("vessel_type", raw_data.get("vesselType")),
            "flag": raw_data.get("flag"),
            "gross_tonnage": raw_data.get(
                "gross_tonnage", raw_data.get("grossTonnage")
            ),
            "imo_number": raw_data.get("imo"),
        }

        # Extract casualties
        casualties = {
            "fatalities": int(raw_data.get("fatalities", 0) or 0),
            "injuries": int(raw_data.get("injuries", 0) or 0),
            "missing": int(raw_data.get("missing", 0) or 0),
        }

        # Build report URLs
        report_url = None
        if ntsb_id:
            report_url = f"{self.BASE_URL}/landing-page?ntsb_number={ntsb_id}"

        return {
            "source": DataSource.NTSB.value,
            "source_id": ntsb_id,
            "event_date": event_date.isoformat() if event_date else None,
            "report_date": raw_data.get("report_date", raw_data.get("reportDate")),
            "incident_type": incident_type.value,
            "status": status.value,
            "title": raw_data.get("title", raw_data.get("description", "")),
            "description": raw_data.get("narrative", raw_data.get("summary", "")),
            "location": location,
            "vessel": vessel,
            "casualties": casualties,
            "probable_cause": raw_data.get(
                "probable_cause", raw_data.get("probableCause")
            ),
            "recommendations": raw_data.get("recommendations", []),
            "report_url": report_url,
            "pdf_url": raw_data.get("pdf_url", raw_data.get("reportPdfUrl")),
            "scraped_at": datetime.utcnow().isoformat(),
            "raw_data": raw_data,
        }

    def scrape(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scrape marine investigations from NTSB CAROL system.

        Args:
            start_date: Start date for scraping. If None, uses min_date.
            end_date: End date for scraping. If None, uses today.

        Returns:
            List of investigation dictionaries

        Raises:
            HTTPError: If HTTP requests fail
            NTSBConnectionError: If connection to CAROL fails
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

        self.logger.info(f"Starting NTSB scrape: {start_date_obj} to {end_date_obj}")

        # Load checkpoint
        self._load_checkpoint()

        investigations: List[Dict[str, Any]] = []
        page = 1
        total_pages = None

        try:
            while True:
                self.logger.info(
                    f"Fetching page {page}"
                    + (f" of {total_pages}" if total_pages else "")
                )

                try:
                    result = self._fetch_search_results(
                        start_date_obj, end_date_obj, page
                    )
                except HTTPError as e:
                    if e.details and e.details.get("status_code") == 404:
                        self.logger.warning("No more results (404)")
                        break
                    raise

                # Extract pagination info
                pagination = result.get("pagination", {})
                total_pages = pagination.get("totalPages", 1)
                total_records = pagination.get("totalRecords", 0)

                if page == 1:
                    self.logger.info(
                        f"Total records: {total_records}, Total pages: {total_pages}"
                    )

                # Process results
                records = result.get("data", result.get("results", []))
                if not records:
                    self.logger.debug(f"No records on page {page}")
                    break

                for raw_record in records:
                    ntsb_id = raw_record.get("ntsb_number", raw_record.get("id", ""))

                    # Skip if already processed
                    if ntsb_id in self._processed_ids:
                        self.logger.debug(f"Skipping processed: {ntsb_id}")
                        continue

                    try:
                        parsed = self._parse_investigation(raw_record)

                        if self.validate_data(parsed):
                            investigations.append(parsed)
                            self._processed_ids.add(ntsb_id)
                        else:
                            self.logger.warning(f"Validation failed for {ntsb_id}")

                    except Exception as e:
                        self.logger.error(f"Error processing record {ntsb_id}: {e}")
                        continue

                # Save checkpoint after each page
                self._save_checkpoint()

                # Check if we've reached the last page
                if page >= total_pages:
                    break

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
            NTSBDataValidationError: If validation fails with critical errors
        """
        ntsb_id = data.get("source_id", "")

        # Required fields
        required_fields = ["source_id", "source", "incident_type"]
        for field in required_fields:
            if not data.get(field):
                self.logger.warning(f"Missing required field: {field}")
                return False

        # Validate NTSB ID format (if present and not empty)
        if ntsb_id and not self._validate_ntsb_id(ntsb_id):
            self.logger.warning(f"Invalid NTSB ID format: {ntsb_id}")
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
                pass  # Non-numeric latitude is okay

        if lon is not None:
            try:
                lon = float(lon)
                if not -180 <= lon <= 180:
                    self.logger.warning(f"Invalid longitude: {lon}")
                    return False
            except (ValueError, TypeError):
                pass  # Non-numeric longitude is okay

        return True

    def _validate_ntsb_id(self, ntsb_id: str) -> bool:
        """
        Validate NTSB investigation ID format.

        Args:
            ntsb_id: NTSB ID to validate

        Returns:
            True if valid format
        """
        if not ntsb_id:
            return False

        # Clean ID
        clean_id = ntsb_id.strip().upper()

        # Check against pattern
        if self.NTSB_ID_PATTERN.match(clean_id):
            return True

        # Also accept more flexible patterns
        # e.g., MAR2201, DCA22MM001, etc.
        if re.match(r"^[A-Z]{3}\d{2,}", clean_id):
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
            "source": DataSource.NTSB.value,
            "total_processed_ids": len(self._processed_ids),
            "last_checkpoint": (
                self._last_checkpoint_time.isoformat()
                if self._last_checkpoint_time
                else None
            ),
            "total_requests": self._request_count,
            "checkpoint_file": str(self._checkpoint_file),
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
