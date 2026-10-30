"""Copernicus API contracts; expectations are independent publisher examples.

Sources (accessed 2026-10-19): CDSAPI setup, sections 1 and 3,
https://cds.climate.copernicus.eu/en/how-to-api ; Marine Toolbox API Subset,
https://help.marine.copernicus.eu/en/articles/8283072 .
HTTP outcomes follow RFC 9110 (2022), sections 15.3, 15.5 and 15.6.
No numerical oceanographic calculation or downloaded observations are used.
"""

import sys
from types import SimpleNamespace

import httpx
import pytest

from worldenergydata.metocean.clients import copernicus_clients as clients
from worldenergydata.metocean.constants import CMEMS_BASE_URL


@pytest.fixture(autouse=True)
def synthetic_credentials(monkeypatch):
    for name in (
        "CDSAPI_KEY",
        "COPERNICUSMARINE_SERVICE_USERNAME",
        "COPERNICUSMARINE_SERVICE_PASSWORD",
    ):
        monkeypatch.setenv(name, "synthetic-placeholder")


@pytest.mark.parametrize("source", ["era5", "cmems"])
def test_catalogue_probe(source):
    def respond(request):
        assert request.url == clients.CATALOGUE_URLS[source]
        payload = (
            {"id": "reanalysis-era5-single-levels"}
            if source == "era5"
            else {"id": "MDS", "type": "Catalog", "links": []}
        )
        return httpx.Response(200, json=payload)

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        assert clients.probe_catalogue(source, http=http)["id"]


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (404, "retired or moved"),
        (410, "retired or moved"),
        (401, "authentication"),
        (403, "authentication"),
        (429, "rate limited"),
        (503, "service error"),
    ],
)
def test_probe_http_failure_classification(status, message):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, text="do not echo response")
        )
    ) as http:
        with pytest.raises(clients.EndpointError, match=message) as error:
            clients.probe_catalogue("era5", http=http)
    assert "do not echo" not in str(error.value)


@pytest.mark.parametrize("payload", [[], {}, {"id": "wrong"}, "login page"])
def test_probe_rejects_unexpected_payload(payload):
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as http:
        with pytest.raises(clients.EndpointError, match="schema"):
            clients.probe_catalogue("era5", http=http)


def test_probe_rejects_html():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text="<html>login</html>")
        )
    ) as http:
        with pytest.raises(clients.EndpointError, match="JSON"):
            clients.probe_catalogue("cmems", http=http)


def test_probe_transport_failure_is_not_retirement():
    def fail(request):
        raise httpx.ConnectError("sensitive transport detail", request=request)

    with httpx.Client(transport=httpx.MockTransport(fail)) as http:
        with pytest.raises(clients.EndpointError, match="transport") as error:
            clients.probe_catalogue("era5", http=http)
    assert error.value.__suppress_context__
    assert "sensitive" not in str(error.value)


def test_probe_rejects_unknown_source():
    with pytest.raises(ValueError, match="source"):
        clients.probe_catalogue("unknown", http=None)


def test_cmems_metadata_url_is_not_motu():
    assert CMEMS_BASE_URL == clients.CATALOGUE_URLS["cmems"]


def test_era5_retrieve_uses_current_api(monkeypatch):
    """CDS published example: identical dataset, selection and output filename."""
    calls = []

    class CDS:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def retrieve(self, dataset, request, target):
            calls.append((dataset, request, target))
            return target

    monkeypatch.setitem(sys.modules, "cdsapi", SimpleNamespace(Client=CDS))
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
    result = clients.ERA5Client().retrieve(
        "reanalysis-era5-pressure-levels", request, "download.grib"
    )
    assert result == "download.grib"
    assert calls == [
        {
            "url": "https://cds.climate.copernicus.eu/api",
            "key": "synthetic-placeholder",
            "quiet": True,
            "debug": False,
        },
        ("reanalysis-era5-pressure-levels", request, "download.grib"),
    ]


def test_marine_subset_uses_toolbox(monkeypatch):
    """Publisher subset example is forwarded without a MOTU service identifier."""
    calls = []

    def subset(**kwargs):
        calls.append(kwargs)
        return "subset.nc"

    monkeypatch.setitem(sys.modules, "copernicusmarine", SimpleNamespace(subset=subset))
    selection = {
        "variables": ["uo", "vo"],
        "minimum_longitude": 50,
        "maximum_longitude": 90,
        "minimum_latitude": 0,
        "maximum_latitude": 25,
        "start_datetime": "2020-01-01",
        "end_datetime": "2020-01-31",
        "minimum_depth": 0,
        "maximum_depth": 30,
    }
    assert (
        clients.CMEMSClient().subset("cmems_mod_glo_phy_my_0.083deg_P1D-m", **selection)
        == "subset.nc"
    )
    assert calls == [
        {
            "dataset_id": "cmems_mod_glo_phy_my_0.083deg_P1D-m",
            "username": "synthetic-placeholder",
            "password": "synthetic-placeholder",
            **selection,
        }
    ]


@pytest.mark.parametrize(
    ("module", "client"),
    [("cdsapi", "ERA5Client"), ("copernicusmarine", "CMEMSClient")],
)
def test_optional_dependency_error(monkeypatch, module, client):
    monkeypatch.setitem(sys.modules, module, None)
    with pytest.raises(ImportError, match=module):
        getattr(clients, client)()


@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_probe_does_not_follow_redirects(status):
    """RFC 9110 (2022), section 15.4: redirects are not catalogue success."""
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                status, headers={"Location": "https://example.org"}
            )
        ),
        follow_redirects=True,
    ) as http:
        with pytest.raises(clients.EndpointError, match="unexpected HTTP"):
            clients.probe_catalogue("era5", http=http)


@pytest.mark.parametrize(
    "payload",
    [
        {"id": "MDS", "type": "Collection", "links": []},
        {"id": "MDS", "type": "Catalog", "links": {}},
    ],
)
def test_marine_schema_rejected(payload):
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as http:
        with pytest.raises(clients.EndpointError, match="schema"):
            clients.probe_catalogue("cmems", http=http)
