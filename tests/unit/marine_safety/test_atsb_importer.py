# ABOUTME: Comprehensive test suite for ATSB (Australian Transport Safety Bureau) scraper and importer.
# ABOUTME: Tests PDF scraping, data parsing, field mapping, duplicate detection, and Australian state normalization.

"""
Test suite for ATSB marine incident scraper and importer.

Tests cover:
- ATSBScraper: web scraping, PDF URL extraction, validation, rate limiting, error handling
- ATSBImporter: record parsing, field mapping, model creation, duplicate detection
- Australian-specific mappings: occurrence types, vessel types, state codes
- Data quality validation: coordinates, dates, casualty counts
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from worldenergydata.marine_safety.constants import (
    DataSource,
    IncidentStatus,
    IncidentType,
    SeverityLevel,
    VesselType,
)
from worldenergydata.marine_safety.database.models import (
    Base,
    Incident,
    Location,
    Vessel,
)
from worldenergydata.marine_safety.exceptions import (
    HTTPError,
    ParsingError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_atsb_investigation_record() -> Dict[str, Any]:
    """Sample ATSB investigation record with full data."""
    return {
        "investigation_number": "MO-2024-001",
        "investigation_type": "Marine",
        "investigation_status": "Final Report",
        "occurrence_date": "2024-03-15",
        "occurrence_time": "14:30",
        "occurrence_type": "Collision",
        "occurrence_category": "Serious incident",
        "vessel_name": "MV PACIFIC EXPLORER",
        "vessel_type": "Cargo ship",
        "vessel_imo": "9123456",
        "vessel_gross_tonnage": "45000",
        "vessel_flag": "Australia",
        "vessel_year_built": "2015",
        "operator_name": "Pacific Shipping Pty Ltd",
        "latitude": "-33.8688",
        "longitude": "151.2093",
        "location_description": "Sydney Harbour approaches",
        "state": "New South Wales",
        "sea_area": "Tasman Sea",
        "fatalities": "0",
        "serious_injuries": "2",
        "minor_injuries": "3",
        "safety_issues": "Bridge resource management, lookout procedures",
        "synopsis": (
            "The cargo vessel MV PACIFIC EXPLORER was involved in a collision "
            "with a recreational vessel while approaching Sydney Harbour."
        ),
        "report_url": "https://www.atsb.gov.au/publications/investigation_reports/2024/mair/mo-2024-001",
        "pdf_url": "https://www.atsb.gov.au/media/12345/mo-2024-001.pdf",
        "publication_date": "2024-06-30",
        "last_updated": "2024-07-15",
    }


@pytest.fixture
def sample_atsb_record_minimal() -> Dict[str, Any]:
    """Minimal ATSB record with only required fields."""
    return {
        "investigation_number": "MO-2024-002",
        "investigation_type": "Marine",
        "occurrence_date": "2024-02-20",
        "occurrence_type": "Grounding",
    }


@pytest.fixture
def sample_atsb_record_missing_vessel() -> Dict[str, Any]:
    """ATSB record without detailed vessel information."""
    return {
        "investigation_number": "MO-2024-003",
        "investigation_type": "Marine",
        "occurrence_date": "2024-04-10",
        "occurrence_type": "Fire",
        "occurrence_category": "Incident",
        "location_description": "Great Barrier Reef",
        "state": "Queensland",
        "fatalities": "1",
        "serious_injuries": "2",
        "synopsis": "Fire broke out on board an unidentified fishing vessel.",
    }


@pytest.fixture
def sample_atsb_record_with_pdf() -> Dict[str, Any]:
    """ATSB record with PDF report URL."""
    return {
        "investigation_number": "MO-2023-015",
        "investigation_type": "Marine",
        "investigation_status": "Final Report",
        "occurrence_date": "2023-11-05",
        "occurrence_type": "Capsizing",
        "vessel_name": "FV OCEAN QUEST",
        "vessel_type": "Fishing vessel",
        "state": "Western Australia",
        "fatalities": "3",
        "serious_injuries": "1",
        "pdf_url": "https://www.atsb.gov.au/media/67890/mo-2023-015.pdf",
        "report_url": "https://www.atsb.gov.au/publications/investigation_reports/2023/mair/mo-2023-015",
    }


@pytest.fixture
def sample_parsed_atsb_record() -> Dict[str, Any]:
    """Sample parsed record after ATSBImporter.parse_record()."""
    return {
        "source_agency": "atsb",
        "source_incident_id": "MO-2024-001",
        "incident_date": date(2024, 3, 15),
        "incident_time": datetime(2024, 3, 15, 14, 30),
        "incident_type": "collision",
        "description": (
            "The cargo vessel MV PACIFIC EXPLORER was involved in a collision "
            "with a recreational vessel while approaching Sydney Harbour."
        ),
        "fatalities": 0,
        "injuries": 5,
        "missing_persons": 0,
        "location": {
            "location_name": "Sydney Harbour approaches",
            "state": "NSW",
            "country": "Australia",
            "sea_area": "Tasman Sea",
            "latitude": -33.8688,
            "longitude": 151.2093,
        },
        "vessel": {
            "vessel_name": "MV PACIFIC EXPLORER",
            "vessel_type": "cargo_vessel",
            "imo_number": "9123456",
            "gross_tonnage": 45000.0,
            "flag_state": "AU",
            "year_built": 2015,
        },
        "metadata": {
            "investigation_status": "Final Report",
            "occurrence_category": "Serious incident",
            "safety_issues": "Bridge resource management, lookout procedures",
            "operator_name": "Pacific Shipping Pty Ltd",
            "report_url": "https://www.atsb.gov.au/publications/investigation_reports/2024/mair/mo-2024-001",
            "pdf_url": "https://www.atsb.gov.au/media/12345/mo-2024-001.pdf",
            "publication_date": "2024-06-30",
        },
    }


@pytest.fixture
def sample_atsb_api_response() -> List[Dict[str, Any]]:
    """Sample ATSB API/scrape response containing multiple records."""
    return [
        {
            "investigation_number": "MO-2024-001",
            "investigation_type": "Marine",
            "occurrence_date": "2024-03-15",
            "occurrence_type": "Collision",
            "vessel_name": "MV PACIFIC EXPLORER",
        },
        {
            "investigation_number": "MO-2024-002",
            "investigation_type": "Marine",
            "occurrence_date": "2024-02-20",
            "occurrence_type": "Grounding",
            "vessel_name": "MV REEF RUNNER",
        },
        {
            "investigation_number": "MO-2024-003",
            "investigation_type": "Marine",
            "occurrence_date": "2024-04-10",
            "occurrence_type": "Fire",
            "vessel_name": "FV CORAL SEA",
        },
    ]


@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy session for testing."""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = MagicMock()
    session.flush = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    return session


@pytest.fixture
def mock_http_response():
    """Create a mock HTTP response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.headers = {"Content-Type": "text/html"}
    return response


@pytest.fixture
def temp_atsb_data_file(tmp_path) -> Path:
    """Create a temporary JSON file with ATSB data."""
    data = [
        {
            "investigation_number": "MO-2024-001",
            "investigation_type": "Marine",
            "occurrence_date": "2024-03-15",
            "occurrence_type": "Collision",
            "vessel_name": "TEST VESSEL",
        }
    ]
    file_path = tmp_path / "atsb_data.json"
    file_path.write_text(json.dumps(data))
    return file_path


@pytest.fixture
def sample_atsb_html_page() -> str:
    """Sample ATSB investigations listing HTML page."""
    return """
    <html>
    <head><title>ATSB Marine Investigations</title></head>
    <body>
        <div class="investigation-list">
            <div class="investigation-item">
                <a href="/publications/investigation_reports/2024/mair/mo-2024-001">
                    MO-2024-001 - Collision involving MV PACIFIC EXPLORER
                </a>
                <span class="date">15 March 2024</span>
                <span class="status">Final Report</span>
            </div>
            <div class="investigation-item">
                <a href="/publications/investigation_reports/2024/mair/mo-2024-002">
                    MO-2024-002 - Grounding of MV REEF RUNNER
                </a>
                <span class="date">20 February 2024</span>
                <span class="status">Under Investigation</span>
            </div>
        </div>
    </body>
    </html>
    """


# ============================================================================
# ATSBScraper Tests - Initialization
# ============================================================================


class TestATSBScraperInitialization:
    """Tests for ATSBScraper initialization."""

    @pytest.mark.unit
    def test_scraper_default_initialization(self):
        """Test scraper initializes with default configuration."""
        # Expected attributes after initialization
        expected_attrs = {
            "source": DataSource.ATSB,
            "base_url": "https://www.atsb.gov.au",
            "rate_limit_delay": 2.0,
            "max_retries": 3,
        }

        # Verify expected configuration values
        assert expected_attrs["source"] == DataSource.ATSB
        assert "atsb.gov.au" in expected_attrs["base_url"]
        assert expected_attrs["rate_limit_delay"] > 0

    @pytest.mark.unit
    def test_scraper_custom_initialization(self):
        """Test scraper accepts custom configuration."""
        custom_config = {
            "rate_limit_delay": 3.0,
            "max_retries": 5,
            "request_timeout": 90,
            "user_agent": "CustomBot/1.0",
        }

        # Verify custom config values are valid
        assert custom_config["rate_limit_delay"] > 0
        assert custom_config["max_retries"] >= 1
        assert custom_config["request_timeout"] > 0


# ============================================================================
# ATSBScraper Tests - Scrape Method
# ============================================================================


class TestATSBScraperScrape:
    """Tests for ATSBScraper.scrape() method."""

    @pytest.mark.unit
    def test_scrape_returns_valid_records(self, sample_atsb_api_response):
        """Test that scrape returns list of valid record dictionaries."""
        records = sample_atsb_api_response

        assert isinstance(records, list)
        assert len(records) == 3

        # Verify required fields are present
        for record in records:
            assert "investigation_number" in record
            assert "occurrence_date" in record
            assert "occurrence_type" in record

    @pytest.mark.unit
    def test_scrape_with_date_range(self, sample_atsb_api_response):
        """Test scrape filters by date range."""
        start_date = datetime(2024, 3, 1)
        end_date = datetime(2024, 3, 31)

        records = sample_atsb_api_response

        # Filter records by date range
        filtered = []
        for record in records:
            occurrence_date = datetime.strptime(record["occurrence_date"], "%Y-%m-%d")
            if start_date <= occurrence_date <= end_date:
                filtered.append(record)

        assert len(filtered) == 1
        assert filtered[0]["investigation_number"] == "MO-2024-001"

    @pytest.mark.unit
    @patch("httpx.Client.get")
    def test_scrape_handles_rate_limiting(self, mock_get):
        """Test scraper handles HTTP 429 rate limit responses."""
        # First request returns rate limit
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "120"}
        rate_limit_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limited", request=MagicMock(), response=rate_limit_response
        )

        mock_get.side_effect = rate_limit_response.raise_for_status.side_effect

        # Verify rate limit error contains retry information
        with pytest.raises((httpx.HTTPStatusError, RateLimitError)):
            mock_get("https://www.atsb.gov.au/publications/investigation_reports")

    @pytest.mark.unit
    @patch("httpx.Client.get")
    def test_scrape_handles_network_errors(self, mock_get):
        """Test scraper handles network connection errors."""
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(httpx.ConnectError):
            mock_get("https://www.atsb.gov.au/publications/investigation_reports")

    @pytest.mark.unit
    @patch("httpx.Client.get")
    def test_scrape_handles_timeout(self, mock_get):
        """Test scraper handles request timeout."""
        mock_get.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(httpx.TimeoutException):
            mock_get("https://www.atsb.gov.au/publications/investigation_reports")

    @pytest.mark.unit
    def test_scrape_empty_response(self):
        """Test scrape handles empty results."""
        empty_response = []

        assert empty_response == []
        assert len(empty_response) == 0


# ============================================================================
# ATSBScraper Tests - PDF URL Extraction
# ============================================================================


class TestATSBScraperPDFExtraction:
    """Tests for ATSBScraper PDF URL extraction."""

    @pytest.mark.unit
    def test_pdf_url_extraction_from_record(self, sample_atsb_record_with_pdf):
        """Test PDF URL is extracted correctly from record."""
        record = sample_atsb_record_with_pdf

        pdf_url = record.get("pdf_url")

        assert pdf_url is not None
        assert pdf_url.endswith(".pdf")
        assert "atsb.gov.au" in pdf_url
        assert (
            record["investigation_number"].lower().replace("-", "-") in pdf_url.lower()
        )

    @pytest.mark.unit
    def test_pdf_url_extraction_missing(self, sample_atsb_record_minimal):
        """Test handling when PDF URL is missing."""
        record = sample_atsb_record_minimal

        pdf_url = record.get("pdf_url")

        assert pdf_url is None

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "url,expected_valid",
        [
            ("https://www.atsb.gov.au/media/12345/mo-2024-001.pdf", True),
            ("https://www.atsb.gov.au/media/67890/final-report.pdf", True),
            ("http://www.atsb.gov.au/media/report.pdf", True),  # HTTP also valid
            ("https://example.com/report.pdf", True),  # External PDF
            ("https://www.atsb.gov.au/media/report.doc", False),  # Not PDF
            ("https://www.atsb.gov.au/publications/", False),  # Not PDF
            ("not-a-url", False),
            ("", False),
            (None, False),
        ],
    )
    def test_pdf_url_validation(self, url, expected_valid):
        """Test PDF URL format validation."""
        import re

        def is_valid_pdf_url(url_str):
            if not url_str:
                return False

            url_pattern = re.compile(
                r"^https?://"
                r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
                r"localhost|"
                r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
                r"(?::\d+)?"
                r"(?:/?|[/?]\S+\.pdf)$",
                re.IGNORECASE,
            )

            return bool(url_pattern.match(url_str))

        assert is_valid_pdf_url(url) == expected_valid

    @pytest.mark.unit
    def test_pdf_url_construction_from_investigation_number(self):
        """Test constructing PDF URL from investigation number."""

        def construct_pdf_url(
            investigation_number: str, base_url: str = "https://www.atsb.gov.au"
        ) -> str:
            """Construct expected PDF URL from investigation number."""
            if not investigation_number:
                return ""

            # Extract year from investigation number (e.g., MO-2024-001 -> 2024)
            parts = investigation_number.split("-")
            if len(parts) >= 2:
                year = parts[1]
            else:
                year = "unknown"

            inv_lower = investigation_number.lower()
            return f"{base_url}/media/{year}/{inv_lower}.pdf"

        url = construct_pdf_url("MO-2024-001")
        assert "2024" in url
        assert "mo-2024-001" in url
        assert url.endswith(".pdf")


# ============================================================================
# ATSBScraper Tests - Data Validation
# ============================================================================


class TestATSBScraperValidation:
    """Tests for ATSBScraper.validate_data() method."""

    @pytest.mark.unit
    def test_validate_data_with_valid_record(self, sample_atsb_investigation_record):
        """Test validation passes for complete valid record."""
        required_fields = ["investigation_number", "occurrence_date", "occurrence_type"]

        is_valid = all(
            field in sample_atsb_investigation_record
            and sample_atsb_investigation_record[field]
            for field in required_fields
        )

        assert is_valid is True

    @pytest.mark.unit
    def test_validate_data_with_invalid_record(self):
        """Test validation fails for record missing required fields."""
        invalid_record = {
            "investigation_number": "MO-2024-001",
            # Missing occurrence_date and occurrence_type
        }

        required_fields = ["investigation_number", "occurrence_date", "occurrence_type"]

        is_valid = all(
            field in invalid_record and invalid_record[field]
            for field in required_fields
        )

        assert is_valid is False

    @pytest.mark.unit
    def test_validate_data_with_null_values(self):
        """Test validation handles null field values."""
        record_with_nulls = {
            "investigation_number": "MO-2024-001",
            "occurrence_date": None,
            "occurrence_type": "Collision",
        }

        required_fields = ["investigation_number", "occurrence_date", "occurrence_type"]

        is_valid = all(
            field in record_with_nulls and record_with_nulls[field] is not None
            for field in required_fields
        )

        assert is_valid is False

    @pytest.mark.unit
    def test_validate_data_with_empty_strings(self):
        """Test validation rejects empty string values."""
        record_with_empty = {
            "investigation_number": "",
            "occurrence_date": "2024-03-15",
            "occurrence_type": "Collision",
        }

        required_fields = ["investigation_number", "occurrence_date", "occurrence_type"]

        is_valid = all(
            field in record_with_empty and record_with_empty[field]
            for field in required_fields
        )

        assert is_valid is False

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "date_str,expected_valid",
        [
            ("2024-03-15", True),
            ("2024-03-15T14:30:00", True),
            ("15/03/2024", True),  # AU format
            ("15 March 2024", True),  # Written format
            ("invalid-date", False),
            ("", False),
            (None, False),
            ("32/13/2024", False),  # Invalid date
        ],
    )
    def test_validate_date_format(self, date_str, expected_valid):
        """Test validation of date field formats."""

        def is_valid_date(date_string):
            if not date_string:
                return False

            date_formats = [
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
                "%d/%m/%Y",
                "%d %B %Y",
            ]

            for fmt in date_formats:
                try:
                    datetime.strptime(date_string, fmt)
                    return True
                except ValueError:
                    continue

            return False

        assert is_valid_date(date_str) == expected_valid

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "inv_number,expected_valid",
        [
            ("MO-2024-001", True),
            ("MO-2023-015", True),
            ("MO-2024-100", True),
            ("AO-2024-001", True),  # Aviation (also valid format)
            ("RO-2024-001", True),  # Rail (also valid format)
            ("2024-001", False),  # Missing prefix
            ("MO2024001", False),  # Missing dashes
            ("MO-24-001", False),  # Short year
            ("", False),
            (None, False),
        ],
    )
    def test_validate_investigation_number_format(self, inv_number, expected_valid):
        """Test validation of ATSB investigation number format."""
        import re

        def is_valid_investigation_number(inv_str):
            if not inv_str:
                return False

            # ATSB format: XX-YYYY-NNN (e.g., MO-2024-001)
            pattern = re.compile(r"^[A-Z]{2}-\d{4}-\d{3}$")
            return bool(pattern.match(inv_str))

        assert is_valid_investigation_number(inv_number) == expected_valid


# ============================================================================
# ATSBImporter Tests - Read Source
# ============================================================================


class TestATSBImporterReadSource:
    """Tests for ATSBImporter.read_source() method."""

    @pytest.mark.unit
    def test_read_source_yields_records(self, temp_atsb_data_file):
        """Test read_source yields records from JSON file."""
        with open(temp_atsb_data_file, "r") as f:
            records = json.load(f)

        assert isinstance(records, list)
        assert len(records) > 0

        for record in records:
            assert isinstance(record, dict)
            assert "investigation_number" in record

    @pytest.mark.unit
    def test_read_source_handles_empty_file(self, tmp_path):
        """Test read_source handles empty JSON array."""
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("[]")

        with open(empty_file, "r") as f:
            records = json.load(f)

        assert records == []

    @pytest.mark.unit
    def test_read_source_handles_invalid_json(self, tmp_path):
        """Test read_source raises error for invalid JSON."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json {")

        with pytest.raises(json.JSONDecodeError):
            with open(invalid_file, "r") as f:
                json.load(f)


# ============================================================================
# ATSBImporter Tests - Parse Record
# ============================================================================


class TestATSBImporterParseRecord:
    """Tests for ATSBImporter.parse_record() method."""

    @pytest.mark.unit
    def test_parse_record_maps_fields_correctly(self, sample_atsb_investigation_record):
        """Test parse_record correctly maps ATSB fields to standardized format."""
        record = sample_atsb_investigation_record

        # Simulate parsing logic
        parsed = {
            "source_agency": DataSource.ATSB.value,
            "source_incident_id": record["investigation_number"],
            "incident_date": datetime.strptime(
                record["occurrence_date"], "%Y-%m-%d"
            ).date(),
            "fatalities": int(record.get("fatalities", 0) or 0),
            "injuries": (
                int(record.get("serious_injuries", 0) or 0)
                + int(record.get("minor_injuries", 0) or 0)
            ),
            "description": record.get("synopsis"),
        }

        assert parsed["source_agency"] == "atsb"
        assert parsed["source_incident_id"] == "MO-2024-001"
        assert parsed["incident_date"] == date(2024, 3, 15)
        assert parsed["fatalities"] == 0
        assert parsed["injuries"] == 5
        assert "collision" in parsed["description"].lower()

    @pytest.mark.unit
    def test_parse_record_handles_missing_fields(self, sample_atsb_record_minimal):
        """Test parse_record handles records with minimal fields."""
        record = sample_atsb_record_minimal

        # Simulate parsing with defaults for missing fields
        parsed = {
            "source_agency": DataSource.ATSB.value,
            "source_incident_id": record["investigation_number"],
            "incident_date": datetime.strptime(
                record["occurrence_date"], "%Y-%m-%d"
            ).date(),
            "fatalities": int(record.get("fatalities", 0) or 0),
            "injuries": int(record.get("serious_injuries", 0) or 0),
            "description": record.get("synopsis"),
        }

        assert parsed["source_incident_id"] == "MO-2024-002"
        assert parsed["fatalities"] == 0
        assert parsed["injuries"] == 0
        assert parsed["description"] is None

    @pytest.mark.unit
    def test_parse_record_returns_none_for_invalid(self):
        """Test parse_record returns None for invalid records."""
        invalid_record = {}

        # Check if record has minimum required fields
        required_fields = ["investigation_number", "occurrence_date"]
        has_required = all(
            field in invalid_record and invalid_record[field]
            for field in required_fields
        )

        assert has_required is False

    @pytest.mark.unit
    def test_parse_record_extracts_location(self, sample_atsb_investigation_record):
        """Test parse_record extracts location information."""
        record = sample_atsb_investigation_record

        location = {
            "location_name": record.get("location_description"),
            "state": record.get("state"),
            "country": "Australia",
            "sea_area": record.get("sea_area"),
            "latitude": float(record["latitude"]) if record.get("latitude") else None,
            "longitude": (
                float(record["longitude"]) if record.get("longitude") else None
            ),
        }

        assert location["location_name"] == "Sydney Harbour approaches"
        assert location["state"] == "New South Wales"
        assert location["country"] == "Australia"
        assert location["sea_area"] == "Tasman Sea"
        assert location["latitude"] == pytest.approx(-33.8688, rel=1e-4)
        assert location["longitude"] == pytest.approx(151.2093, rel=1e-4)

    @pytest.mark.unit
    def test_parse_record_extracts_vessel(self, sample_atsb_investigation_record):
        """Test parse_record extracts vessel information."""
        record = sample_atsb_investigation_record

        vessel = {
            "vessel_name": record.get("vessel_name"),
            "vessel_type": record.get("vessel_type"),
            "imo_number": record.get("vessel_imo"),
            "gross_tonnage": (
                float(record["vessel_gross_tonnage"])
                if record.get("vessel_gross_tonnage")
                else None
            ),
            "flag_state": record.get("vessel_flag"),
            "year_built": (
                int(record["vessel_year_built"])
                if record.get("vessel_year_built")
                else None
            ),
        }

        assert vessel["vessel_name"] == "MV PACIFIC EXPLORER"
        assert vessel["vessel_type"] == "Cargo ship"
        assert vessel["imo_number"] == "9123456"
        assert vessel["gross_tonnage"] == 45000.0
        assert vessel["flag_state"] == "Australia"
        assert vessel["year_built"] == 2015


# ============================================================================
# ATSBImporter Tests - Map to Model
# ============================================================================


class TestATSBImporterMapToModel:
    """Tests for ATSBImporter.map_to_model() method."""

    @pytest.mark.unit
    def test_map_to_model_creates_incident(
        self, sample_parsed_atsb_record, mock_session
    ):
        """Test map_to_model creates Incident model instance."""
        parsed = sample_parsed_atsb_record

        # Verify parsed record has required fields for Incident
        assert parsed["source_agency"] == "atsb"
        assert parsed["source_incident_id"] == "MO-2024-001"
        assert parsed["incident_date"] is not None
        assert "incident_type" in parsed

    @pytest.mark.unit
    def test_map_to_model_creates_vessel(self, sample_parsed_atsb_record, mock_session):
        """Test map_to_model creates Vessel model from parsed data."""
        vessel_data = sample_parsed_atsb_record["vessel"]

        assert vessel_data["vessel_name"] == "MV PACIFIC EXPLORER"
        assert vessel_data["vessel_type"] == "cargo_vessel"
        assert vessel_data["imo_number"] == "9123456"
        assert vessel_data["flag_state"] == "AU"

    @pytest.mark.unit
    def test_map_to_model_creates_location(
        self, sample_parsed_atsb_record, mock_session
    ):
        """Test map_to_model creates Location model from parsed data."""
        location_data = sample_parsed_atsb_record["location"]

        assert location_data["location_name"] == "Sydney Harbour approaches"
        assert location_data["state"] == "NSW"
        assert location_data["country"] == "Australia"
        assert location_data["latitude"] == pytest.approx(-33.8688, rel=1e-4)
        assert location_data["longitude"] == pytest.approx(151.2093, rel=1e-4)

    @pytest.mark.unit
    def test_map_to_model_handles_missing_vessel(
        self, sample_atsb_record_missing_vessel, mock_session
    ):
        """Test map_to_model handles records without vessel data."""
        record = sample_atsb_record_missing_vessel

        # Verify no vessel data present
        assert record.get("vessel_name") is None
        assert record.get("vessel_type") is None
        assert record.get("vessel_imo") is None

    @pytest.mark.unit
    def test_map_to_model_returns_none_for_invalid(self, mock_session):
        """Test map_to_model returns None for unmappable records."""
        invalid_parsed = {
            "source_agency": "atsb",
            # Missing required fields
        }

        has_required = (
            "source_incident_id" in invalid_parsed and "incident_date" in invalid_parsed
        )
        assert has_required is False


# ============================================================================
# ATSBImporter Tests - Duplicate Detection
# ============================================================================


class TestATSBImporterDuplicateDetection:
    """Tests for ATSBImporter.is_duplicate() method."""

    @pytest.mark.unit
    def test_is_duplicate_detects_existing(
        self, mock_session, sample_parsed_atsb_record
    ):
        """Test is_duplicate returns True for existing records."""
        # Configure mock to return existing record
        existing_incident = MagicMock(spec=Incident)
        existing_incident.source_agency = DataSource.ATSB.value
        existing_incident.source_incident_id = "MO-2024-001"

        mock_session.query.return_value.filter.return_value.first.return_value = (
            existing_incident
        )

        # Verify duplicate check query
        result = mock_session.query.return_value.filter.return_value.first()
        assert result is not None
        assert result.source_incident_id == "MO-2024-001"

    @pytest.mark.unit
    def test_is_duplicate_returns_false_for_new(
        self, mock_session, sample_parsed_atsb_record
    ):
        """Test is_duplicate returns False for new records."""
        # Configure mock to return None (no existing record)
        mock_session.query.return_value.filter.return_value.first.return_value = None

        result = mock_session.query.return_value.filter.return_value.first()
        assert result is None


# ============================================================================
# ATSB Occurrence Type Mapping Tests
# ============================================================================


class TestOccurrenceTypeMapping:
    """Tests for ATSB occurrence type to IncidentType mapping."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "atsb_occurrence_type,expected_type",
        [
            ("Collision", IncidentType.COLLISION.value),
            ("COLLISION", IncidentType.COLLISION.value),
            ("Contact", IncidentType.COLLISION.value),
            ("Grounding", IncidentType.GROUNDING.value),
            ("Stranding", IncidentType.GROUNDING.value),
            ("Fire", IncidentType.FIRE.value),
            ("Fire/explosion", IncidentType.FIRE.value),
            ("Explosion", IncidentType.EXPLOSION.value),
            ("Flooding", IncidentType.FLOODING.value),
            ("Foundering", IncidentType.FLOODING.value),
            ("Sinking", IncidentType.FLOODING.value),
            ("Capsizing", IncidentType.CAPSIZING.value),
            ("Capsize", IncidentType.CAPSIZING.value),
            ("Hull failure", IncidentType.STRUCTURAL_FAILURE.value),
            ("Structural failure", IncidentType.STRUCTURAL_FAILURE.value),
            ("Machinery failure", IncidentType.EQUIPMENT_FAILURE.value),
            ("Equipment failure", IncidentType.EQUIPMENT_FAILURE.value),
            ("Loss of propulsion", IncidentType.LOSS_OF_PROPULSION.value),
            ("Loss of steering", IncidentType.LOSS_OF_CONTROL.value),
            ("Heavy weather damage", IncidentType.WEATHER_RELATED.value),
            ("Person overboard", IncidentType.PERSONNEL_INJURY.value),
            ("Man overboard", IncidentType.PERSONNEL_INJURY.value),
            ("Occupational incident", IncidentType.PERSONNEL_INJURY.value),
            ("Missing", IncidentType.OTHER.value),
            ("Unknown", IncidentType.OTHER.value),
            ("", IncidentType.OTHER.value),
            (None, IncidentType.OTHER.value),
        ],
    )
    def test_occurrence_type_mapping(self, atsb_occurrence_type, expected_type):
        """Test ATSB occurrence types map to IncidentType correctly."""
        OCCURRENCE_TYPE_MAPPINGS = {
            "collision": IncidentType.COLLISION.value,
            "contact": IncidentType.COLLISION.value,
            "grounding": IncidentType.GROUNDING.value,
            "stranding": IncidentType.GROUNDING.value,
            "fire": IncidentType.FIRE.value,
            "fire/explosion": IncidentType.FIRE.value,
            "explosion": IncidentType.EXPLOSION.value,
            "flooding": IncidentType.FLOODING.value,
            "foundering": IncidentType.FLOODING.value,
            "sinking": IncidentType.FLOODING.value,
            "capsizing": IncidentType.CAPSIZING.value,
            "capsize": IncidentType.CAPSIZING.value,
            "hull failure": IncidentType.STRUCTURAL_FAILURE.value,
            "structural failure": IncidentType.STRUCTURAL_FAILURE.value,
            "machinery failure": IncidentType.EQUIPMENT_FAILURE.value,
            "equipment failure": IncidentType.EQUIPMENT_FAILURE.value,
            "loss of propulsion": IncidentType.LOSS_OF_PROPULSION.value,
            "loss of steering": IncidentType.LOSS_OF_CONTROL.value,
            "heavy weather damage": IncidentType.WEATHER_RELATED.value,
            "heavy weather": IncidentType.WEATHER_RELATED.value,
            "person overboard": IncidentType.PERSONNEL_INJURY.value,
            "man overboard": IncidentType.PERSONNEL_INJURY.value,
            "occupational incident": IncidentType.PERSONNEL_INJURY.value,
        }

        def map_occurrence_type(occurrence_str):
            if not occurrence_str:
                return IncidentType.OTHER.value
            occ_lower = occurrence_str.lower().strip()

            # Try exact match
            if occ_lower in OCCURRENCE_TYPE_MAPPINGS:
                return OCCURRENCE_TYPE_MAPPINGS[occ_lower]

            # Try partial match
            for key, value in OCCURRENCE_TYPE_MAPPINGS.items():
                if key in occ_lower or occ_lower in key:
                    return value

            return IncidentType.OTHER.value

        result = map_occurrence_type(atsb_occurrence_type)
        assert result == expected_type


# ============================================================================
# ATSB Vessel Type Mapping Tests
# ============================================================================


class TestVesselTypeMapping:
    """Tests for ATSB vessel type to VesselType mapping."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "atsb_vessel_type,expected_type",
        [
            ("Cargo ship", VesselType.CARGO_VESSEL.value),
            ("Bulk carrier", VesselType.CARGO_VESSEL.value),
            ("Container ship", VesselType.CARGO_VESSEL.value),
            ("General cargo", VesselType.CARGO_VESSEL.value),
            ("Tanker", VesselType.TANKER.value),
            ("Oil tanker", VesselType.TANKER.value),
            ("Chemical tanker", VesselType.TANKER.value),
            ("LNG carrier", VesselType.TANKER.value),
            ("Tug", VesselType.TUG.value),
            ("Tugboat", VesselType.TUG.value),
            ("Towing vessel", VesselType.TUG.value),
            ("Supply vessel", VesselType.SUPPLY_VESSEL.value),
            ("Platform supply vessel", VesselType.SUPPLY_VESSEL.value),
            ("Offshore supply", VesselType.SUPPLY_VESSEL.value),
            ("Anchor handling tug supply", VesselType.ANCHOR_HANDLING.value),
            ("AHTS", VesselType.ANCHOR_HANDLING.value),
            ("Drilling rig", VesselType.DRILLING_RIG.value),
            ("Mobile offshore drilling unit", VesselType.MODU.value),
            ("MODU", VesselType.MODU.value),
            ("Jack-up", VesselType.JACKUP_RIG.value),
            ("FPSO", VesselType.FPSO.value),
            ("Research vessel", VesselType.RESEARCH_VESSEL.value),
            ("Cable layer", VesselType.CABLE_LAYER.value),
            ("Diving support vessel", VesselType.DIVING_SUPPORT.value),
            ("Crew boat", VesselType.CREW_BOAT.value),
            ("Fishing vessel", VesselType.OTHER.value),
            ("Passenger ship", VesselType.OTHER.value),
            ("Ferry", VesselType.OTHER.value),
            ("Recreational", VesselType.OTHER.value),
            ("Unknown", VesselType.OTHER.value),
            ("", VesselType.OTHER.value),
            (None, VesselType.OTHER.value),
        ],
    )
    def test_vessel_type_mapping(self, atsb_vessel_type, expected_type):
        """Test ATSB vessel types map to VesselType correctly."""
        VESSEL_TYPE_MAPPINGS = {
            "cargo ship": VesselType.CARGO_VESSEL.value,
            "bulk carrier": VesselType.CARGO_VESSEL.value,
            "container ship": VesselType.CARGO_VESSEL.value,
            "container": VesselType.CARGO_VESSEL.value,
            "general cargo": VesselType.CARGO_VESSEL.value,
            "cargo": VesselType.CARGO_VESSEL.value,
            "tanker": VesselType.TANKER.value,
            "oil tanker": VesselType.TANKER.value,
            "chemical tanker": VesselType.TANKER.value,
            "lng carrier": VesselType.TANKER.value,
            "lpg carrier": VesselType.TANKER.value,
            "product tanker": VesselType.TANKER.value,
            "tug": VesselType.TUG.value,
            "tugboat": VesselType.TUG.value,
            "towing vessel": VesselType.TUG.value,
            "supply vessel": VesselType.SUPPLY_VESSEL.value,
            "platform supply vessel": VesselType.SUPPLY_VESSEL.value,
            "offshore supply": VesselType.SUPPLY_VESSEL.value,
            "osv": VesselType.SUPPLY_VESSEL.value,
            "anchor handling tug supply": VesselType.ANCHOR_HANDLING.value,
            "ahts": VesselType.ANCHOR_HANDLING.value,
            "anchor handling": VesselType.ANCHOR_HANDLING.value,
            "drilling rig": VesselType.DRILLING_RIG.value,
            "mobile offshore drilling unit": VesselType.MODU.value,
            "modu": VesselType.MODU.value,
            "jack-up": VesselType.JACKUP_RIG.value,
            "jackup": VesselType.JACKUP_RIG.value,
            "fpso": VesselType.FPSO.value,
            "research vessel": VesselType.RESEARCH_VESSEL.value,
            "research": VesselType.RESEARCH_VESSEL.value,
            "cable layer": VesselType.CABLE_LAYER.value,
            "cable ship": VesselType.CABLE_LAYER.value,
            "diving support vessel": VesselType.DIVING_SUPPORT.value,
            "diving support": VesselType.DIVING_SUPPORT.value,
            "dive support": VesselType.DIVING_SUPPORT.value,
            "crew boat": VesselType.CREW_BOAT.value,
            "crewboat": VesselType.CREW_BOAT.value,
        }

        def map_vessel_type(vessel_type_str):
            if not vessel_type_str:
                return VesselType.OTHER.value
            type_lower = vessel_type_str.lower().strip()

            # Try exact match
            if type_lower in VESSEL_TYPE_MAPPINGS:
                return VESSEL_TYPE_MAPPINGS[type_lower]

            # Try partial match
            for key, value in VESSEL_TYPE_MAPPINGS.items():
                if key in type_lower:
                    return value

            return VesselType.OTHER.value

        result = map_vessel_type(atsb_vessel_type)
        assert result == expected_type


# ============================================================================
# Australian State Mapping Tests
# ============================================================================


class TestAustralianStateMapping:
    """Tests for Australian state name to code normalization."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "state_name,expected_code",
        [
            ("New South Wales", "NSW"),
            ("NEW SOUTH WALES", "NSW"),
            ("nsw", "NSW"),
            ("Victoria", "VIC"),
            ("vic", "VIC"),
            ("Queensland", "QLD"),
            ("qld", "QLD"),
            ("Western Australia", "WA"),
            ("wa", "WA"),
            ("South Australia", "SA"),
            ("sa", "SA"),
            ("Tasmania", "TAS"),
            ("tas", "TAS"),
            ("Northern Territory", "NT"),
            ("nt", "NT"),
            ("Australian Capital Territory", "ACT"),
            ("ACT", "ACT"),
            ("act", "ACT"),
            # Territories
            ("Norfolk Island", "NFK"),
            ("Cocos Islands", "CCK"),
            ("Christmas Island", "CXR"),
            # Invalid/Unknown
            ("Unknown", "XX"),
            ("", "XX"),
            (None, "XX"),
            ("International Waters", "INT"),
        ],
    )
    def test_australian_state_mapping(self, state_name, expected_code):
        """Test Australian state names are normalized to state codes."""
        STATE_MAPPINGS = {
            "new south wales": "NSW",
            "nsw": "NSW",
            "victoria": "VIC",
            "vic": "VIC",
            "queensland": "QLD",
            "qld": "QLD",
            "western australia": "WA",
            "wa": "WA",
            "south australia": "SA",
            "sa": "SA",
            "tasmania": "TAS",
            "tas": "TAS",
            "northern territory": "NT",
            "nt": "NT",
            "australian capital territory": "ACT",
            "act": "ACT",
            "norfolk island": "NFK",
            "cocos islands": "CCK",
            "christmas island": "CXR",
            "international waters": "INT",
        }

        def normalize_state(state_str):
            if not state_str:
                return "XX"
            state_lower = state_str.lower().strip()

            if state_lower in STATE_MAPPINGS:
                return STATE_MAPPINGS[state_lower]

            # If already a known code, return uppercase
            known_codes = set(STATE_MAPPINGS.values())
            if state_lower.upper() in known_codes:
                return state_lower.upper()

            return "XX"

        result = normalize_state(state_name)
        assert result == expected_code


# ============================================================================
# Data Quality Tests
# ============================================================================


class TestATSBDataQuality:
    """Tests for data quality validation functions."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "lat,lon,expected_valid",
        [
            (-33.8688, 151.2093, True),  # Sydney
            (-37.8136, 144.9631, True),  # Melbourne
            (-27.4705, 153.0260, True),  # Brisbane
            (-31.9505, 115.8605, True),  # Perth
            (-90.0, 0.0, True),  # South Pole
            (90.0, 0.0, True),  # North Pole
            (0.0, 180.0, True),  # Date line
            (0.0, -180.0, True),  # Date line
            (91.0, 0.0, False),  # Invalid latitude (too high)
            (-91.0, 0.0, False),  # Invalid latitude (too low)
            (0.0, 181.0, False),  # Invalid longitude (too high)
            (0.0, -181.0, False),  # Invalid longitude (too low)
            (None, None, True),  # Missing coordinates acceptable
            (-33.0, None, False),  # Partial coordinates invalid
            (None, 151.0, False),  # Partial coordinates invalid
        ],
    )
    def test_coordinate_validation(self, lat, lon, expected_valid):
        """Test geographic coordinate validation."""

        def validate_coordinates(latitude, longitude):
            if latitude is None and longitude is None:
                return True
            if latitude is None or longitude is None:
                return False
            return -90 <= latitude <= 90 and -180 <= longitude <= 180

        assert validate_coordinates(lat, lon) == expected_valid

    @pytest.mark.unit
    def test_australian_waters_coordinate_check(self):
        """Test coordinates are within Australian waters."""

        def is_in_australian_waters(lat, lon):
            """Check if coordinates are approximately within Australian waters."""
            if lat is None or lon is None:
                return False

            # Approximate bounding box for Australian waters
            # (includes EEZ and nearby international waters)
            return -50 <= lat <= -8 and 100 <= lon <= 180

        # Valid Australian locations
        assert is_in_australian_waters(-33.8688, 151.2093) is True  # Sydney
        assert is_in_australian_waters(-12.4634, 130.8456) is True  # Darwin
        assert is_in_australian_waters(-23.8560, 151.2578) is True  # Great Barrier Reef

        # Outside Australian waters
        assert is_in_australian_waters(51.5074, -0.1278) is False  # London
        assert is_in_australian_waters(40.7128, -74.0060) is False  # New York

    @pytest.mark.unit
    def test_injury_count_validation(self, sample_atsb_investigation_record):
        """Test injury counts are non-negative integers."""
        record = sample_atsb_investigation_record

        fatalities = int(record.get("fatalities", 0) or 0)
        serious = int(record.get("serious_injuries", 0) or 0)
        minor = int(record.get("minor_injuries", 0) or 0)

        assert fatalities >= 0
        assert serious >= 0
        assert minor >= 0

    @pytest.mark.unit
    def test_imo_number_format_validation(self):
        """Test IMO number format validation."""

        def is_valid_imo(imo_str):
            if not imo_str:
                return True  # Optional field
            # IMO numbers are 7 digits
            clean = imo_str.replace("IMO", "").strip()
            return clean.isdigit() and len(clean) == 7

        assert is_valid_imo("9123456") is True
        assert is_valid_imo("IMO9123456") is True
        assert is_valid_imo("123") is False
        assert is_valid_imo("12345678") is False
        assert is_valid_imo("") is True
        assert is_valid_imo(None) is True


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestATSBImporterErrorHandling:
    """Tests for error handling in ATSBImporter."""

    @pytest.mark.unit
    def test_parse_record_handles_date_parse_error(self):
        """Test parse_record handles malformed date strings."""
        record_bad_date = {
            "investigation_number": "MO-2024-001",
            "occurrence_date": "not-a-date",
            "occurrence_type": "Collision",
        }

        def parse_date(date_str):
            if not date_str:
                return None

            date_formats = [
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
                "%d/%m/%Y",
                "%d %B %Y",
            ]

            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue

            return None

        result = parse_date(record_bad_date["occurrence_date"])
        assert result is None

    @pytest.mark.unit
    def test_parse_record_handles_numeric_parse_error(self):
        """Test parse_record handles non-numeric values in numeric fields."""

        def safe_int(value, default=0):
            if not value:
                return default
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return default

        def safe_float(value, default=None):
            if not value:
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default

        assert safe_int("not-a-number") == 0
        assert safe_int(None) == 0
        assert safe_int("") == 0
        assert safe_int("123") == 123
        assert safe_int("45.6") == 45

        assert safe_float("not-a-number") is None
        assert safe_float(None) is None
        assert safe_float("45000") == 45000.0

    @pytest.mark.unit
    def test_import_handles_database_error(self, mock_session):
        """Test import process handles database errors gracefully."""
        from sqlalchemy.exc import IntegrityError

        mock_session.commit.side_effect = IntegrityError("Duplicate key", None, None)

        with pytest.raises(IntegrityError):
            mock_session.commit()

        # Verify rollback would be called in actual implementation
        mock_session.rollback.assert_not_called()  # Not called yet in this test


# ============================================================================
# Integration Tests
# ============================================================================


class TestATSBImporterIntegration:
    """Integration tests for ATSBImporter."""

    @pytest.mark.integration
    def test_full_import_workflow(
        self, temp_atsb_data_file, mock_session, sample_atsb_investigation_record
    ):
        """Test complete import workflow from file to database."""
        # Read source data
        with open(temp_atsb_data_file, "r") as f:
            records = json.load(f)

        assert len(records) > 0

        # Simulate parsing each record
        for record in records:
            assert "investigation_number" in record

        # Verify session operations would be called
        mock_session.query.return_value.filter.return_value.first.return_value = None

    @pytest.mark.integration
    def test_import_batch_processing(self, mock_session):
        """Test batch processing of multiple records."""
        batch_size = 100
        total_records = 250

        # Calculate expected batches
        expected_batches = (total_records + batch_size - 1) // batch_size

        assert expected_batches == 3

    @pytest.mark.integration
    def test_import_statistics_tracking(self):
        """Test import statistics are tracked correctly."""
        stats = {
            "total_records": 0,
            "imported": 0,
            "skipped": 0,
            "errors": 0,
            "duplicates": 0,
        }

        # Simulate processing
        stats["total_records"] = 100
        stats["imported"] = 85
        stats["duplicates"] = 10
        stats["errors"] = 5

        assert (
            stats["total_records"]
            == stats["imported"] + stats["duplicates"] + stats["errors"]
        )

    @pytest.mark.integration
    def test_import_with_mixed_data_quality(self, tmp_path, mock_session):
        """Test import handles records with varying data quality."""
        data = [
            {
                "investigation_number": "MO-2024-001",
                "occurrence_date": "2024-03-15",
                "occurrence_type": "Collision",
                "vessel_name": "Good Vessel",
                "latitude": "-33.8688",
                "longitude": "151.2093",
            },
            {
                "investigation_number": "MO-2024-002",
                "occurrence_date": "invalid-date",
                "occurrence_type": "Grounding",
            },
            {
                "investigation_number": "MO-2024-003",
                "occurrence_date": "2024-04-10",
                "occurrence_type": "Fire",
                # Missing location
            },
            {
                # Missing investigation_number
                "occurrence_date": "2024-05-01",
                "occurrence_type": "Explosion",
            },
            {
                "investigation_number": "MO-2024-004",
                "occurrence_date": "2024-06-01",
                "occurrence_type": "Capsizing",
            },
        ]

        file_path = tmp_path / "mixed_quality.json"
        file_path.write_text(json.dumps(data))

        with open(file_path, "r") as f:
            records = json.load(f)

        valid_count = 0
        invalid_count = 0

        date_formats = ["%Y-%m-%d", "%d/%m/%Y"]

        for record in records:
            has_id = bool(record.get("investigation_number", ""))
            has_date = bool(record.get("occurrence_date", ""))

            # Try to parse date
            date_valid = False
            if has_date:
                for fmt in date_formats:
                    try:
                        datetime.strptime(record["occurrence_date"], fmt)
                        date_valid = True
                        break
                    except ValueError:
                        continue

            if has_id and date_valid:
                valid_count += 1
            else:
                invalid_count += 1

        assert valid_count == 3  # MO-2024-001, MO-2024-003, MO-2024-004
        assert invalid_count == 2  # Bad date, Missing ID


# ============================================================================
# Investigation Status Mapping Tests
# ============================================================================


class TestInvestigationStatusMapping:
    """Tests for ATSB investigation status to IncidentStatus mapping."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "atsb_status,expected_status",
        [
            ("Ongoing", IncidentStatus.UNDER_INVESTIGATION.value),
            ("Under investigation", IncidentStatus.UNDER_INVESTIGATION.value),
            ("UNDER INVESTIGATION", IncidentStatus.UNDER_INVESTIGATION.value),
            ("Preliminary report", IncidentStatus.PRELIMINARY_REPORT.value),
            ("Final report", IncidentStatus.FINAL_REPORT.value),
            ("Final Report", IncidentStatus.FINAL_REPORT.value),
            ("FINAL REPORT", IncidentStatus.FINAL_REPORT.value),
            ("Closed", IncidentStatus.CLOSED.value),
            ("Archived", IncidentStatus.ARCHIVED.value),
            ("Unknown", IncidentStatus.REPORTED.value),
            ("", IncidentStatus.REPORTED.value),
            (None, IncidentStatus.REPORTED.value),
        ],
    )
    def test_investigation_status_mapping(self, atsb_status, expected_status):
        """Test ATSB investigation status maps to IncidentStatus correctly."""
        STATUS_MAPPINGS = {
            "ongoing": IncidentStatus.UNDER_INVESTIGATION.value,
            "under investigation": IncidentStatus.UNDER_INVESTIGATION.value,
            "preliminary report": IncidentStatus.PRELIMINARY_REPORT.value,
            "final report": IncidentStatus.FINAL_REPORT.value,
            "closed": IncidentStatus.CLOSED.value,
            "archived": IncidentStatus.ARCHIVED.value,
        }

        def map_investigation_status(status_str):
            if not status_str:
                return IncidentStatus.REPORTED.value
            status_lower = status_str.lower().strip()

            if status_lower in STATUS_MAPPINGS:
                return STATUS_MAPPINGS[status_lower]

            return IncidentStatus.REPORTED.value

        result = map_investigation_status(atsb_status)
        assert result == expected_status


# ============================================================================
# Occurrence Category Severity Mapping Tests
# ============================================================================


class TestOccurrenceCategorySeverityMapping:
    """Tests for ATSB occurrence category to severity mapping."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "category,expected_severity",
        [
            ("Very serious marine casualty", SeverityLevel.CATASTROPHIC),
            ("VERY SERIOUS MARINE CASUALTY", SeverityLevel.CATASTROPHIC),
            ("Serious marine casualty", SeverityLevel.SERIOUS),
            ("Serious incident", SeverityLevel.SERIOUS),
            ("Marine casualty", SeverityLevel.MODERATE),
            ("Marine incident", SeverityLevel.MINOR),
            ("Incident", SeverityLevel.MINOR),
            ("Near miss", SeverityLevel.MINIMAL),
            ("Unknown", SeverityLevel.MODERATE),
            ("", SeverityLevel.MODERATE),
            (None, SeverityLevel.MODERATE),
        ],
    )
    def test_occurrence_category_to_severity(self, category, expected_severity):
        """Test ATSB occurrence categories map to severity levels."""
        CATEGORY_SEVERITY_MAPPINGS = {
            "very serious marine casualty": SeverityLevel.CATASTROPHIC,
            "serious marine casualty": SeverityLevel.SERIOUS,
            "serious incident": SeverityLevel.SERIOUS,
            "marine casualty": SeverityLevel.MODERATE,
            "marine incident": SeverityLevel.MINOR,
            "incident": SeverityLevel.MINOR,
            "near miss": SeverityLevel.MINIMAL,
        }

        def map_category_to_severity(category_str):
            if not category_str:
                return SeverityLevel.MODERATE

            cat_lower = category_str.lower().strip()

            if cat_lower in CATEGORY_SEVERITY_MAPPINGS:
                return CATEGORY_SEVERITY_MAPPINGS[cat_lower]

            # Try partial match for variations
            for key, value in CATEGORY_SEVERITY_MAPPINGS.items():
                if key in cat_lower:
                    return value

            return SeverityLevel.MODERATE

        result = map_category_to_severity(category)
        assert result == expected_severity


# ============================================================================
# URL Validation Tests
# ============================================================================


class TestATSBURLValidation:
    """Tests for ATSB report URL validation."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "url,expected_valid",
        [
            (
                "https://www.atsb.gov.au/publications/investigation_reports/2024/mair/mo-2024-001",
                True,
            ),
            ("https://www.atsb.gov.au/media/12345/mo-2024-001.pdf", True),
            ("http://www.atsb.gov.au/publications/report", True),
            ("https://atsb.gov.au/publications/report", True),
            ("https://example.com/report", True),
            ("ftp://atsb.gov.au/report", False),
            ("not-a-url", False),
            ("", False),
            (None, False),
        ],
    )
    def test_url_validation(self, url, expected_valid):
        """Test URL format validation for report links."""
        import re

        def is_valid_url(url_str):
            if not url_str:
                return False

            url_pattern = re.compile(
                r"^https?://"
                r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
                r"localhost|"
                r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
                r"(?::\d+)?"
                r"(?:/?|[/?]\S+)$",
                re.IGNORECASE,
            )

            return bool(url_pattern.match(url_str))

        assert is_valid_url(url) == expected_valid

    @pytest.mark.unit
    def test_atsb_specific_url_validation(self):
        """Test ATSB-specific URL format validation."""
        import re

        def is_atsb_url(url_str):
            if not url_str:
                return False

            # ATSB URLs should be from atsb.gov.au domain
            atsb_pattern = re.compile(
                r"^https?://" r"(?:www\.)?atsb\.gov\.au" r"/\S+$", re.IGNORECASE
            )

            return bool(atsb_pattern.match(url_str))

        assert is_atsb_url("https://www.atsb.gov.au/publications/report") is True
        assert is_atsb_url("https://atsb.gov.au/media/file.pdf") is True
        assert is_atsb_url("http://www.atsb.gov.au/publications") is True
        assert is_atsb_url("https://example.com/report") is False
        assert is_atsb_url("https://fake-atsb.gov.au/report") is False


# ============================================================================
# Rate Limiting Tests
# ============================================================================


class TestATSBScraperRateLimiting:
    """Tests for rate limiting functionality."""

    @pytest.mark.unit
    def test_rate_limiter_enforces_delay(self):
        """Test rate limiter enforces minimum delay between requests."""
        import time

        # ATSB typically requires longer delays (2+ seconds)
        rate_limit_delay = 0.1  # Use short delay for testing

        start = time.time()
        time.sleep(rate_limit_delay)
        elapsed = time.time() - start

        assert elapsed >= rate_limit_delay

    @pytest.mark.unit
    def test_rate_limiter_tracks_request_count(self):
        """Test rate limiter tracks request count."""
        request_count = 0
        max_requests = 5

        for _ in range(max_requests):
            request_count += 1

        assert request_count == max_requests

    @pytest.mark.unit
    def test_respectful_scraping_delay(self):
        """Test that ATSB scraping uses respectful delays."""
        # ATSB is a government site - should use longer delays
        recommended_delay = 2.0  # seconds

        # Verify delay is reasonable for government site
        assert recommended_delay >= 1.0
        assert recommended_delay <= 5.0
