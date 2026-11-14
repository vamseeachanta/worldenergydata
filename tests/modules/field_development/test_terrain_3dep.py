"""3DEP request contracts; synthetic metadata is not engineering input.

References: USGS TNM Access API v1, Products parameters (2026 access),
https://tnmaccess.nationalmap.gov/api/v1/docs ; Esri Export Image,
https://developers.arcgis.com/rest/services-reference/enterprise/export-image/ .
Pagination cases below are independent integer counts, not terrain measurements.
"""

from unittest.mock import Mock

import pytest
import requests

from worldenergydata.field_development import terrain

# Synthetic ordered rectangle, in the existing catalog's documented coverage.
BBOX = (-95.4, 29.7, -95.3, 29.8)


def response_session(payload):
    response = Mock()
    response.json.return_value = payload
    session = Mock()
    session.get.return_value = response
    return session


def test_find_tiles_preserves_metadata_and_pagination():
    """Hand count: total 3, offset 1, one item => one item remains.

    max/offset/bbox/datasets/prodFormats names come from TNM v1 Products.
    No download is performed; the synthetic identity/vintage remain unchanged.
    """
    payload = {
        "total": 3,
        "items": [
            {
                "sourceId": "synthetic-tile",
                "dateUpdated": "2026-01-01",
                "downloadURL": "https://example.org/tile.tif",
            }
        ],
    }
    session = response_session(payload)
    result = terrain.find_dem_tiles(BBOX, max_items=1, offset=1, session=session)
    assert result == payload
    url = session.get.call_args.args[0]
    params = session.get.call_args.kwargs["params"]
    assert (
        url
        == terrain.load_terrain_sources()["usgs_3dep_staged_tiles"]["endpoints"][
            "tnm_products_api"
        ]
    )
    assert params == {
        "bbox": "-95.4,29.7,-95.3,29.8",
        "datasets": "National Elevation Dataset (NED) 1/3 arc-second",
        "prodFormats": "GeoTIFF",
        "max": 1,
        "offset": 1,
        "outputFormat": "JSON",
    }
    session.get.assert_called_once()


def test_no_tiles_is_distinct_from_invalid_response():
    """Empty coverage has total=0 and items=[] by a hand count of zero."""
    payload = {"total": 0, "items": []}
    assert (
        terrain.find_dem_tiles(BBOX, max_items=1, session=response_session(payload))
        == payload
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"error": "unavailable"},
        {},
        {"total": 1, "items": None},
        {"total": -1, "items": []},
        {"total": True, "items": []},
        {"total": 1, "items": ["not a product"]},
        {"total": 0, "items": [{"sourceId": "impossible"}]},
        {"total": 2, "items": [{}, {}]},  # page size is one, not two
        {"total": 1.5, "items": []},
        [],
        None,
    ],
)
def test_malformed_products_rejected(payload):
    with pytest.raises(terrain.TerrainFetchError, match="products"):
        terrain.find_dem_tiles(BBOX, max_items=1, session=response_session(payload))


@pytest.mark.parametrize(
    "max_items,offset",
    [
        (0, 0),
        (-1, 0),
        (1.5, 0),
        (True, 0),
        (1, -1),
        (1, False),
        (1, 101),
    ],
)
def test_invalid_pagination_rejected_before_network(max_items, offset):
    """TNM v1 Products: offset > 100 requires max a multiple of 5."""
    session = Mock()
    with pytest.raises(ValueError):
        terrain.find_dem_tiles(
            BBOX, max_items=max_items, offset=offset, session=session
        )
    session.get.assert_not_called()


def test_deep_page_uses_documented_multiple():
    """TNM rule: 105 > 100; max=5 is divisible by 5 (5 / 5 = 1)."""
    terrain.find_dem_tiles(
        BBOX,
        max_items=5,
        offset=105,
        session=response_session({"total": 0, "items": []}),
    )


def test_product_http_failure_propagates():
    session = response_session({})
    session.get.return_value.raise_for_status.side_effect = requests.HTTPError()
    with pytest.raises(requests.HTTPError):
        terrain.find_dem_tiles(BBOX, max_items=1, session=session)


def test_product_invalid_json_is_fetch_error():
    session = response_session({})
    session.get.return_value.json.side_effect = ValueError("invalid json")
    with pytest.raises(terrain.TerrainFetchError, match="products"):
        terrain.find_dem_tiles(BBOX, max_items=1, session=session)


def test_unverified_tile_source_rejected(monkeypatch):
    sources = terrain.load_terrain_sources()
    sources["usgs_3dep_staged_tiles"]["status"] = "not_verified"
    monkeypatch.setattr(terrain, "load_terrain_sources", lambda path: sources)
    session = Mock()
    with pytest.raises(terrain.TerrainFetchError, match="not verified"):
        terrain.find_dem_tiles(BBOX, max_items=1, session=session)
    session.get.assert_not_called()


def test_invalid_bbox_rejected_before_tile_request():
    session = Mock()
    with pytest.raises(ValueError):
        terrain.find_dem_tiles((0, 0, 0, 1), max_items=1, session=session)
    session.get.assert_not_called()


def test_dynamic_export_preserves_exact_extent(tmp_path):
    """Esri Export Image adjustAspectRatio=false preserves the supplied bbox.

    Synthetic span 0.00000002 degrees must not round to zero; unlike the
    square output, rectangle width/height = 2/1, so adjustment is observable.
    Bytes are a transport stub, not a qualified GeoTIFF or elevation sample.
    """
    session = Mock()
    session.get.return_value.content = b"II*\x00stub"
    terrain.fetch_dem(
        (-95.40000002, 29.7, -95.4, 29.70000001),
        tmp_path / "dem.tif",
        size=(8, 8),
        session=session,
    )
    params = session.get.call_args.kwargs["params"]
    assert params["adjustAspectRatio"] == "false"
    assert params["bbox"] == "-95.40000002,29.7,-95.4,29.70000001"


@pytest.mark.parametrize("size", [(1.5, 2), (True, 2), (2, float("nan"))])
def test_dynamic_export_requires_integer_pixels(size):
    session = Mock()
    with pytest.raises(ValueError, match="size"):
        terrain.fetch_dem(BBOX, size=size, session=session)
    session.get.assert_not_called()
