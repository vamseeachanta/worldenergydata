"""Copernicus contracts, independent of optional SDKs and live services.

HTTP expected outcomes: RFC 9110 (2022), sections 15.3-15.6, and
RFC 6585 (2012), section 4. Status numbers are protocol identifiers.
Catalogue fixtures are synthetic subsets of publisher documents:
https://cds.climate.copernicus.eu/api/catalogue/v1/collections/reanalysis-era5-single-levels
https://stac.marine.copernicus.eu/metadata/catalog.stac.json
SDK call shape: https://cds.climate.copernicus.eu/en/how-to-api and
https://help.marine.copernicus.eu/en/articles/8283072-copernicus-marine-toolbox-api-subset
No physical coefficients or engineering acceptance limits are used.
"""

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from worldenergydata.metocean.clients.copernicus_clients import (
    CopernicusMarineClient,
    EndpointError,
    Era5Client,
    check_endpoint,
)
from worldenergydata.metocean.constants import CMEMS_BASE_URL, DATA_SOURCE_URLS


def catalogue(source):
    """Expected identity is independently transcribed from publisher JSON."""
    return {
        "id": "reanalysis-era5-single-levels" if source == "era5" else "MDS",
        "type": "Collection" if source == "era5" else "Catalog",
        "stac_version": "1.1.0" if source == "era5" else "1.0.0",
        "links": [{"rel": "self", "href": "https://example.org/catalogue"}],
    }


def transport(status, payload=None, content=None, headers=None):
    def respond(request):
        assert "authorization" not in request.headers
        assert "cookie" not in request.headers
        assert not request.url.query
        return httpx.Response(status, json=payload, content=content, headers=headers)

    return httpx.MockTransport(respond)


@pytest.mark.parametrize("source", ["era5", "cmems"])
def test_current_catalogue(source):
    result = check_endpoint(
        source, timeout=1, transport=transport(200, catalogue(source))
    )
    assert result == catalogue(source)["id"]


@pytest.mark.parametrize(
    "status,category",
    [
        (301, "moved"),
        (302, "moved"),
        (303, "moved"),
        (304, "http"),
        (307, "moved"),
        (308, "moved"),
        (401, "authentication"),
        (403, "authentication"),
        (404, "unavailable_or_retired"),
        (410, "unavailable_or_retired"),
        (429, "rate_limited"),
        (500, "service"),
        (503, "service"),
        (400, "http"),
        (204, "http"),
    ],
)
def test_http_failures_are_safe_and_actionable(status, category):
    with pytest.raises(EndpointError) as error:
        check_endpoint(
            "era5",
            timeout=1,
            transport=transport(
                status,
                content=b"private response text",
                headers={"Location": "https://example.org/private-redirect"},
            ),
        )
    assert error.value.category == category
    assert str(status) in str(error.value)
    assert "private" not in str(error.value)
    assert error.value.__suppress_context__


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"id": "MDS"},
        {**catalogue("cmems"), "id": "wrong"},
        {**catalogue("cmems"), "type": "Collection"},
        {**catalogue("cmems"), "links": []},
        {**catalogue("cmems"), "links": [None]},
        {**catalogue("cmems"), "links": [{}]},
        {**catalogue("cmems"), "stac_version": None},
    ],
)
def test_schema_failure(payload):
    with pytest.raises(EndpointError, match="schema"):
        check_endpoint("cmems", timeout=1, transport=transport(200, payload))


def test_non_json_failure():
    with pytest.raises(EndpointError, match="schema"):
        check_endpoint("era5", timeout=1, transport=transport(200, content=b"<html>"))


def test_disabled_collection():
    payload = {**catalogue("era5"), "cads:disabled_reason": "temporarily unavailable"}
    with pytest.raises(EndpointError, match="disabled"):
        check_endpoint("era5", timeout=1, transport=transport(200, payload))


@pytest.mark.parametrize("exception", [httpx.ConnectError, httpx.ReadTimeout])
def test_transport_error_does_not_disclose_exception(exception):
    def fail(request):
        raise exception("private transport details", request=request)

    with pytest.raises(EndpointError, match="transport") as error:
        check_endpoint("era5", timeout=1, transport=httpx.MockTransport(fail))
    assert "private" not in str(error.value)
    assert error.value.__suppress_context__


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_timeout_is_required_positive_finite_input(timeout):
    with pytest.raises(ValueError, match="timeout"):
        check_endpoint("era5", timeout=timeout)


def test_unknown_source_never_requests():
    with pytest.raises(ValueError, match="source"):
        check_endpoint("unknown", timeout=1)


def test_removed_motu_reference_is_metadata_only():
    assert (
        CMEMS_BASE_URL == "https://stac.marine.copernicus.eu/metadata/catalog.stac.json"
    )
    assert DATA_SOURCE_URLS["CMEMS"] == CMEMS_BASE_URL


def test_cds_request_forwarding(monkeypatch, tmp_path):
    """CDS published example: the selected geopotential request passes unchanged.

    Expected arguments are a literal transcription of the publisher example,
    not a request calculated by the implementation. The fake SDK returns the
    sentinel 'downloaded'; no downloaded data or physics is being asserted.
    """
    sdk = Mock()
    factory = Mock(return_value=sdk)
    monkeypatch.setitem(sys.modules, "cdsapi", SimpleNamespace(Client=factory))
    request = {
        "product_type": ["reanalysis"],
        "variable": ["geopotential"],
        "year": ["2024"],
        "month": ["03"],
        "day": ["01"],
        "time": ["13:00"],
        "pressure_level": ["1000"],
        "data_format": "grib",
    }
    target = tmp_path / "download.grib"
    sdk.retrieve.return_value = "downloaded"
    assert (
        Era5Client().retrieve("reanalysis-era5-pressure-levels", request, target)
        == "downloaded"
    )
    factory.assert_called_once_with(url="https://cds.climate.copernicus.eu/api")
    sdk.retrieve.assert_called_once_with(
        "reanalysis-era5-pressure-levels", request, str(target)
    )


def test_marine_request_forwarding(monkeypatch, tmp_path):
    """Publisher subset example supplies every numeric coordinate/date/depth.

    Independent expected answer is identical keyword forwarding and the fake
    SDK's sentinel return, not a simulated ocean current or data download.
    """
    subset = Mock(return_value="subset-result")
    monkeypatch.setitem(sys.modules, "copernicusmarine", SimpleNamespace(subset=subset))
    request = {
        "dataset_id": "cmems_mod_glo_phy_my_0.083deg_P1D-m",
        "variables": ["uo", "vo"],
        "minimum_longitude": 50,
        "maximum_longitude": 90,
        "minimum_latitude": 0,
        "maximum_latitude": 25,
        "start_datetime": "2020-01-01",
        "end_datetime": "2020-01-31",
        "minimum_depth": 0,
        "maximum_depth": 30,
        "output_directory": str(tmp_path),
        "output_filename": "currents.nc",
    }
    assert CopernicusMarineClient().subset(**request) == "subset-result"
    subset.assert_called_once_with(**request)


@pytest.mark.parametrize(
    "module,client",
    [("cdsapi", Era5Client), ("copernicusmarine", CopernicusMarineClient)],
)
def test_optional_dependency_message(monkeypatch, module, client):
    monkeypatch.setitem(sys.modules, module, None)
    with pytest.raises(ImportError, match=module):
        client()
