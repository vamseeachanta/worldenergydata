"""Tests for RigFleetRouter - TDD Red phase.

Tests cover:
- Router skips when rig fleet not requested in config
- Router returns loader and data when rig fleet is requested
"""

from __future__ import annotations

from worldenergydata.bsee.data.loaders.rig_fleet.router import (
    RigFleetRouter,
)


class TestRigFleetRouter:
    """Tests for rig fleet data routing."""

    def test_router_skips_when_not_requested(self):
        """Config without rig_fleet flag returns empty dict."""
        router = RigFleetRouter()
        cfg = {"data": {"well": True, "production": True}}
        result_cfg, result_data = router.router(cfg)

        assert result_cfg is cfg
        assert result_data == {}

    def test_router_returns_loader_when_requested(self, tmp_path):
        """Config with data.rig_fleet=True returns loader in result dict."""
        router = RigFleetRouter()
        # Point loader at empty dir so _load_data returns None
        router.rig_fleet_loader._bin_dir = str(tmp_path)

        cfg = {"data": {"rig_fleet": True}}
        result_cfg, result_data = router.router(cfg)

        assert result_cfg is cfg
        assert "rig_fleet_loader" in result_data
        assert result_data["rig_fleet_loader"] is router.rig_fleet_loader
        # Data is None because no bin files exist
        assert result_data["rig_fleet_data"] is None

    def test_router_with_empty_data_section(self):
        """Config with empty data section returns empty dict."""
        router = RigFleetRouter()
        cfg = {"data": {}}
        result_cfg, result_data = router.router(cfg)

        assert result_data == {}

    def test_router_with_no_data_section(self):
        """Config without data key returns empty dict."""
        router = RigFleetRouter()
        cfg = {"parameters": {"some_key": "value"}}
        result_cfg, result_data = router.router(cfg)

        assert result_data == {}
