from __future__ import annotations

from worldenergydata.modules.bsee.data.models.pipeline import (
    PipelineLocation,
    PipelinePermit,
)


class TestPipelinePermit:
    """Tests for PipelinePermit dataclass."""

    def _make_permit(self, **overrides) -> PipelinePermit:
        """Helper to create a PipelinePermit with sensible defaults."""
        defaults = {
            "segment_num": "001",
            "ppl_size_code": "12.750",
            "maop_prss": 1480.0,
            "recv_maop_prss": 1440.0,
            "seg_length": 12.5,
            "max_wtr_dpth": 2200.0,
            "min_wtr_dpth": 150.0,
            "prod_code": "OIL",
            "status_code": "ACT",
            "ppl_const_date": "2005-03-20",
            "aban_date": None,
            "area_code": "GC",
            "block_number": "640",
            "lease_number": "G34567",
        }
        defaults.update(overrides)
        return PipelinePermit(**defaults)

    def test_is_active_pipeline_act(self):
        """Pipeline with ACT status code is active."""
        permit = self._make_permit(status_code="ACT")
        assert permit.is_active is True

    def test_is_active_pipeline_pro(self):
        """Pipeline with PRO status code is active."""
        permit = self._make_permit(status_code="PRO")
        assert permit.is_active is True

    def test_is_not_active_abn(self):
        """Pipeline with ABN status code is not active."""
        permit = self._make_permit(status_code="ABN")
        assert permit.is_active is False

    def test_is_not_active_out(self):
        """Pipeline with OUT status code is not active."""
        permit = self._make_permit(status_code="OUT")
        assert permit.is_active is False

    def test_is_not_active_rmv(self):
        """Pipeline with RMV status code is not active."""
        permit = self._make_permit(status_code="RMV")
        assert permit.is_active is False

    def test_is_not_active_none(self):
        """Pipeline with None status code is not active."""
        permit = self._make_permit(status_code=None)
        assert permit.is_active is False

    def test_is_deepwater_above_threshold(self):
        """Pipeline is deepwater when MAX_WTR_DPTH > 1000."""
        permit = self._make_permit(max_wtr_dpth=1500.0)
        assert permit.is_deepwater is True

    def test_is_deepwater_at_threshold(self):
        """Pipeline at exactly 1000 ft is not deepwater."""
        permit = self._make_permit(max_wtr_dpth=1000.0)
        assert permit.is_deepwater is False

    def test_is_not_deepwater_shallow(self):
        """Pipeline in shallow water is not deepwater."""
        permit = self._make_permit(max_wtr_dpth=200.0)
        assert permit.is_deepwater is False

    def test_is_deepwater_none_depth(self):
        """Pipeline with None depth is not deepwater."""
        permit = self._make_permit(max_wtr_dpth=None)
        assert permit.is_deepwater is False

    def test_segment_key(self):
        """Segment key is area_code_block_number_segment_num."""
        permit = self._make_permit(
            area_code="GC",
            block_number="640",
            segment_num="001",
        )
        assert permit.segment_key == "GC_640_001"

    def test_segment_key_different_values(self):
        """Segment key changes with different input values."""
        permit = self._make_permit(
            area_code="WC",
            block_number="168",
            segment_num="005",
        )
        assert permit.segment_key == "WC_168_005"


class TestPipelineLocation:
    """Tests for PipelineLocation dataclass."""

    def test_create_with_all_fields(self):
        """PipelineLocation can be created with all fields."""
        loc = PipelineLocation(
            segment_num="001",
            point_num=1,
            latitude=28.123,
            longitude=-89.456,
            water_depth=500.0,
            area_code="GC",
            block_number="640",
        )
        assert loc.segment_num == "001"
        assert loc.point_num == 1
        assert loc.latitude == 28.123
        assert loc.longitude == -89.456
        assert loc.water_depth == 500.0
        assert loc.area_code == "GC"
        assert loc.block_number == "640"

    def test_defaults_to_none(self):
        """All fields default to None."""
        loc = PipelineLocation()
        assert loc.segment_num is None
        assert loc.point_num is None
        assert loc.latitude is None
        assert loc.longitude is None
        assert loc.water_depth is None
        assert loc.area_code is None
        assert loc.block_number is None
