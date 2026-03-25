"""Tests for EITI Data Explorer API client."""

import pytest
from unittest.mock import MagicMock, patch

from worldenergydata.west_africa.eiti.eiti_api import (
    EitiApiClient,
    EitiApiError,
    EITI_BASE_URL,
)


class TestEitiApiClientInit:
    def test_default_base_url(self):
        client = EitiApiClient()
        assert "eiti.org" in client.base_url or EITI_BASE_URL in client.base_url

    def test_custom_timeout(self):
        client = EitiApiClient(timeout=45)
        assert client.timeout == 45

    def test_cache_enabled_by_default(self):
        client = EitiApiClient()
        assert client.cache_enabled is True

    def test_supported_countries_list(self):
        client = EitiApiClient()
        assert isinstance(client.supported_countries, list)
        assert len(client.supported_countries) > 0

    def test_nigeria_in_supported_countries(self):
        client = EitiApiClient()
        assert "Nigeria" in client.supported_countries or "NG" in client.supported_countries


class TestEitiApiClientGet:
    @patch("worldenergydata.west_africa.eiti.eiti_api.requests")
    def test_get_countries_returns_list(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": 1, "name": "Nigeria", "iso2": "NG"},
            {"id": 2, "name": "Angola", "iso2": "AO"},
        ]
        mock_requests.get.return_value = mock_resp

        client = EitiApiClient(cache_enabled=False)
        result = client.get_countries()
        assert isinstance(result, list)

    @patch("worldenergydata.west_africa.eiti.eiti_api.requests")
    def test_get_raises_on_server_error(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_requests.get.return_value = mock_resp

        client = EitiApiClient(cache_enabled=False)
        with pytest.raises(EitiApiError):
            client.get_countries()

    @patch("worldenergydata.west_africa.eiti.eiti_api.requests")
    def test_get_raises_on_network_error(self, mock_requests):
        mock_requests.get.side_effect = Exception("connection refused")
        mock_requests.exceptions.RequestException = Exception

        client = EitiApiClient(cache_enabled=False)
        with pytest.raises(EitiApiError):
            client.get_countries()

    @patch("worldenergydata.west_africa.eiti.eiti_api.requests")
    def test_get_production_data_with_filters(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "country": "Nigeria",
                    "year": 2022,
                    "company": "NNPC",
                    "volume_bbl": 500_000_000,
                }
            ]
        }
        mock_requests.get.return_value = mock_resp

        client = EitiApiClient(cache_enabled=False)
        result = client.get_production_data(country="Nigeria", year=2022)
        assert isinstance(result, list)

    @patch("worldenergydata.west_africa.eiti.eiti_api.requests")
    def test_caching_prevents_duplicate_requests(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_requests.get.return_value = mock_resp

        client = EitiApiClient(cache_enabled=True)
        client.get_countries()
        client.get_countries()
        assert mock_requests.get.call_count == 1

    @patch("worldenergydata.west_africa.eiti.eiti_api.requests")
    def test_get_payment_data_returns_list(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "country": "Nigeria",
                    "year": 2022,
                    "company": "Shell Nigeria",
                    "payment_type": "royalty",
                    "amount_usd": 1_200_000_000,
                }
            ]
        }
        mock_requests.get.return_value = mock_resp

        client = EitiApiClient(cache_enabled=False)
        result = client.get_payment_data(country="Nigeria", year=2022)
        assert isinstance(result, list)
