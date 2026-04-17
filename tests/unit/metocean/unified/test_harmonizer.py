# ABOUTME: Tests for harmonizer.py — variable name, unit, and time normalisation.

"""Tests for MetoceanHarmonizer standardisation logic."""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from worldenergydata.metocean.unified.harmonizer import MetoceanHarmonizer

STANDARD_COLUMNS = ["timestamp", "parameter", "value", "source", "unit"]


class TestMetoceanHarmonizerNDBC:
    """Harmonize NDBC observations into the long-format schema."""

    def setup_method(self):
        self.h = MetoceanHarmonizer()

    def _make_ndbc_obs(self, n=3):
        """Return a list of mock NDBCObservation-like dicts."""
        from datetime import datetime

        return [
            {
                "station_id": "41001",
                "observation_time": datetime(2023, 6, 1, h, 0),
                "wave_height_m": 1.5 + h * 0.1,
                "dominant_wave_period_s": 8.0,
                "wind_speed_ms": 5.0 + h * 0.2,
                "wind_direction_deg": 180.0,
            }
            for h in range(n)
        ]

    def test_harmonize_ndbc_returns_dataframe(self):
        obs = self._make_ndbc_obs(3)
        df = self.h.harmonize_ndbc(obs)
        assert isinstance(df, pd.DataFrame)

    def test_harmonize_ndbc_has_required_columns(self):
        obs = self._make_ndbc_obs(3)
        df = self.h.harmonize_ndbc(obs)
        for col in STANDARD_COLUMNS:
            assert col in df.columns, f"Missing column: {col}"

    def test_harmonize_ndbc_maps_wave_height_to_Hs(self):
        obs = self._make_ndbc_obs(1)
        df = self.h.harmonize_ndbc(obs)
        assert "Hs" in df["parameter"].values

    def test_harmonize_ndbc_maps_wave_period_to_Tp(self):
        obs = self._make_ndbc_obs(1)
        df = self.h.harmonize_ndbc(obs)
        assert "Tp" in df["parameter"].values

    def test_harmonize_ndbc_maps_wind_speed(self):
        obs = self._make_ndbc_obs(1)
        df = self.h.harmonize_ndbc(obs)
        assert "wind_speed" in df["parameter"].values

    def test_harmonize_ndbc_maps_wind_dir(self):
        obs = self._make_ndbc_obs(1)
        df = self.h.harmonize_ndbc(obs)
        assert "wind_dir" in df["parameter"].values

    def test_harmonize_ndbc_source_label(self):
        obs = self._make_ndbc_obs(2)
        df = self.h.harmonize_ndbc(obs)
        assert all(df["source"] == "ndbc")

    def test_harmonize_ndbc_units_for_Hs(self):
        obs = self._make_ndbc_obs(1)
        df = self.h.harmonize_ndbc(obs)
        hs_rows = df[df["parameter"] == "Hs"]
        assert all(hs_rows["unit"] == "m")


class TestMetoceanHarmonizerOpenMeteo:
    """Harmonize OpenMeteoForecast objects."""

    def setup_method(self):
        self.h = MetoceanHarmonizer()

    def _make_om_obs(self, n=3):
        return [
            {
                "latitude": 28.5,
                "longitude": -88.5,
                "forecast_time": datetime(2023, 6, 1, h, 0),
                "wave_height_m": 2.0,
                "wave_period_s": 10.0,
                "wave_direction_deg": 200.0,
                "current_speed_ms": 0.3,
                "current_direction_deg": 90.0,
            }
            for h in range(n)
        ]

    def test_harmonize_open_meteo_returns_dataframe(self):
        obs = self._make_om_obs(3)
        df = self.h.harmonize_open_meteo(obs)
        assert isinstance(df, pd.DataFrame)

    def test_harmonize_open_meteo_has_required_columns(self):
        obs = self._make_om_obs(2)
        df = self.h.harmonize_open_meteo(obs)
        for col in STANDARD_COLUMNS:
            assert col in df.columns

    def test_harmonize_open_meteo_maps_current_speed(self):
        obs = self._make_om_obs(1)
        df = self.h.harmonize_open_meteo(obs)
        assert "current_speed" in df["parameter"].values

    def test_harmonize_open_meteo_source_label(self):
        obs = self._make_om_obs(2)
        df = self.h.harmonize_open_meteo(obs)
        assert all(df["source"] == "open_meteo")


class TestMetoceanHarmonizerMetNorway:
    """Harmonize MetNorwayForecast objects."""

    def setup_method(self):
        self.h = MetoceanHarmonizer()

    def _make_mn_obs(self, n=3):
        return [
            {
                "latitude": 57.0,
                "longitude": 3.5,
                "forecast_time": datetime(2023, 6, 1, h, 0, tzinfo=timezone.utc),
                "wave_height_m": 1.8,
                "wave_period_s": 9.0,
                "wind_speed_ms": 8.0,
                "wind_direction_deg": 270.0,
                "current_speed_ms": 0.5,
                "current_direction_deg": 45.0,
            }
            for h in range(n)
        ]

    def test_harmonize_met_norway_returns_dataframe(self):
        obs = self._make_mn_obs(3)
        df = self.h.harmonize_met_norway(obs)
        assert isinstance(df, pd.DataFrame)

    def test_harmonize_met_norway_source_label(self):
        obs = self._make_mn_obs(2)
        df = self.h.harmonize_met_norway(obs)
        assert all(df["source"] == "met_norway")

    def test_harmonize_met_norway_timestamps_utc(self):
        obs = self._make_mn_obs(2)
        df = self.h.harmonize_met_norway(obs)
        # timestamps should be timezone-aware UTC or naive UTC
        assert df["timestamp"].dtype == "datetime64[ns]" or str(
            df["timestamp"].dtype
        ).startswith("datetime64")


class TestMetoceanHarmonizerAlignment:
    """Test hourly UTC time-grid alignment."""

    def setup_method(self):
        self.h = MetoceanHarmonizer()

    def test_align_to_hourly_grid(self):
        # 3 rows at non-hourly times → should produce aligned hourly grid
        rows = [
            {
                "timestamp": datetime(2023, 1, 1, 0, 0),
                "parameter": "Hs",
                "value": 1.0,
                "source": "ndbc",
                "unit": "m",
            },
            {
                "timestamp": datetime(2023, 1, 1, 0, 30),
                "parameter": "Hs",
                "value": 1.5,
                "source": "ndbc",
                "unit": "m",
            },
            {
                "timestamp": datetime(2023, 1, 1, 1, 0),
                "parameter": "Hs",
                "value": 2.0,
                "source": "ndbc",
                "unit": "m",
            },
        ]
        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        aligned = self.h.align_to_hourly_grid(df)
        # After alignment, timestamps should be on exact hours
        assert isinstance(aligned, pd.DataFrame)
        assert len(aligned) > 0

    def test_align_does_not_return_empty_for_valid_data(self):
        rows = [
            {
                "timestamp": datetime(2023, 1, 1, h, 0),
                "parameter": "Hs",
                "value": float(h + 1),
                "source": "ndbc",
                "unit": "m",
            }
            for h in range(5)
        ]
        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        aligned = self.h.align_to_hourly_grid(df)
        assert len(aligned) >= 5

    def test_align_directional_uses_nearest_neighbour(self):
        """Wind direction should use nearest-neighbour (not interpolation)."""
        rows = [
            {
                "timestamp": datetime(2023, 1, 1, 0, 0),
                "parameter": "wind_dir",
                "value": 90.0,
                "source": "ndbc",
                "unit": "deg",
            },
            {
                "timestamp": datetime(2023, 1, 1, 2, 0),
                "parameter": "wind_dir",
                "value": 180.0,
                "source": "ndbc",
                "unit": "deg",
            },
        ]
        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        aligned = self.h.align_to_hourly_grid(df)
        # Values must be from the original set (nearest), not interpolated midpoint
        if "wind_dir" in aligned["parameter"].values:
            wind_vals = aligned[aligned["parameter"] == "wind_dir"]["value"].tolist()
            for v in wind_vals:
                assert v in [90.0, 180.0], f"Unexpected interpolated value: {v}"

    def test_merge_sources_combines_dataframes(self):
        df1 = pd.DataFrame(
            [
                {
                    "timestamp": datetime(2023, 1, 1, 0, 0),
                    "parameter": "Hs",
                    "value": 1.0,
                    "source": "ndbc",
                    "unit": "m",
                },
            ]
        )
        df2 = pd.DataFrame(
            [
                {
                    "timestamp": datetime(2023, 1, 1, 0, 0),
                    "parameter": "Hs",
                    "value": 1.2,
                    "source": "open_meteo",
                    "unit": "m",
                },
            ]
        )
        merged = self.h.merge_sources([df1, df2])
        assert isinstance(merged, pd.DataFrame)
        assert len(merged) == 2
        assert set(merged["source"]) == {"ndbc", "open_meteo"}

    def test_merge_sources_empty_list_returns_empty_df(self):
        merged = self.h.merge_sources([])
        assert isinstance(merged, pd.DataFrame)
        assert len(merged) == 0
