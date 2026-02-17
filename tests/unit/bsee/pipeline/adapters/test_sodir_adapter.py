"""Tests for the SODIR adapter (sodir_adapter.py).

Uses lightweight stubs instead of real API calls.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import pytest

from worldenergydata.bsee.pipeline.adapters.common_schema import (
    AdapterResult,
    DataAvailability,
    SourceMetadata,
)
from worldenergydata.bsee.pipeline.adapters.sodir_adapter import (
    SodirAdapter,
    _BCF_TO_M3,
    _MMBBL_TO_M3,
)


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

_RAW_FIELD_TROLL = {
    "fldName": "TROLL",
    "fldNpdidField": 43777,
    "fldStatus": "PRODUCING",
    "fldOperatorName": "Equinor Energy AS",
    "fldDiscoveryYear": 1979,
    "fldProductionStartYear": 1995,
    "fldCessationYear": None,
    "fldOriginalReservesOil": 2.5,
    "fldOriginalReservesGas": 1.3,
    "fldRemainingReservesOil": 1.0,
    "fldRemainingReservesGas": 0.8,
    "fldRecoverableOil": 2.0,
    "fldRecoverableGas": 1.1,
    "fldRecoverableNGL": 0.1,
    "fldRecoverableCondensate": 0.05,
    "fldCumulativeOilProduction": 1.5,
    "fldCumulativeGasProduction": 0.6,
    "fldCumulativeNGLProduction": 0.08,
    "fldCumulativeCondensateProduction": 0.03,
    "fldMainArea": "North Sea",
    "fldWaterDepth": 303,
    "fldDateUpdated": "2025-06-01",
}

_RAW_FIELD_EKOFISK = {
    "fldName": "EKOFISK",
    "fldNpdidField": 43506,
    "fldStatus": "PRODUCING",
    "fldOperatorName": "ConocoPhillips Skandinavia AS",
    "fldDiscoveryYear": 1969,
    "fldProductionStartYear": 1971,
    "fldCessationYear": None,
    "fldOriginalReservesOil": 5.0,
    "fldOriginalReservesGas": 0.5,
    "fldRemainingReservesOil": 1.5,
    "fldRemainingReservesGas": 0.2,
    "fldRecoverableOil": 4.0,
    "fldRecoverableGas": 0.4,
    "fldCumulativeOilProduction": 3.5,
    "fldCumulativeGasProduction": 0.3,
    "fldCumulativeNGLProduction": None,
    "fldCumulativeCondensateProduction": None,
    "fldMainArea": "North Sea",
    "fldWaterDepth": 70,
    "fldDateUpdated": "2025-05-15",
}

_RAW_WELLBORE_1 = {
    "wlbName": "31/2-1",
    "wlbNpdidWellbore": 100001,
    "wlbWell": "31/2-1",
    "wlbStatus": "P&A",
    "wlbPurpose": "EXPLORATION",
    "wlbContent": "OIL",
    "wlbDrillingOperator": "Equinor",
    "wlbProductionLicense": "PL001",
    "wlbTotalDepth": 3500,
    "wlbKellyBushElevation": 25,
    "wlbWaterDepth": 303,
    "wlbCompletionDate": "1980-06-15",
    "wlbEntryDate": "1980-01-10",
    "wlbDrillingStartDate": "1980-01-15",
    "wlbDrillingEndDate": "1980-05-20",
    "wlbNsDecDeg": 60.6,
    "wlbEwDecDeg": 3.7,
    "wlbField": "TROLL",
}

_RAW_WELLBORE_2 = {
    "wlbName": "31/2-2",
    "wlbNpdidWellbore": 100002,
    "wlbWell": "31/2-2",
    "wlbStatus": "PRODUCING",
    "wlbPurpose": "DEVELOPMENT",
    "wlbContent": "OIL/GAS",
    "wlbDrillingOperator": "Equinor",
    "wlbProductionLicense": "PL001",
    "wlbTotalDepth": 4200,
    "wlbKellyBushElevation": 28,
    "wlbWaterDepth": 305,
    "wlbCompletionDate": "1994-11-20",
    "wlbEntryDate": "1994-03-01",
    "wlbDrillingStartDate": "1994-03-10",
    "wlbDrillingEndDate": "1994-10-15",
    "wlbNsDecDeg": 60.61,
    "wlbEwDecDeg": 3.72,
    "wlbField": "TROLL",
}

_RAW_WELLBORE_OTHER_FIELD = {
    "wlbName": "2/4-1",
    "wlbNpdidWellbore": 200001,
    "wlbWell": "2/4-1",
    "wlbStatus": "P&A",
    "wlbPurpose": "EXPLORATION",
    "wlbContent": "OIL",
    "wlbDrillingOperator": "ConocoPhillips",
    "wlbProductionLicense": "PL018",
    "wlbTotalDepth": 3100,
    "wlbWaterDepth": 70,
    "wlbDrillingStartDate": "1969-08-01",
    "wlbDrillingEndDate": "1969-12-15",
    "wlbField": "EKOFISK",
}


# ---------------------------------------------------------------------------
# Stub API client
# ---------------------------------------------------------------------------

class StubSodirAPIClient:
    """Returns fixture data without network calls."""

    def __init__(
        self,
        fields: list[dict] | None = None,
        wellbores: list[dict] | None = None,
    ):
        self.fields = fields if fields is not None else [
            _RAW_FIELD_TROLL,
            _RAW_FIELD_EKOFISK,
        ]
        self.wellbores = wellbores if wellbores is not None else [
            _RAW_WELLBORE_1,
            _RAW_WELLBORE_2,
            _RAW_WELLBORE_OTHER_FIELD,
        ]

    def get_fields(self, **kwargs) -> list[dict]:
        return self.fields

    def get_wellbores(self, **kwargs) -> list[dict]:
        return self.wellbores


class FailingAPIClient:
    """Simulates API failures for resilience testing."""

    def get_fields(self, **kwargs) -> list[dict]:
        raise ConnectionError("SODIR API unreachable")

    def get_wellbores(self, **kwargs) -> list[dict]:
        raise ConnectionError("SODIR API unreachable")


class FieldOnlyFailClient:
    """Fields endpoint fails, wellbores works."""

    def get_fields(self, **kwargs) -> list[dict]:
        raise TimeoutError("Field endpoint timed out")

    def get_wellbores(self, **kwargs) -> list[dict]:
        return [_RAW_WELLBORE_1]


class WellboreOnlyFailClient:
    """Wellbores endpoint fails, fields works."""

    def get_fields(self, **kwargs) -> list[dict]:
        return [_RAW_FIELD_TROLL]

    def get_wellbores(self, **kwargs) -> list[dict]:
        raise RuntimeError("Wellbore endpoint error")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def adapter() -> SodirAdapter:
    """Adapter wired to the stub client with default fixture data."""
    return SodirAdapter(api_client=StubSodirAPIClient())


@pytest.fixture
def failing_adapter() -> SodirAdapter:
    return SodirAdapter(api_client=FailingAPIClient())


# ---------------------------------------------------------------------------
# Tests — adapt() with known field
# ---------------------------------------------------------------------------

class TestAdaptKnownField:
    def test_returns_adapter_result(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert isinstance(result, AdapterResult)

    def test_field_name_matches(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert result.field_name == "TROLL"

    def test_field_code_is_id(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert result.field_code == "43777"

    def test_case_insensitive_match(self, adapter: SodirAdapter):
        result = adapter.adapt("troll")
        assert result.field_name == "TROLL"
        assert result.field_code == "43777"

    def test_well_count(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        # Two TROLL wellbores in fixtures
        assert result.well_count == 2

    def test_area_code(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert result.area_code == "North Sea"

    def test_query_type(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert result.query_type == "field_name"

    def test_source_metadata_attached(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert result.source.source_id == "sodir"
        assert "Norwegian" in result.source.jurisdiction


# ---------------------------------------------------------------------------
# Tests — unknown field
# ---------------------------------------------------------------------------

class TestAdaptUnknownField:
    def test_unknown_field_returns_result(self, adapter: SodirAdapter):
        result = adapter.adapt("NONEXISTENT_FIELD")
        assert isinstance(result, AdapterResult)

    def test_unknown_field_has_warning(self, adapter: SodirAdapter):
        result = adapter.adapt("NONEXISTENT_FIELD")
        assert any("not found" in w for w in result.warnings)

    def test_unknown_field_empty_production(self, adapter: SodirAdapter):
        result = adapter.adapt("NONEXISTENT_FIELD")
        assert result.production.empty

    def test_unknown_field_zero_wells(self, adapter: SodirAdapter):
        result = adapter.adapt("NONEXISTENT_FIELD")
        assert result.well_count == 0


# ---------------------------------------------------------------------------
# Tests — unavailable domains
# ---------------------------------------------------------------------------

class TestUnavailableDomains:
    def test_casing_empty(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert result.casing_strings.empty

    def test_well_paths_empty(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert result.well_paths.empty

    def test_intervention_empty(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert result.intervention_activities.empty

    def test_completion_empty(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert result.completion_activities.empty

    def test_unavailable_warnings_present(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        unavail_warnings = [w for w in result.warnings if "unavailable" in w]
        # casing, intervention, well_path
        assert len(unavail_warnings) >= 3

    def test_production_partial_warning(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert any("cumulative only" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Tests — wellbore summary DataFrame
# ---------------------------------------------------------------------------

class TestWellboreSummary:
    def test_summary_has_columns(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert list(result.wellbore_summary.columns) == [
            "purpose",
            "status",
            "count",
        ]

    def test_summary_non_empty_for_known_field(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert not result.wellbore_summary.empty

    def test_summary_counts_correct(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        total = result.wellbore_summary["count"].sum()
        assert total == 2

    def test_summary_empty_for_unknown_field(self, adapter: SodirAdapter):
        result = adapter.adapt("NONEXISTENT_FIELD")
        assert result.wellbore_summary.empty
        assert list(result.wellbore_summary.columns) == [
            "purpose",
            "status",
            "count",
        ]


# ---------------------------------------------------------------------------
# Tests — drilling activities DataFrame
# ---------------------------------------------------------------------------

class TestDrillingActivities:
    def test_has_expected_columns(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        expected = {
            "wellbore_name",
            "spud_date",
            "completion_date",
            "duration_days",
            "operator",
            "total_depth_m",
            "water_depth_m",
        }
        assert expected == set(result.drilling_activities.columns)

    def test_row_count(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert len(result.drilling_activities) == 2

    def test_depths_in_metres(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        depths = result.drilling_activities["total_depth_m"].dropna()
        # Fixture depths are 3500 and 4200 metres
        assert 3500.0 in depths.values
        assert 4200.0 in depths.values

    def test_empty_for_unknown_field(self, adapter: SodirAdapter):
        result = adapter.adapt("NONEXISTENT_FIELD")
        assert result.drilling_activities.empty


# ---------------------------------------------------------------------------
# Tests — production DataFrame and unit conversions
# ---------------------------------------------------------------------------

class TestProduction:
    def test_production_has_rows(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert len(result.production) == 1

    def test_columns_are_si(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        for col in result.production.columns:
            assert col.endswith("_m3"), f"Column {col} should end with _m3"

    def test_oil_converted_to_m3(self, adapter: SodirAdapter):
        """FieldProcessor converts raw Sm3 -> 1.5 mmbbl; adapter -> m3."""
        result = adapter.adapt("TROLL")
        oil_m3 = result.production["cumulative_oil_m3"].iloc[0]
        # FieldProcessor: 1.5 (raw MSm3) * 6.29 = 9.435 mmbbl
        # Adapter:  9.435 * 1e6 * 0.158987 = ~1_500_086 m3
        expected_mmbbl = 1.5 * 6.29  # from FieldProcessor
        expected_m3 = expected_mmbbl * _MMBBL_TO_M3
        assert abs(oil_m3 - expected_m3) / expected_m3 < 0.01

    def test_gas_converted_to_m3(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        gas_m3 = result.production["cumulative_gas_m3"].iloc[0]
        expected_bcf = 0.6 * 35.3  # FieldProcessor: bsm3 -> BCF
        expected_m3 = expected_bcf * _BCF_TO_M3
        assert abs(gas_m3 - expected_m3) / expected_m3 < 0.01

    def test_recoverable_oil_m3(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        rec_oil = result.production["recoverable_oil_m3"].iloc[0]
        expected_mmbbl = 2.0 * 6.29
        expected_m3 = expected_mmbbl * _MMBBL_TO_M3
        assert abs(rec_oil - expected_m3) / expected_m3 < 0.01

    def test_none_values_stay_none(self):
        """Fields with None production should produce NaN in DataFrame."""
        raw = {
            "fldName": "EMPTY",
            "fldNpdidField": 99999,
            "fldStatus": "DISCOVERY",
            "fldCumulativeOilProduction": None,
            "fldCumulativeGasProduction": None,
            "fldCumulativeNGLProduction": None,
            "fldCumulativeCondensateProduction": None,
            "fldRecoverableOil": None,
            "fldRecoverableGas": None,
        }
        adapter = SodirAdapter(
            api_client=StubSodirAPIClient(fields=[raw], wellbores=[])
        )
        result = adapter.adapt("EMPTY")
        assert pd.isna(result.production["cumulative_oil_m3"].iloc[0])


# ---------------------------------------------------------------------------
# Tests — get_metadata()
# ---------------------------------------------------------------------------

class TestGetMetadata:
    def test_returns_source_metadata(self, adapter: SodirAdapter):
        meta = adapter.get_metadata()
        assert isinstance(meta, SourceMetadata)

    def test_source_id(self, adapter: SodirAdapter):
        assert adapter.get_metadata().source_id == "sodir"

    def test_jurisdiction(self, adapter: SodirAdapter):
        assert "Norwegian" in adapter.get_metadata().jurisdiction

    def test_update_cadence(self, adapter: SodirAdapter):
        assert adapter.get_metadata().update_cadence == "monthly"


# ---------------------------------------------------------------------------
# Tests — get_availability()
# ---------------------------------------------------------------------------

class TestGetAvailability:
    def test_returns_data_availability(self, adapter: SodirAdapter):
        avail = adapter.get_availability()
        assert isinstance(avail, DataAvailability)

    def test_wellbore_available(self, adapter: SodirAdapter):
        assert adapter.get_availability().wellbore.status == "available"

    def test_production_partial(self, adapter: SodirAdapter):
        assert adapter.get_availability().production.status == "partial"

    def test_casing_unavailable(self, adapter: SodirAdapter):
        assert adapter.get_availability().casing.status == "unavailable"

    def test_intervention_unavailable(self, adapter: SodirAdapter):
        assert adapter.get_availability().intervention.status == "unavailable"

    def test_drilling_completion_partial(self, adapter: SodirAdapter):
        assert adapter.get_availability().drilling_completion.status == "partial"

    def test_well_path_partial(self, adapter: SodirAdapter):
        assert adapter.get_availability().well_path.status == "partial"

    def test_source_id_matches(self, adapter: SodirAdapter):
        assert adapter.get_availability().source_id == "sodir"


# ---------------------------------------------------------------------------
# Tests — error resilience
# ---------------------------------------------------------------------------

class TestErrorResilience:
    def test_api_failure_no_crash(self, failing_adapter: SodirAdapter):
        result = failing_adapter.adapt("TROLL")
        assert isinstance(result, AdapterResult)

    def test_api_failure_produces_warnings(self, failing_adapter: SodirAdapter):
        result = failing_adapter.adapt("TROLL")
        assert any("Failed" in w for w in result.warnings)

    def test_api_failure_empty_dataframes(self, failing_adapter: SodirAdapter):
        result = failing_adapter.adapt("TROLL")
        assert result.wellbore_summary.empty
        assert result.drilling_activities.empty
        assert result.production.empty

    def test_field_fetch_fails_wellbores_still_attempted(self):
        adapter = SodirAdapter(api_client=FieldOnlyFailClient())
        result = adapter.adapt("TROLL")
        # Field fetch fails, but we still get a result
        assert isinstance(result, AdapterResult)
        field_warning = [w for w in result.warnings if "Failed to fetch fields" in w]
        assert len(field_warning) == 1

    def test_wellbore_fetch_fails_field_data_preserved(self):
        adapter = SodirAdapter(api_client=WellboreOnlyFailClient())
        result = adapter.adapt("TROLL")
        # Field data should still be there
        assert result.field_name == "TROLL"
        assert result.well_count == 0
        wb_warning = [w for w in result.warnings if "Failed to fetch wellbores" in w]
        assert len(wb_warning) == 1


# ---------------------------------------------------------------------------
# Tests — available_domains (inherited from AdapterInterface)
# ---------------------------------------------------------------------------

class TestAvailableDomains:
    def test_available_domains_list(self, adapter: SodirAdapter):
        domains = adapter.available_domains()
        assert "wellbore" in domains
        assert "drilling_completion" in domains
        assert "production" in domains
        # partial counts as available
        assert "well_path" in domains

    def test_unavailable_not_in_list(self, adapter: SodirAdapter):
        domains = adapter.available_domains()
        assert "casing" not in domains
        assert "intervention" not in domains


# ---------------------------------------------------------------------------
# Tests — leases tuple (SODIR doesn't use leases)
# ---------------------------------------------------------------------------

class TestLeases:
    def test_leases_empty_tuple(self, adapter: SodirAdapter):
        result = adapter.adapt("TROLL")
        assert result.leases == ()


# ---------------------------------------------------------------------------
# Tests — whitespace handling in query
# ---------------------------------------------------------------------------

class TestQueryNormalisation:
    def test_leading_trailing_spaces(self, adapter: SodirAdapter):
        result = adapter.adapt("  TROLL  ")
        assert result.field_name == "TROLL"
        assert result.field_code == "43777"
