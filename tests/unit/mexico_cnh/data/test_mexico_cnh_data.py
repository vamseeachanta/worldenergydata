"""Tests for MexicoCNHData init, router, and helper methods."""

import pytest

from worldenergydata.mexico_cnh.data.mexico_cnh_data import MexicoCNHData


class TestMexicoCNHDataInit:
    def test_default(self):
        cnh = MexicoCNHData()
        assert cnh.scraper is None
        assert cnh.cache_dir is None


class TestCollectDataType:
    def test_production(self):
        cnh = MexicoCNHData()
        result = cnh._collect_data_type("production", {})
        assert result == []

    def test_wells(self):
        cnh = MexicoCNHData()
        result = cnh._collect_data_type("wells", {})
        assert result == []

    def test_fields(self):
        cnh = MexicoCNHData()
        result = cnh._collect_data_type("fields", {})
        assert result == []

    def test_reserves(self):
        cnh = MexicoCNHData()
        result = cnh._collect_data_type("reserves", {})
        assert result == []

    def test_contracts(self):
        cnh = MexicoCNHData()
        result = cnh._collect_data_type("contracts", {})
        assert result == []

    def test_operators(self):
        cnh = MexicoCNHData()
        result = cnh._collect_data_type("operators", {})
        assert result == []

    def test_exploration(self):
        cnh = MexicoCNHData()
        result = cnh._collect_data_type("exploration", {})
        assert result == []

    def test_unknown_type(self):
        cnh = MexicoCNHData()
        result = cnh._collect_data_type("unknown_type", {})
        assert result is None


class TestRouter:
    def test_empty_data_types(self):
        cnh = MexicoCNHData()
        cfg, data = cnh.router({"data_types": []})
        assert data == {}

    def test_single_type(self):
        cnh = MexicoCNHData()
        cfg, data = cnh.router({"data_types": ["production"]})
        assert "production" in data

    def test_multiple_types(self):
        cnh = MexicoCNHData()
        cfg, data = cnh.router({"data_types": ["production", "wells", "fields"]})
        assert len(data) == 3

    def test_cache_dir_created(self, tmp_path):
        cnh = MexicoCNHData()
        cache_dir = str(tmp_path / "cache")
        cfg, data = cnh.router({
            "data_types": [],
            "cache": {"enabled": True, "directory": cache_dir},
        })
        assert cnh.cache_dir is not None


class TestClose:
    def test_close_no_scraper(self):
        cnh = MexicoCNHData()
        cnh.close()
        assert cnh.scraper is None
