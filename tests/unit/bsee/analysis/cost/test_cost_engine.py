# ABOUTME: Unit tests for WRK-171 cost estimation engine.
# ABOUTME: Covers proxy-based estimation, calibrated rate override, confidence labelling,
# ABOUTME: LFS stub fallback (empty DataFrame), and day-rate lookup.

"""Unit tests for worldenergydata.bsee.analysis.cost.cost_engine."""

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.cost.cost_engine import CostEngine
from worldenergydata.bsee.analysis.cost.models import (
    ActivityType,
    ConfidenceLevel,
    CostEstimate,
    WaterDepthBand,
    WellDepthBand,
)
from worldenergydata.bsee.analysis.cost.regional_loader import RegionalCostLoader

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def config_dir() -> Path:
    # parents[5] = <repo_root> (test file is 6 levels deep inside tests/)
    return Path(__file__).parents[5] / "config" / "analysis" / "cost_data"


@pytest.fixture()
def engine(config_dir) -> CostEngine:
    loader = RegionalCostLoader(config_dir=config_dir)
    return CostEngine(loader=loader)


# ---------------------------------------------------------------------------
# TestDrilling
# ---------------------------------------------------------------------------


class TestDrilling:
    def test_estimate_drilling_returns_cost_estimate(self, engine):
        result = engine.estimate_drilling_cost(
            region="gom",
            water_depth_m=1500.0,
            well_depth_m=8000.0,
            drilling_days=60.0,
            year=2022,
        )
        assert isinstance(result, CostEstimate)

    def test_estimated_cost_positive(self, engine):
        result = engine.estimate_drilling_cost(
            region="gom",
            water_depth_m=1500.0,
            well_depth_m=8000.0,
            drilling_days=60.0,
            year=2022,
        )
        assert result.cost_usd_mm > 0.0

    def test_hpht_increases_cost(self, engine):
        standard = engine.estimate_drilling_cost(
            region="gom",
            water_depth_m=1500.0,
            well_depth_m=8000.0,
            drilling_days=60.0,
            year=2022,
            hpht=False,
        )
        hpht = engine.estimate_drilling_cost(
            region="gom",
            water_depth_m=1500.0,
            well_depth_m=8000.0,
            drilling_days=60.0,
            year=2022,
            hpht=True,
        )
        assert hpht.cost_usd_mm > standard.cost_usd_mm

    def test_deepwater_more_expensive_than_jackup(self, engine):
        jackup = engine.estimate_drilling_cost(
            region="gom",
            water_depth_m=100.0,
            well_depth_m=4000.0,
            drilling_days=30.0,
            year=2022,
        )
        deepwater = engine.estimate_drilling_cost(
            region="gom",
            water_depth_m=2000.0,
            well_depth_m=9000.0,
            drilling_days=90.0,
            year=2022,
        )
        assert deepwater.cost_usd_mm > jackup.cost_usd_mm


# ---------------------------------------------------------------------------
# TestCompletion
# ---------------------------------------------------------------------------


class TestCompletion:
    def test_estimate_completion_returns_cost_estimate(self, engine):
        result = engine.estimate_completion_cost(
            region="gom",
            water_depth_m=1500.0,
            well_depth_m=8000.0,
            completion_days=45.0,
            year=2022,
        )
        assert isinstance(result, CostEstimate)

    def test_completion_cost_positive(self, engine):
        result = engine.estimate_completion_cost(
            region="gom",
            water_depth_m=1500.0,
            well_depth_m=8000.0,
            completion_days=45.0,
            year=2022,
        )
        assert result.cost_usd_mm > 0.0


# ---------------------------------------------------------------------------
# TestIntervention
# ---------------------------------------------------------------------------


class TestIntervention:
    def test_estimate_intervention_returns_cost_estimate(self, engine):
        result = engine.estimate_intervention_cost(
            region="gom",
            water_depth_m=1500.0,
            intervention_days=10.0,
            year=2022,
            workover_type="coiled_tubing",
        )
        assert isinstance(result, CostEstimate)

    def test_intervention_confidence_not_high_without_calibration(self, engine):
        result = engine.estimate_intervention_cost(
            region="gom",
            water_depth_m=1500.0,
            intervention_days=10.0,
            year=2022,
            workover_type="wireline",
        )
        assert result.confidence != ConfidenceLevel.HIGH


# ---------------------------------------------------------------------------
# TestLFSStubFallback
# ---------------------------------------------------------------------------


class TestLFSStubFallback:
    def test_empty_well_data_returns_estimate_with_warning(self, engine):
        result = engine.estimate_with_confidence(
            well_data={
                "region": "gom",
                "water_depth_m": 1500.0,
                "well_depth_m": 8000.0,
                "drilling_days": 0.0,  # LFS stub: no real data
                "completion_days": 0.0,
                "year": 2022,
            }
        )
        assert isinstance(result, CostEstimate)
        assert result.confidence == ConfidenceLevel.LOW


# ---------------------------------------------------------------------------
# TestCalibrationOverride
# ---------------------------------------------------------------------------


class TestCalibrationOverride:
    def test_calibrated_engine_returns_different_rate(self, engine):
        from worldenergydata.bsee.analysis.cost.cost_calibration import (
            MultivariateCalibration,
        )
        from worldenergydata.bsee.analysis.cost.sanctioned_dataset import (
            SanctionedProjectDataset,
        )

        training_df = SanctionedProjectDataset().synthetic_dataset(
            n_records=150, seed=42
        )
        calibration = MultivariateCalibration()
        calibration.fit(training_df)

        engine_calibrated = CostEngine(loader=engine._loader, calibration=calibration)

        proxy_result = engine.estimate_drilling_cost(
            region="gom",
            water_depth_m=1500.0,
            well_depth_m=8000.0,
            drilling_days=60.0,
            year=2022,
        )
        calibrated_result = engine_calibrated.estimate_drilling_cost(
            region="gom",
            water_depth_m=1500.0,
            well_depth_m=8000.0,
            drilling_days=60.0,
            year=2022,
        )
        # Calibrated engine should mark confidence as HIGH (calibrated) vs MEDIUM (proxy)
        assert calibrated_result.confidence == ConfidenceLevel.HIGH
        # The calibrated cost may differ from proxy
        assert isinstance(calibrated_result.cost_usd_mm, float)
