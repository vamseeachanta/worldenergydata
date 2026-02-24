"""Tests for hull data loader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.vessel_hull_models.rig_hulls.hull_loader import HullDataLoader


@pytest.fixture
def sample_fleet(tmp_path):
    """Create a minimal curated fleet parquet for testing."""
    data = {
        "VESSEL_NAME": ["DEEPWATER TITAN", "OCEAN STAR", "VALARIS 105", "H&P 100"],
        "RIG_NAME": ["DEEPWATER TITAN", "OCEAN STAR", "VALARIS 105", "H&P 100"],
        "RIG_TYPE": ["drillship", "semi_submersible", "jack_up", "platform_rig"],
        "HULL_FORM_TYPE": [None, None, None, None],
        "LOA_M": [238.0, None, None, None],
        "BEAM_M": [42.0, None, None, None],
        "DRAFT_M": [12.0, None, None, None],
        "WATER_DEPTH_RATING_FT": [12000.0, 7000.0, 400.0, None],
        "DATA_SOURCE": ["xls_historical", "bsee_war", "bsee_war", "bsee_war"],
    }
    df = pd.DataFrame(data)
    pq_path = tmp_path / "drilling_rigs.parquet"
    df.to_parquet(pq_path)
    return tmp_path


class TestHullDataLoader:
    def test_load_enriches_hull_forms(self, sample_fleet):
        loader = HullDataLoader(data_dir=sample_fleet)
        summary = loader.hull_form_summary()
        assert summary.get("drillship") == 1
        assert summary.get("semi_sub") == 1
        assert summary.get("jackup") == 1

    def test_get_by_name(self, sample_fleet):
        loader = HullDataLoader(data_dir=sample_fleet)
        record = loader.get_by_name("DEEPWATER TITAN")
        assert record is not None
        assert record["HULL_FORM_TYPE"] == "drillship"
        assert record["LOA_M"] == 238.0

    def test_get_by_name_case_insensitive(self, sample_fleet):
        loader = HullDataLoader(data_dir=sample_fleet)
        record = loader.get_by_name("deepwater titan")
        assert record is not None

    def test_get_by_name_not_found(self, sample_fleet):
        loader = HullDataLoader(data_dir=sample_fleet)
        assert loader.get_by_name("NONEXISTENT") is None

    def test_get_by_hull_form(self, sample_fleet):
        loader = HullDataLoader(data_dir=sample_fleet)
        drillships = loader.get_by_hull_form("drillship")
        assert len(drillships) == 1

    def test_get_by_rig_type(self, sample_fleet):
        loader = HullDataLoader(data_dir=sample_fleet)
        jackups = loader.get_by_rig_type("jack_up")
        assert len(jackups) == 1
        assert jackups.iloc[0]["HULL_FORM_TYPE"] == "jackup"

    def test_dimension_coverage(self, sample_fleet):
        loader = HullDataLoader(data_dir=sample_fleet)
        coverage = loader.dimension_coverage()
        assert "drillship" in coverage
        assert coverage["drillship"]["total"] == 1
        assert coverage["drillship"]["measured"] == 1

    def test_estimated_dimensions_filled(self, sample_fleet):
        loader = HullDataLoader(data_dir=sample_fleet)
        record = loader.get_by_name("OCEAN STAR")
        assert record is not None
        # Semi-sub with 7000 ft water depth -> should get estimated dims
        assert record["LOA_M"] is not None
        assert record["DIMENSION_CONFIDENCE"] in ("estimated", "generic")

    def test_platform_rig_no_hull_form(self, sample_fleet):
        loader = HullDataLoader(data_dir=sample_fleet)
        record = loader.get_by_name("H&P 100")
        assert record is not None
        # Platform rigs have no hull form
        assert pd.isna(record["HULL_FORM_TYPE"]) or record["HULL_FORM_TYPE"] is None

    def test_missing_data_dir(self, tmp_path):
        loader = HullDataLoader(data_dir=tmp_path / "nonexistent")
        assert loader.hull_form_summary() == {}

    def test_caches_on_second_load(self, sample_fleet):
        loader = HullDataLoader(data_dir=sample_fleet)
        loader.hull_form_summary()  # first load
        loader.hull_form_summary()  # should use cache
        assert loader._df is not None
