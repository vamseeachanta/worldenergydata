"""
Test suite for USCG marine incident scraper.

Tests web scraping, PDF extraction, rate limiting, and error handling.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests
from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError, RequestException, Timeout

from worldenergydata.marine_safety.scrapers.uscg_scraper import (
    USCGMarineCasualtyScraper,
)


@pytest.fixture
def scraper():
    """Create a USCG scraper instance for testing."""
    return USCGScraper(
        rate_limit_delay=0.1, max_retries=3, timeout=5  # Short delay for tests
    )


@pytest.fixture
def sample_html():
    """Sample HTML response from USCG website."""
    return """
  <html>
    <body>
      <table class="incident-table">
        <tr>
          <td class="date">2024-01-15</td>
          <td class="type">Collision</td>
          <td class="vessel">Test Vessel</td>
          <td class="location">Gulf of Mexico</td>
          <td class="severity">Moderate</td>
        </tr>
        <tr>
          <td class="date">2024-01-20</td>
          <td class="type">Grounding</td>
          <td class="vessel">Another Vessel</td>
          <td class="location">Port of Houston</td>
          <td class="severity">Minor</td>
        </tr>
      </table>
    </body>
  </html>
  """


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    response = Mock()
    response.status_code = 200
    response.text = "<html><body>Test</body></html>"
    response.content = b"PDF content here"
    response.headers = {"Content-Type": "text/html"}
    return response


class TestUSCGScraper:
    """Test suite for USCGScraper class."""

    @pytest.mark.unit
    def test_scraper_initialization(self, scraper):
        """Test scraper initializes with correct parameters."""
        assert scraper.rate_limit_delay == 0.1
        assert scraper.max_retries == 3
        assert scraper.timeout == 5

    @pytest.mark.unit
    @patch("requests.get")
    def test_fetch_page_success(self, mock_get, scraper, mock_response):
        """Test successful page fetch."""
        mock_get.return_value = mock_response

        response = scraper.fetch_page("https://uscg.gov/incidents")

        assert response.status_code == 200
        assert response.text == "<html><body>Test</body></html>"
        mock_get.assert_called_once()

    @pytest.mark.unit
    @patch("requests.get")
    def test_fetch_page_timeout(self, mock_get, scraper):
        """Test handling of request timeout."""
        mock_get.side_effect = Timeout("Request timed out")

        with pytest.raises(Timeout):
            scraper.fetch_page("https://uscg.gov/incidents")

    @pytest.mark.unit
    @patch("requests.get")
    def test_fetch_page_connection_error(self, mock_get, scraper):
        """Test handling of connection errors."""
        mock_get.side_effect = ConnectionError("Connection failed")

        with pytest.raises(ConnectionError):
            scraper.fetch_page("https://uscg.gov/incidents")

    @pytest.mark.unit
    @patch("requests.get")
    def test_retry_on_failure(self, mock_get, scraper):
        """Test retry logic on failed requests."""
        # Fail twice, then succeed
        mock_get.side_effect = [
            ConnectionError("Failed"),
            ConnectionError("Failed again"),
            mock_response,
        ]

        response = scraper.fetch_page("https://uscg.gov/incidents")

        assert response.status_code == 200
        assert mock_get.call_count == 3

    @pytest.mark.unit
    @patch("requests.get")
    def test_max_retries_exceeded(self, mock_get, scraper):
        """Test that max retries limit is respected."""
        mock_get.side_effect = ConnectionError("Connection failed")

        with pytest.raises(ConnectionError):
            scraper.fetch_page("https://uscg.gov/incidents")

        # Should try max_retries + 1 times (initial + retries)
        assert mock_get.call_count == scraper.max_retries + 1

    @pytest.mark.unit
    def test_parse_html(self, scraper, sample_html):
        """Test HTML parsing extracts correct data."""
        incidents = scraper.parse_incident_html(sample_html)

        assert len(incidents) == 2
        assert incidents[0]["date"] == "2024-01-15"
        assert incidents[0]["type"] == "Collision"
        assert incidents[0]["vessel"] == "Test Vessel"
        assert incidents[1]["severity"] == "Minor"

    @pytest.mark.unit
    def test_parse_empty_html(self, scraper):
        """Test parsing empty HTML returns empty list."""
        html = "<html><body></body></html>"
        incidents = scraper.parse_incident_html(html)

        assert incidents == []

    @pytest.mark.unit
    def test_parse_malformed_html(self, scraper):
        """Test handling of malformed HTML."""
        html = "<html><body><table><tr><td>Incomplete"
        incidents = scraper.parse_incident_html(html)

        # Should handle gracefully without crashing
        assert isinstance(incidents, list)

    @pytest.mark.integration
    @patch("requests.get")
    def test_scrape_incidents_date_range(self, mock_get, scraper, sample_html):
        """Test scraping incidents within a date range."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_html
        mock_get.return_value = mock_response

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        incidents = scraper.scrape_incidents(start_date, end_date)

        assert len(incidents) > 0
        mock_get.assert_called()


class TestPDFExtraction:
    """Test suite for PDF extraction functionality."""

    @pytest.mark.unit
    @patch("requests.get")
    def test_download_pdf_success(self, mock_get, scraper):
        """Test successful PDF download."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"PDF content here"
        mock_response.headers = {"Content-Type": "application/pdf"}
        mock_get.return_value = mock_response

        pdf_content = scraper.download_pdf("https://uscg.gov/report.pdf")

        assert pdf_content == b"PDF content here"

    @pytest.mark.unit
    @patch("requests.get")
    def test_download_pdf_not_found(self, mock_get, scraper):
        """Test handling of 404 errors for PDFs."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with pytest.raises(Exception):
            scraper.download_pdf("https://uscg.gov/missing.pdf")

    @pytest.mark.unit
    @patch("PyPDF2.PdfReader")
    def test_extract_pdf_text(self, mock_pdf_reader, scraper):
        """Test PDF text extraction."""
        mock_page = Mock()
        mock_page.extract_text.return_value = "Incident report text"

        mock_reader = Mock()
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader

        text = scraper.extract_pdf_text(b"PDF content")

        assert "Incident report text" in text

    @pytest.mark.unit
    def test_parse_pdf_metadata(self, scraper):
        """Test extraction of metadata from PDF text."""
        pdf_text = """
    Incident Date: 2024-01-15
    Vessel: Test Ship
    Location: Gulf of Mexico
    Type: Collision
    Casualties: 2
    """

        metadata = scraper.parse_pdf_metadata(pdf_text)

        assert metadata["incident_date"] == "2024-01-15"
        assert metadata["vessel"] == "Test Ship"
        assert metadata["type"] == "Collision"
        assert metadata["casualties"] == 2


class TestRateLimiter:
    """Test suite for rate limiting functionality."""

    @pytest.mark.unit
    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly."""
        limiter = RateLimiter(delay=1.0, max_requests=10)

        assert limiter.delay == 1.0
        assert limiter.max_requests == 10

    @pytest.mark.unit
    def test_rate_limiter_enforces_delay(self):
        """Test that rate limiter enforces minimum delay."""
        limiter = RateLimiter(delay=0.1)

        start = datetime.now()
        limiter.wait()
        limiter.wait()
        elapsed = (datetime.now() - start).total_seconds()

        assert elapsed >= 0.1

    @pytest.mark.unit
    def test_rate_limiter_tracks_requests(self):
        """Test that rate limiter tracks request count."""
        limiter = RateLimiter(delay=0.01, max_requests=5)

        for _ in range(5):
            limiter.wait()

        assert limiter.request_count == 5

    @pytest.mark.unit
    def test_rate_limiter_resets_window(self):
        """Test that rate limiter resets after time window."""
        limiter = RateLimiter(delay=0.01, max_requests=3, window=0.1)

        for _ in range(3):
            limiter.wait()

        # Wait for window to expire
        import time

        time.sleep(0.15)

        limiter.wait()
        assert limiter.request_count == 1


class TestRetryStrategy:
    """Test suite for retry strategy implementation."""

    @pytest.mark.unit
    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        strategy = RetryStrategy(max_retries=3, backoff_factor=2.0, initial_delay=1.0)

        delays = [strategy.get_delay(i) for i in range(3)]

        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 4.0

    @pytest.mark.unit
    def test_max_delay_cap(self):
        """Test that delay is capped at maximum."""
        strategy = RetryStrategy(
            max_retries=5, backoff_factor=2.0, initial_delay=1.0, max_delay=5.0
        )

        delay = strategy.get_delay(10)

        assert delay <= 5.0

    @pytest.mark.unit
    def test_should_retry_logic(self):
        """Test retry decision logic."""
        strategy = RetryStrategy(max_retries=3)

        assert strategy.should_retry(0) is True
        assert strategy.should_retry(2) is True
        assert strategy.should_retry(3) is False
        assert strategy.should_retry(5) is False


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    @pytest.mark.unit
    @patch("requests.get")
    def test_http_500_error(self, mock_get, scraper):
        """Test handling of HTTP 500 errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = RequestException("Server error")
        mock_get.return_value = mock_response

        with pytest.raises(RequestException):
            scraper.fetch_page("https://uscg.gov/incidents")

    @pytest.mark.unit
    @patch("requests.get")
    def test_invalid_ssl_certificate(self, mock_get, scraper):
        """Test handling of SSL certificate errors."""
        mock_get.side_effect = requests.exceptions.SSLError("SSL error")

        with pytest.raises(requests.exceptions.SSLError):
            scraper.fetch_page("https://uscg.gov/incidents")

    @pytest.mark.unit
    def test_invalid_url_format(self, scraper):
        """Test handling of invalid URL formats."""
        with pytest.raises(Exception):
            scraper.fetch_page("not-a-valid-url")

    @pytest.mark.unit
    @patch("requests.get")
    def test_network_timeout_recovery(self, mock_get, scraper, mock_response):
        """Test recovery from network timeouts."""
        # Timeout once, then succeed
        mock_get.side_effect = [Timeout("Timeout"), mock_response]

        response = scraper.fetch_page("https://uscg.gov/incidents")

        assert response.status_code == 200
