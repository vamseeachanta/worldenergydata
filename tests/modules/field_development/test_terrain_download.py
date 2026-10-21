"""Staged DEM transport tests; fixtures are not measured terrain.

TNM v1 ProductsResponse fields: https://tnmaccess.nationalmap.gov/api/v1/docs
(accessed 2026-10-21). TIFF signatures: libtiff tiff.h, TIFF_VERSION_CLASSIC,
TIFF_VERSION_BIG, TIFF_LITTLEENDIAN, TIFF_BIGENDIAN (accessed 2026-10-21).
All byte limits below are synthetic caller inputs, not engineering criteria.
"""

import json
from copy import deepcopy
from hashlib import sha256
from unittest.mock import Mock

import pytest
import requests

from worldenergydata.field_development import terrain_tiles
from worldenergydata.field_development.terrain import TerrainFetchError

# Hand count: four signature bytes plus three payload bytes = seven bytes.
# This is deliberately only a TIFF transport stub, not a valid elevation raster.
TIFF = b"II*\x00abc"
PRODUCT = {
    "sourceId": "synthetic-tile",
    "format": "GeoTIFF",
    "downloadURL": (
        "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/"
        "historical/n30w096/USGS_13_n30w096_20100201.tif"
    ),
    "sizeInBytes": 7,
    "publicationDate": "2010-02-01",
    "boundingBox": {"minX": -96, "minY": 29, "maxX": -95, "maxY": 30},
}


def stream_session(chunks=(TIFF,), *, headers=None):
    response = Mock(status_code=requests.codes.ok, headers=headers or {})
    response.iter_content.return_value = iter(chunks)
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    session = Mock()
    session.get.return_value = response
    return session, response


def download(tmp_path, *, product=None, max_bytes=7, session=None):
    return terrain_tiles.download_dem_tile(
        PRODUCT if product is None else product,
        tmp_path / "tile.tif",
        max_bytes=max_bytes,
        timeout=10,
        session=session or stream_session()[0],
    )


def test_download_retains_provenance_and_counts_split_chunks(tmp_path):
    """Independent count: 1 + 2 + 0 + 4 = 7; budget 7 accepts equality.

    Digest is independently computed over the literal expected bytes. Metadata
    is copied verbatim, including the historical URL and source publication date.
    """
    session, response = stream_session(
        (b"I", b"I*", b"", b"\x00abc"), headers={"Content-Length": "7"}
    )
    product = deepcopy(PRODUCT)
    result = download(tmp_path, product=product, session=session)
    assert result.path.read_bytes() == TIFF
    assert result.size_bytes == 7
    assert result.sha256 == sha256(TIFF).hexdigest()
    assert result.product == PRODUCT
    product["boundingBox"]["minX"] = 0
    assert result.product == PRODUCT
    manifest = result.to_manifest()
    assert manifest["file"] == "tile.tif"
    assert manifest["product"] == PRODUCT
    assert manifest["sha256"] == result.sha256
    assert manifest["size_bytes"] == 7
    assert manifest["source_id"] == "usgs_3dep_staged_tiles"
    assert manifest["qualification"] == "NOT_EVALUATED"
    assert manifest["retrieved_at"].endswith("+00:00")
    assert json.loads(json.dumps(manifest)) == manifest
    manifest["product"]["sourceId"] = "changed"
    assert result.product == PRODUCT
    session.get.assert_called_once_with(
        PRODUCT["downloadURL"],
        stream=True,
        allow_redirects=False,
        headers={"Accept-Encoding": "identity"},
        timeout=10,
    )
    response.__exit__.assert_called_once()
    assert list(tmp_path.iterdir()) == [result.path]


@pytest.mark.parametrize("signature", [b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"])
def test_classic_and_big_tiff_transport_headers(tmp_path, signature):
    """libtiff tiff.h: classic version 42, BigTIFF version 43, either endian."""
    result = download(tmp_path, session=stream_session((signature + b"abc",))[0])
    assert result.path.read_bytes() == signature + b"abc"


@pytest.mark.parametrize("max_bytes", [0, -1, True, 7.5])
def test_invalid_budget_rejected_without_network(tmp_path, max_bytes):
    session, _ = stream_session()
    with pytest.raises(ValueError, match="max_bytes"):
        download(tmp_path, max_bytes=max_bytes, session=session)
    session.get.assert_not_called()


def test_advertised_product_too_large_rejected_without_network(tmp_path):
    """Seven advertised bytes exceed a six-byte caller budget by one byte."""
    session, _ = stream_session()
    with pytest.raises(TerrainFetchError, match="budget"):
        download(tmp_path, max_bytes=6, session=session)
    session.get.assert_not_called()


@pytest.mark.parametrize(
    "changes",
    [
        {"sourceId": ""},
        {"sourceId": None},
        {"format": "LAZ"},
        {"sizeInBytes": -1},
        {"sizeInBytes": True},
        {"sizeInBytes": "7"},
        {"downloadURL": "http://prd-tnm.s3.amazonaws.com/tile.tif"},
        {"downloadURL": "https://example.org/tile.tif"},
        {"downloadURL": PRODUCT["downloadURL"] + "?token=synthetic"},
        {"downloadURL": PRODUCT["downloadURL"] + "#fragment"},
        {"downloadURL": PRODUCT["downloadURL"].replace("historical/", "../")},
        {"downloadURL": PRODUCT["downloadURL"].replace("historical/", "%2e%2e/")},
        {"downloadURL": PRODUCT["downloadURL"].replace("13/TIFF/", "1/TIFF/")},
        {"downloadURL": PRODUCT["downloadURL"].replace(".tif", ".zip")},
        {"downloadURL": None},
    ],
)
def test_invalid_product_rejected_before_network(tmp_path, changes):
    session, _ = stream_session()
    with pytest.raises(ValueError):
        download(tmp_path, product={**PRODUCT, **changes}, session=session)
    session.get.assert_not_called()


@pytest.mark.parametrize("size", [None, 0])
def test_missing_or_unknown_product_size_still_enforces_stream_budget(tmp_path, size):
    """Unknown catalog size is not permission to exceed the caller's six bytes."""
    product = {**PRODUCT, "sizeInBytes": size}
    session, _ = stream_session((TIFF[:4], TIFF[4:]))
    with pytest.raises(TerrainFetchError, match="budget"):
        download(tmp_path, product=product, max_bytes=6, session=session)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "headers,chunks,error",
    [
        ({"Content-Length": "8"}, (TIFF,), "budget"),
        ({"Content-Length": "6"}, (TIFF,), "length"),
        ({"Content-Length": "invalid"}, (TIFF,), "length"),
        ({"Content-Length": "-1"}, (TIFF,), "length"),
        ({"Content-Encoding": "gzip"}, (TIFF,), "encoding"),
        ({}, (b"II*\x00ab",), "size"),
        ({}, (b'{"error":true}',), "budget"),
        ({}, (b"notTIFF",), "TIFF"),
        ({}, (b"II",), "TIFF"),
        ({}, (), "TIFF"),
    ],
)
def test_invalid_stream_never_publishes_partial_file(tmp_path, headers, chunks, error):
    session, response = stream_session(chunks, headers=headers)
    with pytest.raises(TerrainFetchError, match=error):
        download(tmp_path, session=session)
    assert not list(tmp_path.iterdir())
    response.__exit__.assert_called_once()


@pytest.mark.parametrize(
    "status", [requests.codes.found, requests.codes.partial_content]
)
def test_redirect_or_partial_response_rejected(tmp_path, status):
    session, response = stream_session()
    response.status_code = status
    with pytest.raises(TerrainFetchError, match="complete"):
        download(tmp_path, session=session)
    assert not list(tmp_path.iterdir())


def test_connection_failure_cleans_partial_file(tmp_path):
    def broken_stream():
        yield TIFF[:4]
        raise requests.ConnectionError("synthetic disconnect")

    session, _ = stream_session(broken_stream())
    with pytest.raises(requests.ConnectionError):
        download(tmp_path, session=session)
    assert not list(tmp_path.iterdir())


def test_existing_file_is_preserved_without_network(tmp_path):
    path = tmp_path / "tile.tif"
    path.write_bytes(b"existing data")
    session, _ = stream_session()
    with pytest.raises(FileExistsError):
        download(tmp_path, session=session)
    session.get.assert_not_called()
    assert path.read_bytes() == b"existing data"


def test_file_created_during_download_is_preserved(tmp_path):
    def racing_stream():
        yield TIFF[:4]
        (tmp_path / "tile.tif").write_bytes(b"concurrent data")
        yield TIFF[4:]

    session, _ = stream_session(racing_stream())
    with pytest.raises(FileExistsError):
        download(tmp_path, session=session)
    assert (tmp_path / "tile.tif").read_bytes() == b"concurrent data"
    assert len(list(tmp_path.iterdir())) == 1


def test_unverified_source_rejected(tmp_path, monkeypatch):
    sources = terrain_tiles.load_terrain_sources()
    sources["usgs_3dep_staged_tiles"]["status"] = "not_verified"
    monkeypatch.setattr(terrain_tiles, "load_terrain_sources", lambda path: sources)
    session, _ = stream_session()
    with pytest.raises(TerrainFetchError, match="not verified"):
        download(tmp_path, session=session)
    session.get.assert_not_called()


@pytest.mark.parametrize("timeout", [0, -1, True, float("inf"), float("nan"), "10"])
def test_invalid_timeout_rejected_without_network(tmp_path, timeout):
    session, _ = stream_session()
    with pytest.raises(ValueError, match="timeout"):
        terrain_tiles.download_dem_tile(
            PRODUCT,
            tmp_path / "tile.tif",
            max_bytes=7,
            timeout=timeout,
            session=session,
        )
    session.get.assert_not_called()


def test_non_mapping_product_is_type_error(tmp_path):
    with pytest.raises(TypeError, match="mapping"):
        terrain_tiles.download_dem_tile(
            [], tmp_path / "tile.tif", max_bytes=7, timeout=10
        )


@pytest.mark.parametrize("size", [None, 0])
def test_unknown_advertised_size_can_succeed(tmp_path, size):
    result = download(tmp_path, product={**PRODUCT, "sizeInBytes": size})
    assert result.size_bytes == 7


def test_current_product_is_supported(tmp_path):
    product = {
        **PRODUCT,
        "downloadURL": PRODUCT["downloadURL"].replace("historical/", "current/"),
    }
    assert download(tmp_path, product=product).product == product


def test_http_error_does_not_create_destination(tmp_path):
    session, response = stream_session()
    response.raise_for_status.side_effect = requests.HTTPError("synthetic HTTP failure")
    with pytest.raises(requests.HTTPError):
        download(tmp_path, session=session)
    assert not list(tmp_path.iterdir())
    response.__exit__.assert_called_once()


def test_existing_dangling_symlink_is_preserved(tmp_path):
    path = tmp_path / "tile.tif"
    path.symlink_to(tmp_path / "missing.tif")
    session, _ = stream_session()
    with pytest.raises(FileExistsError):
        download(tmp_path, session=session)
    session.get.assert_not_called()
    assert path.is_symlink()


def test_publication_failure_removes_only_staging_file(tmp_path, monkeypatch):
    def fail_link(*args):
        raise OSError("synthetic hard-link failure")

    monkeypatch.setattr(terrain_tiles.os, "link", fail_link)
    with pytest.raises(OSError, match="hard-link"):
        download(tmp_path)
    assert not list(tmp_path.iterdir())


def test_offline_worked_example(tmp_path):
    """Hand count: I,I,*,NUL,a,b,c = seven bytes; one discovered product.

    The script must retain that literal byte sequence and its metadata; it
    cannot claim terrain qualification from a magic-only transport fixture.
    """
    import runpy
    from pathlib import Path

    example = (
        Path(__file__).resolve().parents[3] / "examples" / "terrain_dem_download.py"
    )
    functions = runpy.run_path(str(example))
    manifest = functions["run_example"](tmp_path)
    assert manifest["size_bytes"] == 7
    assert manifest["sha256"] == sha256(TIFF).hexdigest()
    assert manifest["qualification"] == "NOT_EVALUATED"
    assert (tmp_path / manifest["file"]).read_bytes() == TIFF
    assert json.loads((tmp_path / "tile.manifest.json").read_text()) == manifest


def test_real_requests_session_streams_through_injected_adapter(tmp_path):
    """Seven literal bytes traverse requests.Response.iter_content, without I/O.

    A memory-backed adapter exercises the actual requests session and response
    lifecycle instead of implementing a second version of streaming behavior.
    """
    from io import BytesIO

    class MemoryAdapter(requests.adapters.BaseAdapter):
        def send(self, request, **kwargs):
            assert request.url == PRODUCT["downloadURL"]
            assert request.headers["Accept-Encoding"] == "identity"
            assert kwargs["stream"] is True
            response = requests.Response()
            response.status_code = requests.codes.ok
            response.headers["Content-Length"] = "7"
            response.raw = BytesIO(TIFF)
            response.request = request
            return response

        def close(self):
            pass

    with requests.Session() as session:
        session.mount("https://", MemoryAdapter())
        result = download(tmp_path, session=session)
    assert result.path.read_bytes() == TIFF
    assert result.size_bytes == 7
