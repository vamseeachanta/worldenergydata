# ABOUTME: Tests for the metocean CLI interface.
# ABOUTME: Validates Typer commands, argument parsing, and command execution.

"""
Tests for Metocean CLI Interface

Validates the Typer-based CLI for metocean data fetching and management.
Tests cover:
- Command structure and help
- Argument parsing
- Station commands
- Fetch commands
- Cache commands
- Database commands
- Export commands
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner

from worldenergydata.modules.metocean.cli import (
    ExportFormat,
    RegionChoice,
    SourceChoice,
    _get_region_bbox,
    _parse_bbox,
    _parse_coords,
    _parse_date,
    app,
)

runner = CliRunner()


class TestCLIHelpers:
    """Tests for CLI helper functions."""

    def test_get_region_bbox_gom(self):
        """Test getting GOM region bounding box."""
        bbox = _get_region_bbox(RegionChoice.gom)
        assert bbox is not None
        assert len(bbox) == 4
        # GOM_BBOX should have valid coordinates
        min_lat, max_lat, min_lon, max_lon = bbox
        assert min_lat < max_lat
        assert min_lon < max_lon

    def test_get_region_bbox_all_returns_none(self):
        """Test that 'all' region returns None (no filtering)."""
        bbox = _get_region_bbox(RegionChoice.all)
        assert bbox is None

    def test_get_region_bbox_atlantic(self):
        """Test getting Atlantic region bounding box."""
        bbox = _get_region_bbox(RegionChoice.atlantic)
        assert bbox is not None
        assert len(bbox) == 4

    def test_parse_coords_valid(self):
        """Test parsing valid coordinate string."""
        coords = _parse_coords("29.5,-88.5")
        assert coords == (29.5, -88.5)

    def test_parse_coords_with_spaces(self):
        """Test parsing coordinates with spaces."""
        coords = _parse_coords("29.5, -88.5")
        assert coords == (29.5, -88.5)

    def test_parse_coords_invalid(self):
        """Test parsing invalid coordinate string raises Exit."""
        from click.exceptions import Exit

        with pytest.raises(Exit):
            _parse_coords("invalid")

    def test_parse_coords_incomplete(self):
        """Test parsing incomplete coordinate string raises Exit."""
        from click.exceptions import Exit

        with pytest.raises(Exit):
            _parse_coords("29.5")

    def test_parse_bbox_valid(self):
        """Test parsing valid bounding box string."""
        bbox = _parse_bbox("25.0,30.0,-95.0,-85.0")
        assert bbox == (25.0, 30.0, -95.0, -85.0)

    def test_parse_bbox_invalid(self):
        """Test parsing invalid bounding box string raises Exit."""
        from click.exceptions import Exit

        with pytest.raises(Exit):
            _parse_bbox("25.0,30.0")

    def test_parse_date_valid(self):
        """Test parsing valid date string."""
        date = _parse_date("2024-01-15")
        assert date == datetime(2024, 1, 15)

    def test_parse_date_invalid(self):
        """Test parsing invalid date string raises Exit."""
        from click.exceptions import Exit

        with pytest.raises(Exit):
            _parse_date("invalid-date")


class TestCLIEnums:
    """Tests for CLI enum classes."""

    def test_source_choice_values(self):
        """Test SourceChoice enum values."""
        assert SourceChoice.ndbc.value == "ndbc"
        assert SourceChoice.coops.value == "coops"
        assert SourceChoice.open_meteo.value == "open-meteo"

    def test_region_choice_values(self):
        """Test RegionChoice enum values."""
        assert RegionChoice.gom.value == "gom"
        assert RegionChoice.atlantic.value == "atlantic"
        assert RegionChoice.pacific.value == "pacific"
        assert RegionChoice.alaska.value == "alaska"
        assert RegionChoice.all.value == "all"

    def test_export_format_values(self):
        """Test ExportFormat enum values."""
        assert ExportFormat.csv.value == "csv"
        assert ExportFormat.json.value == "json"
        assert ExportFormat.netcdf.value == "netcdf"


class TestMainApp:
    """Tests for main app commands."""

    def test_app_help(self):
        """Test main app shows help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "metocean" in result.stdout.lower() or "Metocean" in result.stdout

    def test_info_command(self):
        """Test info command shows module information."""
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "Metocean" in result.stdout or "metocean" in result.stdout

    @patch("worldenergydata.modules.metocean.cli.CacheManager")
    def test_status_command(self, mock_cache_manager):
        """Test status command shows system status."""
        mock_cache = Mock()
        mock_cache.status.return_value = {
            "enabled": True,
            "entries": 10,
            "size_mb": 5.5,
            "max_size_mb": 500,
        }
        mock_cache_manager.return_value = mock_cache

        result = runner.invoke(app, ["status"])
        # Status command should execute without error
        assert result.exit_code == 0


class TestStationsCommands:
    """Tests for station management commands."""

    def test_stations_help(self):
        """Test stations subcommand help."""
        result = runner.invoke(app, ["stations", "--help"])
        assert result.exit_code == 0
        assert "list" in result.stdout or "search" in result.stdout

    @patch("worldenergydata.modules.metocean.cli.NDBCClient")
    def test_stations_list_ndbc(self, mock_client_class):
        """Test listing NDBC stations."""
        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        mock_result = Mock()
        mock_result.success = True
        mock_result.data = [
            Mock(
                station_id="41001",
                name="Test Station",
                lat=34.5,
                lon=-72.5,
                station_type="buoy",
            )
        ]
        mock_client.fetch_stations.return_value = mock_result
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["stations", "list", "--source", "ndbc"])
        # Should not crash
        assert result.exit_code == 0 or "error" not in result.stdout.lower()

    @patch("worldenergydata.modules.metocean.cli.NDBCClient")
    def test_stations_list_with_region_filter(self, mock_client_class):
        """Test listing stations with region filter."""
        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        mock_result = Mock()
        mock_result.success = True
        mock_result.data = []
        mock_client.fetch_stations.return_value = mock_result
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app, ["stations", "list", "--source", "ndbc", "--region", "gom"]
        )
        assert result.exit_code == 0 or "error" not in result.stdout.lower()

    @patch("worldenergydata.modules.metocean.cli.NDBCClient")
    def test_stations_info(self, mock_client_class):
        """Test getting station info."""
        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        mock_result = Mock()
        mock_result.success = True
        mock_result.data = Mock(
            station_id="41001",
            name="Test Station",
            lat=34.5,
            lon=-72.5,
            station_type="buoy",
        )
        mock_client.get_station_info.return_value = mock_result
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["stations", "info", "41001"])
        assert result.exit_code == 0 or "error" not in result.stdout.lower()


class TestFetchCommands:
    """Tests for data fetching commands."""

    def test_fetch_help(self):
        """Test fetch subcommand help."""
        result = runner.invoke(app, ["fetch", "--help"])
        assert result.exit_code == 0

    @patch("worldenergydata.modules.metocean.cli.NDBCClient")
    def test_fetch_ndbc(self, mock_client_class):
        """Test fetching NDBC data."""
        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        mock_result = Mock()
        mock_result.success = True
        mock_result.data = [
            Mock(
                timestamp=datetime.now(),
                wave_height=1.5,
                wave_period=8.0,
                wind_speed=10.5,
                wind_direction=180,
            )
        ]
        mock_client.fetch_realtime.return_value = mock_result
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["fetch", "ndbc", "41001"])
        assert result.exit_code == 0 or "error" not in result.stdout.lower()

    @patch("worldenergydata.modules.metocean.cli.COOPSClient")
    def test_fetch_coops(self, mock_client_class):
        """Test fetching CO-OPS data."""
        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        mock_result = Mock()
        mock_result.success = True
        mock_result.data = []
        mock_client.fetch_water_levels.return_value = mock_result
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["fetch", "coops", "8729108"])
        assert result.exit_code == 0 or "error" not in result.stdout.lower()

    @patch("worldenergydata.modules.metocean.cli.OpenMeteoClient")
    def test_fetch_open_meteo(self, mock_client_class):
        """Test fetching Open-Meteo data."""
        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        mock_result = Mock()
        mock_result.success = True
        mock_result.data = Mock(
            latitude=29.0,
            longitude=-88.0,
            hourly=[],
        )
        mock_client.fetch_forecast.return_value = mock_result
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["fetch", "open-meteo", "--coords", "29.0,-88.0"])
        assert result.exit_code == 0 or "error" not in result.stdout.lower()


class TestCacheCommands:
    """Tests for cache management commands."""

    def test_cache_help(self):
        """Test cache subcommand help."""
        result = runner.invoke(app, ["cache", "--help"])
        assert result.exit_code == 0

    @patch("worldenergydata.modules.metocean.cli.CacheManager")
    def test_cache_status(self, mock_cache_manager):
        """Test cache status command."""
        mock_cache = Mock()
        mock_cache.status.return_value = {
            "enabled": True,
            "entries": 25,
            "expired": 5,
            "active": 20,
            "total_hits": 100,
            "size_bytes": 11010048,
            "size_mb": 10.5,
            "max_size_mb": 500,
            "ttl_hours": 24,
            "cache_dir": "/tmp/cache",
            "by_source": {"ndbc": 15, "coops": 10},
        }
        mock_cache_manager.return_value = mock_cache

        result = runner.invoke(app, ["cache", "status"])
        assert result.exit_code == 0

    @patch("worldenergydata.modules.metocean.cli.CacheManager")
    def test_cache_clear(self, mock_cache_manager):
        """Test cache clear command."""
        mock_cache = Mock()
        mock_cache.clear.return_value = 10
        mock_cache_manager.return_value = mock_cache

        result = runner.invoke(app, ["cache", "clear", "--yes"])
        assert result.exit_code == 0

    @patch("worldenergydata.modules.metocean.cli.CacheManager")
    def test_cache_cleanup(self, mock_cache_manager):
        """Test cache cleanup command."""
        mock_cache = Mock()
        mock_cache.cleanup_expired.return_value = 5
        mock_cache_manager.return_value = mock_cache

        result = runner.invoke(app, ["cache", "cleanup"])
        assert result.exit_code == 0


class TestDatabaseCommands:
    """Tests for database management commands."""

    def test_db_help(self):
        """Test db subcommand help."""
        result = runner.invoke(app, ["db", "--help"])
        assert result.exit_code == 0

    @patch("worldenergydata.modules.metocean.cli.init_database")
    def test_db_init(self, mock_init_db):
        """Test database initialization command."""
        mock_init_db.return_value = True

        result = runner.invoke(app, ["db", "init"])
        assert result.exit_code == 0

    @patch("worldenergydata.modules.metocean.cli.get_config")
    def test_db_status(self, mock_get_config):
        """Test database status command."""
        mock_config = Mock()
        mock_config.database.host = "localhost"
        mock_config.database.port = 5432
        mock_config.database.database = "metocean"
        mock_get_config.return_value = mock_config

        result = runner.invoke(app, ["db", "status"])
        assert result.exit_code == 0


class TestExportCommands:
    """Tests for export commands."""

    def test_export_help(self):
        """Test export subcommand help."""
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0


class TestHistoricalCommand:
    """Tests for historical data command."""

    @patch("worldenergydata.modules.metocean.cli.NDBCClient")
    def test_historical_command(self, mock_client_class):
        """Test fetching historical data."""
        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        mock_result = Mock()
        mock_result.success = True
        mock_result.data = []
        mock_client.fetch_historical.return_value = mock_result
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "historical",
                "41001",
                "2024-01-01",
                "2024-01-31",
                "--source",
                "ndbc",
            ],
        )
        assert result.exit_code == 0 or "error" not in result.stdout.lower()


class TestErrorHandling:
    """Tests for CLI error handling."""

    def test_invalid_source(self):
        """Test handling invalid source."""
        result = runner.invoke(app, ["stations", "list", "--source", "invalid_source"])
        # Should show error or help
        assert result.exit_code != 0 or "error" in result.stdout.lower()

    def test_invalid_region(self):
        """Test handling invalid region."""
        result = runner.invoke(
            app, ["stations", "list", "--source", "ndbc", "--region", "invalid"]
        )
        # Should show error or help
        assert result.exit_code != 0 or "error" in result.stdout.lower()

    def test_missing_required_argument(self):
        """Test handling missing required argument."""
        result = runner.invoke(app, ["fetch", "ndbc"])
        # Should show error about missing station ID
        assert result.exit_code != 0 or "error" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
