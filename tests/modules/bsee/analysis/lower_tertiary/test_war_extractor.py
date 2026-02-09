"""Tests for the Lower Tertiary WAR extractor.

Uses real WAR data from the eWellWARRawData.zip archive.
Tests are skipped if the zip is not available locally.
"""

from __future__ import annotations

import pytest
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Fixtures (module-scoped for performance -- WAR zip is ~363K rows)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def project_root() -> Path:
    """Resolve project root from test file location."""
    return Path(__file__).resolve().parent.parent.parent.parent.parent.parent


@pytest.fixture(scope="module")
def config(project_root: Path):
    """Load the Lower Tertiary YAML config."""
    from worldenergydata.bsee.analysis.lower_tertiary.config import LTConfig

    yaml_path = project_root / "config" / "input" / "world_oil_lower_tertiary.yaml"
    if not yaml_path.exists():
        pytest.skip("YAML config not available")
    return LTConfig(yaml_path)


@pytest.fixture(scope="module")
def war_extractor(project_root: Path, config):
    """Instantiate the WAR extractor with real data."""
    from worldenergydata.bsee.analysis.lower_tertiary.war_extractor import (
        LTWarExtractor,
    )

    war_zip = project_root / config.data_paths["war_zip"]
    if not war_zip.exists():
        pytest.skip("WAR zip not available locally")
    return LTWarExtractor(war_zip, config)


# ---------------------------------------------------------------------------
# Tests: extract_field
# ---------------------------------------------------------------------------


class TestExtractField:
    """Verify single-field extraction by area code and block number."""

    def test_extract_tiber_has_records(self, war_extractor) -> None:
        """Tiber (KC-102) is a known LT discovery with ~38 WAR records."""
        df = war_extractor.extract_field("Tiber")

        assert isinstance(df, pd.DataFrame)
        assert not df.empty, "Tiber should have WAR records"
        assert len(df) >= 20, (
            f"Expected at least 20 Tiber records, got {len(df)}"
        )
        # All rows should be KC area
        assert (df["BOTM_AREA_CODE"] == "KC").all()

    def test_extract_field_julia(self, war_extractor) -> None:
        """Julia (WR-540, 584, 627) should have records."""
        df = war_extractor.extract_field("Julia")

        assert isinstance(df, pd.DataFrame)
        assert not df.empty, "Julia should have WAR records"
        assert (df["BOTM_AREA_CODE"] == "WR").all()
        # Blocks should be within the Julia set
        valid_blocks = {"540", "584", "627"}
        actual_blocks = set(df["BOTM_BLOCK_NUM"].unique())
        assert actual_blocks.issubset(valid_blocks), (
            f"Unexpected blocks: {actual_blocks - valid_blocks}"
        )

    def test_extract_unknown_field_raises(self, war_extractor) -> None:
        """Requesting an unknown field should raise KeyError."""
        with pytest.raises(KeyError, match="Unknown field"):
            war_extractor.extract_field("NonexistentField")


# ---------------------------------------------------------------------------
# Tests: extract_all_fields
# ---------------------------------------------------------------------------


class TestExtractAllFields:
    """Verify bulk extraction across all configured fields."""

    def test_extract_all_fields_returns_dict(self, war_extractor) -> None:
        """Returns a dict mapping field names to DataFrames."""
        result = war_extractor.extract_all_fields()

        assert isinstance(result, dict)
        assert len(result) > 0, "Should have at least one field with data"
        for name, df in result.items():
            assert isinstance(name, str)
            assert isinstance(df, pd.DataFrame)
            assert not df.empty

    def test_extract_all_includes_known_fields(self, war_extractor) -> None:
        """Known producing fields should appear in results."""
        result = war_extractor.extract_all_fields()
        # These are mature fields that definitely have WAR records
        expected_present = {"Tiber", "Julia"}
        actual_keys = set(result.keys())
        missing = expected_present - actual_keys
        assert not missing, f"Expected fields missing from results: {missing}"


# ---------------------------------------------------------------------------
# Tests: drilling_activity_by_year
# ---------------------------------------------------------------------------


class TestDrillingActivityByYear:
    """Verify the year-aggregated drilling activity output."""

    def test_drilling_activity_by_year_shape(self, war_extractor) -> None:
        """Returns a DataFrame with field, year, and records columns."""
        df = war_extractor.drilling_activity_by_year()

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "field" in df.columns
        assert "year" in df.columns
        assert "records" in df.columns

    def test_drilling_activity_years_are_plausible(self, war_extractor) -> None:
        """Years should be within the WAR data range (1988-2026)."""
        df = war_extractor.drilling_activity_by_year()
        valid_years = df["year"].dropna()

        assert (valid_years >= 1988).all(), "Years before 1988 are unexpected"
        assert (valid_years <= 2030).all(), "Years after 2030 are unexpected"

    def test_drilling_activity_records_positive(self, war_extractor) -> None:
        """Record counts should all be positive integers."""
        df = war_extractor.drilling_activity_by_year()

        assert (df["records"] > 0).all()


# ---------------------------------------------------------------------------
# Tests: rig_utilization
# ---------------------------------------------------------------------------


class TestRigUtilization:
    """Verify rig utilization aggregation."""

    def test_rig_utilization_shape(self, war_extractor) -> None:
        """Returns a DataFrame with rig_name, field, and records columns."""
        df = war_extractor.rig_utilization()

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "rig_name" in df.columns
        assert "field" in df.columns
        assert "records" in df.columns

    def test_rig_utilization_has_named_rigs(self, war_extractor) -> None:
        """Rig names should be non-empty strings."""
        df = war_extractor.rig_utilization()
        rig_names = df["rig_name"].dropna().unique()

        assert len(rig_names) > 0, "Should have at least one named rig"
        for name in rig_names:
            assert isinstance(name, str)
            assert len(name.strip()) > 0, "Rig name should not be blank"


# ---------------------------------------------------------------------------
# Tests: subsea_vs_drytree_activity
# ---------------------------------------------------------------------------


class TestSubseaVsDryTreeActivity:
    """Verify the subsea/dry-tree grouping."""

    def test_subsea_vs_drytree_returns_dict_with_keys(
        self, war_extractor
    ) -> None:
        """Returns a dict with 'subsea' and 'dry_tree' keys."""
        result = war_extractor.subsea_vs_drytree_activity()

        assert isinstance(result, dict)
        assert "subsea" in result
        assert "dry_tree" in result
        assert isinstance(result["subsea"], pd.DataFrame)
        assert isinstance(result["dry_tree"], pd.DataFrame)

    def test_subsea_has_field_column(self, war_extractor) -> None:
        """Subsea DataFrame should have a 'field' column for grouping."""
        result = war_extractor.subsea_vs_drytree_activity()
        subsea = result["subsea"]

        if not subsea.empty:
            assert "field" in subsea.columns
            # Fields should be from the subsea config section
            subsea_field_names = set(subsea["field"].unique())
            assert len(subsea_field_names) > 0

    def test_dry_tree_has_field_column(self, war_extractor) -> None:
        """Dry-tree DataFrame should have a 'field' column for grouping."""
        result = war_extractor.subsea_vs_drytree_activity()
        dry_tree = result["dry_tree"]

        if not dry_tree.empty:
            assert "field" in dry_tree.columns
            dry_tree_field_names = set(dry_tree["field"].unique())
            assert len(dry_tree_field_names) > 0
