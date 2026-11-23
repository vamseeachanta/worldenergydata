"""Tests for common catalog data models."""

import json
import tempfile
from pathlib import Path

import yaml

from worldenergydata.common.catalog import (
    DataCatalog,
    DatasetEntry,
    ModuleCatalogEntry,
)


class TestDatasetEntry:
    def test_basic(self):
        entry = DatasetEntry(
            name="production",
            path="data/production.csv",
            format="csv",
            domain="production",
            size_bytes=1024,
        )
        assert entry.name == "production"
        assert entry.size_bytes == 1024

    def test_defaults(self):
        entry = DatasetEntry(
            name="test", path="p", format="csv", domain="d", size_bytes=0
        )
        assert entry.row_count is None
        assert entry.columns is None
        assert entry.update_frequency is None
        assert entry.source_url is None
        assert entry.last_modified is None
        assert entry.description is None
        assert entry.last_refreshed is None
        assert entry.is_lfs_stub is False
        assert entry.data_status == "unknown"

    def test_with_all_fields(self):
        entry = DatasetEntry(
            name="wells",
            path="data/wells.parquet",
            format="parquet",
            domain="drilling",
            size_bytes=5000000,
            row_count=10000,
            columns=["api", "lat", "lon"],
            update_frequency="monthly",
            source_url="https://example.com/wells",
            last_modified="2024-01-01T00:00:00",
            description="Well locations",
            last_refreshed="2024-01-15T00:00:00",
            is_lfs_stub=True,
            data_status="lfs_stub",
        )
        assert entry.row_count == 10000
        assert len(entry.columns) == 3
        assert entry.is_lfs_stub is True


class TestModuleCatalogEntry:
    def test_basic(self):
        mod = ModuleCatalogEntry(
            name="bsee",
            description="BSEE data module",
            path="src/worldenergydata/bsee",
        )
        assert mod.name == "bsee"
        assert mod.datasets == []
        assert mod.binary_stores == []

    def test_total_size_bytes(self):
        ds1 = DatasetEntry(
            name="a", path="a.csv", format="csv", domain="d", size_bytes=100
        )
        ds2 = DatasetEntry(
            name="b", path="b.csv", format="csv", domain="d", size_bytes=200
        )
        bin1 = DatasetEntry(
            name="c", path="c.zip", format="zip", domain="d", size_bytes=500
        )
        mod = ModuleCatalogEntry(
            name="test",
            description="Test",
            path="test/",
            datasets=[ds1, ds2],
            binary_stores=[bin1],
        )
        assert mod.total_size_bytes == 800

    def test_dataset_count(self):
        ds = DatasetEntry(
            name="a", path="a.csv", format="csv", domain="d", size_bytes=100
        )
        bin1 = DatasetEntry(
            name="b", path="b.zip", format="zip", domain="d", size_bytes=100
        )
        mod = ModuleCatalogEntry(
            name="test",
            description="Test",
            path="test/",
            datasets=[ds],
            binary_stores=[bin1],
        )
        assert mod.dataset_count == 2

    def test_empty_module(self):
        mod = ModuleCatalogEntry(name="empty", description="Empty", path="empty/")
        assert mod.total_size_bytes == 0
        assert mod.dataset_count == 0


class TestDataCatalog:
    def test_default(self):
        cat = DataCatalog()
        assert cat.version == "1.1.0"
        assert cat.generated_at != ""
        assert cat.modules == {}

    def test_total_modules(self):
        cat = DataCatalog()
        cat.modules["bsee"] = ModuleCatalogEntry(
            name="bsee", description="BSEE", path="bsee/"
        )
        cat.modules["sodir"] = ModuleCatalogEntry(
            name="sodir", description="SODIR", path="sodir/"
        )
        assert cat.total_modules == 2

    def test_total_datasets(self):
        ds = DatasetEntry(
            name="a", path="a.csv", format="csv", domain="d", size_bytes=100
        )
        mod = ModuleCatalogEntry(
            name="bsee", description="BSEE", path="bsee/", datasets=[ds]
        )
        cat = DataCatalog()
        cat.modules["bsee"] = mod
        assert cat.total_datasets == 1

    def test_total_size_bytes(self):
        ds = DatasetEntry(
            name="a", path="a.csv", format="csv", domain="d", size_bytes=500
        )
        mod = ModuleCatalogEntry(
            name="test", description="Test", path="t/", datasets=[ds]
        )
        cat = DataCatalog()
        cat.modules["test"] = mod
        assert cat.total_size_bytes == 500

    def test_to_dict(self):
        ds = DatasetEntry(
            name="prod",
            path="p.csv",
            format="csv",
            domain="production",
            size_bytes=1024,
        )
        mod = ModuleCatalogEntry(
            name="bsee",
            description="BSEE data",
            path="bsee/",
            datasets=[ds],
        )
        cat = DataCatalog(version="1.0.0")
        cat.modules["bsee"] = mod

        d = cat.to_dict()
        assert d["version"] == "1.0.0"
        assert d["total_modules"] == 1
        assert d["total_datasets"] == 1
        assert d["total_size_bytes"] == 1024
        assert "bsee" in d["modules"]

    def test_to_yaml(self):
        ds = DatasetEntry(
            name="test",
            path="t.csv",
            format="csv",
            domain="test",
            size_bytes=100,
        )
        mod = ModuleCatalogEntry(
            name="test", description="Test", path="t/", datasets=[ds]
        )
        cat = DataCatalog()
        cat.modules["test"] = mod

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "catalog.yaml"
            cat.to_yaml(path)
            assert path.exists()

            with open(path) as f:
                loaded = yaml.safe_load(f)
            assert loaded["total_modules"] == 1

    def test_to_json(self):
        ds = DatasetEntry(
            name="test",
            path="t.csv",
            format="csv",
            domain="test",
            size_bytes=100,
        )
        mod = ModuleCatalogEntry(
            name="test", description="Test", path="t/", datasets=[ds]
        )
        cat = DataCatalog()
        cat.modules["test"] = mod

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "catalog.json"
            cat.to_json(path)
            assert path.exists()

            with open(path) as f:
                loaded = json.load(f)
            assert loaded["total_modules"] == 1

    def test_generated_at_auto_set(self):
        cat = DataCatalog()
        assert len(cat.generated_at) > 10  # ISO format is > 10 chars

    def test_generated_at_preserves_explicit(self):
        cat = DataCatalog(generated_at="2024-01-01T00:00:00Z")
        assert cat.generated_at == "2024-01-01T00:00:00Z"
