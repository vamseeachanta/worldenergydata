"""Offline CRM acquisition cases; no expected result comes from the helper.

The synthetic catalog follows NOAA's CRM catalog (accessed 2026-10-19):
https://www.ngdc.noaa.gov/thredds/catalog/crm/catalog.xml
WCS request keys follow Unidata TDS, WCS Reference, WCS 1.0.0 examples:
https://docs.unidata.ucar.edu/tds/current/userguide/wcs_ref.html
All byte limits, timeouts and coordinates below are synthetic test inputs.
"""

import gzip
import hashlib
import io
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
from urllib3.response import HTTPResponse

from worldenergydata.field_development.coastal_relief import (
    build_crm_subset_url,
    discover_crm_datasets,
    fetch_crm_subset,
    parse_crm_catalog,
)
from worldenergydata.field_development.terrain import TerrainFetchError

CATALOG_URL = "https://example.org/thredds/catalog/crm/catalog.xml"
CATALOG = b"""<catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
  <service name="all" serviceType="Compound" base="">
    <service name="wcs" serviceType="WCS" base="/thredds/wcs/"/>
    <service name="http" serviceType="HTTPServer" base="/thredds/fileServer/"/>
  </service>
  <dataset name="CRM">
    <metadata inherited="true"><serviceName>all</serviceName></metadata>
    <dataset name="volume" urlPath="crm/crm_vol3.nc"/>
    <dataset name="regional" urlPath="crm/crm_socal_3as_vers2.nc"/>
    <dataset name="other" urlPath="other/ignored.nc"/>
  </dataset>
</catalog>"""
BBOX = (-85.0, 25.0, -84.0, 26.0)
# NetCDF Users Guide v1.2, Appendix B, magic = 'C' 'D' 'F' VERSION.
# This is a transport fixture, not a scientifically qualified netCDF file.
PAYLOAD = b"CDF\x01synthetic"


class Response:
    def __init__(self, content=CATALOG, *, status=200, headers=None, error=None):
        self.content = content
        self.status_code = status
        self.headers = headers or {}
        self.error = error
        self.closed = False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("synthetic HTTP failure")

    def iter_content(self, chunk_size):
        midpoint = len(self.content) // 2
        yield self.content[:midpoint]
        if self.error:
            raise self.error
        yield b""
        yield self.content[midpoint:]

    def close(self):
        self.closed = True


class Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


@pytest.fixture
def dataset():
    return parse_crm_catalog(CATALOG, catalog_url=CATALOG_URL)[0]


def test_catalog_inherited_services_and_regional_names():
    """Join /thredds/wcs/ + crm/crm_vol3.nc on the catalog's origin by hand."""
    datasets = parse_crm_catalog(CATALOG, catalog_url=CATALOG_URL)
    assert [item.name for item in datasets] == ["volume", "regional"]
    assert datasets[0].url_path == "crm/crm_vol3.nc"
    assert datasets[0].wcs_url == "https://example.org/thredds/wcs/crm/crm_vol3.nc"
    assert datasets[0].catalog_url == CATALOG_URL


def test_direct_service_overrides_inheritance():
    catalog = CATALOG.replace(
        b'<dataset name="volume"', b'<dataset serviceName="wcs" name="volume"'
    )
    assert len(parse_crm_catalog(catalog, catalog_url=CATALOG_URL)) == 2


@pytest.mark.parametrize("inherited", ["true", "false"])
@pytest.mark.parametrize("attribute", [True, False])
def test_direct_service_is_not_inherited_by_nested_datasets(inherited, attribute):
    local_attribute = 'serviceName="local"' if attribute else ""
    local_element = "" if attribute else "<serviceName>local</serviceName>"
    catalog = f"""<catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
      <service name="all" serviceType="WCS" base="/thredds/wcs/"/>
      <service name="local" serviceType="WCS" base="/local/"/>
      <dataset name="parent" urlPath="crm/parent.nc" {local_attribute}>
        {local_element}
        <metadata inherited="{inherited}"><serviceName>all</serviceName></metadata>
        <dataset name="child" urlPath="crm/child.nc"/>
      </dataset>
    </catalog>""".encode()
    if inherited == "false":
        with pytest.raises(TerrainFetchError, match="WCS"):
            parse_crm_catalog(catalog, catalog_url=CATALOG_URL)
    else:
        datasets = parse_crm_catalog(catalog, catalog_url=CATALOG_URL)
        assert [item.wcs_url for item in datasets] == [
            "https://example.org/local/crm/parent.nc",
            "https://example.org/thredds/wcs/crm/child.nc",
        ]


@pytest.mark.parametrize(
    "catalog", [b"<html/>", b"<catalog", b"<!DOCTYPE catalog><catalog/>"]
)
def test_invalid_catalog_rejected(catalog):
    with pytest.raises(TerrainFetchError):
        parse_crm_catalog(catalog, catalog_url=CATALOG_URL)


@pytest.mark.parametrize(
    "base",
    [
        b"https://other.example/wcs/",
        b"//other.example/wcs/",
        b"/../wcs/",
        b"/wcs/?query=x",
    ],
)
def test_unsafe_service_base_rejected(base):
    with pytest.raises(TerrainFetchError):
        parse_crm_catalog(
            CATALOG.replace(b"/thredds/wcs/", base), catalog_url=CATALOG_URL
        )


def test_missing_wcs_rejected():
    with pytest.raises(TerrainFetchError, match="WCS"):
        parse_crm_catalog(
            CATALOG.replace(b'serviceType="WCS"', b'serviceType="WMS"'),
            catalog_url=CATALOG_URL,
        )


def test_duplicate_paths_rejected():
    with pytest.raises(TerrainFetchError, match="duplicate"):
        parse_crm_catalog(
            CATALOG.replace(b"crm/crm_socal_3as_vers2.nc", b"crm/crm_vol3.nc"),
            catalog_url=CATALOG_URL,
        )


def test_discover_uses_catalog_endpoint_and_closes():
    response = Response()
    session = Session(response)
    datasets = discover_crm_datasets(
        timeout=10, max_bytes=len(CATALOG), session=session
    )
    assert len(datasets) == 2
    url, options = session.calls[0]
    assert url == "https://www.ngdc.noaa.gov/thredds/catalog/crm/catalog.xml"
    assert options == {"timeout": 10, "stream": True, "allow_redirects": False}
    assert response.closed


def test_subset_request_lon_lat_order(dataset):
    """BBOX is copied west,south,east,north; no coordinate calculation occurs.

    NOAA volume 3 DescribeCoverage (2026-10-19) names z and OGC:CRS84.
    Unidata WCS 1.0.0 NetCDF3 example supplies the remaining request keys.
    """
    url = build_crm_subset_url(dataset, BBOX, coverage="z")
    assert urlsplit(url)._replace(query="").geturl() == dataset.wcs_url
    assert parse_qs(urlsplit(url).query) == {
        "service": ["WCS"],
        "version": ["1.0.0"],
        "request": ["GetCoverage"],
        "coverage": ["z"],
        "format": ["NetCDF3"],
        "crs": ["OGC:CRS84"],
        "bbox": ["-85.0,25.0,-84.0,26.0"],
    }


@pytest.mark.parametrize(
    "bbox",
    [(1, 2, 0, 3), (0, 3, 1, 2), (0, 0, float("inf"), 1), (0, float("nan"), 1, 2)],
)
def test_bad_bbox_rejected(dataset, bbox):
    with pytest.raises(ValueError):
        build_crm_subset_url(dataset, bbox, coverage="z")


def test_coverage_is_required_and_encoded(dataset):
    with pytest.raises(ValueError):
        build_crm_subset_url(dataset, BBOX, coverage="")
    query = parse_qs(
        urlsplit(build_crm_subset_url(dataset, BBOX, coverage="z&other")).query
    )
    assert query["coverage"] == ["z&other"]
    assert "other" not in query


def test_download_receipt_and_no_overwrite(dataset, tmp_path):
    """Count 4 magic bytes + 9 ASCII bytes = 13; hash those exact fixture bytes.

    hashlib is the independent standard-library SHA-256 oracle; neither the
    receipt's count nor its digest is used to derive the expected results.
    """
    target = tmp_path / "subset.nc"
    response = Response(PAYLOAD)
    session = Session(response)
    receipt = fetch_crm_subset(
        dataset, BBOX, target, coverage="z", timeout=10, max_bytes=13, session=session
    )
    assert target.read_bytes() == PAYLOAD
    assert receipt.path == target
    assert receipt.size_bytes == 13
    assert receipt.sha256 == hashlib.sha256(PAYLOAD).hexdigest()
    assert receipt.request_url == session.calls[0][0]
    assert receipt.catalog_url == dataset.catalog_url
    assert response.closed
    with pytest.raises(FileExistsError):
        fetch_crm_subset(
            dataset,
            BBOX,
            target,
            coverage="z",
            timeout=10,
            max_bytes=13,
            session=session,
        )
    assert len(session.calls) == 1
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize(
    "payload",
    [b"", b"CDF", b"CDF\x05synthetic", b"<xml>error</xml>", b'{"error":true}'],
)
def test_non_netcdf_never_published(dataset, tmp_path, payload):
    target = tmp_path / "subset.nc"
    response = Response(payload)
    with pytest.raises(TerrainFetchError, match="netCDF"):
        fetch_crm_subset(
            dataset,
            BBOX,
            target,
            coverage="z",
            timeout=10,
            max_bytes=100,
            session=Session(response),
        )
    assert not target.exists()
    assert response.closed
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("headers", [{}, {"Content-Length": "14"}])
def test_byte_limit_before_publication(dataset, tmp_path, headers):
    response = Response(PAYLOAD, headers=headers)
    with pytest.raises(TerrainFetchError, match="max_bytes"):
        fetch_crm_subset(
            dataset,
            BBOX,
            tmp_path / "subset.nc",
            coverage="z",
            timeout=10,
            max_bytes=12,
            session=Session(response),
        )
    assert not list(tmp_path.iterdir())
    assert response.closed


@pytest.mark.parametrize("status", [302, 404, 500])
def test_catalog_http_failures_close_response(status):
    response = Response(status=status)
    with pytest.raises((TerrainFetchError, requests.HTTPError)):
        discover_crm_datasets(timeout=10, max_bytes=100, session=Session(response))
    assert response.closed


def test_interrupted_download_is_not_published(dataset, tmp_path):
    response = Response(PAYLOAD, error=requests.ConnectionError("interrupted"))
    with pytest.raises(requests.ConnectionError):
        fetch_crm_subset(
            dataset,
            BBOX,
            tmp_path / "subset.nc",
            coverage="z",
            timeout=10,
            max_bytes=100,
            session=Session(response),
        )
    assert not list(tmp_path.iterdir())
    assert response.closed


@pytest.mark.parametrize(
    "timeout,max_bytes",
    [(0, 10), (float("nan"), 10), (float("inf"), 10), (10, 0), (10, True), (10, 1.5)],
)
def test_invalid_resource_limits(timeout, max_bytes):
    session = Session(Response())
    with pytest.raises(ValueError):
        discover_crm_datasets(timeout=timeout, max_bytes=max_bytes, session=session)
    assert not session.calls


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_xml_entity_declarations_rejected(encoding):
    xml = """<?xml version="1.0"?><!DOCTYPE catalog [<!ENTITY injected "volume">]>
    <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
    <dataset name="&injected;"/></catalog>""".encode(
        encoding
    )
    with pytest.raises(TerrainFetchError):
        parse_crm_catalog(xml, catalog_url=CATALOG_URL)


@pytest.mark.parametrize("length", ["-1", "not-a-length", "12", "14"])
def test_invalid_or_incomplete_length_not_published(dataset, tmp_path, length):
    response = Response(PAYLOAD, headers={"Content-Length": length})
    with pytest.raises(TerrainFetchError, match="length"):
        fetch_crm_subset(
            dataset,
            BBOX,
            tmp_path / "subset.nc",
            coverage="z",
            timeout=10,
            max_bytes=100,
            session=Session(response),
        )
    assert not list(tmp_path.iterdir())
    assert response.closed


def gzip_response(payload):
    """Use the real requests/urllib3 decoding path without network access."""
    wire_bytes = gzip.compress(payload, mtime=0)
    response = requests.Response()
    response.status_code = 200
    response.headers.update(
        {"Content-Length": str(len(wire_bytes)), "Content-Encoding": "gzip"}
    )
    response.raw = HTTPResponse(
        body=io.BytesIO(wire_bytes),
        headers=response.headers,
        preload_content=False,
        decode_content=False,
    )
    return response


def test_compressed_wire_length_can_exceed_decoded_budget(dataset, tmp_path):
    """The decoded payload fits: 4 magic bytes + 9 ASCII bytes = 13 bytes."""
    response = gzip_response(PAYLOAD)
    assert int(response.headers["Content-Length"]) > 13
    target = tmp_path / "subset.nc"
    receipt = fetch_crm_subset(
        dataset,
        BBOX,
        target,
        coverage="z",
        timeout=10,
        max_bytes=13,
        session=Session(response),
    )
    assert receipt.size_bytes == 13
    assert target.read_bytes() == PAYLOAD
    assert receipt.sha256 == hashlib.sha256(PAYLOAD).hexdigest()
    assert response.raw.closed


def test_decompressed_length_limit(dataset, tmp_path):
    """4 magic bytes + 96 repeated bytes = 100; the decoded cap is 99 bytes."""
    response = gzip_response(b"CDF\x01" + b"x" * 96)
    assert int(response.headers["Content-Length"]) < 99
    with pytest.raises(TerrainFetchError, match="max_bytes"):
        fetch_crm_subset(
            dataset,
            BBOX,
            tmp_path / "subset.nc",
            coverage="z",
            timeout=10,
            max_bytes=99,
            session=Session(response),
        )
    assert not list(tmp_path.iterdir())
    assert response.raw.closed


def test_duplicate_service_names_rejected():
    catalog = CATALOG.replace(
        b'<dataset name="CRM">',
        b'<service name="wcs" serviceType="WCS" base="/other/"/><dataset name="CRM">',
    )
    with pytest.raises(TerrainFetchError, match="duplicate"):
        parse_crm_catalog(catalog, catalog_url=CATALOG_URL)


def test_compound_service_base_not_guessed():
    catalog = CATALOG.replace(
        b'serviceType="Compound" base=""', b'serviceType="Compound" base="/prefix/"'
    )
    with pytest.raises(TerrainFetchError, match="compound"):
        parse_crm_catalog(catalog, catalog_url=CATALOG_URL)


def test_catalog_byte_limit():
    response = Response(CATALOG)
    with pytest.raises(TerrainFetchError, match="max_bytes"):
        discover_crm_datasets(
            timeout=10, max_bytes=len(CATALOG) - 1, session=Session(response)
        )
    assert response.closed


def test_repeated_identical_leaf_services_in_different_compounds():
    """NOAA repeats wcs under all and allButWMS; the leaf definitions agree."""
    catalog = CATALOG.replace(
        b'<dataset name="CRM">',
        b'<service name="allButWMS" serviceType="Compound" base="">'
        b'<service name="wcs" serviceType="WCS" base="/thredds/wcs/"/>'
        b'</service><dataset name="CRM">',
    )
    assert len(parse_crm_catalog(catalog, catalog_url=CATALOG_URL)) == 2
