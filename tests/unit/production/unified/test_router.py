"""Tests for RegionRouter."""

import pytest

from worldenergydata.production.unified.adapters.brazil_anp_adapter import (
    BrazilAnpAdapter,
)
from worldenergydata.production.unified.adapters.bsee_adapter import BseeAdapter
from worldenergydata.production.unified.adapters.canada_adapter import CanadaAdapter
from worldenergydata.production.unified.adapters.eia_us_adapter import EiaUsAdapter
from worldenergydata.production.unified.adapters.mexico_cnh_adapter import (
    MexicoCnhAdapter,
)
from worldenergydata.production.unified.adapters.sodir_adapter import SodirAdapter
from worldenergydata.production.unified.adapters.spain_cores_adapter import (
    SpainCoresAdapter,
)
from worldenergydata.production.unified.adapters.texas_rrc_adapter import (
    TexasRrcAdapter,
)
from worldenergydata.production.unified.adapters.ukcs_adapter import UkcsAdapter
from worldenergydata.production.unified.router import RegionRouter


class TestRegionRouter:
    def setup_method(self):
        self.router = RegionRouter()

    def test_list_regions_returns_nine(self):
        regions = self.router.list_regions()
        assert len(regions) == 9

    def test_list_regions_sorted(self):
        regions = self.router.list_regions()
        assert regions == sorted(regions)

    def test_get_adapter_ncs(self):
        adapter = self.router.get_adapter("ncs")
        assert isinstance(adapter, SodirAdapter)

    def test_get_adapter_gom(self):
        adapter = self.router.get_adapter("gom")
        assert isinstance(adapter, BseeAdapter)

    def test_get_adapter_brazil(self):
        adapter = self.router.get_adapter("brazil")
        assert isinstance(adapter, BrazilAnpAdapter)

    def test_get_adapter_ukcs(self):
        adapter = self.router.get_adapter("ukcs")
        assert isinstance(adapter, UkcsAdapter)

    def test_get_adapter_spain(self):
        adapter = self.router.get_adapter("spain")
        assert isinstance(adapter, SpainCoresAdapter)

    def test_get_adapter_eia_us(self):
        adapter = self.router.get_adapter("eia_us")
        assert isinstance(adapter, EiaUsAdapter)

    def test_get_adapter_mexico(self):
        adapter = self.router.get_adapter("mexico")
        assert isinstance(adapter, MexicoCnhAdapter)

    def test_get_adapter_texas(self):
        adapter = self.router.get_adapter("texas")
        assert isinstance(adapter, TexasRrcAdapter)

    def test_get_adapter_canada(self):
        adapter = self.router.get_adapter("canada")
        assert isinstance(adapter, CanadaAdapter)

    def test_alias_norway_resolves_to_ncs(self):
        adapter = self.router.get_adapter("norway")
        assert isinstance(adapter, SodirAdapter)

    def test_alias_bsee_resolves_to_gom(self):
        adapter = self.router.get_adapter("bsee")
        assert isinstance(adapter, BseeAdapter)

    def test_alias_uk_resolves_to_ukcs(self):
        adapter = self.router.get_adapter("uk")
        assert isinstance(adapter, UkcsAdapter)

    def test_alias_cores_resolves_to_spain(self):
        adapter = self.router.get_adapter("cores")
        assert isinstance(adapter, SpainCoresAdapter)

    def test_unknown_region_raises_key_error(self):
        with pytest.raises(KeyError, match="Unknown region"):
            self.router.get_adapter("atlantis_basin")

    def test_resolve_regions_deduplicates(self):
        resolved = self.router.resolve_regions(["ncs", "norway", "gom"])
        assert resolved.count("ncs") == 1
        assert "gom" in resolved

    def test_resolve_regions_case_insensitive(self):
        resolved = self.router.resolve_regions(["NCS", "GOM"])
        assert "ncs" in resolved
        assert "gom" in resolved
