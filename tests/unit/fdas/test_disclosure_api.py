# ABOUTME: Tests for the FDAS disclosure analytics namespace/query seam (issue #338).
# ABOUTME: Verifies explicit grounding in fdas/api.py + lazy export via fdas/__init__.py.

"""Tests for ``worldenergydata.fdas.api.DisclosureAnalyticsQuery``.

The FDAS consumer-facing surface for annual disclosure analytics lives in
``fdas/api.py``. It must:

  - be explicitly named and importable from that module,
  - be reachable via the lazy attribute pattern on the ``fdas`` package,
  - delegate to ``cost.disclosure_analytics`` (no duplicated logic),
  - not regress the existing ``economics`` namespace.
"""

from __future__ import annotations

import importlib
import inspect

import pytest


@pytest.fixture
def analytics_module():
    return importlib.import_module("worldenergydata.cost.disclosure_analytics")


@pytest.fixture
def sample_records(analytics_module):
    DR = analytics_module.DisclosureRecord
    return [
        DR(
            operator="AcmeCorp",
            fiscal_year=2021,
            reported_capex_usd_mm=800.0,
            scope=analytics_module.SCOPE_PROJECT,
            project_name="Mariner-A",
            provenance={"source": "10-K"},
        ),
        DR(
            operator="AcmeCorp",
            fiscal_year=2022,
            reported_capex_usd_mm=900.0,
            scope=analytics_module.SCOPE_PROJECT,
            project_name="Mariner-A",
            provenance={"source": "10-K"},
        ),
        DR(
            operator="AcmeCorp",
            fiscal_year=2021,
            reported_capex_usd_mm=4200.0,
            scope=analytics_module.SCOPE_OPERATOR,
            provenance={"source": "10-K"},
        ),
        DR(
            operator="AcmeCorp",
            fiscal_year=2022,
            reported_capex_usd_mm=5000.0,
            scope=analytics_module.SCOPE_OPERATOR,
            provenance={"source": "10-K"},
        ),
    ]


# --------------------------------------------------------------------------
# API seam grounding — the plan requires the surface be hosted explicitly
# in fdas/api.py, not as a loose package attribute.
# --------------------------------------------------------------------------


class TestDisclosureAnalyticsAPISeam:
    def test_fdas_api_module_defines_disclosure_analytics_query_class(self):
        api = importlib.import_module("worldenergydata.fdas.api")
        assert hasattr(api, "DisclosureAnalyticsQuery")
        assert inspect.isclass(api.DisclosureAnalyticsQuery)

    def test_fdas_api_module_exposes_disclosure_analytics_singleton(self):
        api = importlib.import_module("worldenergydata.fdas.api")
        assert hasattr(api, "disclosure_analytics")
        assert isinstance(api.disclosure_analytics, api.DisclosureAnalyticsQuery)

    def test_disclosure_query_has_project_and_operator_methods(self):
        api = importlib.import_module("worldenergydata.fdas.api")
        cls = api.DisclosureAnalyticsQuery
        assert callable(getattr(cls, "project_revision", None))
        assert callable(getattr(cls, "operator_capex", None))
        assert callable(getattr(cls, "benchmark", None))


# --------------------------------------------------------------------------
# Lazy export via fdas/__init__.py
# --------------------------------------------------------------------------


class TestFDASPackageLazyExport:
    def test_fdas_exposes_disclosure_analytics_namespace(self):
        fdas = importlib.import_module("worldenergydata.fdas")
        ns = fdas.disclosure_analytics
        assert ns is not None

    def test_fdas_package_still_exposes_economics_namespace(self):
        """Regression guard — #338 must not break the #288 query API seam."""
        fdas = importlib.import_module("worldenergydata.fdas")
        assert fdas.economics is not None

    def test_fdas_package_unknown_attribute_still_raises(self):
        fdas = importlib.import_module("worldenergydata.fdas")
        with pytest.raises(AttributeError):
            _ = fdas.nonexistent_attribute_xyz


# --------------------------------------------------------------------------
# Query behavior — project + operator views returned via FDAS seam
# --------------------------------------------------------------------------


class TestFDASDisclosureQueryBehavior:
    def test_fdas_query_object_returns_project_revision_view(
        self, sample_records, analytics_module
    ):
        from worldenergydata.fdas.api import disclosure_analytics

        view = disclosure_analytics.project_revision(sample_records)
        assert all(isinstance(row, analytics_module.ProjectRevisionRow) for row in view)
        mariner = sorted(
            [r for r in view if r.project_name == "Mariner-A"],
            key=lambda r: r.fiscal_year,
        )
        assert len(mariner) == 2
        assert mariner[0].yoy_delta_usd_mm is None
        assert mariner[1].yoy_delta_usd_mm == pytest.approx(100.0)

    def test_fdas_query_object_returns_operator_capex_view(
        self, sample_records, analytics_module
    ):
        from worldenergydata.fdas.api import disclosure_analytics

        view = disclosure_analytics.operator_capex(sample_records)
        assert all(isinstance(row, analytics_module.OperatorCapexRow) for row in view)
        acme = sorted(
            [r for r in view if r.operator == "AcmeCorp"], key=lambda r: r.fiscal_year
        )
        assert len(acme) == 2
        assert acme[1].yoy_delta_usd_mm == pytest.approx(800.0)

    def test_fdas_benchmark_refuses_non_comparable_rows(
        self, sample_records, analytics_module
    ):
        """FDAS benchmark is the same gated hook — non-comparable rows must refuse."""
        from worldenergydata.fdas.api import disclosure_analytics

        view = disclosure_analytics.project_revision(sample_records)
        result = disclosure_analytics.benchmark(
            view,
            predictor_cost_usd_mm=1000.0,
            operator="AcmeCorp",
            project_name="Mariner-A",
        )
        # None of the sample records are flagged COMPARABILITY_COMPARABLE.
        assert result is None

    def test_fdas_benchmark_accepts_comparable_rows(self, analytics_module):
        from worldenergydata.fdas.api import disclosure_analytics

        DR = analytics_module.DisclosureRecord
        records = [
            DR(
                operator="AcmeCorp",
                fiscal_year=2022,
                reported_capex_usd_mm=950.0,
                scope=analytics_module.SCOPE_PROJECT,
                project_name="Mariner-A",
                provenance={"source": "10-K"},
                comparability_status=analytics_module.COMPARABILITY_COMPARABLE,
                comparability_basis="USD-2020-real",
            ),
        ]
        view = disclosure_analytics.project_revision(records)
        result = disclosure_analytics.benchmark(
            view,
            predictor_cost_usd_mm=1100.0,
            operator="AcmeCorp",
            project_name="Mariner-A",
        )
        assert result is not None
        assert result.disclosed_capex_usd_mm == pytest.approx(950.0)
        assert result.absolute_delta_usd_mm == pytest.approx(150.0)
