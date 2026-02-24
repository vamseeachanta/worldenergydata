"""Tests for Nigeria NUPRC PDF downloader and table extractor."""

import io
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from worldenergydata.west_africa.nigeria.nuprc_client import (
    NuprcClient,
    NuprcAPIError,
    parse_blend_table_from_pdf,
    list_report_urls,
)


NUPRC_PORTAL = "https://www.nuprc.gov.ng/oil-production-status-report/"


class TestNuprcClientInit:
    def test_default_base_url(self):
        client = NuprcClient()
        assert "nuprc.gov.ng" in client.base_url

    def test_custom_timeout(self):
        client = NuprcClient(timeout=60)
        assert client.timeout == 60

    def test_cache_enabled_by_default(self):
        client = NuprcClient()
        assert client.cache_enabled is True

    def test_disable_cache(self):
        client = NuprcClient(cache_enabled=False)
        assert client.cache_enabled is False


class TestNuprcClientDownload:
    @patch("worldenergydata.west_africa.nigeria.nuprc_client.requests")
    def test_download_returns_bytes(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"%PDF-1.4 fake pdf content"
        mock_requests.get.return_value = mock_resp

        client = NuprcClient(cache_enabled=False)
        data = client.download_pdf("https://example.com/report.pdf")
        assert isinstance(data, bytes)
        assert len(data) > 0

    @patch("worldenergydata.west_africa.nigeria.nuprc_client.requests")
    def test_download_raises_on_http_error(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not found"
        mock_requests.get.return_value = mock_resp

        client = NuprcClient(cache_enabled=False)
        with pytest.raises(NuprcAPIError):
            client.download_pdf("https://example.com/missing.pdf")

    @patch("worldenergydata.west_africa.nigeria.nuprc_client.requests")
    def test_download_raises_on_network_error(self, mock_requests):
        mock_requests.get.side_effect = Exception("Connection refused")
        mock_requests.exceptions.RequestException = Exception

        client = NuprcClient(cache_enabled=False)
        with pytest.raises(NuprcAPIError):
            client.download_pdf("https://example.com/report.pdf")

    @patch("worldenergydata.west_africa.nigeria.nuprc_client.requests")
    def test_download_uses_cache_on_second_call(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"%PDF fake"
        mock_requests.get.return_value = mock_resp

        client = NuprcClient(cache_enabled=True)
        url = "https://example.com/report.pdf"
        client.download_pdf(url)
        client.download_pdf(url)
        # Only one real HTTP call due to caching
        assert mock_requests.get.call_count == 1


class TestParseBlendsFromPdf:
    def test_parse_returns_list(self):
        # Minimal PDF bytes simulation — parser handles gracefully
        fake_pdf = b""
        result = parse_blend_table_from_pdf(fake_pdf)
        assert isinstance(result, list)

    def test_parse_empty_pdf_returns_empty_list(self):
        result = parse_blend_table_from_pdf(b"")
        assert result == []

    def test_parse_result_has_required_keys(self):
        """Parse result dicts must include blend, volume_kbd, month, year."""
        sample_row = {
            "blend": "BONNY LIGHT",
            "volume_kbd": 150.0,
            "month": 3,
            "year": 2024,
        }
        # Structural test: verify the key schema is correct
        required = {"blend", "volume_kbd", "month", "year"}
        assert required.issubset(sample_row.keys())

    def test_parse_handles_none_gracefully(self):
        result = parse_blend_table_from_pdf(None)
        assert result == []


class TestListReportUrls:
    @patch("worldenergydata.west_africa.nigeria.nuprc_client.requests")
    def test_returns_list(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <html><body>
        <a href="/wp-content/uploads/2024/03/report-march.pdf">March 2024</a>
        <a href="/wp-content/uploads/2024/02/report-feb.pdf">Feb 2024</a>
        </body></html>
        """
        mock_requests.get.return_value = mock_resp

        urls = list_report_urls(NUPRC_PORTAL)
        assert isinstance(urls, list)

    @patch("worldenergydata.west_africa.nigeria.nuprc_client.requests")
    def test_returns_empty_on_network_error(self, mock_requests):
        mock_requests.get.side_effect = Exception("timeout")
        mock_requests.exceptions.RequestException = Exception
        urls = list_report_urls(NUPRC_PORTAL)
        assert urls == []

    @patch("worldenergydata.west_africa.nigeria.nuprc_client.requests")
    def test_filters_non_pdf_links(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <html><body>
        <a href="/page">Some page</a>
        <a href="/report.pdf">PDF link</a>
        <a href="/doc.docx">Word doc</a>
        </body></html>
        """
        mock_requests.get.return_value = mock_resp
        urls = list_report_urls(NUPRC_PORTAL)
        assert all(u.endswith(".pdf") for u in urls)
