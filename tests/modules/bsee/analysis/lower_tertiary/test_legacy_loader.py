"""Tests for legacy production CSV loader.

Run with:
    PYTHONPATH=src /usr/bin/python3 -m pytest \
        tests/modules/bsee/analysis/lower_tertiary/test_legacy_loader.py -v \
        --override-ini="addopts=-v --tb=short" \
        -W "default::pytest.PytestRemovedIn9Warning"
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture(scope="module")
def project_root() -> Path:
    """Resolve project root from test file location."""
    return Path(__file__).resolve().parent.parent.parent.parent.parent.parent


@pytest.fixture(scope="module")
def config(project_root: Path):
    """Load LTConfig from the canonical YAML file."""
    from worldenergydata.bsee.analysis.lower_tertiary.config import LTConfig

    yaml_path = project_root / "config" / "input" / "world_oil_lower_tertiary.yaml"
    return LTConfig(yaml_path)


@pytest.fixture(scope="module")
def loader(project_root: Path, config):
    """Create a LegacyProductionLoader pointed at the real legacy CSV directory."""
    from worldenergydata.bsee.analysis.lower_tertiary.legacy_loader import (
        LegacyProductionLoader,
    )

    return LegacyProductionLoader(config, project_root)


# ── Available fields ─────────────────────────────────────────────────


class TestAvailableFields:
    """Verify discovery of legacy field keys from config."""

    def test_returns_list(self, loader) -> None:
        fields = loader.available_fields()
        assert isinstance(fields, list)

    def test_has_three_fields(self, loader) -> None:
        assert len(loader.available_fields()) == 3

    def test_contains_julia(self, loader) -> None:
        assert "julia" in loader.available_fields()

    def test_contains_stmalo(self, loader) -> None:
        assert "stmalo" in loader.available_fields()

    def test_contains_stones(self, loader) -> None:
        assert "stones" in loader.available_fields()


# ── Production rate (wide -> long) ───────────────────────────────────


class TestProductionRate:
    """Load wide-format rate CSVs and melt to long format."""

    def test_load_rate_julia_not_empty(self, loader) -> None:
        df = loader.load_production_rate("julia")
        assert not df.empty

    def test_load_rate_julia_has_expected_columns(self, loader) -> None:
        df = loader.load_production_rate("julia")
        assert "date" in df.columns
        assert "api12" in df.columns
        assert "value" in df.columns

    def test_load_rate_julia_date_dtype(self, loader) -> None:
        df = loader.load_production_rate("julia")
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_load_rate_julia_no_nans_in_value(self, loader) -> None:
        df = loader.load_production_rate("julia")
        assert df["value"].notna().all()

    def test_load_rate_unknown_field_raises(self, loader) -> None:
        with pytest.raises(KeyError):
            loader.load_production_rate("nonexistent")

    def test_load_rate_stmalo(self, loader) -> None:
        df = loader.load_production_rate("stmalo")
        assert not df.empty
        assert "date" in df.columns

    def test_load_rate_stones(self, loader) -> None:
        df = loader.load_production_rate("stones")
        assert not df.empty
        assert "date" in df.columns


# ── Cumulative production (wide -> long) ─────────────────────────────


class TestCumulative:
    """Load wide-format cumulative CSVs and melt to long format."""

    def test_load_cumulative_julia_not_empty(self, loader) -> None:
        df = loader.load_cumulative("julia")
        assert not df.empty

    def test_load_cumulative_julia_has_expected_columns(self, loader) -> None:
        df = loader.load_cumulative("julia")
        assert "date" in df.columns
        assert "api12" in df.columns
        assert "value" in df.columns

    def test_load_cumulative_julia_date_dtype(self, loader) -> None:
        df = loader.load_cumulative("julia")
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_load_cumulative_unknown_field_raises(self, loader) -> None:
        with pytest.raises(KeyError):
            loader.load_cumulative("nonexistent")


# ── Summary tables (already long format) ─────────────────────────────


class TestProductionSummary:
    """Load production summary CSVs (already in long/tabular format)."""

    def test_load_prod_summary_julia_not_empty(self, loader) -> None:
        df = loader.load_production_summary("julia")
        assert not df.empty

    def test_load_prod_summary_julia_has_api12(self, loader) -> None:
        df = loader.load_production_summary("julia")
        assert "API12" in df.columns

    def test_load_prod_summary_julia_has_cumulative(self, loader) -> None:
        df = loader.load_production_summary("julia")
        assert "O_CUMMULATIVE_PROD_MMBBL" in df.columns

    def test_load_prod_summary_unknown_raises(self, loader) -> None:
        with pytest.raises(KeyError):
            loader.load_production_summary("nonexistent")


class TestWellSummary:
    """Load well summary CSVs (already in long/tabular format)."""

    def test_load_well_summary_julia_not_empty(self, loader) -> None:
        df = loader.load_well_summary("julia")
        assert not df.empty

    def test_load_well_summary_julia_has_api12(self, loader) -> None:
        df = loader.load_well_summary("julia")
        assert "API12" in df.columns

    def test_load_well_summary_julia_has_water_depth(self, loader) -> None:
        df = loader.load_well_summary("julia")
        assert "Water Depth (feet)" in df.columns

    def test_load_well_summary_unknown_raises(self, loader) -> None:
        with pytest.raises(KeyError):
            loader.load_well_summary("nonexistent")


# ── Field total rate ─────────────────────────────────────────────────


class TestFieldTotalRate:
    """Sum production rates across all wells for a field."""

    def test_field_total_rate_julia_not_empty(self, loader) -> None:
        df = loader.field_total_rate("julia")
        assert not df.empty

    def test_field_total_rate_julia_has_expected_columns(self, loader) -> None:
        df = loader.field_total_rate("julia")
        assert "date" in df.columns
        assert "total_rate" in df.columns

    def test_field_total_rate_julia_positive_max(self, loader) -> None:
        df = loader.field_total_rate("julia")
        assert df["total_rate"].max() > 0

    def test_field_total_rate_julia_date_dtype(self, loader) -> None:
        df = loader.field_total_rate("julia")
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_field_total_rate_julia_no_duplicate_dates(self, loader) -> None:
        df = loader.field_total_rate("julia")
        assert df["date"].is_unique

    def test_field_total_rate_julia_sorted_by_date(self, loader) -> None:
        df = loader.field_total_rate("julia")
        dates = df["date"].tolist()
        assert dates == sorted(dates)

    def test_field_total_rate_unknown_raises(self, loader) -> None:
        with pytest.raises(KeyError):
            loader.field_total_rate("nonexistent")


# ── Cross-field consistency ──────────────────────────────────────────


class TestCrossFieldConsistency:
    """Verify loader works consistently across all three legacy fields."""

    @pytest.mark.parametrize("field", ["julia", "stmalo", "stones"])
    def test_rate_loads_for_all_fields(self, loader, field: str) -> None:
        df = loader.load_production_rate(field)
        assert not df.empty
        assert set(df.columns) == {"date", "api12", "value"}

    @pytest.mark.parametrize("field", ["julia", "stmalo", "stones"])
    def test_cumulative_loads_for_all_fields(self, loader, field: str) -> None:
        df = loader.load_cumulative(field)
        assert not df.empty
        assert set(df.columns) == {"date", "api12", "value"}

    @pytest.mark.parametrize("field", ["julia", "stmalo", "stones"])
    def test_prod_summary_loads_for_all_fields(self, loader, field: str) -> None:
        df = loader.load_production_summary(field)
        assert not df.empty

    @pytest.mark.parametrize("field", ["julia", "stmalo", "stones"])
    def test_well_summary_loads_for_all_fields(self, loader, field: str) -> None:
        df = loader.load_well_summary(field)
        assert not df.empty
