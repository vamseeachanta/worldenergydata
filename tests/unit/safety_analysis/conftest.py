"""Shared test fixtures for safety analysis tests."""

import pandas as pd
import pytest

from worldenergydata.safety_analysis.core.schemas import SchemaMapping


@pytest.fixture
def sample_observations_df():
    """Sample observation data as a DataFrame."""
    return pd.DataFrame(
        {
            "rig_id": ["RIG-001", "RIG-001", "RIG-002", "RIG-002", "RIG-001"],
            "date": [
                "2024-01-01",
                "2024-01-02",
                "2024-01-01",
                "2024-01-03",
                "2024-01-04",
            ],
            "description": [
                "Worker wearing proper PPE during drilling",
                "Loose cable near walkway creating trip hazard",
                "Proper lockout tagout procedure followed",
                "Missing guardrail on upper platform",
                "Good housekeeping on drill floor",
            ],
            "obs_type": ["safe", "at_risk", "safe", "at_risk", "safe"],
            "action": [
                "Positive reinforcement given",
                "Cable secured immediately",
                "Acknowledged good practice",
                "Temporary barrier installed",
                "Team recognized",
            ],
        }
    )


@pytest.fixture
def sample_incidents_df():
    """Sample incident data as a DataFrame."""
    return pd.DataFrame(
        {
            "rig_id": ["RIG-001", "RIG-002", "RIG-001", "RIG-002"],
            "incident_date": [
                "2024-01-05",
                "2024-01-10",
                "2024-01-15",
                "2024-01-20",
            ],
            "description": [
                "Worker slipped on wet surface",
                "Minor hand injury during pipe handling",
                "Near miss with dropped object",
                "Chemical splash during mixing operation",
            ],
            "actual_severity": [
                "1 - Minor Hurt",
                "1 - Minor Hurt",
                "0 - No Hurt",
                "2 - Moderate Hurt",
            ],
            "potential_severity": [
                "2 - Moderate Hurt",
                "2 - Moderate Hurt",
                "3 - Severe Hurt",
                "3 - Severe Hurt",
            ],
            "work_activity": [
                "Drilling",
                "Pipe handling",
                "Lifting operations",
                "Chemical operations",
            ],
        }
    )


@pytest.fixture
def observation_schema():
    """Schema mapping for sample observation data."""
    return SchemaMapping(
        name="test_observations",
        source_type="observation",
        asset_id_column="rig_id",
        datetime_column="date",
        description_column="description",
        type_column="obs_type",
        action_column="action",
        type_mapping={
            "safe": "safe",
            "at_risk": "at_risk",
            "near_miss": "near_miss",
        },
    )


@pytest.fixture
def incident_schema():
    """Schema mapping for sample incident data."""
    return SchemaMapping(
        name="test_incidents",
        source_type="incident",
        asset_id_column="rig_id",
        datetime_column="incident_date",
        description_column="description",
        severity_column="actual_severity",
        potential_severity_column="potential_severity",
        work_activity_column="work_activity",
        severity_mapping={
            "0 - No Hurt": "no_hurt",
            "1 - Minor Hurt": "minor",
            "2 - Moderate Hurt": "moderate",
            "3 - Severe Hurt": "severe",
            "4 - Fatality": "fatality",
            "5 - Multiple Fatalities": "multiple_fatalities",
        },
    )


@pytest.fixture
def sample_csv_file(sample_observations_df, tmp_path):
    """Write sample observation data to a CSV file."""
    path = tmp_path / "sample_observations.csv"
    sample_observations_df.to_csv(path, index=False)
    return path


@pytest.fixture
def sample_excel_file(sample_observations_df, tmp_path):
    """Write sample observation data to an Excel file."""
    path = tmp_path / "sample_observations.xlsx"
    sample_observations_df.to_excel(path, index=False)
    return path


@pytest.fixture
def sample_parquet_file(sample_observations_df, tmp_path):
    """Write sample observation data to a Parquet file."""
    path = tmp_path / "sample_observations.parquet"
    sample_observations_df.to_parquet(path, index=False)
    return path


@pytest.fixture
def sample_incidents_csv(sample_incidents_df, tmp_path):
    """Write sample incident data to a CSV file."""
    path = tmp_path / "sample_incidents.csv"
    sample_incidents_df.to_csv(path, index=False)
    return path
