"""
Tests for dashboard data loading functions.

TDD: Tests written BEFORE implementation.
Covers:
  - BSEE production data loading
  - BSEE platform/well location data loading
  - FDAS incident data loading
  - Sample/fallback data generation when real data absent
"""

from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Production data loader tests
# ---------------------------------------------------------------------------


class TestLoadProductionData:
    """Tests for load_production_data()."""

    def test_load_production_data_returns_dataframe(self):
        """load_production_data() must return a pandas DataFrame."""
        from worldenergydata.dashboard.data_loader import load_production_data

        df = load_production_data()
        assert isinstance(df, pd.DataFrame)

    def test_load_production_data_has_required_columns(self):
        """Production DataFrame must include oil, gas, water, date, and label columns."""
        from worldenergydata.dashboard.data_loader import load_production_data

        df = load_production_data()
        required = {"PRODUCTION_DATE", "OIL_BBL", "GAS_MCF", "WATER_BBL", "FIELD_NAME"}
        assert required.issubset(
            set(df.columns)
        ), f"Missing columns: {required - set(df.columns)}"

    def test_load_production_data_not_empty(self):
        """Production DataFrame must have at least one row."""
        from worldenergydata.dashboard.data_loader import load_production_data

        df = load_production_data()
        assert len(df) > 0

    def test_load_production_data_numeric_volumes(self):
        """Oil, gas, water columns must be numeric."""
        from worldenergydata.dashboard.data_loader import load_production_data

        df = load_production_data()
        for col in ("OIL_BBL", "GAS_MCF", "WATER_BBL"):
            assert pd.api.types.is_numeric_dtype(
                df[col]
            ), f"Column {col} is not numeric"

    def test_load_production_data_date_parseable(self):
        """PRODUCTION_DATE column must be parseable as datetime."""
        from worldenergydata.dashboard.data_loader import load_production_data

        df = load_production_data()
        parsed = pd.to_datetime(df["PRODUCTION_DATE"], errors="coerce")
        assert parsed.notna().all(), "Some PRODUCTION_DATE values could not be parsed"

    def test_load_production_data_accepts_data_dir_override(self, tmp_path):
        """Function must accept an optional data_dir path argument."""
        from worldenergydata.dashboard.data_loader import load_production_data

        # Empty directory - should return fallback sample data, not raise
        df = load_production_data(data_dir=tmp_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0


# ---------------------------------------------------------------------------
# Platform / well location data tests
# ---------------------------------------------------------------------------


class TestLoadPlatformData:
    """Tests for load_platform_data()."""

    def test_load_platform_data_returns_dataframe(self):
        """load_platform_data() must return a pandas DataFrame."""
        from worldenergydata.dashboard.data_loader import load_platform_data

        df = load_platform_data()
        assert isinstance(df, pd.DataFrame)

    def test_load_platform_data_has_coordinate_columns(self):
        """Platform DataFrame must include latitude and longitude columns."""
        from worldenergydata.dashboard.data_loader import load_platform_data

        df = load_platform_data()
        assert "LATITUDE" in df.columns, "Missing LATITUDE column"
        assert "LONGITUDE" in df.columns, "Missing LONGITUDE column"

    def test_load_platform_data_has_status_column(self):
        """Platform DataFrame must include a status or well-status column."""
        from worldenergydata.dashboard.data_loader import load_platform_data

        df = load_platform_data()
        assert "WELL_STATUS" in df.columns, "Missing WELL_STATUS column"

    def test_load_platform_data_coordinates_in_gom_bounds(self):
        """All coordinates must fall within Gulf of Mexico bounding box."""
        from worldenergydata.dashboard.data_loader import load_platform_data

        df = load_platform_data()
        df_clean = df.dropna(subset=["LATITUDE", "LONGITUDE"])
        assert (
            df_clean["LATITUDE"].between(17.0, 31.0)
        ).all(), "Latitude out of GOM bounds"
        assert (
            df_clean["LONGITUDE"].between(-98.0, -80.0)
        ).all(), "Longitude out of GOM bounds"

    def test_load_platform_data_not_empty(self):
        """Platform DataFrame must have at least one row."""
        from worldenergydata.dashboard.data_loader import load_platform_data

        df = load_platform_data()
        assert len(df) > 0


# ---------------------------------------------------------------------------
# FDAS incident data tests
# ---------------------------------------------------------------------------


class TestLoadIncidentData:
    """Tests for load_incident_data()."""

    def test_load_incident_data_returns_dataframe(self):
        """load_incident_data() must return a pandas DataFrame."""
        from worldenergydata.dashboard.data_loader import load_incident_data

        df = load_incident_data()
        assert isinstance(df, pd.DataFrame)

    def test_load_incident_data_has_required_columns(self):
        """Incident DataFrame must include type, severity, year, and area columns."""
        from worldenergydata.dashboard.data_loader import load_incident_data

        df = load_incident_data()
        required = {"INCIDENT_TYPE", "SEVERITY", "INCIDENT_YEAR", "AREA_NAME"}
        assert required.issubset(
            set(df.columns)
        ), f"Missing columns: {required - set(df.columns)}"

    def test_load_incident_data_severity_values_valid(self):
        """SEVERITY column must only contain recognised severity levels."""
        from worldenergydata.dashboard.data_loader import load_incident_data

        VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        df = load_incident_data()
        bad = set(df["SEVERITY"].dropna().unique()) - VALID_SEVERITIES
        assert not bad, f"Unexpected severity values: {bad}"

    def test_load_incident_data_year_is_integer_like(self):
        """INCIDENT_YEAR column must be integer or castable to integer."""
        from worldenergydata.dashboard.data_loader import load_incident_data

        df = load_incident_data()
        years = pd.to_numeric(df["INCIDENT_YEAR"], errors="coerce")
        assert years.notna().all(), "Some INCIDENT_YEAR values are not numeric"
        assert (years >= 1990).all(), "Incident years should be >= 1990"

    def test_load_incident_data_not_empty(self):
        """Incident DataFrame must have at least one row."""
        from worldenergydata.dashboard.data_loader import load_incident_data

        df = load_incident_data()
        assert len(df) > 0

    def test_load_incident_data_accepts_data_dir_override(self, tmp_path):
        """Function must accept an optional data_dir argument."""
        from worldenergydata.dashboard.data_loader import load_incident_data

        df = load_incident_data(data_dir=tmp_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0


# ---------------------------------------------------------------------------
# Sample data generator tests
# ---------------------------------------------------------------------------


class TestSampleDataGenerators:
    """Tests for the internal sample/fallback data generators."""

    def test_sample_production_schema(self):
        """Sample production data must match the expected schema."""
        from worldenergydata.dashboard.data_loader import _sample_production_data

        df = _sample_production_data()
        assert isinstance(df, pd.DataFrame)
        assert "FIELD_NAME" in df.columns
        assert "OIL_BBL" in df.columns

    def test_sample_platform_schema(self):
        """Sample platform data must match the expected schema."""
        from worldenergydata.dashboard.data_loader import _sample_platform_data

        df = _sample_platform_data()
        assert isinstance(df, pd.DataFrame)
        assert "LATITUDE" in df.columns
        assert "LONGITUDE" in df.columns

    def test_sample_incident_schema(self):
        """Sample incident data must match the expected schema."""
        from worldenergydata.dashboard.data_loader import _sample_incident_data

        df = _sample_incident_data()
        assert isinstance(df, pd.DataFrame)
        assert "INCIDENT_TYPE" in df.columns
        assert "SEVERITY" in df.columns
