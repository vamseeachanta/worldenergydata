"""Current Copernicus SDK adapters and credential-free catalogue smoke checks.

CDSAPI setup (accessed 2026-10-19):
https://cds.climate.copernicus.eu/en/how-to-api
Marine migration and subset API (accessed 2026-10-19):
https://help.marine.copernicus.eu/en/articles/8612591
https://help.marine.copernicus.eu/en/articles/8283072
Downloads require the publisher's credentials and accepted dataset terms.
SDK imports are deferred until a download adapter is constructed.
"""

import os
from collections.abc import Mapping
from importlib import import_module
from typing import Any

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


class CredentialsRequired(RuntimeError):
    """An account source lacks required environment configuration."""


def _environment(source: str, *names: str) -> list[str]:
    values = [os.environ.get(name, "") for name in names]
    if not all(value.strip() for value in values):
        raise CredentialsRequired(f"{source}: credentials required from environment")
    return values


class _SDKErrorBoundary:
    """Sanitize third-party exception classes/text at the credential boundary.

    The scope is intentionally limited to SDK initialization and requests.
    Cancellation and process-exit exceptions propagate unchanged.
    """

    def __init__(self, source: str, action: str) -> None:
        self.source, self.action = source, action

    def __enter__(self):
        return self

    def __exit__(self, kind, error, traceback):
        if kind is not None and issubclass(kind, Exception):
            raise EndpointError(
                f"{self.source}: {self.action} failed; details suppressed"
            ) from None
        return False


class ERA5Client:
    """Current CDS API; credentials come only from CDSAPI_KEY.

    Supplying an explicit URL and key prevents cdsapi's configuration-file
    fallback. CDS setup documents the current URL and dataset licence consent.
    """

    def __init__(self) -> None:
        (key,) = _environment("era5", "CDSAPI_KEY")
        sdk = _sdk("cdsapi")
        with _SDKErrorBoundary("era5", "SDK initialization"):
            self._client = sdk.Client(url=CDS_API_URL, key=key, quiet=True, debug=False)

    def retrieve(self, dataset: str, request: Mapping[str, Any], target: str) -> Any:
        """Forward the publisher request; SDK error details may hold credentials."""
        with _SDKErrorBoundary("era5", "retrieval"):
            return self._client.retrieve(dataset, dict(request), target)


class CMEMSClient:
    """Marine Toolbox; credentials come only from the documented environment.

    Both values are supplied explicitly, preventing stored-credential fallback.
    Credentials cannot be overridden in selection arguments.
    """

    def __init__(self) -> None:
        self._username, self._password = _environment(
            "cmems",
            "COPERNICUSMARINE_SERVICE_USERNAME",
            "COPERNICUSMARINE_SERVICE_PASSWORD",
        )
        self._toolbox = _sdk("copernicusmarine")

    def subset(self, dataset_id: str, **selection: Any) -> Any:
        """Forward selections with environment credentials and sanitized errors."""
        if {"username", "password", "credentials_file"}.intersection(selection):
            raise ValueError("Credentials must come only from environment")
        with _SDKErrorBoundary("cmems", "subset"):
            return self._toolbox.subset(
                dataset_id=dataset_id,
                username=self._username,
                password=self._password,
                **selection,
            )
