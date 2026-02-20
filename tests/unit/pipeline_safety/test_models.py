"""Tests for pipeline safety database models."""

from datetime import datetime

import pytest

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

    def test_column_defaults_defined(self):
        """SQLAlchemy Column defaults are defined (applied at INSERT time, not construction)."""
        col = PipelineIncident.__table__.columns["fatalities"]
        assert col.default is not None
        assert col.default.arg == 0
        col_inj = PipelineIncident.__table__.columns["injuries"]
        assert col_inj.default is not None
        assert col_inj.default.arg == 0

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
