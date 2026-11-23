"""Tests for BSEE CLI infrastructure data type extensions."""

from worldenergydata.cli.commands.bsee import DataType


class TestDataTypeEnum:
    def test_infrastructure_types_exist(self):
        assert DataType.platform == "platform"
        assert DataType.pipeline_permit == "pipeline_permit"
        assert DataType.deepwater_structure == "deepwater_structure"
        assert DataType.pipeline_location == "pipeline_location"
        assert DataType.infrastructure == "infrastructure"

    def test_all_type_still_exists(self):
        assert DataType.all == "all"

    def test_original_types_preserved(self):
        assert DataType.well == "well"
        assert DataType.production == "production"
        assert DataType.block == "block"
        assert DataType.lease == "lease"


class TestRefreshConfigBuilding:
    def _build_refresh_config(self, data_type: DataType) -> dict:
        """Simulate the config building logic from the refresh command."""
        infrastructure_types = [
            DataType.platform,
            DataType.pipeline_permit,
            DataType.deepwater_structure,
            DataType.pipeline_location,
            DataType.infrastructure,
            DataType.all,
        ]

        cfg = {
            "basename": "bsee",
            "data": {
                "refresh": True,
                "apm": data_type in [DataType.well, DataType.all],
                "production": data_type in [DataType.production, DataType.all],
                "platform": data_type
                in [DataType.platform, DataType.infrastructure, DataType.all],
                "pipeline_permit": data_type
                in [DataType.pipeline_permit, DataType.infrastructure, DataType.all],
                "deepwater_structure": data_type
                in [
                    DataType.deepwater_structure,
                    DataType.infrastructure,
                    DataType.all,
                ],
                "pipeline_location": data_type
                in [DataType.pipeline_location, DataType.infrastructure, DataType.all],
            },
            "meta": {
                "mode": "enhanced" if data_type in infrastructure_types else "legacy",
            },
        }
        return cfg

    def test_platform_type_sets_platform_flag(self):
        cfg = self._build_refresh_config(DataType.platform)
        assert cfg["data"]["platform"] is True
        assert cfg["data"]["pipeline_permit"] is False
        assert cfg["meta"]["mode"] == "enhanced"

    def test_infrastructure_sets_all_four_flags(self):
        cfg = self._build_refresh_config(DataType.infrastructure)
        assert cfg["data"]["platform"] is True
        assert cfg["data"]["pipeline_permit"] is True
        assert cfg["data"]["deepwater_structure"] is True
        assert cfg["data"]["pipeline_location"] is True
        assert cfg["meta"]["mode"] == "enhanced"

    def test_all_type_includes_infrastructure(self):
        cfg = self._build_refresh_config(DataType.all)
        assert cfg["data"]["apm"] is True
        assert cfg["data"]["production"] is True
        assert cfg["data"]["platform"] is True
        assert cfg["data"]["pipeline_permit"] is True
        assert cfg["data"]["deepwater_structure"] is True
        assert cfg["data"]["pipeline_location"] is True

    def test_well_type_uses_legacy_mode(self):
        cfg = self._build_refresh_config(DataType.well)
        assert cfg["meta"]["mode"] == "legacy"
        assert cfg["data"]["platform"] is False

    def test_production_type_uses_legacy_mode(self):
        cfg = self._build_refresh_config(DataType.production)
        assert cfg["meta"]["mode"] == "legacy"
