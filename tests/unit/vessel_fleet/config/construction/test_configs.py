"""Tests for construction vessel fleet configs."""

import pytest


@pytest.fixture(
    params=[
        "allseas",
        "boskalis",
        "deme",
        "eneti",
        "heerema",
        "mcdermott",
        "oht",
        "saipem_vessels",
        "subsea7",
        "van_oord",
    ]
)
def config_module(request):
    """Load each construction config module."""
    import importlib

    mod = importlib.import_module(
        f"worldenergydata.vessel_fleet.config.construction.{request.param}"
    )
    return mod, request.param


class TestConstructionConfigs:
    def test_has_config(self, config_module):
        mod, name = config_module
        assert hasattr(mod, "CONFIG"), f"{name} missing CONFIG"

    def test_config_has_name(self, config_module):
        mod, name = config_module
        assert mod.CONFIG.name, f"{name} CONFIG.name is empty"

    def test_config_has_fleet_url(self, config_module):
        mod, name = config_module
        assert mod.CONFIG.fleet_url.startswith("http"), f"{name} bad URL"

    def test_config_vessel_category(self, config_module):
        mod, name = config_module
        assert mod.CONFIG.vessel_category == "construction_vessel"

    def test_has_known_vessels(self, config_module):
        mod, name = config_module
        assert hasattr(mod, "KNOWN_VESSELS"), f"{name} missing KNOWN_VESSELS"
        assert isinstance(mod.KNOWN_VESSELS, list)
        assert len(mod.KNOWN_VESSELS) >= 1

    def test_known_vessels_have_name(self, config_module):
        mod, name = config_module
        for v in mod.KNOWN_VESSELS:
            assert "VESSEL_NAME" in v, f"{name}: vessel missing VESSEL_NAME"
            assert v["VESSEL_NAME"], f"{name}: empty VESSEL_NAME"

    def test_field_mapping_has_vessel_name(self, config_module):
        mod, name = config_module
        values = mod.CONFIG.field_mapping.values()
        assert (
            "VESSEL_NAME" in values
        ), f"{name}: field_mapping missing VESSEL_NAME target"
