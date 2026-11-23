"""Tests for pipeline safety database models."""

from datetime import datetime

from worldenergydata.pipeline_safety.database.models import (
    Base,
    PipelineIncident,
)


class TestPipelineIncident:
    def test_tablename(self):
        assert PipelineIncident.__tablename__ == "pipeline_incidents"

    def test_repr(self):
        incident = PipelineIncident(
            id=1,
            report_number="RPT-001",
            report_type="hazardous_liquid",
            operator_name="Test Operator",
            incident_date=datetime(2024, 6, 1),
            pipeline_type="crude_oil",
        )
        repr_str = repr(incident)
        assert "RPT-001" in repr_str
        assert "Test Operator" in repr_str
        assert "crude_oil" in repr_str

    def test_unknown_consequences_have_no_zero_default(self):
        """Unknown consequences must not acquire a zero default at INSERT."""
        col = PipelineIncident.__table__.columns["fatalities"]
        assert col.default is None
        assert col.nullable
        col_inj = PipelineIncident.__table__.columns["injuries"]
        assert col_inj.default is None
        assert col_inj.nullable

    def test_nullable_columns(self):
        incident = PipelineIncident(
            report_number="RPT-002",
            report_type="gas_distribution",
            operator_name="Op",
            incident_date=datetime(2024, 1, 1),
        )
        # Without a session, defaults aren't applied
        assert incident.fatalities is None
        assert incident.injuries is None

    def test_base_exists(self):
        assert Base is not None
        assert hasattr(Base, "metadata")
