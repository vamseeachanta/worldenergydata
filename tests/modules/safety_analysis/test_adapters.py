# ABOUTME: Integration tests for safety analysis data source adapters.
"""
Phase 4 integration tests for BaseAdapter, HSEAdapter, and CSVAdapter.

Tests verify the adapter interface contract, data loading from CSV files,
and transformation of raw DataFrames into domain model objects.
"""

import pandas as pd
import pytest

from worldenergydata.modules.safety_analysis.adapters.base_adapter import BaseAdapter
from worldenergydata.modules.safety_analysis.adapters.hse_adapter import HSEAdapter
from worldenergydata.modules.safety_analysis.core.models import (
    SafetyIncident,
    SafetyObservation,
)
from worldenergydata.modules.safety_analysis.core.schemas import SchemaMapping
from worldenergydata.modules.safety_analysis.exceptions import SafetyDataError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hse_observations_csv(tmp_path):
    """Create a CSV file matching HSE default schema for observations."""
    csv_path = tmp_path / "hse_observations.csv"
    csv_path.write_text(
        "facility_name,incident_date,description,incident_type,severity\n"
        "RIG-001,2024-01-15,Worker wearing proper PPE,safe,minor\n"
        "RIG-002,2024-02-20,Unsafe lifting technique,at_risk,moderate\n"
    )
    return csv_path


@pytest.fixture
def hse_incidents_csv(tmp_path):
    """Create a CSV file matching HSE default schema for incidents."""
    csv_path = tmp_path / "hse_incidents.csv"
    csv_path.write_text(
        "facility_name,incident_date,description,incident_type,severity\n"
        "RIG-001,2024-01-20,Worker sprained ankle,injury,minor\n"
        "RIG-002,2024-02-15,Oil spill on deck,spill,moderate\n"
    )
    return csv_path


@pytest.fixture
def custom_schema():
    """A custom schema mapping for HSEAdapter tests."""
    return SchemaMapping(
        name="custom_hse",
        source_type="observation",
        asset_id_column="rig_id",
        datetime_column="date",
        description_column="description",
        type_column="obs_type",
        action_column="action",
        type_mapping={
            "safe": "safe",
            "at_risk": "at_risk",
        },
    )


# ---------------------------------------------------------------------------
# TestBaseAdapter
# ---------------------------------------------------------------------------


class TestBaseAdapter:
    """Tests for the abstract BaseAdapter interface."""

    def test_cannot_instantiate_directly(self):
        """BaseAdapter is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseAdapter()

    def test_subclass_must_implement_methods(self):
        """An incomplete subclass that omits abstract methods raises TypeError."""

        class IncompleteAdapter(BaseAdapter):
            pass

        with pytest.raises(TypeError):
            IncompleteAdapter()

    def test_concrete_subclass_instantiates(self):
        """A fully implemented subclass can be instantiated."""

        class ConcreteAdapter(BaseAdapter):
            name = "concrete"

            def load_observations(self, **kwargs):
                return pd.DataFrame()

            def load_incidents(self, **kwargs):
                return pd.DataFrame()

        adapter = ConcreteAdapter()
        assert adapter.name == "concrete"

    def test_load_all_delegates_to_methods(self):
        """load_all returns the tuple from load_observations and load_incidents."""

        class StubAdapter(BaseAdapter):
            name = "stub"

            def load_observations(self, **kwargs):
                return pd.DataFrame({"obs": [1, 2]})

            def load_incidents(self, **kwargs):
                return pd.DataFrame({"inc": [3, 4]})

        adapter = StubAdapter()
        obs_df, inc_df = adapter.load_all()
        assert len(obs_df) == 2
        assert len(inc_df) == 2
        assert "obs" in obs_df.columns
        assert "inc" in inc_df.columns


# ---------------------------------------------------------------------------
# TestHSEAdapter
# ---------------------------------------------------------------------------


class TestHSEAdapter:
    """Tests for the HSEAdapter concrete implementation."""

    def test_default_schema(self):
        """HSEAdapter has a default schema with expected column mappings."""
        adapter = HSEAdapter()
        schema = adapter._schema
        assert schema.name == "hse_default"
        assert schema.asset_id_column == "facility_name"
        assert schema.datetime_column == "incident_date"
        assert schema.description_column == "description"

    def test_name_property(self):
        """HSEAdapter reports its name as 'hse'."""
        adapter = HSEAdapter()
        assert adapter.name == "hse"

    def test_load_observations_from_csv(self, hse_observations_csv):
        """HSEAdapter loads observations from a CSV file."""
        adapter = HSEAdapter()
        df = adapter.load_observations(csv_path=hse_observations_csv)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "facility_name" in df.columns

    def test_load_observations_no_path_raises(self):
        """HSEAdapter raises SafetyDataError when no csv_path is provided."""
        adapter = HSEAdapter()
        with pytest.raises(SafetyDataError, match="csv_path required"):
            adapter.load_observations()

    def test_load_incidents_from_csv(self, hse_incidents_csv):
        """HSEAdapter loads incidents from a CSV file."""
        adapter = HSEAdapter()
        df = adapter.load_incidents(csv_path=hse_incidents_csv)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "facility_name" in df.columns

    def test_load_incidents_no_path_raises(self):
        """HSEAdapter raises SafetyDataError when no csv_path is provided."""
        adapter = HSEAdapter()
        with pytest.raises(SafetyDataError, match="csv_path required"):
            adapter.load_incidents()

    def test_process_observations(self, sample_observations_df, observation_schema):
        """process_observations returns a list of SafetyObservation models."""
        adapter = HSEAdapter(schema=observation_schema)
        results = adapter.process_observations(sample_observations_df)
        assert isinstance(results, list)
        assert len(results) == len(sample_observations_df)
        assert all(isinstance(r, SafetyObservation) for r in results)

    def test_process_observations_fields(
        self, sample_observations_df, observation_schema
    ):
        """Processed observations carry correct asset_id and description."""
        adapter = HSEAdapter(schema=observation_schema)
        results = adapter.process_observations(sample_observations_df)
        first = results[0]
        assert first.asset_id == "RIG-001"
        assert "PPE" in first.description

    def test_process_incidents(self, sample_incidents_df, incident_schema):
        """process_incidents returns a list of SafetyIncident models."""
        adapter = HSEAdapter(schema=incident_schema)
        results = adapter.process_incidents(sample_incidents_df)
        assert isinstance(results, list)
        assert len(results) == len(sample_incidents_df)
        assert all(isinstance(r, SafetyIncident) for r in results)

    def test_process_incidents_fields(self, sample_incidents_df, incident_schema):
        """Processed incidents carry correct asset_id values."""
        adapter = HSEAdapter(schema=incident_schema)
        results = adapter.process_incidents(sample_incidents_df)
        asset_ids = {r.asset_id for r in results}
        assert "RIG-001" in asset_ids
        assert "RIG-002" in asset_ids

    def test_custom_schema(self, custom_schema):
        """HSEAdapter accepts and uses a custom SchemaMapping."""
        adapter = HSEAdapter(schema=custom_schema)
        assert adapter._schema.name == "custom_hse"
        assert adapter._schema.asset_id_column == "rig_id"


# ---------------------------------------------------------------------------
# TestCSVAdapter
# ---------------------------------------------------------------------------


class TestCSVAdapter:
    """Tests for the CSVAdapter (TDD red phase -- class not yet implemented)."""

    def test_csv_adapter_importable(self):
        """CSVAdapter can be imported from the adapters package."""
        from worldenergydata.modules.safety_analysis.adapters.csv_adapter import (
            CSVAdapter,
        )

        assert CSVAdapter is not None

    def test_load_observations(self, sample_csv_file, observation_schema):
        """CSVAdapter.load_observations loads data from the configured path."""
        from worldenergydata.modules.safety_analysis.adapters.csv_adapter import (
            CSVAdapter,
        )

        adapter = CSVAdapter(
            observations_path=sample_csv_file,
            incidents_path=None,
            observation_schema=observation_schema,
            incident_schema=None,
        )
        df = adapter.load_observations()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5

    def test_load_incidents(self, sample_incidents_csv, incident_schema):
        """CSVAdapter.load_incidents loads data from the configured path."""
        from worldenergydata.modules.safety_analysis.adapters.csv_adapter import (
            CSVAdapter,
        )

        adapter = CSVAdapter(
            observations_path=None,
            incidents_path=sample_incidents_csv,
            observation_schema=None,
            incident_schema=incident_schema,
        )
        df = adapter.load_incidents()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 4

    def test_load_observations_no_path_raises(self, observation_schema):
        """CSVAdapter raises SafetyDataError when no observations_path is set."""
        from worldenergydata.modules.safety_analysis.adapters.csv_adapter import (
            CSVAdapter,
        )

        adapter = CSVAdapter(
            observations_path=None,
            incidents_path=None,
            observation_schema=observation_schema,
            incident_schema=None,
        )
        with pytest.raises(SafetyDataError):
            adapter.load_observations()

    def test_process_observations(
        self, sample_csv_file, sample_observations_df, observation_schema
    ):
        """CSVAdapter.process_observations returns SafetyObservation models."""
        from worldenergydata.modules.safety_analysis.adapters.csv_adapter import (
            CSVAdapter,
        )

        adapter = CSVAdapter(
            observations_path=sample_csv_file,
            incidents_path=None,
            observation_schema=observation_schema,
            incident_schema=None,
        )
        results = adapter.process_observations(sample_observations_df)
        assert isinstance(results, list)
        assert all(isinstance(r, SafetyObservation) for r in results)
        assert len(results) == len(sample_observations_df)

    def test_load_all(
        self,
        sample_csv_file,
        sample_incidents_csv,
        observation_schema,
        incident_schema,
    ):
        """CSVAdapter.load_all returns a tuple of (obs_df, inc_df)."""
        from worldenergydata.modules.safety_analysis.adapters.csv_adapter import (
            CSVAdapter,
        )

        adapter = CSVAdapter(
            observations_path=sample_csv_file,
            incidents_path=sample_incidents_csv,
            observation_schema=observation_schema,
            incident_schema=incident_schema,
        )
        obs_df, inc_df = adapter.load_all()
        assert isinstance(obs_df, pd.DataFrame)
        assert isinstance(inc_df, pd.DataFrame)
        assert len(obs_df) > 0
        assert len(inc_df) > 0
