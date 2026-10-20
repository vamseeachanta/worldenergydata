"""Current Copernicus SDK adapters and credential-free catalogue diagnostics.

CDS setup and request contract: https://cds.climate.copernicus.eu/en/how-to-api
Marine migration and subset contract:
https://help.marine.copernicus.eu/en/articles/8612591-switching-from-old-to-new-services
https://help.marine.copernicus.eu/en/articles/8283072-copernicus-marine-toolbox-api-subset
Catalogue success establishes metadata availability only, not download access.
"""

import math
from collections.abc import Mapping
from importlib import import_module
from os import PathLike
from typing import Any

import httpx

from worldenergydata.metocean.constants import CMEMS_CATALOGUE_URL

# Current URLs and identities are published in the CDS setup page and these
# publisher JSON catalogues (accessed 2026-10-19); versions are not pinned.
CDS_API_URL = "https://cds.climate.copernicus.eu/api"
CDS_CATALOGUE_URL = (
    "https://cds.climate.copernicus.eu/api/catalogue/v1/collections/"
    "reanalysis-era5-single-levels"
)
_CATALOGUES = {
    "era5": (CDS_CATALOGUE_URL, "reanalysis-era5-single-levels", "Collection"),
    "cmems": (CMEMS_CATALOGUE_URL, "MDS", "Catalog"),
}


class EndpointError(RuntimeError):
    """Safe, classified diagnostic that omits response and exception contents."""

    def __init__(self, source: str, category: str, status: int | None = None):
        self.category = category
        self.status = status
        detail = f" (HTTP {status})" if status is not None else ""
        super().__init__(
            f"{source} catalogue: {category}{detail}; check the publisher service "
            "and migration documentation. Download access is NOT_EVALUATED."
        )


def check_endpoint(
    source: str, *, timeout: float, transport: httpx.BaseTransport | None = None
) -> str:
    """Return a validated catalogue identity, or fail with a classified error.

    Only fixed public catalogue URLs are requested. Redirects are diagnostic
    failures and are never followed. No environment proxy, authentication,
    cookies or SDK configuration is loaded. Timeout is an operator input,
    not an engineering acceptance limit. Transport injection supports offline
    tests. A missing endpoint is not conclusive proof of service retirement.
    """
    if source not in _CATALOGUES:
        raise ValueError("source must be 'era5' or 'cmems'")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be positive and finite")
    url, identity, kind = _CATALOGUES[source]
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        ) as client:
            response = client.get(url)
    except httpx.RequestError:
        raise EndpointError(source, "transport") from None

    # HTTP semantics: RFC 9110 (2022), sections 15.3-15.6; rate limiting:
    # RFC 6585 (2012), section 4. These numbers are protocol identifiers.
    status = response.status_code
    if status != 200:
        if status in (301, 302, 303, 307, 308):
            category = "moved"
        elif status in (401, 403):
            category = "authentication"
        elif status in (404, 410):
            category = "unavailable_or_retired"
        elif status == 429:
            category = "rate_limited"
        elif 500 <= status < 600:
            category = "service"
        else:
            category = "http"
        raise EndpointError(source, category, status) from None
    try:
        payload = response.json()
    except ValueError:
        raise EndpointError(source, "schema", status) from None
    if (
        not isinstance(payload, dict)
        or payload.get("id") != identity
        or payload.get("type") != kind
        or not isinstance(payload.get("stac_version"), str)
        or not payload["stac_version"]
        or not isinstance(payload.get("links"), list)
        or not payload["links"]
        or any(
            not isinstance(link, dict)
            or not isinstance(link.get("rel"), str)
            or not link["rel"]
            or not isinstance(link.get("href"), str)
            or not link["href"]
            for link in payload["links"]
        )
    ):
        raise EndpointError(source, "schema", status) from None
    if payload.get("cads:disabled_reason"):
        raise EndpointError(source, "disabled", status) from None
    return identity


def _sdk(name: str) -> Any:
    try:
        return import_module(name)
    except ImportError:
        raise ImportError(
            f"Optional dependency '{name}' is required; install the publisher SDK."
        ) from None


class Era5Client:
    """Use the supported CDS SDK with its current endpoint and local credentials.

    Configure authentication externally as described in the CDS setup guide.
    Dataset terms must be accepted before retrieval. Request validation and
    download handling belong to the SDK; no legacy api/v2 fallback is used.
    """

    def __init__(self) -> None:
        self._client = _sdk("cdsapi").Client(url=CDS_API_URL)

    def retrieve(
        self, dataset: str, request: Mapping[str, Any], target: str | PathLike[str]
    ) -> Any:
        """Forward a publisher-generated request and return the SDK result."""
        return self._client.retrieve(dataset, dict(request), str(target))


class CopernicusMarineClient:
    """Use Marine Toolbox subsetting instead of the removed MOTU service.

    Configure SDK authentication externally. The SDK validates selections and
    controls output files; this adapter does not infer dataset compatibility.
    """

    def __init__(self) -> None:
        self._client = _sdk("copernicusmarine")

    def subset(self, **selection: Any) -> Any:
        """Forward the published Toolbox keyword interface unchanged."""
        return self._client.subset(**selection)
