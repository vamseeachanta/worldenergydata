# ABOUTME: Tests for the terrain/bathymetry source catalog + fetch_dem helper (issue #930).
# ABOUTME: Offline by default — network use is faked; one live smoke test is opt-in via marker.
"""Tests for ``worldenergydata.field_development.terrain``."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from worldenergydata.field_development.terrain import (
    REQUIRED_SOURCE_FIELDS,
    TERRAIN_SOURCES_PATH,
    TerrainFetchError,
    fetch_dem,
    load_terrain_sources,
)

HOUSTON_BBOX = (-95.40, 29.70, -95.30, 29.80)

# ---------------------------------------------------------------------------
# Catalog contract
# ---------------------------------------------------------------------------


class TestCatalog:
    def test_catalog_ships_next_to_module(self):
        assert TERRAIN_SOURCES_PATH.is_file()

    def test_loads_and_validates(self):
        sources = load_terrain_sources()
        assert sources, "catalog must not be empty"
        for entry in sources.values():
            assert REQUIRED_SOURCE_FIELDS.issubset(entry)

    def test_expected_source_families_present(self):
        sources = load_terrain_sources()
        for source_id in (
            "usgs_3dep_dem",
            "usgs_3dep_staged_tiles",
            "gebco_global_bathymetry",
            "noaa_ncei_coastal_relief",
            "boem_gom_bathymetry",
        ):
            assert source_id in sources, f"missing source family: {source_id}"

    def test_verified_entries_carry_evidence_and_date(self):
        for source_id, entry in load_terrain_sources().items():
            assert entry["status"] == "verified", source_id
            assert str(entry["verification"]).strip(), source_id
            assert str(entry["verified_on"]), source_id
            assert str(entry["license"]).strip(), source_id

    def test_all_endpoints_https(self):
        for entry in load_terrain_sources().values():
            for url in entry["endpoints"].values():
                assert str(url).startswith("https://")

    def test_dem_source_has_export_endpoint(self):
        entry = load_terrain_sources()["usgs_3dep_dem"]
        assert "export_image" in entry["endpoints"]

    def test_missing_field_rejected(self, tmp_path: Path):
        sources = load_terrain_sources()
        broken = {"sources": {"bad": {"name": "incomplete"}}}
        assert sources  # sanity: the real catalog loaded before we break a copy
        bad_path = tmp_path / "broken.yml"
        bad_path.write_text(yaml.safe_dump(broken), encoding="utf-8")
        with pytest.raises(ValueError, match="is missing"):
            load_terrain_sources(bad_path)

    def test_invalid_status_rejected(self, tmp_path: Path):
        catalog = yaml.safe_load(TERRAIN_SOURCES_PATH.read_text(encoding="utf-8"))
        entry = catalog["sources"]["usgs_3dep_dem"]
        entry["status"] = "maybe"
        bad_path = tmp_path / "bad_status.yml"
        bad_path.write_text(yaml.safe_dump({"sources": {"x": entry}}), encoding="utf-8")
        with pytest.raises(ValueError, match="invalid status"):
            load_terrain_sources(bad_path)


# ---------------------------------------------------------------------------
# fetch_dem — offline, via injected fake session
# ---------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Duck-typed requests.Session capturing the outgoing call."""

    def __init__(self, response: FakeResponse):
        self._response = response
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, params: dict, timeout: float) -> FakeResponse:
        self.calls.append((url, params))
        return self._response

    def head(self, *a, **k):  # pragma: no cover - not used by fetch_dem
        raise AssertionError("fetch_dem must not HEAD")


TIFF_BYTES = b"II*\x00" + b"\x00" * 64


class TestFetchDem:
    def test_writes_geotiff_and_builds_request_from_catalog(self, tmp_path: Path):
        session = FakeSession(FakeResponse(TIFF_BYTES))
        out = tmp_path / "dem.tif"
        result = fetch_dem(HOUSTON_BBOX, out, size=(64, 64), session=session)

        assert result == out
        assert out.read_bytes() == TIFF_BYTES

        ((url, params),) = session.calls
        catalog_url = load_terrain_sources()["usgs_3dep_dem"]["endpoints"][
            "export_image"
        ]
        assert url == catalog_url  # endpoint comes from YAML, not code
        assert params["bbox"] == "-95.400000,29.700000,-95.300000,29.800000"
        assert params["size"] == "64,64"
        assert params["format"] == "tiff"
        assert params["f"] == "image"

    def test_default_out_path_lands_in_tmp(self, tmp_path: Path):
        session = FakeSession(FakeResponse(TIFF_BYTES))
        result = fetch_dem(HOUSTON_BBOX, size=(32, 32), session=session)
        try:
            assert result.is_file()
            assert result.suffix == ".tif"
            assert "usgs_3dep_dem" in result.name
        finally:
            result.unlink(missing_ok=True)

    def test_non_tiff_response_raises(self, tmp_path: Path):
        session = FakeSession(FakeResponse(b'{"error": {"code": 400}}'))
        with pytest.raises(TerrainFetchError, match="did not return a GeoTIFF"):
            fetch_dem(HOUSTON_BBOX, tmp_path / "dem.tif", session=session)
        assert not (tmp_path / "dem.tif").exists()

    @pytest.mark.parametrize(
        "bbox",
        [
            (-95.3, 29.7, -95.4, 29.8),  # min_lon > max_lon
            (-95.4, 29.8, -95.3, 29.7),  # min_lat > max_lat
            (-195.0, 29.7, -95.3, 29.8),  # lon out of range
            (-95.4, 29.7, -95.3, 99.0),  # lat out of range
        ],
    )
    def test_invalid_bbox_rejected(self, bbox):
        with pytest.raises(ValueError):
            fetch_dem(bbox, session=FakeSession(FakeResponse(TIFF_BYTES)))

    def test_zero_size_rejected(self):
        with pytest.raises(ValueError, match="size"):
            fetch_dem(
                HOUSTON_BBOX,
                size=(0, 64),
                session=FakeSession(FakeResponse(TIFF_BYTES)),
            )

    def test_unknown_source_rejected(self):
        with pytest.raises(KeyError):
            fetch_dem(
                HOUSTON_BBOX,
                source_id="nonexistent",
                session=FakeSession(FakeResponse(TIFF_BYTES)),
            )


# ---------------------------------------------------------------------------
# Live smoke test — opt-in only (network marker + env gate)
# ---------------------------------------------------------------------------


@pytest.mark.network
@pytest.mark.skipif(
    not os.environ.get("WED_LIVE_NETWORK_TESTS"),
    reason="live endpoint check; set WED_LIVE_NETWORK_TESTS=1 to run",
)
def test_fetch_dem_live_smoke(tmp_path: Path):
    out = fetch_dem(HOUSTON_BBOX, tmp_path / "live_dem.tif", size=(32, 32))
    data = out.read_bytes()
    assert data[:4] in (b"II*\x00", b"MM\x00*")
    assert len(data) > 1000
