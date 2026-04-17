# ABOUTME: Tests for coverage.py — which clients cover a given lat/lon.

"""Tests for MetoceanCoverage client selection logic."""

from datetime import datetime

import pytest

from worldenergydata.metocean.unified.coverage import MetoceanCoverage

# ---------------------------------------------------------------------------
# Gulf of Mexico (GoM) location — lat 28.5, lon -88.5
# ---------------------------------------------------------------------------

COORDS_GOM = (28.5, -88.5)
COORDS_NORTH_SEA = (57.0, 3.5)
COORDS_ARCTIC = (72.0, 15.0)
COORDS_GLOBAL = (-10.0, 100.0)  # Indian Ocean — only global sources


class TestMetoceanCoverageGoM:
    """Coverage rules for Gulf of Mexico coordinates."""

    def setup_method(self):
        self.cov = MetoceanCoverage()

    def test_ndbc_covers_gom(self):
        clients = self.cov.get_clients(*COORDS_GOM)
        assert "ndbc" in clients

    def test_coops_covers_gom(self):
        clients = self.cov.get_clients(*COORDS_GOM)
        assert "coops" in clients

    def test_open_meteo_covers_gom(self):
        clients = self.cov.get_clients(*COORDS_GOM)
        assert "open_meteo" in clients

    def test_erddap_covers_gom(self):
        clients = self.cov.get_clients(*COORDS_GOM)
        assert "erddap" in clients

    def test_met_norway_does_not_cover_gom(self):
        clients = self.cov.get_clients(*COORDS_GOM)
        assert "met_norway" not in clients


class TestMetoceanCoverageNorthSea:
    """Coverage rules for North Sea coordinates."""

    def setup_method(self):
        self.cov = MetoceanCoverage()

    def test_met_norway_covers_north_sea(self):
        clients = self.cov.get_clients(*COORDS_NORTH_SEA)
        assert "met_norway" in clients

    def test_open_meteo_covers_north_sea(self):
        clients = self.cov.get_clients(*COORDS_NORTH_SEA)
        assert "open_meteo" in clients

    def test_erddap_covers_north_sea(self):
        clients = self.cov.get_clients(*COORDS_NORTH_SEA)
        assert "erddap" in clients

    def test_ndbc_does_not_cover_north_sea(self):
        clients = self.cov.get_clients(*COORDS_NORTH_SEA)
        assert "ndbc" not in clients

    def test_coops_does_not_cover_north_sea(self):
        clients = self.cov.get_clients(*COORDS_NORTH_SEA)
        assert "coops" not in clients


class TestMetoceanCoverageGlobal:
    """Global sources always available."""

    def setup_method(self):
        self.cov = MetoceanCoverage()

    def test_open_meteo_covers_indian_ocean(self):
        clients = self.cov.get_clients(*COORDS_GLOBAL)
        assert "open_meteo" in clients

    def test_erddap_covers_indian_ocean(self):
        clients = self.cov.get_clients(*COORDS_GLOBAL)
        assert "erddap" in clients

    def test_no_regional_sources_for_indian_ocean(self):
        clients = self.cov.get_clients(*COORDS_GLOBAL)
        assert "ndbc" not in clients
        assert "coops" not in clients
        assert "met_norway" not in clients


class TestMetoceanCoverageBoundary:
    """Edge-case boundary tests for coverage zones."""

    def setup_method(self):
        self.cov = MetoceanCoverage()

    def test_lat_at_lower_ndbc_boundary(self):
        # lat=15 is the minimum for NDBC/COOPS coverage
        clients = self.cov.get_clients(15.0, -90.0)
        assert "ndbc" in clients

    def test_lat_below_ndbc_boundary(self):
        clients = self.cov.get_clients(14.9, -90.0)
        assert "ndbc" not in clients

    def test_met_norway_lower_boundary(self):
        clients = self.cov.get_clients(55.0, 5.0)
        assert "met_norway" in clients

    def test_met_norway_below_lower_boundary(self):
        clients = self.cov.get_clients(54.9, 5.0)
        assert "met_norway" not in clients

    def test_priority_order_returns_list(self):
        clients = self.cov.get_clients(*COORDS_GOM)
        assert isinstance(clients, list)
        assert len(clients) > 0

    def test_source_priority_measured_before_forecast(self):
        """Measured sources (NDBC, COOPS) should rank before forecast sources."""
        clients = self.cov.get_clients(*COORDS_GOM)
        # NDBC is measured; open_meteo is forecast — ndbc should appear first
        ndbc_idx = clients.index("ndbc")
        om_idx = clients.index("open_meteo")
        assert ndbc_idx < om_idx
