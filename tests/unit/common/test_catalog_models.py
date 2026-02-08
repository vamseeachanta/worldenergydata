"""
Tests for worldenergydata.common.catalog module.

Tests cover:
- DatasetEntry creation with all fields and minimal fields
- ModuleCatalogEntry computed properties (total_size, dataset_count)
- ModuleCatalogEntry edge case with empty datasets
- DataCatalog aggregate totals across modules
- DataCatalog serialization to dict, YAML, and JSON
- DataCatalog auto-populates generated_at timestamp
"""

import json
from pathlib import Path

import pytest
import yaml

from worldenergydata.common.catalog import (
    DataCatalog,
    DatasetEntry,
    ModuleCatalogEntry,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_dataset() -> DatasetEntry:
    """A fully-populated dataset entry."""
    return DatasetEntry(
        name="production_monthly",
        path="data/production/monthly.csv",
        format="csv",
        domain="production",
        size_bytes=1_048_576,
        row_count=50_000,
        columns=["date", "well_id", "oil_bbl", "gas_mcf"],
        update_frequency="monthly",
        source_url="https://example.com/data",
        last_modified="2025-01-15T00:00:00Z",
        description="Monthly production data by well",
    )


@pytest.fixture
def minimal_dataset() -> DatasetEntry:
    """A dataset entry with only required fields."""
    return DatasetEntry(
        name="wells",
        path="data/wells.parquet",
        format="parquet",
        domain="infrastructure",
        size_bytes=524_288,
    )


@pytest.fixture
def sample_binary_store() -> DatasetEntry:
    """A binary store entry (e.g. a zip archive)."""
    return DatasetEntry(
        name="historical_archive",
        path="data/binary/archive.zip",
        format="zip",
        domain="production",
        size_bytes=2_097_152,
    )


@pytest.fixture
def sample_module(
    sample_dataset: DatasetEntry,
    minimal_dataset: DatasetEntry,
    sample_binary_store: DatasetEntry,
) -> ModuleCatalogEntry:
    """A module catalog entry with mixed datasets and binary stores."""
    return ModuleCatalogEntry(
        name="production",
        description="Production data module",
        path="src/worldenergydata/production",
        domains=["production", "infrastructure"],
        datasets=[sample_dataset, minimal_dataset],
        binary_stores=[sample_binary_store],
        documentation={"readme": "docs/production.md"},
    )


@pytest.fixture
def sample_catalog(sample_module: ModuleCatalogEntry) -> DataCatalog:
    """A data catalog with one module."""
    catalog = DataCatalog(
        version="1.0.0",
        generated_at="2025-06-01T00:00:00+00:00",
    )
    catalog.modules["production"] = sample_module
    return catalog


# ---------------------------------------------------------------------------
# DatasetEntry Tests
# ---------------------------------------------------------------------------


class TestDatasetEntry:
    """Tests for DatasetEntry dataclass."""

    def test_dataset_entry_creation(self, sample_dataset: DatasetEntry):
        """Create a DatasetEntry with all fields populated."""
        assert sample_dataset.name == "production_monthly"
        assert sample_dataset.path == "data/production/monthly.csv"
        assert sample_dataset.format == "csv"
        assert sample_dataset.domain == "production"
        assert sample_dataset.size_bytes == 1_048_576
        assert sample_dataset.row_count == 50_000
        assert sample_dataset.columns == [
            "date",
            "well_id",
            "oil_bbl",
            "gas_mcf",
        ]
        assert sample_dataset.update_frequency == "monthly"
        assert sample_dataset.source_url == "https://example.com/data"
        assert sample_dataset.last_modified == "2025-01-15T00:00:00Z"
        assert sample_dataset.description == "Monthly production data by well"

    def test_dataset_entry_minimal(self, minimal_dataset: DatasetEntry):
        """Create a DatasetEntry with only required fields; optional fields default to None."""
        assert minimal_dataset.name == "wells"
        assert minimal_dataset.path == "data/wells.parquet"
        assert minimal_dataset.format == "parquet"
        assert minimal_dataset.domain == "infrastructure"
        assert minimal_dataset.size_bytes == 524_288
        assert minimal_dataset.row_count is None
        assert minimal_dataset.columns is None
        assert minimal_dataset.update_frequency is None
        assert minimal_dataset.source_url is None
        assert minimal_dataset.last_modified is None
        assert minimal_dataset.description is None


# ---------------------------------------------------------------------------
# ModuleCatalogEntry Tests
# ---------------------------------------------------------------------------


class TestModuleCatalogEntry:
    """Tests for ModuleCatalogEntry dataclass."""

    def test_module_catalog_entry_total_size(
        self, sample_module: ModuleCatalogEntry
    ):
        """total_size_bytes sums datasets and binary_stores."""
        # sample_dataset: 1_048_576
        # minimal_dataset: 524_288
        # sample_binary_store: 2_097_152
        expected = 1_048_576 + 524_288 + 2_097_152
        assert sample_module.total_size_bytes == expected

    def test_module_catalog_entry_dataset_count(
        self, sample_module: ModuleCatalogEntry
    ):
        """dataset_count is the sum of datasets and binary_stores."""
        # 2 datasets + 1 binary store = 3
        assert sample_module.dataset_count == 3

    def test_module_catalog_entry_empty(self):
        """An empty module has zero total size and zero dataset count."""
        empty_module = ModuleCatalogEntry(
            name="empty",
            description="Empty module",
            path="src/worldenergydata/empty",
        )
        assert empty_module.total_size_bytes == 0
        assert empty_module.dataset_count == 0
        assert empty_module.domains == []
        assert empty_module.datasets == []
        assert empty_module.binary_stores == []
        assert empty_module.documentation == {}


# ---------------------------------------------------------------------------
# DataCatalog Tests
# ---------------------------------------------------------------------------


class TestDataCatalog:
    """Tests for DataCatalog dataclass."""

    def test_data_catalog_totals(self, sample_catalog: DataCatalog):
        """Aggregate totals across all modules."""
        assert sample_catalog.total_modules == 1
        assert sample_catalog.total_datasets == 3
        expected_size = 1_048_576 + 524_288 + 2_097_152
        assert sample_catalog.total_size_bytes == expected_size

    def test_data_catalog_to_dict(self, sample_catalog: DataCatalog):
        """to_dict produces the expected top-level structure."""
        result = sample_catalog.to_dict()

        assert result["version"] == "1.0.0"
        assert result["generated_at"] == "2025-06-01T00:00:00+00:00"
        assert result["total_modules"] == 1
        assert result["total_datasets"] == 3
        assert result["total_size_bytes"] == 1_048_576 + 524_288 + 2_097_152
        assert "production" in result["modules"]

        prod_module = result["modules"]["production"]
        assert prod_module["name"] == "production"
        assert prod_module["description"] == "Production data module"
        assert len(prod_module["datasets"]) == 2
        assert len(prod_module["binary_stores"]) == 1

    def test_data_catalog_to_yaml(
        self, sample_catalog: DataCatalog, tmp_path: Path
    ):
        """to_yaml writes a valid YAML file that round-trips."""
        yaml_path = tmp_path / "catalog" / "data_catalog.yaml"
        sample_catalog.to_yaml(yaml_path)

        assert yaml_path.exists()

        with open(yaml_path) as f:
            loaded = yaml.safe_load(f)

        assert loaded["version"] == "1.0.0"
        assert loaded["total_modules"] == 1
        assert "production" in loaded["modules"]

    def test_data_catalog_to_json(
        self, sample_catalog: DataCatalog, tmp_path: Path
    ):
        """to_json writes a valid JSON file that round-trips."""
        json_path = tmp_path / "catalog" / "data_catalog.json"
        sample_catalog.to_json(json_path)

        assert json_path.exists()

        with open(json_path) as f:
            loaded = json.load(f)

        assert loaded["version"] == "1.0.0"
        assert loaded["total_modules"] == 1
        assert "production" in loaded["modules"]

    def test_data_catalog_generated_at_auto(self):
        """generated_at is auto-populated with an ISO timestamp when left empty."""
        catalog = DataCatalog()
        assert catalog.generated_at != ""
        # Verify it contains a valid ISO-ish timestamp (has 'T' separator)
        assert "T" in catalog.generated_at
