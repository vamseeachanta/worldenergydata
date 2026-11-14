"""Current Copernicus SDK adapters and credential-free catalogue smoke checks.

CDSAPI setup (accessed 2026-10-19):
https://cds.climate.copernicus.eu/en/how-to-api
Marine migration and subset API (accessed 2026-10-19):
https://help.marine.copernicus.eu/en/articles/8612591
https://help.marine.copernicus.eu/en/articles/8283072
Downloads require the publisher's credentials and accepted dataset terms.
SDK imports are deferred until a download adapter is constructed.
"""

from importlib import import_module
from typing import Any, Mapping

import httpx

from worldenergydata.metocean.constants import CMEMS_BASE_URL

# CDSAPI setup, section 1: use /api, without the legacy /v2 suffix.
CDS_API_URL = "https://cds.climate.copernicus.eu/api"
CATALOGUE_URLS = {
    "era5": f"{CDS_API_URL}/catalogue/v1/collections/reanalysis-era5-single-levels",
    "cmems": CMEMS_BASE_URL,
}


class EndpointError(RuntimeError):
    """A smoke check failed; messages omit response bodies and credentials."""


def probe_catalogue(source: str, *, http: httpx.Client) -> dict[str, Any]:
    """Read public metadata; the caller supplies an HTTP client and timeout.

    Success establishes catalogue availability only, never download readiness.
    No automatic retries, credential loading or dataset downloads are performed.
    """
    if source not in CATALOGUE_URLS:
        raise ValueError("source must be era5 or cmems")
    try:
        response = http.get(CATALOGUE_URLS[source], follow_redirects=False)
    except httpx.RequestError:
        raise EndpointError(
            f"{source}: transport failure; retirement not established"
        ) from None

    # RFC 9110 (2022), sections 15.3, 15.5.2-.5, 15.5.11 and 15.6;
    # rate limiting: RFC 6585 (2012), section 4. These are HTTP protocol codes.
    status = response.status_code
    if status in {404, 410}:
        reason = "endpoint retired or moved; check publisher migration guidance"
    elif status in {401, 403}:
        reason = "authentication/access rejected; retirement not established"
    elif status == 429:
        reason = "rate limited; retry later"
    elif response.is_server_error:
        reason = "service error; retry later"
    elif not response.is_success:
        reason = "unexpected HTTP response; check publisher migration guidance"
    else:
        return _catalogue_payload(source, response)
    raise EndpointError(f"{source}: HTTP {status}: {reason}")


def _catalogue_payload(source: str, response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        raise EndpointError(f"{source}: expected catalogue JSON") from None
    # Expected identities come from the public catalogue documents linked below:
    # https://cds.climate.copernicus.eu/api/catalogue/v1/collections/reanalysis-era5-single-levels
    # https://stac.marine.copernicus.eu/metadata/catalog.stac.json
    expected_id = "reanalysis-era5-single-levels" if source == "era5" else "MDS"
    valid = isinstance(payload, dict) and payload.get("id") == expected_id
    if source == "cmems" and valid:
        valid = payload.get("type") == "Catalog" and isinstance(
            payload.get("links"), list
        )
    if not valid:
        raise EndpointError(f"{source}: unexpected catalogue schema or identity")
    return payload


def _sdk(module: str) -> Any:
    try:
        return import_module(module)
    except ImportError:
        raise ImportError(
            f"Install the optional {module} SDK to use this adapter"
        ) from None


class ERA5Client:
    """CDS adapter using current API configuration and SDK-managed credentials."""

    def __init__(self) -> None:
        self._client = _sdk("cdsapi").Client(url=CDS_API_URL)

    def retrieve(self, dataset: str, request: Mapping[str, Any], target: str) -> Any:
        """Pass the dataset download form's current request to CDS unchanged."""
        return self._client.retrieve(dataset, dict(request), target)


class CMEMSClient:
    """Marine Toolbox adapter; dataset IDs replace retired MOTU service IDs."""

    def __init__(self) -> None:
        self._toolbox = _sdk("copernicusmarine")

    def subset(self, dataset_id: str, **selection: Any) -> Any:
        """Forward documented Toolbox selections; credentials stay SDK-managed."""
        return self._toolbox.subset(dataset_id=dataset_id, **selection)
