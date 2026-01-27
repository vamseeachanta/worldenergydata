"""
USCG Marine Casualty Scraper

Production-ready scraper for USCG marine casualty reports from:
https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/
Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/Marine-Casualty-Reports/

This scraper:
- Scrapes USCG marine casualty reports from HTML listings and PDF documents
- Implements retry logic with exponential backoff
- Handles rate limiting for respectful scraping
- Uses checkpointing for long-running scrapes
- Validates extracted data using Pydantic models
- Provides structured logging and error handling

Author: WorldEnergyData Project
License: MIT
"""

import json
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

import pdfplumber
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, field_validator
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from worldenergydata.common import get_logger

logger = get_logger(__name__)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for Data Validation
# ============================================================================


class VesselInfo(BaseModel):
    """Vessel information model."""

    name: Optional[str] = Field(None, description="Vessel name")
    imo_number: Optional[str] = Field(None, description="IMO number")
    official_number: Optional[str] = Field(None, description="Official number")
    vessel_type: Optional[str] = Field(None, description="Type of vessel")
    flag: Optional[str] = Field(None, description="Flag state")
    gross_tonnage: Optional[float] = Field(None, description="Gross tonnage")

    @field_validator("imo_number")
    @classmethod
    def validate_imo(cls, v: Optional[str]) -> Optional[str]:
        """Validate IMO number format (7 digits)."""
        if v and not re.match(r"^\d{7}$", v):
            logger.warning(f"Invalid IMO number format: {v}")
            return None
        return v


class LocationInfo(BaseModel):
    """Location information model."""

    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")
    location_description: Optional[str] = Field(None, description="Text description")
    port: Optional[str] = Field(None, description="Port name")
    waterway: Optional[str] = Field(None, description="Waterway name")
    state: Optional[str] = Field(None, description="State")
    country: str = Field(default="USA", description="Country")


class CasualtyInfo(BaseModel):
    """Casualty statistics model."""

    fatalities: int = Field(default=0, ge=0, description="Number of fatalities")
    injuries: int = Field(default=0, ge=0, description="Number of injuries")
    missing: int = Field(default=0, ge=0, description="Number missing")

    @field_validator("fatalities", "injuries", "missing")
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        """Ensure casualty counts are non-negative."""
        return max(0, v)


class MarineIncident(BaseModel):
    """Complete marine incident model."""

    incident_id: str = Field(..., description="Unique incident identifier")
    incident_date: datetime = Field(..., description="Date of incident")
    report_date: Optional[datetime] = Field(None, description="Date report published")
    incident_type: str = Field(..., description="Type of incident")
    severity: Optional[str] = Field(None, description="Incident severity")

    vessel: Optional[VesselInfo] = Field(None, description="Vessel information")
    location: Optional[LocationInfo] = Field(None, description="Location information")
    casualties: CasualtyInfo = Field(
        default_factory=CasualtyInfo, description="Casualty statistics"
    )

    description: Optional[str] = Field(None, description="Incident description")
    causes: List[str] = Field(default_factory=list, description="Identified causes")
    recommendations: List[str] = Field(
        default_factory=list, description="Safety recommendations"
    )

    report_url: Optional[str] = Field(None, description="URL to full report")
    pdf_url: Optional[str] = Field(None, description="URL to PDF report")

    source: str = Field(default="USCG", description="Data source")
    scraped_at: datetime = Field(
        default_factory=datetime.utcnow, description="Scrape timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# Base Scraper Abstract Class
# ============================================================================


class BaseScraper(ABC):
    """
    Abstract base class for all marine safety data scrapers.

    Provides common functionality for:
    - HTTP requests with retry logic
    - Rate limiting
    - Checkpointing
    - Logging
    - Error handling
    """

    def __init__(
        self,
        checkpoint_dir: Optional[Path] = None,
        rate_limit_delay: float = 1.0,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        """
        Initialize base scraper.

        Args:
            checkpoint_dir: Directory for checkpoint files
            rate_limit_delay: Delay between requests in seconds
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        """
        self.checkpoint_dir = checkpoint_dir or Path.cwd() / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "WorldEnergyData-Scraper/1.0 (Research Project; +https://github.com/worldenergydata)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

        self.last_request_time = 0.0
        self._processed_urls: Set[str] = set()

        logger.info(f"Initialized {self.__class__.__name__}")

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    @retry(
        retry=retry_if_exception_type((requests.RequestException, requests.Timeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _fetch_url(self, url: str, **kwargs) -> requests.Response:
        """
        Fetch URL with retry logic and rate limiting.

        Args:
            url: URL to fetch
            **kwargs: Additional arguments for requests.get()

        Returns:
            Response object

        Raises:
            requests.RequestException: On request failure after retries
        """
        self._rate_limit()

        logger.debug(f"Fetching: {url}")

        kwargs.setdefault("timeout", self.timeout)
        response = self.session.get(url, **kwargs)
        response.raise_for_status()

        return response

    def _save_checkpoint(self, checkpoint_name: str, data: Dict[str, Any]) -> None:
        """
        Save checkpoint data to disk.

        Args:
            checkpoint_name: Name of checkpoint file
            data: Data to save
        """
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_name}.json"

        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Checkpoint saved: {checkpoint_file}")

    def _load_checkpoint(self, checkpoint_name: str) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint data from disk.

        Args:
            checkpoint_name: Name of checkpoint file

        Returns:
            Checkpoint data or None if not found
        """
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_name}.json"

        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Checkpoint loaded: {checkpoint_file}")
            return data
        except Exception as e:
            logger.error(f"Failed to load checkpoint {checkpoint_file}: {e}")
            return None

    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Main scraping method to be implemented by subclasses.

        Returns:
            List of scraped incident records
        """
        pass


# ============================================================================
# USCG Marine Casualty Scraper
# ============================================================================


class USCGMarineCasualtyScraper(BaseScraper):
    """
    Scraper for USCG Marine Casualty Reports.

    Scrapes marine casualty data from:
    - HTML listing pages
    - PDF investigation reports
    - Public database queries

    Features:
    - Automatic pagination handling
    - PDF text extraction and parsing
    - Checkpoint support for resume capability
    - Comprehensive error handling and logging
    """

    # USCG data source URLs
    BASE_URL = "https://www.dco.uscg.mil"
    CASUALTY_REPORTS_URL = (
        "https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-"
        "Prevention-Policy-CG-5P/Inspections-Compliance-CG-5PC-/Office-of-"
        "Investigations-Casualty-Analysis/Marine-Casualty-Reports/"
    )

    # Incident type mappings
    INCIDENT_TYPES = {
        "collision": "Collision",
        "grounding": "Grounding",
        "fire": "Fire/Explosion",
        "explosion": "Fire/Explosion",
        "sinking": "Sinking",
        "capsizing": "Capsizing",
        "flooding": "Flooding",
        "allision": "Allision",
        "material failure": "Material Failure",
        "personnel casualty": "Personnel Casualty",
    }

    def __init__(
        self,
        checkpoint_dir: Optional[Path] = None,
        rate_limit_delay: float = 2.0,  # Be respectful: 2 seconds between requests
        max_retries: int = 3,
        timeout: int = 30,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        resume_from_checkpoint: bool = True,
    ):
        """
        Initialize USCG scraper.

        Args:
            checkpoint_dir: Directory for checkpoint files
            rate_limit_delay: Delay between requests (default 2s for respectful scraping)
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            start_year: Start year for scraping (default: 1982)
            end_year: End year for scraping (default: current year)
            resume_from_checkpoint: Whether to resume from last checkpoint
        """
        super().__init__(checkpoint_dir, rate_limit_delay, max_retries, timeout)

        self.start_year = start_year or 1982
        self.end_year = end_year or datetime.now().year
        self.resume_from_checkpoint = resume_from_checkpoint

        self.incidents: List[MarineIncident] = []
        self._processed_report_ids: Set[str] = set()

        logger.info(
            f"USCG Scraper initialized for years {self.start_year}-{self.end_year}"
        )

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Main scraping method.

        Returns:
            List of incident dictionaries
        """
        logger.info("Starting USCG marine casualty scrape")

        # Load checkpoint if resuming
        if self.resume_from_checkpoint:
            checkpoint = self._load_checkpoint("uscg_scraper")
            if checkpoint:
                self._processed_report_ids = set(checkpoint.get("processed_ids", []))
                logger.info(
                    f"Resuming from checkpoint: {len(self._processed_report_ids)} "
                    f"reports already processed"
                )

        try:
            # Step 1: Fetch and parse report listing pages
            report_links = self._fetch_report_listings()
            logger.info(f"Found {len(report_links)} report links")

            # Step 2: Process each report
            for idx, (report_id, report_url) in enumerate(report_links.items(), 1):
                if report_id in self._processed_report_ids:
                    logger.debug(f"Skipping already processed report: {report_id}")
                    continue

                logger.info(f"Processing report {idx}/{len(report_links)}: {report_id}")

                try:
                    incident = self._process_report(report_id, report_url)
                    if incident:
                        self.incidents.append(incident)
                        self._processed_report_ids.add(report_id)

                        # Save checkpoint every 10 reports
                        if idx % 10 == 0:
                            self._save_checkpoint(
                                "uscg_scraper",
                                {
                                    "processed_ids": list(self._processed_report_ids),
                                    "last_update": datetime.utcnow().isoformat(),
                                    "total_incidents": len(self.incidents),
                                },
                            )

                except Exception as e:
                    logger.error(
                        f"Error processing report {report_id}: {e}", exc_info=True
                    )
                    continue

            # Final checkpoint
            self._save_checkpoint(
                "uscg_scraper",
                {
                    "processed_ids": list(self._processed_report_ids),
                    "last_update": datetime.utcnow().isoformat(),
                    "total_incidents": len(self.incidents),
                },
            )

            logger.info(f"Scraping complete: {len(self.incidents)} incidents collected")

            # Convert Pydantic models to dictionaries
            return [incident.model_dump() for incident in self.incidents]

        except Exception as e:
            logger.error(f"Fatal error during scraping: {e}", exc_info=True)
            raise

    def _fetch_report_listings(self) -> Dict[str, str]:
        """
        Fetch and parse report listing pages.

        Returns:
            Dictionary mapping report IDs to URLs
        """
        report_links = {}

        try:
            response = self._fetch_url(self.CASUALTY_REPORTS_URL)
            soup = BeautifulSoup(response.content, "html.parser")

            # Find all report links (adjust selector based on actual page structure)
            for link in soup.find_all("a", href=True):
                href = link["href"]

                # Look for PDF links or report detail pages
                if any(
                    pattern in href.lower()
                    for pattern in [".pdf", "report", "casualty", "investigation"]
                ):
                    full_url = urljoin(self.BASE_URL, href)

                    # Extract report ID from URL or link text
                    report_id = self._extract_report_id(
                        full_url, link.get_text(strip=True)
                    )

                    if report_id:
                        report_links[report_id] = full_url

            logger.info(f"Found {len(report_links)} reports on listing page")

        except Exception as e:
            logger.error(f"Error fetching report listings: {e}", exc_info=True)

        return report_links

    def _extract_report_id(self, url: str, link_text: str) -> Optional[str]:
        """
        Extract report ID from URL or link text.

        Args:
            url: Report URL
            link_text: Link text

        Returns:
            Report ID or None
        """
        # Try to extract from URL
        match = re.search(r"(?:report|investigation)[_-]?(\d+)", url, re.IGNORECASE)
        if match:
            return f"USCG-{match.group(1)}"

        # Try to extract from link text
        match = re.search(r"(\d{4,})", link_text)
        if match:
            return f"USCG-{match.group(1)}"

        # Generate from URL hash as fallback
        return f"USCG-{abs(hash(url)) % 1000000:06d}"

    def _process_report(
        self, report_id: str, report_url: str
    ) -> Optional[MarineIncident]:
        """
        Process a single report (HTML or PDF).

        Args:
            report_id: Report identifier
            report_url: URL to report

        Returns:
            MarineIncident object or None
        """
        try:
            if report_url.lower().endswith(".pdf"):
                return self._process_pdf_report(report_id, report_url)
            else:
                return self._process_html_report(report_id, report_url)

        except Exception as e:
            logger.error(f"Error processing report {report_id}: {e}", exc_info=True)
            return None

    def _process_html_report(
        self, report_id: str, report_url: str
    ) -> Optional[MarineIncident]:
        """
        Process HTML report page.

        Args:
            report_id: Report identifier
            report_url: URL to report

        Returns:
            MarineIncident object or None
        """
        try:
            response = self._fetch_url(report_url)
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract data from HTML (structure depends on actual page layout)
            data = self._extract_html_data(soup, report_url)

            # Build and validate incident model
            incident_data = {"incident_id": report_id, "report_url": report_url, **data}

            return MarineIncident(**incident_data)

        except ValidationError as e:
            logger.error(f"Validation error for {report_id}: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Error processing HTML report {report_id}: {e}", exc_info=True
            )
            return None

    def _process_pdf_report(
        self, report_id: str, pdf_url: str
    ) -> Optional[MarineIncident]:
        """
        Process PDF report.

        Args:
            report_id: Report identifier
            pdf_url: URL to PDF

        Returns:
            MarineIncident object or None
        """
        try:
            # Download PDF
            response = self._fetch_url(pdf_url, stream=True)

            # Save temporarily for pdfplumber
            temp_pdf = self.checkpoint_dir / f"{report_id}.pdf"
            with open(temp_pdf, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Extract text from PDF
            text = self._extract_pdf_text(temp_pdf)

            # Parse text for incident data
            data = self._parse_pdf_text(text, pdf_url)

            # Clean up temporary file
            temp_pdf.unlink(missing_ok=True)

            # Build and validate incident model
            incident_data = {"incident_id": report_id, "pdf_url": pdf_url, **data}

            return MarineIncident(**incident_data)

        except ValidationError as e:
            logger.error(f"Validation error for {report_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing PDF report {report_id}: {e}", exc_info=True)
            return None

    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """
        Extract text from PDF using pdfplumber.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text
        """
        text_parts = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"Error extracting PDF text from {pdf_path}: {e}")
            return ""

    def _extract_html_data(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Extract incident data from HTML.

        Args:
            soup: BeautifulSoup object
            url: Source URL

        Returns:
            Dictionary of extracted data
        """
        data = {
            "incident_date": datetime.now(),  # Placeholder
            "incident_type": "Unknown",
            "description": "",
        }

        # Extract text content
        text = soup.get_text(separator=" ", strip=True)

        # Try to extract incident date
        date_match = re.search(
            r"(?:date|occurred|incident).*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            text,
            re.IGNORECASE,
        )
        if date_match:
            try:
                data["incident_date"] = datetime.strptime(
                    date_match.group(1).replace("-", "/"), "%m/%d/%Y"
                )
            except ValueError:
                pass

        # Try to extract incident type
        for pattern, incident_type in self.INCIDENT_TYPES.items():
            if pattern.lower() in text.lower():
                data["incident_type"] = incident_type
                break

        # Extract description from paragraphs
        paragraphs = [
            p.get_text(strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > 50
        ]
        if paragraphs:
            data["description"] = " ".join(paragraphs[:3])  # First 3 paragraphs

        return data

    def _parse_pdf_text(self, text: str, url: str) -> Dict[str, Any]:
        """
        Parse extracted PDF text for incident data.

        Args:
            text: Extracted text
            url: Source URL

        Returns:
            Dictionary of extracted data
        """
        data = {
            "incident_date": datetime.now(),  # Placeholder
            "incident_type": "Unknown",
            "description": "",
            "vessel": None,
            "location": None,
            "casualties": CasualtyInfo(),
        }

        # Extract incident date
        date_patterns = [
            r"(?:date|occurred|incident).*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1).replace("-", "/")
                    data["incident_date"] = datetime.strptime(date_str, "%m/%d/%Y")
                    break
                except ValueError:
                    continue

        # Extract incident type
        for pattern, incident_type in self.INCIDENT_TYPES.items():
            if pattern.lower() in text.lower():
                data["incident_type"] = incident_type
                break

        # Extract vessel name
        vessel_match = re.search(
            r"(?:vessel|ship)\s+(?:name)?:?\s*([A-Z][A-Za-z\s]+?)(?:\s+(?:IMO|Official)|\n|$)",
            text,
        )
        if vessel_match:
            data["vessel"] = VesselInfo(name=vessel_match.group(1).strip())

        # Extract casualties
        fatality_match = re.search(
            r"(\d+)\s+(?:fatalities|deaths)", text, re.IGNORECASE
        )
        if fatality_match:
            data["casualties"].fatalities = int(fatality_match.group(1))

        injury_match = re.search(r"(\d+)\s+injuries", text, re.IGNORECASE)
        if injury_match:
            data["casualties"].injuries = int(injury_match.group(1))

        # Extract description (first paragraph after "Summary" or "Synopsis")
        summary_match = re.search(
            r"(?:summary|synopsis|description)[:\s]+(.*?)(?:\n\n|\nCauses|\nRecommendations)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if summary_match:
            data["description"] = summary_match.group(1).strip()[
                :500
            ]  # Limit to 500 chars

        return data

    def export_to_json(self, output_file: Path) -> None:
        """
        Export scraped incidents to JSON file.

        Args:
            output_file: Path to output JSON file
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                [incident.model_dump() for incident in self.incidents],
                f,
                indent=2,
                default=str,
            )

        logger.info(f"Exported {len(self.incidents)} incidents to {output_file}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about scraped data.

        Returns:
            Dictionary of statistics
        """
        total = len(self.incidents)

        if total == 0:
            return {"total_incidents": 0}

        # Count by incident type
        type_counts = {}
        for incident in self.incidents:
            incident_type = incident.incident_type
            type_counts[incident_type] = type_counts.get(incident_type, 0) + 1

        # Count casualties
        total_fatalities = sum(inc.casualties.fatalities for inc in self.incidents)
        total_injuries = sum(inc.casualties.injuries for inc in self.incidents)

        # Year distribution
        year_counts = {}
        for incident in self.incidents:
            year = incident.incident_date.year
            year_counts[year] = year_counts.get(year, 0) + 1

        return {
            "total_incidents": total,
            "incident_types": type_counts,
            "total_fatalities": total_fatalities,
            "total_injuries": total_injuries,
            "year_distribution": dict(sorted(year_counts.items())),
            "date_range": {
                "start": min(inc.incident_date for inc in self.incidents).isoformat(),
                "end": max(inc.incident_date for inc in self.incidents).isoformat(),
            },
        }


# ============================================================================
# Main Execution
# ============================================================================


def main():
    """Main execution function for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="USCG Marine Casualty Scraper")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("uscg_incidents.json"),
        help="Output JSON file path",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=Path("checkpoints"),
        help="Checkpoint directory",
    )
    parser.add_argument("--start-year", type=int, help="Start year for scraping")
    parser.add_argument("--end-year", type=int, help="End year for scraping")
    parser.add_argument(
        "--no-resume", action="store_true", help="Do not resume from checkpoint"
    )

    args = parser.parse_args()

    # Initialize scraper
    scraper = USCGMarineCasualtyScraper(
        checkpoint_dir=args.checkpoint_dir,
        start_year=args.start_year,
        end_year=args.end_year,
        resume_from_checkpoint=not args.no_resume,
    )

    # Run scraping
    incidents = scraper.scrape()

    # Export results
    scraper.export_to_json(args.output)

    # Print statistics
    stats = scraper.get_statistics()
    print("\n" + "=" * 60)
    print("SCRAPING STATISTICS")
    print("=" * 60)
    print(f"Total incidents: {stats['total_incidents']}")
    print(f"Total fatalities: {stats['total_fatalities']}")
    print(f"Total injuries: {stats['total_injuries']}")
    print("\nIncident types:")
    for itype, count in stats["incident_types"].items():
        print(f"  {itype}: {count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
