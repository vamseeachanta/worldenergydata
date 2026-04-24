# ABOUTME: Tests for the Python query API (BSEE, FDAS, marine_safety).
# ABOUTME: Validates import paths, function signatures, filter logic, and calculations.

"""Tests for the worldenergydata query API layer.

Covers:
  - BSEE: ProductionQuery, WellsQuery, CompaniesQuery
  - FDAS: EconomicsQuery (NPV, IRR, MIRR, payback, all_metrics)
  - Marine Safety: IncidentsQuery

Uses mocking to avoid dependency on actual binary data files.
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# ==========================================================================
# BSEE Query API Tests
# ==========================================================================


class TestBSEEProductionQuery:
    """Tests for worldenergydata.bsee.api.ProductionQuery."""

    def test_import_production_query(self):
        """ProductionQuery is importable from bsee.api."""
        from worldenergydata.bsee.api import ProductionQuery

        assert ProductionQuery is not None

    def test_query_method_exists(self):
        """ProductionQuery.query has the expected signature."""
        from worldenergydata.bsee.api import ProductionQuery

        sig = inspect.signature(ProductionQuery.query)
        params = list(sig.parameters.keys())
        assert "lease" in params
        assert "year" in params
        assert "years" in params

    def test_annual_summary_method_exists(self):
        """ProductionQuery.annual_summary has the expected signature."""
        from worldenergydata.bsee.api import ProductionQuery

        sig = inspect.signature(ProductionQuery.annual_summary)
        assert "year" in sig.parameters

    @patch(
        "worldenergydata.bsee.data.loaders.production.production_loader.ProductionLoader.load"
    )
    def test_query_no_filters_returns_dataframe(self, mock_load):
        """query() with no filters returns whatever the loader provides."""
        from worldenergydata.bsee.api import ProductionQuery

        mock_df = pd.DataFrame(
            {
                "LEASE_NUMBER": ["G001", "G002"],
                "PROD_YEAR": [2022, 2023],
                "LEASE_OIL_PROD": [1000.0, 2000.0],
            }
        )
        mock_load.return_value = mock_df

        pq = ProductionQuery()
        result = pq.query()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    @patch(
        "worldenergydata.bsee.data.loaders.production.production_loader.ProductionLoader.load"
    )
    def test_query_no_data_returns_empty(self, mock_load):
        """query() returns empty DataFrame when loader has no data."""
        from worldenergydata.bsee.api import ProductionQuery

        mock_load.return_value = None

        pq = ProductionQuery()
        result = pq.query()
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @patch(
        "worldenergydata.bsee.data.loaders.production.production_loader.ProductionLoader.load"
    )
    def test_query_year_filter(self, mock_load):
        """query(years=...) filters by year range."""
        from worldenergydata.bsee.api import ProductionQuery

        mock_df = pd.DataFrame(
            {
                "LEASE_NUMBER": ["G001", "G002", "G003"],
                "PROD_YEAR": [2020, 2021, 2022],
                "LEASE_OIL_PROD": [100, 200, 300],
            }
        )
        mock_load.return_value = mock_df

        pq = ProductionQuery()
        result = pq.query(years=range(2021, 2023))
        assert len(result) == 2
        assert set(result["PROD_YEAR"].tolist()) == {2021, 2022}

    @patch(
        "worldenergydata.bsee.data.loaders.production.production_loader.ProductionLoader.load"
    )
    def test_query_lease_and_years_filter(self, mock_load):
        """query(lease=..., years=...) filters by both."""
        from worldenergydata.bsee.api import ProductionQuery

        mock_df = pd.DataFrame(
            {
                "LEASE_NUMBER": ["G001", "G001", "G002"],
                "PROD_YEAR": [2020, 2021, 2020],
                "LEASE_OIL_PROD": [100, 200, 300],
            }
        )
        mock_load.return_value = mock_df

        pq = ProductionQuery()
        result = pq.query(lease="G001", years=[2020])
        assert len(result) == 1
        assert result.iloc[0]["LEASE_NUMBER"] == "G001"
        assert result.iloc[0]["PROD_YEAR"] == 2020


class TestBSEEWellsQuery:
    """Tests for worldenergydata.bsee.api.WellsQuery."""

    def test_import_wells_query(self):
        """WellsQuery is importable from bsee.api."""
        from worldenergydata.bsee.api import WellsQuery

        assert WellsQuery is not None

    def test_query_method_signature(self):
        """WellsQuery.query has the expected parameters."""
        from worldenergydata.bsee.api import WellsQuery

        sig = inspect.signature(WellsQuery.query)
        params = list(sig.parameters.keys())
        assert "api_number" in params
        assert "field" in params
        assert "area_code" in params
        assert "water_depth_min" in params
        assert "water_depth_max" in params

    @patch(
        "worldenergydata.bsee.data.loaders.well.borehole_acquirer.BoreholeDataAcquirer.acquire_borehole_dataframe"
    )
    def test_query_no_data_returns_empty(self, mock_acquire):
        """query() returns empty DataFrame when no borehole data is cached."""
        from worldenergydata.bsee.api import WellsQuery

        mock_acquire.return_value = None

        wq = WellsQuery()
        result = wq.query()
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @patch(
        "worldenergydata.bsee.data.loaders.well.borehole_acquirer.BoreholeDataAcquirer.acquire_borehole_dataframe"
    )
    def test_query_area_code_filter(self, mock_acquire):
        """query(area_code=...) filters by BOTM_AREA_CODE."""
        from worldenergydata.bsee.api import WellsQuery

        mock_df = pd.DataFrame(
            {
                "API_WELL_NUMBER": ["001", "002", "003"],
                "BOTM_AREA_CODE": ["MC", "GC", "MC"],
                "BOTM_BLOCK_NUMBER": ["778", "680", "255"],
                "WATER_DEPTH": [6500.0, 4300.0, 3200.0],
            }
        )
        mock_acquire.return_value = mock_df

        wq = WellsQuery()
        result = wq.query(area_code="MC")
        assert len(result) == 2
        assert all(
            r.strip().upper() == "MC" for r in result["BOTM_AREA_CODE"].astype(str)
        )

    @patch(
        "worldenergydata.bsee.data.loaders.well.borehole_acquirer.BoreholeDataAcquirer.acquire_borehole_dataframe"
    )
    def test_query_water_depth_filter(self, mock_acquire):
        """query(water_depth_min=...) filters by WATER_DEPTH."""
        from worldenergydata.bsee.api import WellsQuery

        mock_df = pd.DataFrame(
            {
                "API_WELL_NUMBER": ["001", "002", "003"],
                "BOTM_AREA_CODE": ["MC", "GC", "MC"],
                "BOTM_BLOCK_NUMBER": ["778", "680", "255"],
                "WATER_DEPTH": [6500.0, 4300.0, 3200.0],
            }
        )
        mock_acquire.return_value = mock_df

        wq = WellsQuery()
        result = wq.query(water_depth_min=5000)
        assert len(result) == 1
        assert result.iloc[0]["WATER_DEPTH"] == 6500.0


class TestBSEECompaniesQuery:
    """Tests for worldenergydata.bsee.api.CompaniesQuery."""

    def test_import_companies_query(self):
        """CompaniesQuery is importable from bsee.api."""
        from worldenergydata.bsee.api import CompaniesQuery

        assert CompaniesQuery is not None

    def test_query_method_signature(self):
        """CompaniesQuery.query has the expected parameters."""
        from worldenergydata.bsee.api import CompaniesQuery

        sig = inspect.signature(CompaniesQuery.query)
        params = list(sig.parameters.keys())
        assert "name" in params
        assert "operator_id" in params
        assert "region" in params
        assert "include_inactive" in params

    @patch(
        "worldenergydata.bsee.data.loaders.company.company_loader.CompanyLoader.load_active"
    )
    def test_query_no_data_returns_empty(self, mock_load):
        """query() returns empty DataFrame when no company data available."""
        from worldenergydata.bsee.api import CompaniesQuery

        mock_load.return_value = None

        cq = CompaniesQuery()
        result = cq.query()
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @patch(
        "worldenergydata.bsee.data.loaders.company.company_loader.CompanyLoader.load_active"
    )
    def test_query_returns_all_active(self, mock_load):
        """query() with no filters returns all active companies."""
        from worldenergydata.bsee.api import CompaniesQuery

        mock_df = pd.DataFrame(
            {
                "MMS_COMPANY_NUM": [100, 200, 300],
                "BUS_ASC_NAME": ["Shell", "BP", "Chevron"],
            }
        )
        mock_load.return_value = mock_df

        cq = CompaniesQuery()
        result = cq.query()
        assert len(result) == 3

    @patch(
        "worldenergydata.bsee.data.loaders.company.company_loader.CompanyLoader.get_by_company_name"
    )
    def test_query_name_filter(self, mock_get):
        """query(name=...) delegates to get_by_company_name."""
        from worldenergydata.bsee.api import CompaniesQuery

        mock_get.return_value = pd.DataFrame(
            {"MMS_COMPANY_NUM": [100], "BUS_ASC_NAME": ["Shell"]}
        )

        cq = CompaniesQuery()
        result = cq.query(name="Shell")
        mock_get.assert_called_once_with("Shell")
        assert len(result) == 1


# ==========================================================================
# FDAS Economics Query API Tests
# ==========================================================================


class TestFDASEconomicsQuery:
    """Tests for worldenergydata.fdas.api.EconomicsQuery."""

    def test_import_economics_query(self):
        """EconomicsQuery is importable from fdas.api."""
        from worldenergydata.fdas.api import EconomicsQuery

        assert EconomicsQuery is not None

    def test_npv_method_signature(self):
        """EconomicsQuery.npv has the expected parameters."""
        from worldenergydata.fdas.api import EconomicsQuery

        sig = inspect.signature(EconomicsQuery.npv)
        params = list(sig.parameters.keys())
        assert "cashflows" in params
        assert "discount_rate" in params
        assert "period" in params
        assert "trimmed" in params

    def test_npv_calculation(self):
        """NPV calculation returns a reasonable float value."""
        from worldenergydata.fdas.api import EconomicsQuery

        # Simple annual cashflow: -1000 today, +600 year 1, +600 year 2
        cashflows = [-1000, 600, 600]
        npv = EconomicsQuery.npv(cashflows, discount_rate=0.10, period="annual")
        assert isinstance(npv, float)
        # At 10% annual: NPV = -1000 + 600/1.1 + 600/1.21 = ~41.32
        assert npv > 0  # Should be positive

    def test_npv_negative_result(self):
        """NPV returns negative for poor cashflows."""
        from worldenergydata.fdas.api import EconomicsQuery

        cashflows = [-1000, 50, 50]
        npv = EconomicsQuery.npv(cashflows, discount_rate=0.10, period="annual")
        assert npv < 0

    def test_npv_accepts_list(self):
        """NPV accepts plain Python list (not just numpy arrays)."""
        from worldenergydata.fdas.api import EconomicsQuery

        npv = EconomicsQuery.npv([-100, 50, 50, 50], 0.05, period="annual")
        assert isinstance(npv, float)

    def test_npv_accepts_numpy_array(self):
        """NPV accepts numpy array input."""
        from worldenergydata.fdas.api import EconomicsQuery

        cf = np.array([-100, 50, 50, 50])
        npv = EconomicsQuery.npv(cf, 0.05, period="annual")
        assert isinstance(npv, float)

    def test_irr_calculation(self):
        """IRR returns a tuple of (period_irr, annual_irr)."""
        from worldenergydata.fdas.api import EconomicsQuery

        cashflows = [-1000, 200, 300, 400, 500]
        result = EconomicsQuery.irr(cashflows, period="annual")
        assert isinstance(result, tuple)
        assert len(result) == 2
        period_irr, annual_irr = result
        assert isinstance(period_irr, float)
        assert isinstance(annual_irr, float)
        # For annual period, they should be equal
        assert abs(period_irr - annual_irr) < 1e-10

    def test_mirr_calculation(self):
        """MIRR returns a tuple of (monthly_mirr, annual_mirr)."""
        from worldenergydata.fdas.api import EconomicsQuery

        cashflows = [-1000, 100, 200, 300, 400, 500]
        result = EconomicsQuery.mirr(cashflows, discount_rate=0.10)
        assert isinstance(result, tuple)
        assert len(result) == 2
        mirr_m, mirr_a = result
        assert isinstance(mirr_m, float)
        assert isinstance(mirr_a, float)

    def test_payback_period_calculation(self):
        """payback_period returns (periods, years)."""
        from worldenergydata.fdas.api import EconomicsQuery

        # -100 + 50 + 50 = 0 at period 2
        cashflows = [-100, 50, 50, 50]
        periods, years = EconomicsQuery.payback_period(cashflows, period="annual")
        assert isinstance(periods, int)
        assert isinstance(years, float)
        assert periods == 2  # Cumulative turns non-negative at index 2

    def test_all_metrics(self):
        """all_metrics returns a dict with expected keys."""
        from worldenergydata.fdas.api import EconomicsQuery

        cashflows = [-1000, 100, 200, 300, 400, 500]
        result = EconomicsQuery.all_metrics(cashflows, 0.10, period="annual")
        assert isinstance(result, dict)
        assert "npv" in result
        assert "mirr_annual" in result
        assert "irr_annual" in result
        assert "payback_years" in result

    def test_validate_cashflows(self):
        """validate_cashflows returns diagnostic dict."""
        from worldenergydata.fdas.api import EconomicsQuery

        info = EconomicsQuery.validate_cashflows([-1000, 100, 200])
        assert isinstance(info, dict)
        assert info["has_both_signs"] is True
        assert info["has_nonzero"] is True
        assert info["length"] == 3


# ==========================================================================
# FDAS Disclosure Analytics Query API Tests (issue #338)
# ==========================================================================


class TestFDASDisclosureAnalyticsQuery:
    """Tests for worldenergydata.fdas.api.DisclosureAnalyticsQuery (issue #338)."""

    def test_import_disclosure_analytics_query(self):
        """DisclosureAnalyticsQuery is importable from fdas.api."""
        from worldenergydata.fdas.api import DisclosureAnalyticsQuery

        assert DisclosureAnalyticsQuery is not None

    def test_project_revision_method_signature(self):
        """DisclosureAnalyticsQuery.project_revision accepts a records iterable."""
        from worldenergydata.fdas.api import DisclosureAnalyticsQuery

        sig = inspect.signature(DisclosureAnalyticsQuery.project_revision)
        params = list(sig.parameters.keys())
        assert "records" in params

    def test_operator_capex_method_signature(self):
        from worldenergydata.fdas.api import DisclosureAnalyticsQuery

        sig = inspect.signature(DisclosureAnalyticsQuery.operator_capex)
        params = list(sig.parameters.keys())
        assert "records" in params

    def test_benchmark_method_signature(self):
        from worldenergydata.fdas.api import DisclosureAnalyticsQuery

        sig = inspect.signature(DisclosureAnalyticsQuery.benchmark)
        params = list(sig.parameters.keys())
        assert "project_revision_view" in params
        assert "predictor_cost_usd_mm" in params
        assert "operator" in params
        assert "project_name" in params

    def test_project_revision_returns_derived_rows(self):
        """End-to-end: FDAS seam delegates to cost.disclosure_analytics."""
        from worldenergydata.cost.disclosure_analytics import (
            SCOPE_PROJECT,
            DisclosureRecord,
            ProjectRevisionRow,
        )
        from worldenergydata.fdas.api import DisclosureAnalyticsQuery

        records = [
            DisclosureRecord(
                operator="AcmeCorp",
                fiscal_year=2022,
                reported_capex_usd_mm=900.0,
                scope=SCOPE_PROJECT,
                project_name="Mariner-A",
                provenance={"source": "10-K"},
            ),
        ]
        view = DisclosureAnalyticsQuery.project_revision(records)
        assert len(view) == 1
        assert isinstance(view[0], ProjectRevisionRow)
        assert view[0].yoy_delta_usd_mm is None

    def test_benchmark_refuses_non_comparable_rows(self):
        """Comparability gating is enforced at the FDAS seam too."""
        from worldenergydata.cost.disclosure_analytics import (
            SCOPE_PROJECT,
            DisclosureRecord,
        )
        from worldenergydata.fdas.api import DisclosureAnalyticsQuery

        records = [
            DisclosureRecord(
                operator="AcmeCorp",
                fiscal_year=2022,
                reported_capex_usd_mm=900.0,
                scope=SCOPE_PROJECT,
                project_name="Mariner-A",
                provenance={"source": "10-K"},
                comparability_status=None,  # missing -> must refuse
            ),
        ]
        view = DisclosureAnalyticsQuery.project_revision(records)
        result = DisclosureAnalyticsQuery.benchmark(
            view,
            predictor_cost_usd_mm=1000.0,
            operator="AcmeCorp",
            project_name="Mariner-A",
        )
        assert result is None


# ==========================================================================
# Marine Safety Query API Tests
# ==========================================================================


class TestMarineSafetyIncidentsQuery:
    """Tests for worldenergydata.marine_safety.api.IncidentsQuery."""

    def test_import_incidents_query(self):
        """IncidentsQuery is importable from marine_safety.api."""
        from worldenergydata.marine_safety.api import IncidentsQuery

        assert IncidentsQuery is not None

    def test_query_method_signature(self):
        """IncidentsQuery.query has the expected parameters."""
        from worldenergydata.marine_safety.api import IncidentsQuery

        sig = inspect.signature(IncidentsQuery.query)
        params = list(sig.parameters.keys())
        assert "source" in params
        assert "sources" in params
        assert "year" in params
        assert "start_year" in params
        assert "end_year" in params
        assert "vessel_type" in params
        assert "incident_type" in params
        assert "region" in params

    def test_query_returns_dataframe(self):
        """query() with no filters returns a DataFrame (synthetic data)."""
        from worldenergydata.marine_safety.api import IncidentsQuery

        iq = IncidentsQuery()
        result = iq.query()
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        # Verify expected columns
        expected_cols = {"source", "incident_id", "date", "incident_type"}
        assert expected_cols.issubset(set(result.columns))

    def test_query_source_filter(self):
        """query(source=...) filters to a single source."""
        from worldenergydata.marine_safety.api import IncidentsQuery

        iq = IncidentsQuery()
        result = iq.query(source="maib")
        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert all(result["source"] == "maib")

    def test_query_year_filter(self):
        """query(year=...) filters to a single year."""
        from worldenergydata.marine_safety.api import IncidentsQuery

        iq = IncidentsQuery()
        # Get all data first to find a year that exists
        all_data = iq.query()
        if not all_data.empty and "date" in all_data.columns:
            years = pd.to_datetime(all_data["date"], errors="coerce").dt.year
            valid_years = years.dropna()
            if not valid_years.empty:
                test_year = int(valid_years.iloc[0])
                result = iq.query(year=test_year)
                assert isinstance(result, pd.DataFrame)

    def test_query_vessel_type_filter(self):
        """query(vessel_type=...) filters by vessel type."""
        from worldenergydata.marine_safety.api import IncidentsQuery

        iq = IncidentsQuery()
        result = iq.query(vessel_type="tanker")
        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert all(result["vessel_type"] == "tanker")

    def test_query_incident_type_filter(self):
        """query(incident_type=...) filters by incident type."""
        from worldenergydata.marine_safety.api import IncidentsQuery

        iq = IncidentsQuery()
        result = iq.query(incident_type="collision")
        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert all(result["incident_type"] == "collision")

    def test_query_multiple_sources(self):
        """query(sources=[...]) filters to multiple sources."""
        from worldenergydata.marine_safety.api import IncidentsQuery

        iq = IncidentsQuery()
        result = iq.query(sources=["maib", "imo"])
        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert set(result["source"].unique()).issubset({"maib", "imo"})

    def test_trends_returns_dataframe(self):
        """trends() returns a DataFrame with year/source/count columns."""
        from worldenergydata.marine_safety.api import IncidentsQuery

        iq = IncidentsQuery()
        data = iq.query()
        if not data.empty:
            trends = iq.trends(data)
            assert isinstance(trends, pd.DataFrame)
            assert "count" in trends.columns

    def test_top_types_returns_dataframe(self):
        """top_types() returns a DataFrame with incident_type and count."""
        from worldenergydata.marine_safety.api import IncidentsQuery

        iq = IncidentsQuery()
        data = iq.query()
        if not data.empty:
            top = iq.top_types(data, n=3)
            assert isinstance(top, pd.DataFrame)
            assert len(top) <= 3


# ==========================================================================
# Package-level import tests
# ==========================================================================


class TestPackageLevelImports:
    """Test that query APIs are accessible via top-level package imports."""

    def test_bsee_api_accessible(self):
        """wed.bsee.production/wells/companies should be accessible."""
        import worldenergydata as wed

        bsee_mod = wed.bsee
        # These are lazy-loaded via bsee/__init__.py __getattr__
        assert bsee_mod.production is not None
        assert bsee_mod.wells is not None
        assert bsee_mod.companies is not None

    def test_fdas_api_accessible(self):
        """wed.fdas.economics should be accessible."""
        import worldenergydata as wed

        fdas_mod = wed.fdas
        # Lazy-loaded via fdas/__init__.py __getattr__
        assert fdas_mod.economics is not None

    def test_fdas_disclosure_analytics_accessible(self):
        """wed.fdas.disclosure_analytics should be accessible (issue #338)."""
        import worldenergydata as wed

        fdas_mod = wed.fdas
        # Lazy-loaded via fdas/__init__.py __getattr__
        assert fdas_mod.disclosure_analytics is not None
        # Must be the same class as defined in fdas.api — no divergent surface.
        from worldenergydata.fdas.api import DisclosureAnalyticsQuery

        assert isinstance(fdas_mod.disclosure_analytics, DisclosureAnalyticsQuery)

    def test_marine_safety_api_accessible(self):
        """wed.marine_safety_api should resolve to marine_safety.api module."""
        import worldenergydata as wed

        ms_api = wed.marine_safety_api
        assert hasattr(ms_api, "incidents")

    def test_bsee_production_query_callable(self):
        """wed.bsee.production.query is callable."""
        import worldenergydata as wed

        assert callable(wed.bsee.production.query)

    def test_fdas_economics_npv_callable(self):
        """wed.fdas.economics.npv is callable."""
        import worldenergydata as wed

        assert callable(wed.fdas.economics.npv)

    def test_fdas_disclosure_analytics_callables(self):
        """wed.fdas.disclosure_analytics exposes project_revision/operator_capex/benchmark."""
        import worldenergydata as wed

        ns = wed.fdas.disclosure_analytics
        assert callable(ns.project_revision)
        assert callable(ns.operator_capex)
        assert callable(ns.benchmark)

    def test_marine_safety_incidents_query_callable(self):
        """wed.marine_safety_api.incidents.query is callable."""
        import worldenergydata as wed

        assert callable(wed.marine_safety_api.incidents.query)

    def test_unknown_attribute_raises(self):
        """Accessing unknown attribute raises AttributeError."""
        import worldenergydata as wed

        with pytest.raises(AttributeError):
            _ = wed.nonexistent_module_xyz
