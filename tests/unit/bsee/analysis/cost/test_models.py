# ABOUTME: Unit tests for WRK-171 cost data models (CostRecord, CostEstimate, CalibrationComparison).
# ABOUTME: Verifies schema fields, validation, confidence labels, and serialisation.

"""Unit tests for worldenergydata.bsee.analysis.cost.models."""

import pytest

from worldenergydata.bsee.analysis.cost.models import (
    ActivityType,
    CalibrationComparison,
    ConfidenceLevel,
    CostEstimate,
    CostRecord,
    CostType,
    RigType,
    WaterDepthBand,
    WellDepthBand,
    classify_water_depth_band,
    classify_well_depth_band,
)


# ---------------------------------------------------------------------------
# TestCostRecord
# ---------------------------------------------------------------------------


class TestCostRecord:
    def test_minimal_construction_succeeds(self):
        record = CostRecord(
            project_name="Test Project",
            region="gom",
            water_depth_m=1500.0,
            well_depth_m=8000.0,
            operator="Shell",
            year_sanction=2018,
            year_drilling=2020,
            rig_type=RigType.DRILLSHIP,
            activity_type=ActivityType.DRILLING,
            hpht=False,
            subsea=True,
            cost_usd_mm=120.0,
            cost_type=CostType.WELL_COST,
            source="Annual Report 2020",
            confidence=ConfidenceLevel.HIGH,
        )
        assert record.project_name == "Test Project"
        assert record.cost_usd_mm == 120.0

    def test_cost_must_be_positive(self):
        with pytest.raises(ValueError, match="cost_usd_mm must be positive"):
            CostRecord(
                project_name="Bad Project",
                region="gom",
                water_depth_m=1500.0,
                well_depth_m=8000.0,
                operator="Shell",
                year_sanction=2018,
                year_drilling=2020,
                rig_type=RigType.DRILLSHIP,
                activity_type=ActivityType.DRILLING,
                hpht=False,
                subsea=True,
                cost_usd_mm=-10.0,
                cost_type=CostType.WELL_COST,
                source="Annual Report 2020",
                confidence=ConfidenceLevel.HIGH,
            )

    def test_water_depth_band_computed(self):
        record = CostRecord(
            project_name="P",
            region="gom",
            water_depth_m=600.0,
            well_depth_m=5000.0,
            operator="BP",
            year_sanction=2015,
            year_drilling=2017,
            rig_type=RigType.SEMI_SUB,
            activity_type=ActivityType.DRILLING,
            hpht=False,
            subsea=True,
            cost_usd_mm=80.0,
            cost_type=CostType.WELL_COST,
            source="BP 2017",
            confidence=ConfidenceLevel.MEDIUM,
        )
        assert record.water_depth_band == WaterDepthBand.MID

    def test_well_depth_band_computed(self):
        # 5000 m is between 3048 m (10 000 ft) and 6096 m (20 000 ft) → MEDIUM band
        record = CostRecord(
            project_name="P",
            region="gom",
            water_depth_m=300.0,
            well_depth_m=5000.0,
            operator="Chevron",
            year_sanction=2019,
            year_drilling=2021,
            rig_type=RigType.SEMI_SUB,
            activity_type=ActivityType.DRILLING,
            hpht=False,
            subsea=True,
            cost_usd_mm=60.0,
            cost_type=CostType.WELL_COST,
            source="Chevron 2021",
            confidence=ConfidenceLevel.MEDIUM,
        )
        assert record.well_depth_band == WellDepthBand.MEDIUM

    def test_to_dict_has_required_keys(self):
        record = CostRecord(
            project_name="P",
            region="gom",
            water_depth_m=1000.0,
            well_depth_m=9000.0,
            operator="ExxonMobil",
            year_sanction=2016,
            year_drilling=2018,
            rig_type=RigType.DRILLSHIP,
            activity_type=ActivityType.DRILLING,
            hpht=True,
            subsea=True,
            cost_usd_mm=200.0,
            cost_type=CostType.WELL_COST,
            source="ExxonMobil 2018",
            confidence=ConfidenceLevel.HIGH,
        )
        d = record.to_dict()
        required_keys = {
            "project_name", "region", "water_depth_m", "water_depth_band",
            "well_depth_m", "well_depth_band", "operator", "year_sanction",
            "year_drilling", "rig_type", "activity_type", "hpht", "subsea",
            "cost_usd_mm", "cost_type", "source", "confidence",
        }
        assert required_keys.issubset(set(d.keys()))


# ---------------------------------------------------------------------------
# TestCostEstimate
# ---------------------------------------------------------------------------


class TestCostEstimate:
    def test_construction_with_confidence(self):
        est = CostEstimate(
            activity_type=ActivityType.DRILLING,
            region="gom",
            water_depth_band=WaterDepthBand.DEEP,
            well_depth_band=WellDepthBand.DEEP,
            cost_usd_mm=180.0,
            cost_per_day_usd=450_000.0,
            duration_days=400.0,
            confidence=ConfidenceLevel.HIGH,
            source="calibrated_model",
            year=2022,
        )
        assert est.cost_usd_mm == 180.0
        assert est.confidence == ConfidenceLevel.HIGH

    def test_cost_per_day_positive(self):
        with pytest.raises(ValueError, match="cost_per_day_usd must be positive"):
            CostEstimate(
                activity_type=ActivityType.DRILLING,
                region="gom",
                water_depth_band=WaterDepthBand.DEEP,
                well_depth_band=WellDepthBand.DEEP,
                cost_usd_mm=100.0,
                cost_per_day_usd=-1.0,
                duration_days=200.0,
                confidence=ConfidenceLevel.MEDIUM,
                source="proxy",
                year=2021,
            )


# ---------------------------------------------------------------------------
# TestCalibrationComparison
# ---------------------------------------------------------------------------


class TestCalibrationComparison:
    def test_bias_positive_when_calibrated_higher(self):
        comp = CalibrationComparison(
            region="gom",
            water_depth_band=WaterDepthBand.DEEP,
            activity_type=ActivityType.DRILLING,
            proxy_rate_usd_day=400_000.0,
            calibrated_rate_usd_day=500_000.0,
            n_data_points=12,
            rmse_usd_mm=5.0,
            confidence=ConfidenceLevel.HIGH,
        )
        assert comp.bias_pct > 0.0

    def test_bias_negative_when_proxy_higher(self):
        comp = CalibrationComparison(
            region="gom",
            water_depth_band=WaterDepthBand.SHALLOW,
            activity_type=ActivityType.DRILLING,
            proxy_rate_usd_day=200_000.0,
            calibrated_rate_usd_day=150_000.0,
            n_data_points=8,
            rmse_usd_mm=3.0,
            confidence=ConfidenceLevel.MEDIUM,
        )
        assert comp.bias_pct < 0.0

    def test_bias_zero_when_equal(self):
        comp = CalibrationComparison(
            region="gom",
            water_depth_band=WaterDepthBand.MID,
            activity_type=ActivityType.COMPLETION,
            proxy_rate_usd_day=300_000.0,
            calibrated_rate_usd_day=300_000.0,
            n_data_points=5,
            rmse_usd_mm=2.0,
            confidence=ConfidenceLevel.MEDIUM,
        )
        assert abs(comp.bias_pct) < 1e-9


# ---------------------------------------------------------------------------
# TestClassifyDepthBand
# ---------------------------------------------------------------------------


class TestClassifyDepthBand:
    @pytest.mark.parametrize("depth_m, expected", [
        # Boundaries: SHALLOW <=300, MID <=1524, DEEP <=3048, ULTRA_DEEP >3048
        (0.0, WaterDepthBand.SHALLOW),
        (150.0, WaterDepthBand.SHALLOW),
        (300.0, WaterDepthBand.SHALLOW),
        (301.0, WaterDepthBand.MID),
        (1524.0, WaterDepthBand.MID),    # exact boundary → MID
        (1525.0, WaterDepthBand.DEEP),
        (3048.0, WaterDepthBand.DEEP),
        (3049.0, WaterDepthBand.ULTRA_DEEP),
    ])
    def test_water_depth_band(self, depth_m, expected):
        assert classify_water_depth_band(depth_m) == expected

    @pytest.mark.parametrize("depth_m, expected", [
        # Boundaries: SHALLOW <=3048, MEDIUM <=6096, DEEP <=7620, ULTRA_DEEP >7620
        (1000.0, WellDepthBand.SHALLOW),
        (3048.0, WellDepthBand.SHALLOW),   # exact boundary → SHALLOW
        (3049.0, WellDepthBand.MEDIUM),
        (6096.0, WellDepthBand.MEDIUM),    # exact boundary → MEDIUM
        (6097.0, WellDepthBand.DEEP),
        (7620.0, WellDepthBand.DEEP),      # exact boundary → DEEP
        (7621.0, WellDepthBand.ULTRA_DEEP),
    ])
    def test_well_depth_band(self, depth_m, expected):
        assert classify_well_depth_band(depth_m) == expected
