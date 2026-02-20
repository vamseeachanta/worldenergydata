"""Tests for NOAA CO-OPS client dataclasses and constants."""

from datetime import datetime

import pytest

from worldenergydata.metocean.clients.coops_client import (
    COOPSClient,
    COOPSCurrent,
    COOPSStation,
    COOPSTidePrediction,
    COOPSWaterLevel,
)
from worldenergydata.metocean.constants import StationType


# ---------------------------------------------------------------------------
# COOPSStation dataclass
# ---------------------------------------------------------------------------

class TestCOOPSStation:
    def test_init(self):
        station = COOPSStation(
            station_id="8761724",
            name="Grand Isle",
            latitude=29.263,
            longitude=-89.957,
        )
        assert station.station_id == "8761724"
        assert station.name == "Grand Isle"
        assert station.latitude == pytest.approx(29.263)
        assert station.longitude == pytest.approx(-89.957)

    def test_defaults(self):
        station = COOPSStation(
            station_id="1234",
            name="Test",
            latitude=0.0,
            longitude=0.0,
        )
        assert station.state is None
        assert station.station_type == StationType.COASTAL
        assert station.has_water_level is False
        assert station.has_currents is False
        assert station.has_predictions is False
        assert station.reference_datum is None
        assert station.metadata == {}

    def test_full_init(self):
        station = COOPSStation(
            station_id="8761724",
            name="Grand Isle",
            latitude=29.263,
            longitude=-89.957,
            state="LA",
            station_type=StationType.COASTAL,
            has_water_level=True,
            has_currents=False,
            has_predictions=True,
            reference_datum="MLLW",
            metadata={"owner": "NOAA"},
        )
        assert station.state == "LA"
        assert station.has_water_level is True
        assert station.has_predictions is True
        assert station.reference_datum == "MLLW"


# ---------------------------------------------------------------------------
# COOPSWaterLevel dataclass
# ---------------------------------------------------------------------------

class TestCOOPSWaterLevel:
    def test_init(self):
        obs = COOPSWaterLevel(
            station_id="8761724",
            observation_time=datetime(2024, 1, 15, 12, 0),
            water_level_m=0.35,
        )
        assert obs.station_id == "8761724"
        assert obs.water_level_m == pytest.approx(0.35)
        assert obs.quality_flag == "v"
        assert obs.datum == "MLLW"

    def test_with_sigma(self):
        obs = COOPSWaterLevel(
            station_id="8761724",
            observation_time=datetime(2024, 1, 15),
            water_level_m=0.5,
            sigma=0.02,
            quality_flag="p",
            datum="MSL",
        )
        assert obs.sigma == pytest.approx(0.02)
        assert obs.quality_flag == "p"
        assert obs.datum == "MSL"


# ---------------------------------------------------------------------------
# COOPSCurrent dataclass
# ---------------------------------------------------------------------------

class TestCOOPSCurrent:
    def test_init(self):
        current = COOPSCurrent(
            station_id="g06010",
            observation_time=datetime(2024, 1, 15, 12, 0),
            speed_ms=0.5,
            direction_deg=180.0,
        )
        assert current.speed_ms == pytest.approx(0.5)
        assert current.direction_deg == pytest.approx(180.0)
        assert current.bin_depth_m is None
        assert current.quality_flag == "v"

    def test_with_bin_depth(self):
        current = COOPSCurrent(
            station_id="g06010",
            observation_time=datetime(2024, 1, 15),
            speed_ms=0.3,
            direction_deg=90.0,
            bin_depth_m=5.0,
        )
        assert current.bin_depth_m == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# COOPSTidePrediction dataclass
# ---------------------------------------------------------------------------

class TestCOOPSTidePrediction:
    def test_init(self):
        pred = COOPSTidePrediction(
            station_id="8761724",
            prediction_time=datetime(2024, 1, 15, 6, 0),
            water_level_m=0.8,
        )
        assert pred.water_level_m == pytest.approx(0.8)
        assert pred.tide_type is None
        assert pred.datum == "MLLW"

    def test_high_tide(self):
        pred = COOPSTidePrediction(
            station_id="8761724",
            prediction_time=datetime(2024, 1, 15, 6, 0),
            water_level_m=1.2,
            tide_type="H",
            datum="MSL",
        )
        assert pred.tide_type == "H"
        assert pred.datum == "MSL"


# ---------------------------------------------------------------------------
# COOPSClient constants
# ---------------------------------------------------------------------------

class TestCOOPSClientConstants:
    def test_data_url(self):
        assert "tidesandcurrents" in COOPSClient.DATA_URL

    def test_stations_url(self):
        assert "stations" in COOPSClient.STATIONS_URL

    def test_products(self):
        products = COOPSClient.PRODUCTS
        assert "water_level" in products
        assert "predictions" in products
        assert "currents" in products
        assert "high_low" in products

    def test_datums(self):
        datums = COOPSClient.DATUMS
        assert "MLLW" in datums
        assert "MSL" in datums
        assert "NAVD" in datums
        assert len(datums) == 8


# ---------------------------------------------------------------------------
# COOPSClient._parse_station
# ---------------------------------------------------------------------------

class TestParseStation:
    def test_basic(self):
        client = COOPSClient()
        data = {
            "id": "8761724",
            "name": "Grand Isle",
            "lat": 29.263,
            "lng": -89.957,
            "state": "LA",
        }
        station = client._parse_station(data)
        assert station.station_id == "8761724"
        assert station.name == "Grand Isle"
        assert station.latitude == pytest.approx(29.263)
        assert station.longitude == pytest.approx(-89.957)

    def test_missing_coords_raises(self):
        client = COOPSClient()
        data = {"id": "1234", "name": "Test"}
        with pytest.raises(ValueError, match="missing coordinates"):
            client._parse_station(data)

    def test_string_coords(self):
        client = COOPSClient()
        data = {
            "id": "9999",
            "name": "Test",
            "lat": "30.0",
            "lng": "-90.0",
        }
        station = client._parse_station(data)
        assert station.latitude == pytest.approx(30.0)
        assert station.longitude == pytest.approx(-90.0)
