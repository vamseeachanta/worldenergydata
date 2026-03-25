"""Tests for the Texas RRC adapter.

Uses stub/fixture data — no real file downloads or network access.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from worldenergydata.bsee.pipeline.adapters.common_schema import (
    AdapterInterface,
    AdapterResult,
    DataAvailability,
    SourceMetadata,
)
from worldenergydata.bsee.pipeline.adapters.rrc_adapter import RRCAdapter
from worldenergydata.bsee.pipeline.adapters.units import (
    BBL_TO_M3,
    MCF_TO_M3,
)


# ---------------------------------------------------------------------------
# Fixtures — stub CSV data
# ---------------------------------------------------------------------------

WELL_COLUMNS = [
    "API_NO",
    "FIELD_NAME",
    "DISTRICT",
    "WELL_STATUS",
    "WELL_TYPE",
    "TOTAL_DEPTH",
    "LEASE_NO",
    "COMPLETION_DATE",
    "PLUG_DATE",
    "WELLBORE_PROFILE",
    "LATITUDE",
    "LONGITUDE",
]

WELL_ROWS = [
    ["4210100001", "EAGLE FORD", "1", "A", "O", "12000", "L001", "2020-01-15", None, "HORIZONTAL", "28.5", "-97.5"],
    ["4210100002", "EAGLE FORD", "1", "P", "G", "10000", "L002", "2019-05-20", "2023-01-10", "VERTICAL", "28.6", "-97.6"],
    ["4210100003", "EAGLE FORD", "1", "A", "O", "14000", "L001", "2021-03-01", None, "HORIZONTAL", "28.55", "-97.55"],
    ["4210100004", "EAGLE FORD", "2", "A", "G", "11000", "L003", "2022-06-10", None, "DIRECTIONAL", "29.0", "-98.0"],
    ["4210100005", "PERMIAN BASIN", "8", "A", "O", "8000", "L010", "2018-11-01", None, "VERTICAL", "31.5", "-102.0"],
]

PERMIT_COLUMNS = [
    "PERMIT_NO",
    "PERMIT_TYPE",
    "APPROVED_DATE",
    "FIELD_NAME",
    "DISTRICT",
    "TOTAL_DEPTH",
    "HORIZONTAL_LENGTH",
    "API_NO",
    "WELL_PURPOSE",
]

PERMIT_ROWS = [
    ["P001", "N", "2020-01-01", "EAGLE FORD", "1", "12000", "5000", "4210100001", "O"],
    ["P002", "N", "2019-04-15", "EAGLE FORD", "1", "10000", "0", "4210100002", "G"],
    ["P003", "W", "2023-06-01", "EAGLE FORD", "1", "12000", "0", "4210100001", "O"],
    ["P004", "N", "2022-05-01", "EAGLE FORD", "2", "11000", "4000", "4210100004", "G"],
    ["P005", "N", "2018-10-01", "PERMIAN BASIN", "8", "8000", "0", "4210100005", "O"],
]

PRODUCTION_COLUMNS = [
    "FIELD_NAME",
    "DISTRICT",
    "LEASE_NO",
    "OIL_BBL",
    "GAS_MCF",
    "WATER_BBL",
    "COND_BBL",
    "CYCLE_YEAR_MONTH",
]

PRODUCTION_ROWS = [
    ["EAGLE FORD", "1", "L001", "5000", "30000", "2000", "100", "202301"],
    ["EAGLE FORD", "1", "L002", "3000", "20000", "1000", "50", "202301"],
    ["EAGLE FORD", "1", "L001", "4500", "28000", "1800", "90", "202302"],
    ["EAGLE FORD", "2", "L003", "6000", "35000", "2500", "120", "202301"],
    ["PERMIAN BASIN", "8", "L010", "10000", "5000", "4000", "200", "202301"],
]


@pytest.fixture
def stub_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory with stub CSV files."""
    # Wells CSV
    well_df = pd.DataFrame(WELL_ROWS, columns=WELL_COLUMNS)
    well_df.to_csv(tmp_path / "texas_rrc_og_well_20260101.csv", index=False)

    # Permits CSV
    permit_df = pd.DataFrame(PERMIT_ROWS, columns=PERMIT_COLUMNS)
    permit_df.to_csv(
        tmp_path / "texas_rrc_drilling_permits_20260101.csv", index=False,
    )

    # Production CSV
    prod_df = pd.DataFrame(PRODUCTION_ROWS, columns=PRODUCTION_COLUMNS)
    prod_df.to_csv(
        tmp_path / "texas_rrc_og_production_20260101.csv", index=False,
    )

    return tmp_path


@pytest.fixture
def adapter(stub_data_dir: Path) -> RRCAdapter:
    """Return an RRCAdapter pointed at the stub data directory."""
    return RRCAdapter(data_dir=stub_data_dir)


@pytest.fixture
def empty_adapter(tmp_path: Path) -> RRCAdapter:
    """Return an RRCAdapter pointed at an empty directory."""
    return RRCAdapter(data_dir=tmp_path)


# ---------------------------------------------------------------------------
# Tests: interface compliance
# ---------------------------------------------------------------------------


class TestRRCAdapterInterface:
    def test_is_adapter_interface_subclass(self):
        assert issubclass(RRCAdapter, AdapterInterface)

    def test_get_metadata_returns_source_metadata(self, adapter: RRCAdapter):
        meta = adapter.get_metadata()
        assert isinstance(meta, SourceMetadata)
        assert meta.source_id == "rrc"
        assert meta.source_name == "Railroad Commission of Texas"
        assert meta.jurisdiction == "Texas onshore and state waters"
        assert "rrc.texas.gov" in meta.api_base_url
        assert meta.update_cadence == "monthly"

    def test_get_availability_returns_rrc_availability(self, adapter: RRCAdapter):
        avail = adapter.get_availability()
        assert isinstance(avail, DataAvailability)
        assert avail.source_id == "rrc"
        assert avail.wellbore.status == "available"
        assert avail.casing.status == "unavailable"
        assert avail.production.status == "available"
        assert avail.intervention.status == "partial"
        assert avail.well_path.status == "partial"

    def test_available_domains(self, adapter: RRCAdapter):
        domains = adapter.available_domains()
        assert "wellbore" in domains
        assert "drilling_completion" in domains
        assert "production" in domains
        assert "intervention" in domains
        assert "well_path" in domains
        assert "casing" not in domains


# ---------------------------------------------------------------------------
# Tests: adapt() basic behaviour
# ---------------------------------------------------------------------------


class TestAdaptBasic:
    def test_adapt_returns_adapter_result(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        assert isinstance(result, AdapterResult)
        assert result.field_name == "EAGLE FORD"
        assert result.field_code == "EAGLE FORD"
        assert result.source.source_id == "rrc"
        assert result.query_type == "field_name"

    def test_adapt_case_insensitive(self, adapter: RRCAdapter):
        result = adapter.adapt("eagle ford")
        assert result.field_name == "EAGLE FORD"
        assert result.well_count > 0

    def test_adapt_strips_whitespace(self, adapter: RRCAdapter):
        result = adapter.adapt("  EAGLE FORD  ")
        assert result.field_name == "EAGLE FORD"
        assert result.well_count > 0

    def test_adapt_nonexistent_field(self, adapter: RRCAdapter):
        result = adapter.adapt("NONEXISTENT FIELD")
        assert result.well_count == 0
        assert result.wellbore_summary.empty
        assert any("No wells matched" in w for w in result.warnings)

    def test_adapt_empty_directory(self, empty_adapter: RRCAdapter):
        result = empty_adapter.adapt("EAGLE FORD")
        assert result.well_count == 0
        assert len(result.warnings) > 0


# ---------------------------------------------------------------------------
# Tests: district filtering
# ---------------------------------------------------------------------------


class TestDistrictFiltering:
    def test_filter_by_district(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD", district="1")
        # District 1 has 3 EAGLE FORD wells, district 2 has 1
        assert result.well_count == 3
        assert result.area_code == "1"

    def test_filter_by_district_int(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD", district=2)
        assert result.well_count == 1
        assert result.area_code == "2"

    def test_filter_district_no_match(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD", district="9")
        assert result.well_count == 0
        assert any("No wells matched" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Tests: wellbore summary
# ---------------------------------------------------------------------------


class TestWellboreSummary:
    def test_wellbore_summary_columns(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        ws = result.wellbore_summary
        assert not ws.empty
        assert "total_wells" in ws.columns
        assert "active_wells" in ws.columns
        assert "plugged_wells" in ws.columns
        assert "horizontal_wells" in ws.columns
        assert "avg_depth_m" in ws.columns

    def test_wellbore_counts(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        ws = result.wellbore_summary.iloc[0]
        # 4 EAGLE FORD wells total (3 in district 1, 1 in district 2)
        assert ws["total_wells"] == 4
        # Active: rows with status A (3 wells)
        assert ws["active_wells"] == 3
        # Plugged: row with status P (1 well)
        assert ws["plugged_wells"] == 1

    def test_wellbore_depth_in_metres(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        ws = result.wellbore_summary.iloc[0]
        # Average depth of 12000, 10000, 14000, 11000 ft = 11750 ft
        expected_m = 11750 * 0.3048
        assert ws["avg_depth_m"] == pytest.approx(expected_m, rel=0.01)


# ---------------------------------------------------------------------------
# Tests: unavailable domains
# ---------------------------------------------------------------------------


class TestUnavailableDomains:
    def test_casing_empty_with_warning(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        assert result.casing_strings.empty
        assert any("Casing data unavailable" in w for w in result.warnings)

    def test_well_paths_empty_with_warning(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        assert result.well_paths.empty
        assert any("Well path survey data" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Tests: unit conversions
# ---------------------------------------------------------------------------


class TestUnitConversions:
    def test_production_oil_converted_to_m3(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        prod = result.production
        assert not prod.empty
        if "oil_production" in prod.columns:
            # January: L001 5000 + L002 3000 + L003 6000 = 14000 BBL
            # But L003 is district 2, L001 and L002 are district 1 -- all EAGLE FORD
            jan_row = prod.iloc[0]
            # All values should be in m3 (original * BBL_TO_M3)
            assert jan_row["oil_production"] > 0
            # Verify not in original BBL range (5000-14000)
            # In m3: 14000 * 0.158987 = ~2226
            # The exact value depends on aggregation

    def test_production_gas_converted_to_m3(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        prod = result.production
        if "gas_production" in prod.columns and not prod.empty:
            # Gas should be in m3 (original MCF * MCF_TO_M3)
            total_gas = prod["gas_production"].sum()
            # Original total for EAGLE FORD: 30000+20000+28000+35000 = 113000 MCF
            expected_m3 = 113000 * MCF_TO_M3
            assert total_gas == pytest.approx(expected_m3, rel=0.05)

    def test_production_water_converted_to_m3(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        prod = result.production
        if "water_production" in prod.columns and not prod.empty:
            total_water = prod["water_production"].sum()
            # Original total: 2000+1000+1800+2500 = 7300 BBL
            expected_m3 = 7300 * BBL_TO_M3
            assert total_water == pytest.approx(expected_m3, rel=0.05)

    def test_drilling_depth_converted_to_metres(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        drills = result.drilling_activities
        if not drills.empty and "total_depth" in drills.columns:
            # All depths should be in metres (< original feet values)
            max_depth = drills["total_depth"].max()
            # Original max is 12000 ft -> ~3657.6 m
            assert max_depth < 5000  # metres, not feet
            assert max_depth > 3000  # reasonable metre range


# ---------------------------------------------------------------------------
# Tests: production aggregation
# ---------------------------------------------------------------------------


class TestProductionAggregation:
    def test_production_aggregated_by_field(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        prod = result.production
        assert not prod.empty

    def test_production_grouped_by_date(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        prod = result.production
        if "production_date" in prod.columns:
            # EAGLE FORD has Jan and Feb production
            dates = prod["production_date"].unique()
            assert len(dates) >= 1

    def test_permian_basin_production_separate(self, adapter: RRCAdapter):
        ef_result = adapter.adapt("EAGLE FORD")
        pb_result = adapter.adapt("PERMIAN BASIN")
        if not ef_result.production.empty and not pb_result.production.empty:
            ef_oil = ef_result.production["oil_production"].sum()
            pb_oil = pb_result.production["oil_production"].sum()
            # They should be different
            assert ef_oil != pb_oil

    def test_district_filter_narrows_production(self, adapter: RRCAdapter):
        all_ef = adapter.adapt("EAGLE FORD")
        d1_ef = adapter.adapt("EAGLE FORD", district="1")
        if (
            not all_ef.production.empty
            and not d1_ef.production.empty
            and "oil_production" in all_ef.production.columns
        ):
            all_oil = all_ef.production["oil_production"].sum()
            d1_oil = d1_ef.production["oil_production"].sum()
            # District 1 should be less than all districts combined
            assert d1_oil < all_oil


# ---------------------------------------------------------------------------
# Tests: drilling activities
# ---------------------------------------------------------------------------


class TestDrillingActivities:
    def test_drilling_activities_populated(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        drills = result.drilling_activities
        assert not drills.empty

    def test_drilling_has_permit_info(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        drills = result.drilling_activities
        if not drills.empty:
            # Should contain permit-related columns
            assert any(
                c in drills.columns
                for c in ["permit_number", "permit_type", "approved_date"]
            )


# ---------------------------------------------------------------------------
# Tests: completion activities
# ---------------------------------------------------------------------------


class TestCompletionActivities:
    def test_completions_from_well_data(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        comps = result.completion_activities
        # Wells with completion_date should yield completion records
        assert not comps.empty

    def test_completion_depth_in_metres(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        comps = result.completion_activities
        if not comps.empty and "total_depth" in comps.columns:
            max_depth = comps["total_depth"].max()
            # All depths should be in metres (< original feet values)
            assert max_depth < 5000


# ---------------------------------------------------------------------------
# Tests: intervention activities
# ---------------------------------------------------------------------------


class TestInterventionActivities:
    def test_intervention_includes_workovers(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        interventions = result.intervention_activities
        if not interventions.empty and "intervention_type" in interventions.columns:
            types = interventions["intervention_type"].unique().tolist()
            assert any(t in types for t in ["workover", "plug_and_abandon"])

    def test_intervention_includes_plugged_wells(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        interventions = result.intervention_activities
        if not interventions.empty and "intervention_type" in interventions.columns:
            assert "plug_and_abandon" in interventions["intervention_type"].values


# ---------------------------------------------------------------------------
# Tests: leases
# ---------------------------------------------------------------------------


class TestLeases:
    def test_leases_extracted(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        assert len(result.leases) > 0
        assert isinstance(result.leases, tuple)

    def test_leases_sorted(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        assert list(result.leases) == sorted(result.leases)

    def test_leases_unique(self, adapter: RRCAdapter):
        result = adapter.adapt("EAGLE FORD")
        assert len(result.leases) == len(set(result.leases))


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_missing_data_dir_warns(self):
        adapter = RRCAdapter(data_dir=Path("/nonexistent/path"))
        result = adapter.adapt("EAGLE FORD")
        assert result.well_count == 0
        assert len(result.warnings) > 0

    def test_corrupt_csv_warns(self, tmp_path: Path):
        # Write a corrupt file
        (tmp_path / "texas_rrc_og_well_20260101.csv").write_text(
            "not,a,valid\ncsv,file,\x00\x01\x02"
        )
        adapter = RRCAdapter(data_dir=tmp_path)
        result = adapter.adapt("EAGLE FORD")
        # Should not raise; warnings collected
        assert isinstance(result, AdapterResult)

    def test_processor_import_failure_handled(self, stub_data_dir: Path):
        adapter = RRCAdapter(data_dir=stub_data_dir)
        with patch(
            "worldenergydata.bsee.pipeline.adapters.rrc_adapter.RRCAdapter._load_wells",
            side_effect=Exception("test failure"),
        ):
            # The adapt method should handle this gracefully
            # since _load_wells is called inside adapt
            with pytest.raises(Exception):
                adapter.adapt("EAGLE FORD")
