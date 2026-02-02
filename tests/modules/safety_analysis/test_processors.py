"""Tests for safety data processors."""

import pytest

from worldenergydata.modules.safety_analysis.constants import (
    ObservationType,
    SeverityLevel,
)
from worldenergydata.modules.safety_analysis.data.processors import (
    IncidentProcessor,
    ObservationProcessor,
)
from worldenergydata.modules.safety_analysis.exceptions import SafetyDataError


class TestObservationProcessor:
    def test_process_returns_observations(
        self, sample_observations_df, observation_schema
    ):
        processor = ObservationProcessor(observation_schema)
        observations = processor.process(sample_observations_df)
        assert len(observations) == 5
        assert observations[0].asset_id == "RIG-001"
        assert observations[0].observation_type == ObservationType.SAFE

    def test_process_to_dataframe(self, sample_observations_df, observation_schema):
        processor = ObservationProcessor(observation_schema)
        result = processor.process_to_dataframe(sample_observations_df)
        assert "asset_id" in result.columns
        assert "observed_at" in result.columns
        assert "description" in result.columns
        assert len(result) == 5

    def test_missing_required_column(self, observation_schema):
        import pandas as pd

        bad_df = pd.DataFrame({"wrong_col": [1, 2]})
        processor = ObservationProcessor(observation_schema)
        with pytest.raises(SafetyDataError, match="Missing required columns"):
            processor.process(bad_df)

    def test_type_mapping(self, sample_observations_df, observation_schema):
        processor = ObservationProcessor(observation_schema)
        observations = processor.process(sample_observations_df)
        types = [o.observation_type for o in observations]
        assert ObservationType.SAFE in types
        assert ObservationType.AT_RISK in types

    def test_action_captured(self, sample_observations_df, observation_schema):
        processor = ObservationProcessor(observation_schema)
        observations = processor.process(sample_observations_df)
        assert observations[0].action_taken is not None


class TestIncidentProcessor:
    def test_process_returns_incidents(self, sample_incidents_df, incident_schema):
        processor = IncidentProcessor(incident_schema)
        incidents = processor.process(sample_incidents_df)
        assert len(incidents) == 4
        assert incidents[0].asset_id == "RIG-001"

    def test_process_to_dataframe(self, sample_incidents_df, incident_schema):
        processor = IncidentProcessor(incident_schema)
        result = processor.process_to_dataframe(sample_incidents_df)
        assert "asset_id" in result.columns
        assert "occurred_at" in result.columns
        assert len(result) == 4

    def test_severity_mapping(self, sample_incidents_df, incident_schema):
        processor = IncidentProcessor(incident_schema)
        incidents = processor.process(sample_incidents_df)
        severities = [i.actual_severity for i in incidents]
        assert SeverityLevel.MINOR in severities
        assert SeverityLevel.NO_HURT in severities

    def test_missing_required_column(self, incident_schema):
        import pandas as pd

        bad_df = pd.DataFrame({"wrong_col": [1, 2]})
        processor = IncidentProcessor(incident_schema)
        with pytest.raises(SafetyDataError, match="Missing required columns"):
            processor.process(bad_df)

    def test_work_activity_captured(self, sample_incidents_df, incident_schema):
        processor = IncidentProcessor(incident_schema)
        incidents = processor.process(sample_incidents_df)
        assert incidents[0].work_activity == "Drilling"
