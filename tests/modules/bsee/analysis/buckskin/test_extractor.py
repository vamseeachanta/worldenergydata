"""Tests for BuckskinExtractor — BSEE data extraction for the Buckskin field.

Buckskin spans Keathley Canyon (KC) blocks 785, 828, 829, 830, 871, 872.
The extractor loads pickled .bin files and filters rows to these blocks.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pickle_dataframe(df: pd.DataFrame, path: Path) -> Path:
    """Pickle a DataFrame to *path* and return the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(path)
    return path


def _make_production_df(
    api_numbers: list[str],
    area_codes: list[str],
    block_nums: list[int],
    years: list[int],
    oil: list[float],
    gas: list[float],
    water: list[float],
    lease_numbers: list[str] | None = None,
) -> pd.DataFrame:
    """Build a synthetic production DataFrame."""
    n = len(api_numbers)
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": api_numbers,
            "LEASE_NUMBER": lease_numbers or [f"L{i:04d}" for i in range(n)],
            "BOTM_AREA_CODE": area_codes,
            "BOTM_BLOCK_NUM": block_nums,
            "PROD_YEAR": years,
            "MON_O_PROD_VOL": oil,
            "MON_G_PROD_VOL": gas,
            "MON_WTR_PROD_VOL": water,
        }
    )


def _make_well_df(
    api_numbers: list[str],
    names: list[str],
    area_codes: list[str],
    block_nums: list[int],
    depths: list[float],
    spud_dates: list[str],
    type_codes: list[str],
) -> pd.DataFrame:
    """Build a synthetic well DataFrame."""
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": api_numbers,
            "WELL_NAME": names,
            "BOTM_AREA_CODE": area_codes,
            "BOTM_BLOCK_NUM": block_nums,
            "WATER_DEPTH": depths,
            "WELL_SPUD_DATE": spud_dates,
            "WELL_TYPE_CODE": type_codes,
        }
    )


def _make_war_df(
    api_numbers: list[str],
    rig_names: list[str],
    area_codes: list[str],
    block_nums: list[int],
    start_dates: list[str],
    end_dates: list[str],
    activity_codes: list[str],
) -> pd.DataFrame:
    """Build a synthetic WAR activity DataFrame."""
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": api_numbers,
            "RIG_NAME": rig_names,
            "BOTM_AREA_CODE": area_codes,
            "BOTM_BLOCK_NUM": block_nums,
            "WAR_RPT_START_DT": start_dates,
            "WAR_RPT_END_DT": end_dates,
            "WAR_ACTIVITY_CODE": activity_codes,
        }
    )


def _make_lease_df(
    lease_numbers: list[str],
    area_codes: list[str],
    block_nums: list[int],
    eff_dates: list[str],
) -> pd.DataFrame:
    """Build a synthetic lease DataFrame."""
    return pd.DataFrame(
        {
            "LEASE_NUMBER": lease_numbers,
            "AREA_CODE": area_codes,
            "BLOCK_NUM": block_nums,
            "LEASE_EFF_DATE": eff_dates,
        }
    )


def _make_completions_df(
    api_numbers: list[str],
    comp_dates: list[str],
    status_codes: list[str],
) -> pd.DataFrame:
    """Build a synthetic completions DataFrame."""
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": api_numbers,
            "COMP_DATE": comp_dates,
            "COMP_STATUS_CODE": status_codes,
        }
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Verify BuckskinExtractor class-level constants."""

    def test_constants_blocks(self):
        from worldenergydata.bsee.analysis.buckskin.extractor import (
            BuckskinExtractor,
        )

        assert BuckskinExtractor.BLOCKS == [785, 828, 829, 830, 871, 872]

    def test_constants_area_code(self):
        from worldenergydata.bsee.analysis.buckskin.extractor import (
            BuckskinExtractor,
        )

        assert BuckskinExtractor.AREA_CODE == "KC"


# ---------------------------------------------------------------------------
# Production extraction
# ---------------------------------------------------------------------------


class TestExtractProduction:
    """Tests for extract_production()."""

    def test_extract_production_filters_by_block(self, tmp_path: Path):
        """Only KC rows whose block number is in BLOCKS are returned."""
        from worldenergydata.bsee.analysis.buckskin.extractor import (
            BuckskinExtractor,
        )

        # Arrange -- one matching row (KC 785) and one non-matching (KC 999)
        df = _make_production_df(
            api_numbers=["6080000001", "6080000002"],
            area_codes=["KC", "KC"],
            block_nums=[785, 999],
            years=[2020, 2020],
            oil=[100.0, 200.0],
            gas=[50.0, 60.0],
            water=[10.0, 20.0],
        )
        bin_dir = tmp_path / "bin"
        _pickle_dataframe(df, bin_dir / "production.bin")

        extractor = BuckskinExtractor(bin_dir=bin_dir)

        # Act
        result = extractor.extract_production()

        # Assert
        assert len(result) == 1
        assert result.iloc[0]["BOTM_BLOCK_NUM"] == 785
        assert result.iloc[0]["MON_O_PROD_VOL"] == 100.0

    def test_extract_production_multiple_blocks(self, tmp_path: Path):
        """All six Buckskin blocks are captured when present."""
        from worldenergydata.bsee.analysis.buckskin.extractor import (
            BuckskinExtractor,
        )

        blocks = [785, 828, 829, 830, 871, 872]
        df = _make_production_df(
            api_numbers=[f"608000000{i}" for i in range(6)],
            area_codes=["KC"] * 6,
            block_nums=blocks,
            years=[2020] * 6,
            oil=[100.0] * 6,
            gas=[50.0] * 6,
            water=[10.0] * 6,
        )
        bin_dir = tmp_path / "bin"
        _pickle_dataframe(df, bin_dir / "production.bin")

        extractor = BuckskinExtractor(bin_dir=bin_dir)
        result = extractor.extract_production()

        assert len(result) == 6
        assert sorted(result["BOTM_BLOCK_NUM"].tolist()) == sorted(blocks)

    def test_extract_production_missing_file_returns_empty(self, tmp_path: Path):
        """When the .bin file does not exist, an empty DataFrame is returned."""
        from worldenergydata.bsee.analysis.buckskin.extractor import (
            BuckskinExtractor,
        )

        extractor = BuckskinExtractor(bin_dir=tmp_path / "nonexistent")
        result = extractor.extract_production()

        assert isinstance(result, pd.DataFrame)
        assert result.empty


# ---------------------------------------------------------------------------
# Well extraction
# ---------------------------------------------------------------------------


class TestExtractWells:
    """Tests for extract_wells()."""

    def test_extract_wells_filters_by_block(self, tmp_path: Path):
        """Only KC wells in Buckskin blocks are returned."""
        from worldenergydata.bsee.analysis.buckskin.extractor import (
            BuckskinExtractor,
        )

        df = _make_well_df(
            api_numbers=["6080000001", "6080000002", "6080000003"],
            names=["WELL-A", "WELL-B", "WELL-C"],
            area_codes=["KC", "KC", "GC"],
            block_nums=[829, 500, 829],
            depths=[6800.0, 7000.0, 6500.0],
            spud_dates=["2015-03-01", "2016-06-15", "2017-09-20"],
            type_codes=["D", "D", "E"],
        )
        bin_dir = tmp_path / "bin"
        _pickle_dataframe(df, bin_dir / "wells.bin")

        extractor = BuckskinExtractor(bin_dir=bin_dir)
        result = extractor.extract_wells()

        # Only the first row matches (KC + block 829)
        assert len(result) == 1
        assert result.iloc[0]["API_WELL_NUMBER"] == "6080000001"


# ---------------------------------------------------------------------------
# WAR activity extraction
# ---------------------------------------------------------------------------


class TestExtractWarActivity:
    """Tests for extract_war_activity()."""

    def test_extract_war_activity_from_zip(self, tmp_path: Path):
        """WAR records are filtered by Buckskin blocks after loading."""
        from worldenergydata.bsee.analysis.buckskin.extractor import (
            BuckskinExtractor,
        )

        war_df = _make_war_df(
            api_numbers=["6080000001", "6080000002", "6080000003"],
            rig_names=["RIG-A", "RIG-B", "RIG-C"],
            area_codes=["KC", "KC", "KC"],
            block_nums=[871, 100, 872],
            start_dates=["2020-01-01", "2020-02-01", "2020-03-01"],
            end_dates=["2020-01-15", "2020-02-15", "2020-03-15"],
            activity_codes=["DRILL", "COMPL", "WO"],
        )

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir(parents=True)
        war_zip = tmp_path / "war.zip"

        # Mock the WAR zip loading to return our synthetic DataFrame
        with patch(
            "worldenergydata.bsee.analysis.buckskin.extractor.load_war_from_zip",
            return_value=war_df,
        ):
            extractor = BuckskinExtractor(
                bin_dir=bin_dir, war_zip_path=war_zip
            )
            result = extractor.extract_war_activity()

        # Blocks 871 and 872 match; 100 does not
        assert len(result) == 2
        assert set(result["BOTM_BLOCK_NUM"].tolist()) == {871, 872}


# ---------------------------------------------------------------------------
# Lease extraction
# ---------------------------------------------------------------------------


class TestExtractLeases:
    """Tests for extract_leases()."""

    def test_extract_leases_filters_by_block(self, tmp_path: Path):
        """Only KC leases on Buckskin blocks are returned."""
        from worldenergydata.bsee.analysis.buckskin.extractor import (
            BuckskinExtractor,
        )

        df = _make_lease_df(
            lease_numbers=["G12345", "G12346", "G12347"],
            area_codes=["KC", "KC", "GC"],
            block_nums=[785, 999, 785],
            eff_dates=["2005-01-01", "2006-01-01", "2007-01-01"],
        )
        bin_dir = tmp_path / "bin"
        _pickle_dataframe(df, bin_dir / "leases.bin")

        extractor = BuckskinExtractor(bin_dir=bin_dir)
        result = extractor.extract_leases()

        # First row matches (KC + 785); second is wrong block; third is GC
        assert len(result) == 1
        assert result.iloc[0]["LEASE_NUMBER"] == "G12345"


# ---------------------------------------------------------------------------
# Completions extraction
# ---------------------------------------------------------------------------


class TestExtractCompletions:
    """Tests for extract_completions()."""

    def test_extract_completions_joins_on_api(self, tmp_path: Path):
        """Completions are filtered by API numbers present in the well list."""
        from worldenergydata.bsee.analysis.buckskin.extractor import (
            BuckskinExtractor,
        )

        # Wells -- only API 6080000001 is on a Buckskin block
        wells_df = _make_well_df(
            api_numbers=["6080000001", "6080000002"],
            names=["WELL-A", "WELL-B"],
            area_codes=["KC", "KC"],
            block_nums=[830, 999],
            depths=[6800.0, 7000.0],
            spud_dates=["2015-03-01", "2016-06-15"],
            type_codes=["D", "E"],
        )

        # Completions -- includes records for both APIs
        comp_df = _make_completions_df(
            api_numbers=["6080000001", "6080000002", "6080000001"],
            comp_dates=["2016-01-01", "2017-01-01", "2018-01-01"],
            status_codes=["COM", "COM", "TA"],
        )

        bin_dir = tmp_path / "bin"
        _pickle_dataframe(wells_df, bin_dir / "wells.bin")
        _pickle_dataframe(comp_df, bin_dir / "completions.bin")

        extractor = BuckskinExtractor(bin_dir=bin_dir)
        result = extractor.extract_completions()

        # Only completions for API 6080000001 (the Buckskin well)
        assert len(result) == 2
        assert set(result["API_WELL_NUMBER"].tolist()) == {"6080000001"}


# ---------------------------------------------------------------------------
# extract_all
# ---------------------------------------------------------------------------


class TestExtractAll:
    """Tests for extract_all()."""

    def test_extract_all_returns_dict(self, tmp_path: Path):
        """extract_all() returns a dict with the expected dataset keys."""
        from worldenergydata.bsee.analysis.buckskin.extractor import (
            BuckskinExtractor,
        )

        # Create minimal .bin files so extractions do not error
        bin_dir = tmp_path / "bin"
        _pickle_dataframe(
            _make_production_df(
                ["A"], ["KC"], [785], [2020], [1.0], [1.0], [1.0]
            ),
            bin_dir / "production.bin",
        )
        _pickle_dataframe(
            _make_well_df(
                ["A"], ["W"], ["KC"], [785], [6800.0], ["2015-01-01"], ["D"]
            ),
            bin_dir / "wells.bin",
        )
        _pickle_dataframe(
            _make_lease_df(["G1"], ["KC"], [785], ["2005-01-01"]),
            bin_dir / "leases.bin",
        )
        _pickle_dataframe(
            _make_completions_df(["A"], ["2016-01-01"], ["COM"]),
            bin_dir / "completions.bin",
        )

        extractor = BuckskinExtractor(bin_dir=bin_dir)
        result = extractor.extract_all()

        assert isinstance(result, dict)
        expected_keys = {
            "production",
            "wells",
            "war_activity",
            "leases",
            "completions",
        }
        assert set(result.keys()) == expected_keys
        for key in expected_keys:
            assert isinstance(result[key], pd.DataFrame)


# ---------------------------------------------------------------------------
# Data cleaning
# ---------------------------------------------------------------------------


class TestDataCleaning:
    """Tests for whitespace stripping on load."""

    def test_strip_whitespace_on_load(self, tmp_path: Path):
        """String columns have leading/trailing whitespace stripped."""
        from worldenergydata.bsee.analysis.buckskin.extractor import (
            BuckskinExtractor,
        )

        df = _make_production_df(
            api_numbers=["  6080000001  "],
            area_codes=["  KC  "],
            block_nums=[785],
            years=[2020],
            oil=[100.0],
            gas=[50.0],
            water=[10.0],
        )
        bin_dir = tmp_path / "bin"
        _pickle_dataframe(df, bin_dir / "production.bin")

        extractor = BuckskinExtractor(bin_dir=bin_dir)
        result = extractor.extract_production()

        assert len(result) == 1
        assert result.iloc[0]["API_WELL_NUMBER"] == "6080000001"
        assert result.iloc[0]["BOTM_AREA_CODE"] == "KC"
