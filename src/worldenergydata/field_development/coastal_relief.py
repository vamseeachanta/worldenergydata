"""Discover NOAA CRM datasets and acquire bounded native-grid WCS subsets.

No network access occurs on import. Limits are caller inputs, not scientific
acceptance criteria. A transport receipt does not qualify elevations, units,
vertical datums or spatial accuracy for engineering use.

Sources (accessed 2026-10-19):
* NOAA CRM THREDDS catalog, September 2010 dataset citation:
  https://www.ngdc.noaa.gov/thredds/catalog/crm/catalog.xml
* Unidata TDS WCS Reference, WCS 1.0.0 examples and limitations:
  https://docs.unidata.ucar.edu/tds/current/userguide/wcs_ref.html
* NetCDF Users Guide v1.2, Appendix B, classic format magic:
  https://docs.unidata.ucar.edu/nug/current/file_format_specifications.html
"""

from __future__ import annotations

import hashlib
import io
import math
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import urlencode, urlsplit, urlunsplit

import requests
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from .terrain import TerrainFetchError, _validate_bbox, load_terrain_sources

# Namespace and CRM path layout: NOAA CRM catalog, September 2010 citation.
_NS = "{http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0}"
_CRM_PATH = re.compile(r"crm/[A-Za-z0-9_.-]+\.nc\Z")
# NetCDF Users Guide v1.2, Appendix B: classic / 64-bit-offset VERSION bytes.
_NETCDF3_MAGICS = (b"CDF\x01", b"CDF\x02")


@dataclass(frozen=True)
class CrmDataset:
    """One catalog-advertised CRM dataset; no inferred geographic coverage."""

    name: str
    url_path: str
    wcs_url: str
    catalog_url: str


@dataclass(frozen=True)
class CrmDownload:
    """Transport provenance; retain this receipt with the unqualified data."""

    path: Path
    size_bytes: int
    sha256: str
    request_url: str
    catalog_url: str


def _origin(url: str) -> tuple[str, str]:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
        raise TerrainFetchError("CRM endpoints must use credential-free HTTPS")
    return parts.scheme, parts.netloc


def _service_url(catalog_url: str, base: str, path: str) -> str:
    scheme, netloc = _origin(catalog_url)
    # Accept only absolute paths on the catalog origin, never remote services.
    if (
        not base.startswith("/")
        or base.startswith("//")
        or not base.endswith("/")
        or re.search(r"[^A-Za-z0-9_./-]", base)
        or ".." in base.split("/")
    ):
        raise TerrainFetchError("unsupported WCS service base")
    return urlunsplit((scheme, netloc, base + path, "", ""))


def parse_crm_catalog(xml: bytes, *, catalog_url: str) -> tuple[CrmDataset, ...]:
    """Read inline CRM datasets and their inherited WCS services.

    Catalog references are not followed. Ambiguous or absent WCS services and
    duplicate dataset paths are refused instead of guessing an endpoint.
    """
    _origin(catalog_url)
    try:
        root = ElementTree.fromstring(xml, forbid_dtd=True)
    except (ElementTree.ParseError, DefusedXmlException) as exc:
        raise TerrainFetchError("invalid CRM catalog XML") from exc
    if root.tag != _NS + "catalog":
        raise TerrainFetchError("not a THREDDS catalog")
    services = {}
    for service in root.iter(_NS + "service"):
        name = service.attrib.get("name")
        if name in services:
            previous = services[name]
            # NOAA repeats identical leaf services in its compound groups.
            if previous.attrib != service.attrib or len(previous) or len(service):
                raise TerrainFetchError("duplicate catalog service name")
            continue
        if service.attrib.get(
            "serviceType", ""
        ).lower() == "compound" and service.attrib.get("base"):
            raise TerrainFetchError("unsupported compound service base")
        services[name] = service
    datasets: list[CrmDataset] = []
    seen: set[str] = set()

    def visit(node: Any, inherited: str | None) -> None:
        local = node.attrib.get("serviceName") or node.findtext(_NS + "serviceName")
        descendant_service = inherited
        for metadata in node.findall(_NS + "metadata"):
            if metadata.attrib.get("inherited") == "true":
                descendant_service = metadata.findtext(_NS + "serviceName") or inherited
        service_name = local or descendant_service
        path = node.attrib.get("urlPath", "")
        if _CRM_PATH.fullmatch(path):
            service = services.get(service_name)
            wcs = (
                [
                    s
                    for s in service.iter(_NS + "service")
                    if s.attrib.get("serviceType", "").lower() == "wcs"
                ]
                if service is not None
                else []
            )
            if len(wcs) != 1:
                raise TerrainFetchError(
                    "dataset must advertise exactly one WCS service"
                )
            if path in seen:
                raise TerrainFetchError("duplicate CRM dataset path")
            seen.add(path)
            datasets.append(
                CrmDataset(
                    name=node.attrib.get("name", path),
                    url_path=path,
                    wcs_url=_service_url(
                        catalog_url, wcs[0].attrib.get("base", ""), path
                    ),
                    catalog_url=catalog_url,
                )
            )
        for child in node.findall(_NS + "dataset"):
            visit(child, local or descendant_service)

    for dataset in root.findall(_NS + "dataset"):
        visit(dataset, None)
    if not datasets:
        raise TerrainFetchError("catalog contains no inline CRM datasets")
    return tuple(datasets)


def _validate_limits(timeout: float, max_bytes: int) -> None:
    if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")


def _receive(
    url: str, stream: BinaryIO, *, timeout: float, max_bytes: int, session: Any
) -> tuple[int, str]:
    _origin(url)
    response = session.get(url, timeout=timeout, stream=True, allow_redirects=False)
    try:
        response.raise_for_status()
        # RFC 9110 (2022), section 15.3.1: require a complete 200 OK response.
        if response.status_code != 200:
            raise TerrainFetchError("CRM endpoint did not return HTTP 200")
        length = response.headers.get("Content-Length")
        if length is not None:
            if not re.fullmatch(r"[0-9]+", length):
                raise TerrainFetchError("invalid response content length")
            length = int(length)
            if length > max_bytes:
                raise TerrainFetchError("response exceeds max_bytes")
        total = 0
        digest = hashlib.sha256()
        for chunk in response.iter_content(
            chunk_size=min(max_bytes, io.DEFAULT_BUFFER_SIZE)
        ):
            total += len(chunk)
            if total > max_bytes:
                raise TerrainFetchError("response exceeds max_bytes")
            stream.write(chunk)
            digest.update(chunk)
        if (
            length is not None
            and response.headers.get("Content-Encoding", "identity") == "identity"
            and total != length
        ):
            raise TerrainFetchError("response content length mismatch")
        return total, digest.hexdigest()
    finally:
        response.close()


def discover_crm_datasets(
    *,
    timeout: float,
    max_bytes: int,
    catalog_path: Path | None = None,
    session: Any = None,
) -> tuple[CrmDataset, ...]:
    """Fetch just the catalog; cap decompressed XML bytes and refuse redirects."""
    _validate_limits(timeout, max_bytes)
    entry = load_terrain_sources(catalog_path)["noaa_ncei_coastal_relief"]
    if entry["status"] != "verified":
        raise TerrainFetchError("CRM catalog source is not verified")
    url = entry["endpoints"]["thredds_catalog"]
    stream = io.BytesIO()
    _receive(
        url,
        stream,
        timeout=timeout,
        max_bytes=max_bytes,
        session=session if session is not None else requests,
    )
    return parse_crm_catalog(stream.getvalue(), catalog_url=url)


def build_crm_subset_url(
    dataset: CrmDataset, bbox: tuple[float, float, float, float], *, coverage: str
) -> str:
    """Prepare WCS native-grid NetCDF3 output; bbox is west,south,east,north.

    Coverage must come from this dataset's DescribeCoverage response. No
    interpolation, resampling, vertical datum or fixed resolution is assumed.
    Numeric geography bounds are inherited from terrain._validate_bbox.
    """
    _validate_bbox(bbox)
    _origin(dataset.wcs_url)
    if not coverage or not coverage.strip():
        raise ValueError("coverage must be supplied from DescribeCoverage")
    if urlsplit(dataset.wcs_url).query or urlsplit(dataset.wcs_url).fragment:
        raise TerrainFetchError("WCS endpoint must not contain a query or fragment")
    # Unidata TDS WCS Reference, WCS 1.0.0 NetCDF3 GetCoverage example;
    # NOAA volume 3 DescribeCoverage (2026-10-19) advertises OGC:CRS84.
    params = {
        "service": "WCS",
        "version": "1.0.0",
        "request": "GetCoverage",
        "coverage": coverage,
        "format": "NetCDF3",
        "crs": "OGC:CRS84",
        "bbox": ",".join(str(value) for value in bbox),
    }
    return dataset.wcs_url + "?" + urlencode(params)


def fetch_crm_subset(
    dataset: CrmDataset,
    bbox: tuple[float, float, float, float],
    out_path: Path,
    *,
    coverage: str,
    timeout: float,
    max_bytes: int,
    session: Any = None,
) -> CrmDownload:
    """Stream a bounded subset and publish it exclusively after transport checks.

    Existing outputs are never overwritten. Failed or interrupted transfers
    leave no destination file. Magic validation only distinguishes NetCDF3
    transport from typical service-error pages; it is not a scientific reader.
    """
    _validate_limits(timeout, max_bytes)
    url = build_crm_subset_url(dataset, bbox, coverage=coverage)
    out_path = Path(out_path)
    if out_path.exists():
        raise FileExistsError("subset destination already exists")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=out_path.parent, suffix=".part") as stream:
        size, digest = _receive(
            url,
            stream,
            timeout=timeout,
            max_bytes=max_bytes,
            session=session if session is not None else requests,
        )
        stream.seek(0)
        if stream.read(len(_NETCDF3_MAGICS[0])) not in _NETCDF3_MAGICS:
            raise TerrainFetchError("CRM endpoint did not return netCDF3")
        stream.flush()
        # Same-directory hard link publishes atomically and refuses replacement.
        os.link(stream.name, out_path)
    return CrmDownload(out_path, size, digest, url, dataset.catalog_url)
