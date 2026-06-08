"""Tests for the metocean scheduler adapter."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from worldenergydata.metocean.clients.base_client import FetchResult
from worldenergydata.metocean.clients.open_meteo_client import OpenMeteoForecast
from worldenergydata.metocean.constants import DataSource
from worldenergydata.scheduler.jobs.metocean_refresh import MetoceanRefreshJob


def _forecast(lat: float = 28.5, lon: float = -88.5) -> OpenMeteoForecast:
    return OpenMeteoForecast(
        latitude=lat,
        longitude=lon,
        forecast_time=datetime(2026, 6, 8, 12, 0),
        wave_height_m=1.2,
        wave_direction_deg=180.0,
    )


def _result(data, had_errors: bool = False) -> FetchResult[OpenMeteoForecast]:
    return FetchResult(
        data=data,
        source=DataSource.OPEN_METEO,
        fetch_time=datetime(2026, 6, 8, 12, 0),
        records_count=len(data),
        had_errors=had_errors,
        error_messages=["failed"] if had_errors else [],
    )


def test_metocean_writes_forecast_parquet_for_configured_locations(tmp_path: Path):
    client = MagicMock()
    client.fetch_forecast.return_value = _result([_forecast()])

    with patch(
        "worldenergydata.scheduler.jobs.metocean_refresh.OpenMeteoClient",
        return_value=client,
    ):
        result = MetoceanRefreshJob().run(
            {
                "output_dir": str(tmp_path),
                "forecast_days": 1,
                "locations": [{"lat": 28.5, "lon": -88.5, "name": "GOM"}],
            }
        )

    assert result.status == "success"
    assert result.records_updated == 1
    output = tmp_path / "open_meteo_gom.parquet"
    assert output.exists()
    df = pd.read_parquet(output)
    assert df.loc[0, "location_name"] == "GOM"
    assert df.loc[0, "wave_height_m"] == 1.2
    client.fetch_forecast.assert_called_once_with(
        latitude=28.5,
        longitude=-88.5,
        forecast_days=1,
    )


def test_metocean_partial_location_failure_still_succeeds(tmp_path: Path):
    client = MagicMock()
    client.fetch_forecast.side_effect = [
        _result([_forecast()]),
        _result([], had_errors=True),
    ]

    with patch(
        "worldenergydata.scheduler.jobs.metocean_refresh.OpenMeteoClient",
        return_value=client,
    ):
        result = MetoceanRefreshJob().run(
            {
                "output_dir": str(tmp_path),
                "locations": [
                    {"lat": 28.5, "lon": -88.5, "name": "GOM"},
                    {"lat": 60.0, "lon": 2.0, "name": "NCS"},
                ],
            }
        )

    assert result.status == "success"
    assert result.records_updated == 1
    assert "NCS" in (result.error_msg or "")


def test_metocean_all_locations_failed_returns_failure(tmp_path: Path):
    client = MagicMock()
    client.fetch_forecast.return_value = _result([], had_errors=True)

    with patch(
        "worldenergydata.scheduler.jobs.metocean_refresh.OpenMeteoClient",
        return_value=client,
    ):
        result = MetoceanRefreshJob().run(
            {
                "output_dir": str(tmp_path),
                "locations": [{"lat": 28.5, "lon": -88.5, "name": "GOM"}],
            }
        )

    assert result.status == "failure"
    assert result.records_updated == 0
    assert "All metocean locations failed" in (result.error_msg or "")
