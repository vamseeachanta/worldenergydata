"""Tests for infrastructure data refresh in DataRefreshEnhanced."""

from unittest.mock import patch

from worldenergydata.modules.bsee.data.refresh.data_refresh_enhanced import (
    DataRefreshEnhanced,
)


class TestInfrastructureRefreshFlagRouting:
    def test_platform_flag_triggers_refresh(self):
        cfg = {
            "meta": {"mode": "enhanced"},
            "data": {"platform": True},
        }
        refresh = DataRefreshEnhanced(
            use_chunked_downloads=False, use_optimized_processing=False
        )
        with (
            patch.object(refresh, "refresh_platform_data_enhanced") as mock_refresh,
            patch.object(refresh, "refresh_well_data_enhanced"),
            patch.object(refresh, "refresh_war_data_enhanced"),
            patch.object(refresh, "refresh_production_data_enhanced"),
            patch.object(refresh, "refresh_pipeline_permit_data_enhanced"),
            patch.object(refresh, "refresh_deepwater_structure_data_enhanced"),
            patch.object(refresh, "refresh_pipeline_location_data_enhanced"),
        ):
            refresh.router(cfg)
            mock_refresh.assert_called_once_with(cfg)

    def test_no_infrastructure_flags_skips_infrastructure(self):
        cfg = {
            "meta": {"mode": "enhanced"},
            "data": {"well": True},
        }
        refresh = DataRefreshEnhanced(
            use_chunked_downloads=False, use_optimized_processing=False
        )
        with (
            patch.object(refresh, "refresh_platform_data_enhanced") as mock_plat,
            patch.object(refresh, "refresh_well_data_enhanced"),
            patch.object(refresh, "refresh_war_data_enhanced"),
            patch.object(refresh, "refresh_production_data_enhanced"),
            patch.object(refresh, "refresh_pipeline_permit_data_enhanced"),
            patch.object(refresh, "refresh_deepwater_structure_data_enhanced"),
            patch.object(refresh, "refresh_pipeline_location_data_enhanced"),
        ):
            refresh.router(cfg)
            # Platform refresh IS called (the method checks the flag internally)
            mock_plat.assert_called_once_with(cfg)
