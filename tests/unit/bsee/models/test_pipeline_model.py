"""Tests for BSEE pipeline domain models."""

from worldenergydata.bsee.data.models.pipeline import PipelineLocation, PipelinePermit


class TestPipelinePermit:
    """Tests for PipelinePermit dataclass."""

    def test_create_with_defaults(self):
        permit = PipelinePermit()
        assert permit.segment_num is None
        assert permit.status_code is None

    def test_create_with_all_fields(self):
        permit = PipelinePermit(
            segment_num="001",
            ppl_size_code="12",
            maop_prss=1200.0,
            recv_maop_prss=1100.0,
            seg_length=5.5,
            max_wtr_dpth=3000.0,
            min_wtr_dpth=500.0,
            prod_code="OIL",
            status_code="ACT",
            ppl_const_date="2020-01-01",
            aban_date=None,
            area_code="GC",
            block_number="640",
            lease_number="OCS-G 12345",
        )
        assert permit.segment_num == "001"
        assert permit.maop_prss == 1200.0

    def test_is_active_with_active_status(self):
        permit = PipelinePermit(status_code="ACT")
        assert permit.is_active is True

    def test_is_active_with_none_status(self):
        permit = PipelinePermit(status_code=None)
        assert permit.is_active is False

    def test_is_active_with_abandoned(self):
        permit = PipelinePermit(status_code="ABN")
        assert permit.is_active is False

    def test_is_active_with_out(self):
        permit = PipelinePermit(status_code="OUT")
        assert permit.is_active is False

    def test_is_active_with_removed(self):
        permit = PipelinePermit(status_code="RMV")
        assert permit.is_active is False

    def test_is_deepwater_above_threshold(self):
        permit = PipelinePermit(max_wtr_dpth=1500.0)
        assert permit.is_deepwater is True

    def test_is_deepwater_at_threshold(self):
        permit = PipelinePermit(max_wtr_dpth=1000.0)
        assert permit.is_deepwater is False

    def test_is_deepwater_below_threshold(self):
        permit = PipelinePermit(max_wtr_dpth=500.0)
        assert permit.is_deepwater is False

    def test_is_deepwater_none_depth(self):
        permit = PipelinePermit(max_wtr_dpth=None)
        assert permit.is_deepwater is False

    def test_segment_key(self):
        permit = PipelinePermit(
            area_code="GC", block_number="640", segment_num="001"
        )
        assert permit.segment_key == "GC_640_001"


class TestPipelineLocation:
    """Tests for PipelineLocation dataclass."""

    def test_create_with_defaults(self):
        loc = PipelineLocation()
        assert loc.segment_num is None
        assert loc.latitude is None

    def test_create_with_all_fields(self):
        loc = PipelineLocation(
            segment_num="001",
            point_num=1,
            latitude=28.5,
            longitude=-89.2,
            water_depth=3000.0,
            area_code="GC",
            block_number="640",
        )
        assert loc.point_num == 1
        assert loc.latitude == 28.5
        assert loc.longitude == -89.2
