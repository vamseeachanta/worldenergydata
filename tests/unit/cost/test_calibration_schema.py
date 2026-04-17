"""
ABOUTME: Tests for CostDataPoint Pydantic schema — field validation and constraints.
ABOUTME: Verifies schema accepts valid sanctioned-project cost entries and rejects invalid ones.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldenergydata.cost.data_collection.calibration_schema import (
    ActivityType,
    Confidence,
    CostDataPoint,
    CostType,
    RigType,
    SubseaType,
    WaterDepthBand,
    WellDepthBand,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_kwargs() -> dict:
    """Minimal valid CostDataPoint keyword arguments."""
    return {
        "project_name": "Mad Dog Phase 2",
        "region": "GOM",
        "water_depth_m": 1310.0,
        "water_depth_band": WaterDepthBand.DEEP,
        "well_depth_m": 7620.0,
        "well_depth_band": WellDepthBand.DEEP,
        "operator": "BP",
        "year_sanction": 2017,
        "rig_type": RigType.SEMI_SUB,
        "activity_type": ActivityType.DRILLING,
        "hpht": False,
        "subsea": SubseaType.SUBSEA,
        "cost_usd_mm": 145.0,
        "cost_type": CostType.TOTAL_CAPEX,
        "source": "BP Annual Report 2017, FID announcement",
        "confidence": Confidence.HIGH,
    }


# ---------------------------------------------------------------------------
# Schema instantiation tests
# ---------------------------------------------------------------------------


class TestCostDataPointValidCreation:
    """CostDataPoint accepts well-formed entries."""

    def test_valid_minimal_record_instantiates(self):
        """A complete valid record creates a CostDataPoint without error."""
        point = CostDataPoint(**_valid_kwargs())
        assert point.project_name == "Mad Dog Phase 2"
        assert point.region == "GOM"
        assert point.water_depth_m == 1310.0
        assert point.cost_usd_mm == 145.0

    def test_optional_fields_default_to_none(self):
        """year_drilling and well_depth_m are optional; absent fields default to None."""
        kwargs = _valid_kwargs()
        kwargs.pop("well_depth_m")
        kwargs.pop("well_depth_band")
        point = CostDataPoint(**kwargs)
        assert point.well_depth_m is None
        assert point.well_depth_band is None

    def test_year_drilling_optional(self):
        """year_drilling field is optional."""
        point = CostDataPoint(**_valid_kwargs())
        assert point.year_drilling is None

    def test_year_drilling_populated(self):
        """year_drilling can be set to a valid year."""
        kwargs = _valid_kwargs()
        kwargs["year_drilling"] = 2019
        point = CostDataPoint(**kwargs)
        assert point.year_drilling == 2019

    def test_hpht_true_flag(self):
        """hpht=True is accepted."""
        kwargs = _valid_kwargs()
        kwargs["hpht"] = True
        point = CostDataPoint(**kwargs)
        assert point.hpht is True

    def test_dry_tree_subsea_type(self):
        """SubseaType.DRY_TREE is a valid subsea value."""
        kwargs = _valid_kwargs()
        kwargs["subsea"] = SubseaType.DRY_TREE
        point = CostDataPoint(**kwargs)
        assert point.subsea == SubseaType.DRY_TREE


# ---------------------------------------------------------------------------
# Enum validation tests
# ---------------------------------------------------------------------------


class TestCostDataPointEnumFields:
    """Enum fields only accept declared values."""

    def test_invalid_rig_type_raises(self):
        """Unrecognised rig_type raises ValidationError."""
        kwargs = _valid_kwargs()
        kwargs["rig_type"] = "helicopter"
        with pytest.raises(ValidationError):
            CostDataPoint(**kwargs)

    def test_invalid_activity_type_raises(self):
        """Unrecognised activity_type raises ValidationError."""
        kwargs = _valid_kwargs()
        kwargs["activity_type"] = "exploration_seismic"
        with pytest.raises(ValidationError):
            CostDataPoint(**kwargs)

    def test_invalid_confidence_raises(self):
        """Unrecognised confidence level raises ValidationError."""
        kwargs = _valid_kwargs()
        kwargs["confidence"] = "uncertain"
        with pytest.raises(ValidationError):
            CostDataPoint(**kwargs)

    def test_invalid_cost_type_raises(self):
        """Unrecognised cost_type raises ValidationError."""
        kwargs = _valid_kwargs()
        kwargs["cost_type"] = "estimate"
        with pytest.raises(ValidationError):
            CostDataPoint(**kwargs)

    def test_water_depth_band_enum_values(self):
        """All declared WaterDepthBand values are accepted."""
        for band in WaterDepthBand:
            kwargs = _valid_kwargs()
            kwargs["water_depth_band"] = band
            point = CostDataPoint(**kwargs)
            assert point.water_depth_band == band


# ---------------------------------------------------------------------------
# Numeric constraint tests
# ---------------------------------------------------------------------------


class TestCostDataPointNumericConstraints:
    """Numeric fields enforce positive / range constraints."""

    def test_negative_cost_raises(self):
        """cost_usd_mm must be positive; negative value raises ValidationError."""
        kwargs = _valid_kwargs()
        kwargs["cost_usd_mm"] = -10.0
        with pytest.raises(ValidationError):
            CostDataPoint(**kwargs)

    def test_zero_cost_raises(self):
        """cost_usd_mm must be > 0; zero raises ValidationError."""
        kwargs = _valid_kwargs()
        kwargs["cost_usd_mm"] = 0.0
        with pytest.raises(ValidationError):
            CostDataPoint(**kwargs)

    def test_negative_water_depth_raises(self):
        """water_depth_m must be non-negative; negative raises ValidationError."""
        kwargs = _valid_kwargs()
        kwargs["water_depth_m"] = -5.0
        with pytest.raises(ValidationError):
            CostDataPoint(**kwargs)

    def test_year_sanction_reasonable_range(self):
        """year_sanction within 1970–2035 is accepted."""
        kwargs = _valid_kwargs()
        for year in [1970, 2000, 2024, 2035]:
            kwargs["year_sanction"] = year
            point = CostDataPoint(**kwargs)
            assert point.year_sanction == year

    def test_year_sanction_out_of_range_raises(self):
        """year_sanction before 1970 raises ValidationError."""
        kwargs = _valid_kwargs()
        kwargs["year_sanction"] = 1960
        with pytest.raises(ValidationError):
            CostDataPoint(**kwargs)


# ---------------------------------------------------------------------------
# Public dataset smoke test
# ---------------------------------------------------------------------------


class TestPublicDatasetLoad:
    """Public dataset module returns a non-empty list of CostDataPoint records."""

    def test_load_public_dataset_returns_list(self):
        """load_public_dataset() returns at least 20 records."""
        from worldenergydata.cost.data_collection.public_dataset import (
            load_public_dataset,
        )

        records = load_public_dataset()
        assert isinstance(records, list)
        assert len(records) >= 20

    def test_all_records_are_cost_data_points(self):
        """Every entry returned is a valid CostDataPoint instance."""
        from worldenergydata.cost.data_collection.public_dataset import (
            load_public_dataset,
        )

        records = load_public_dataset()
        for rec in records:
            assert isinstance(rec, CostDataPoint)

    def test_dataset_covers_multiple_regions(self):
        """Dataset includes data from at least 3 distinct geographic regions."""
        from worldenergydata.cost.data_collection.public_dataset import (
            load_public_dataset,
        )

        records = load_public_dataset()
        regions = {r.region for r in records}
        assert len(regions) >= 3

    def test_dataset_spans_multiple_years(self):
        """Dataset sanctions span at least 10 years."""
        from worldenergydata.cost.data_collection.public_dataset import (
            load_public_dataset,
        )

        records = load_public_dataset()
        years = {r.year_sanction for r in records}
        assert max(years) - min(years) >= 10
