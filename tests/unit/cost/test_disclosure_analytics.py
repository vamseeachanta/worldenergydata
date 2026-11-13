# ABOUTME: Unit tests for derived annual disclosure analytics views (issue #338).
# ABOUTME: Proves project/operator scope separation, raw-vs-derived isolation, and #336 comparability gating.

"""Tests for ``worldenergydata.cost.disclosure_analytics``.

Covers #338 scope:
  - Project annual cost revision view.
  - Operator annual capex series view.
  - Cost-side consumer hook bounded by #336 comparability metadata.
  - Raw-vs-derived separation + lower-tertiary deferral invariants.

These tests deliberately avoid importing from ``worldenergydata.cost.data_collection``:
the raw disclosure foundation lands in #334, and #338 must work against its own
minimal record shape until then.
"""

from __future__ import annotations

import copy
import importlib
import inspect

import pytest

# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def analytics_module():
    return importlib.import_module("worldenergydata.cost.disclosure_analytics")


@pytest.fixture
def make_record(analytics_module):
    """Factory for ``DisclosureRecord`` instances with sensible defaults."""

    def _factory(**overrides):
        defaults = dict(
            operator="AcmeCorp",
            fiscal_year=2022,
            reported_capex_usd_mm=1000.0,
            scope=analytics_module.SCOPE_PROJECT,
            project_name="Mariner-A",
            provenance={"source": "10-K", "filing_id": "acme-2022-10k"},
            comparability_status=None,
            comparability_basis=None,
            currency="USD",
        )
        defaults.update(overrides)
        return analytics_module.DisclosureRecord(**defaults)

    return _factory


@pytest.fixture
def project_dataset(analytics_module, make_record):
    """Two operator/project groups across three fiscal years each, plus stray operator rows."""
    return [
        make_record(
            operator="AcmeCorp",
            project_name="Mariner-A",
            fiscal_year=2020,
            reported_capex_usd_mm=800.0,
        ),
        make_record(
            operator="AcmeCorp",
            project_name="Mariner-A",
            fiscal_year=2021,
            reported_capex_usd_mm=900.0,
        ),
        make_record(
            operator="AcmeCorp",
            project_name="Mariner-A",
            fiscal_year=2022,
            reported_capex_usd_mm=950.0,
            comparability_status=analytics_module.COMPARABILITY_COMPARABLE,
        ),
        make_record(
            operator="BetaOil",
            project_name="Horizon-East",
            fiscal_year=2021,
            reported_capex_usd_mm=500.0,
        ),
        make_record(
            operator="BetaOil",
            project_name="Horizon-East",
            fiscal_year=2022,
            reported_capex_usd_mm=525.0,
        ),
        # Operator-scope row that must NEVER appear in the project view.
        make_record(
            operator="AcmeCorp",
            scope=analytics_module.SCOPE_OPERATOR,
            project_name=None,
            fiscal_year=2022,
            reported_capex_usd_mm=5000.0,
        ),
    ]


@pytest.fixture
def operator_dataset(analytics_module, make_record):
    return [
        make_record(
            operator="AcmeCorp",
            scope=analytics_module.SCOPE_OPERATOR,
            project_name=None,
            fiscal_year=2020,
            reported_capex_usd_mm=3800.0,
        ),
        make_record(
            operator="AcmeCorp",
            scope=analytics_module.SCOPE_OPERATOR,
            project_name=None,
            fiscal_year=2021,
            reported_capex_usd_mm=4200.0,
        ),
        make_record(
            operator="AcmeCorp",
            scope=analytics_module.SCOPE_OPERATOR,
            project_name=None,
            fiscal_year=2022,
            reported_capex_usd_mm=5000.0,
        ),
        # Project-scope row that must not leak into operator view.
        make_record(
            operator="AcmeCorp",
            project_name="Mariner-A",
            fiscal_year=2022,
            reported_capex_usd_mm=950.0,
        ),
    ]


# --------------------------------------------------------------------------
# Project revision view
# --------------------------------------------------------------------------


class TestProjectRevisionView:
    def test_project_scope_records_produce_project_revision_view(
        self, analytics_module, project_dataset
    ):
        """Project rows create a derived revision view with YoY deltas."""
        view = analytics_module.load_project_cost_revision_view(project_dataset)
        mariner = [
            r
            for r in view
            if r.operator == "AcmeCorp" and r.project_name == "Mariner-A"
        ]
        assert len(mariner) == 3
        mariner_sorted = sorted(mariner, key=lambda r: r.fiscal_year)
        assert mariner_sorted[0].yoy_delta_usd_mm is None
        assert mariner_sorted[0].yoy_delta_pct is None
        assert mariner_sorted[1].yoy_delta_usd_mm == pytest.approx(100.0)
        assert mariner_sorted[1].yoy_delta_pct == pytest.approx(0.125)
        assert mariner_sorted[2].yoy_delta_usd_mm == pytest.approx(50.0)
        assert mariner_sorted[2].yoy_delta_pct == pytest.approx(50.0 / 900.0)

    def test_operator_rows_never_appear_in_linkable_project_view(
        self, analytics_module, project_dataset
    ):
        view = analytics_module.load_project_cost_revision_view(project_dataset)
        for row in view:
            assert row.project_name is not None
            assert row.project_name != ""

    def test_derived_rows_preserve_provenance_fields(
        self, analytics_module, project_dataset
    ):
        view = analytics_module.load_project_cost_revision_view(project_dataset)
        for row in view:
            assert "source" in row.provenance
            assert row.provenance["source"] == "10-K"
            assert "filing_id" in row.provenance

    def test_yoy_delta_only_computed_with_valid_prior_year(
        self, analytics_module, make_record
    ):
        # Isolated single year: no prior -> no delta.
        records = [
            make_record(
                operator="SoloCorp",
                project_name="OnlyProject",
                fiscal_year=2022,
                reported_capex_usd_mm=700.0,
            ),
        ]
        view = analytics_module.load_project_cost_revision_view(records)
        assert len(view) == 1
        assert view[0].yoy_delta_usd_mm is None
        assert view[0].yoy_delta_pct is None

    def test_yoy_delta_not_computed_across_non_contiguous_operators(
        self, analytics_module, make_record
    ):
        """Prior-year comparison must be per (operator, project) group, not cross-group."""
        records = [
            make_record(
                operator="Op1",
                project_name="P",
                fiscal_year=2020,
                reported_capex_usd_mm=100.0,
            ),
            make_record(
                operator="Op2",
                project_name="P",
                fiscal_year=2021,
                reported_capex_usd_mm=300.0,
            ),
        ]
        view = analytics_module.load_project_cost_revision_view(records)
        op2 = [r for r in view if r.operator == "Op2"][0]
        assert op2.yoy_delta_usd_mm is None


# --------------------------------------------------------------------------
# Operator annual capex view
# --------------------------------------------------------------------------


class TestOperatorCapexView:
    def test_operator_scope_records_produce_operator_capex_view(
        self, analytics_module, operator_dataset
    ):
        view = analytics_module.load_operator_annual_capex_view(operator_dataset)
        acme = sorted(
            [r for r in view if r.operator == "AcmeCorp"], key=lambda r: r.fiscal_year
        )
        assert len(acme) == 3
        assert acme[0].yoy_delta_usd_mm is None
        assert acme[1].yoy_delta_usd_mm == pytest.approx(400.0)
        assert acme[2].yoy_delta_usd_mm == pytest.approx(800.0)
        assert acme[1].yoy_delta_pct == pytest.approx(400.0 / 3800.0)

    def test_project_rows_never_appear_in_operator_view(
        self, analytics_module, operator_dataset
    ):
        view = analytics_module.load_operator_annual_capex_view(operator_dataset)
        # Operator view rows must not carry project-scope residue.
        for row in view:
            # The derived row schema has no project_name field at all -> attribute error is OK,
            # but if present (future schema evolution), it must be falsy.
            project_attr = getattr(row, "project_name", None)
            assert not project_attr


# --------------------------------------------------------------------------
# Raw-vs-derived separation
# --------------------------------------------------------------------------


class TestRawVsDerivedSeparation:
    def test_raw_records_are_not_mutated_by_view_generation(
        self, analytics_module, project_dataset
    ):
        snapshot = copy.deepcopy(project_dataset)
        analytics_module.load_project_cost_revision_view(project_dataset)
        analytics_module.load_operator_annual_capex_view(project_dataset)
        assert project_dataset == snapshot

    def test_derived_provenance_is_isolated_from_raw(
        self, analytics_module, project_dataset
    ):
        view = analytics_module.load_project_cost_revision_view(project_dataset)
        # Mutating a derived row's provenance must not bleed back into raw.
        first = view[0]
        first.provenance["injected"] = True
        for raw in project_dataset:
            assert "injected" not in raw.provenance


# --------------------------------------------------------------------------
# Cost-side consumer hook (benchmark)
# --------------------------------------------------------------------------


class TestCostDisclosureBenchmark:
    def test_cost_consumer_can_compare_predictor_output_to_latest_disclosed_capex_when_rows_are_comparable(
        self, analytics_module, make_record
    ):
        records = [
            make_record(
                operator="AcmeCorp",
                project_name="Mariner-A",
                fiscal_year=2022,
                reported_capex_usd_mm=950.0,
                comparability_status=analytics_module.COMPARABILITY_COMPARABLE,
                comparability_basis="USD-2020-real",
            ),
        ]
        view = analytics_module.load_project_cost_revision_view(records)
        result = analytics_module.build_cost_disclosure_benchmark(
            view,
            predictor_cost_usd_mm=1100.0,
            operator="AcmeCorp",
            project_name="Mariner-A",
        )
        assert result is not None
        assert result.disclosed_capex_usd_mm == pytest.approx(950.0)
        assert result.predicted_capex_usd_mm == pytest.approx(1100.0)
        assert result.absolute_delta_usd_mm == pytest.approx(150.0)
        assert result.pct_delta == pytest.approx(150.0 / 950.0)
        assert result.comparability_status == analytics_module.COMPARABILITY_COMPARABLE

    def test_cost_consumer_refuses_mixed_basis_or_non_comparable_rows(
        self, analytics_module, make_record
    ):
        records = [
            make_record(
                operator="AcmeCorp",
                project_name="Mariner-A",
                fiscal_year=2022,
                reported_capex_usd_mm=950.0,
                comparability_status="mixed_basis",
            ),
        ]
        view = analytics_module.load_project_cost_revision_view(records)
        result = analytics_module.build_cost_disclosure_benchmark(
            view,
            predictor_cost_usd_mm=1100.0,
            operator="AcmeCorp",
            project_name="Mariner-A",
        )
        assert result is None

    def test_cost_consumer_refuses_rows_with_missing_comparability_metadata(
        self, analytics_module, make_record
    ):
        # comparability_status defaults to None — must be rejected rather than assumed comparable.
        records = [
            make_record(
                operator="AcmeCorp",
                project_name="Mariner-A",
                fiscal_year=2022,
                reported_capex_usd_mm=950.0,
            ),
        ]
        view = analytics_module.load_project_cost_revision_view(records)
        result = analytics_module.build_cost_disclosure_benchmark(
            view,
            predictor_cost_usd_mm=1100.0,
            operator="AcmeCorp",
            project_name="Mariner-A",
        )
        assert result is None

    def test_cost_consumer_returns_none_when_no_matching_project(
        self, analytics_module, make_record
    ):
        records = [
            make_record(
                operator="AcmeCorp",
                project_name="Mariner-A",
                fiscal_year=2022,
                reported_capex_usd_mm=950.0,
                comparability_status=analytics_module.COMPARABILITY_COMPARABLE,
            ),
        ]
        view = analytics_module.load_project_cost_revision_view(records)
        result = analytics_module.build_cost_disclosure_benchmark(
            view,
            predictor_cost_usd_mm=1100.0,
            operator="Unknown",
            project_name="Mariner-A",
        )
        assert result is None


# --------------------------------------------------------------------------
# Deferral invariant: lower_tertiary untouched by #338
# --------------------------------------------------------------------------


class TestLowerTertiaryDeferralInvariant:
    def test_no_lower_tertiary_behavior_changes_are_introduced(self):
        """#338 must not import or mutate anything in ``lower_tertiary``.

        This is a static guard — the analytics module's source must not
        reference the lower-tertiary namespace at all.
        """
        import worldenergydata.cost.disclosure_analytics as analytics

        source = inspect.getsource(analytics)
        assert "lower_tertiary" not in source, (
            "disclosure_analytics must not reference lower_tertiary until a "
            "dedicated mapping contract exists (see issue #338 plan)."
        )

    def test_lower_tertiary_npv_module_remains_importable_unchanged(self):
        """Basic smoke — lower_tertiary.npv must still import without side effects from #338."""
        module = importlib.import_module("worldenergydata.lower_tertiary.npv")
        # Confirm module loaded — we do not make assertions on internal behavior
        # because #338 is not in the business of lower-tertiary economics.
        assert module is not None


# --------------------------------------------------------------------------
# Public export surface
# --------------------------------------------------------------------------


class TestCostPackageExports:
    def test_cost_package_exposes_disclosure_analytics_surface(self):
        from worldenergydata import cost

        for name in (
            "DisclosureRecord",
            "ProjectRevisionRow",
            "OperatorCapexRow",
            "DisclosureBenchmarkResult",
            "load_project_cost_revision_view",
            "load_operator_annual_capex_view",
            "build_cost_disclosure_benchmark",
            "COMPARABILITY_COMPARABLE",
            "SCOPE_PROJECT",
            "SCOPE_OPERATOR",
        ):
            assert hasattr(cost, name), f"cost module missing export: {name}"

    def test_cost_predictor_exports_remain_intact(self):
        from worldenergydata import cost

        # #338 must not regress the existing cost public API.
        assert hasattr(cost, "CostPredictor")
        assert hasattr(cost, "PredictionResult")
        assert hasattr(cost, "CostDataPoint")
        assert hasattr(cost, "load_public_dataset")


# Explicit revision selectors retain history separately from annual series.
def _revision_record(analytics_module, version_id="v1", parent=None, **changes):
    from worldenergydata.cost.data_collection import DisclosureRevisionMetadata

    revision = dict(
        logical_disclosure_key="annual-capex-2023",
        version_id=version_id,
        supersedes_version_id=parent,
        revision_classification="amended" if parent else "original",
        publication_date="2024-03-01" if parent else None,
    )
    revision.update(changes.pop("revision_changes", {}))
    payload = dict(
        operator="Example operator",
        fiscal_year=2023,
        reported_capex_usd_mm=100.0,
        scope=analytics_module.SCOPE_OPERATOR,
        revision=DisclosureRevisionMetadata(**revision),
        provenance={"citation": {"page": "table 1"}},
    )
    payload.update(changes)
    return analytics_module.DisclosureRecord(**payload)


def test_revision_history_returns_full_ordered_lineage(analytics_module):
    original = _revision_record(analytics_module)
    amended = _revision_record(analytics_module, "v2", "v1")
    restated = _revision_record(analytics_module, "v3", "v2")
    rows = [restated, original, amended]
    snapshot = copy.deepcopy(rows)
    history = analytics_module.load_disclosure_revision_history(iter(rows))
    assert [r.revision.version_id for r in history] == ["v1", "v2", "v3"]
    history[0].provenance["citation"]["page"] = "changed"
    assert rows == snapshot


@pytest.mark.parametrize(
    "left,right,winner",
    [
        ({"effective_date": "2024-05-01"}, {"effective_date": "2024-04-01"}, "a"),
        ({"publication_date": "2024-04-01"}, {}, "a"),
        ({}, {}, "z"),
    ],
)
def test_current_effective_selector_uses_defined_precedence(
    analytics_module, left, right, winner
):
    root = _revision_record(analytics_module)
    a = _revision_record(analytics_module, "a", "v1", revision_changes=left)
    z = _revision_record(analytics_module, "z", "v1", revision_changes=right)
    for rows in ([root, a, z], [z, root, a]):
        selected = analytics_module.load_current_effective_disclosure_rows(iter(rows))
        assert [r.revision.version_id for r in selected] == [winner]


def test_chain_depth_precedes_dates_and_missing_effective_date_is_oldest(
    analytics_module,
):
    root = _revision_record(analytics_module)
    newer_date = _revision_record(
        analytics_module, "a", "v1", revision_changes={"effective_date": "2025-01-01"}
    )
    deeper = _revision_record(analytics_module, "b", "a")
    assert (
        analytics_module.load_current_effective_disclosure_rows(
            [root, newer_date, deeper]
        )[0].revision.version_id
        == "b"
    )
    no_effective = _revision_record(
        analytics_module, "z", "v1", revision_changes={"publication_date": "2026-01-01"}
    )
    assert (
        analytics_module.load_current_effective_disclosure_rows(
            [root, newer_date, no_effective]
        )[0].revision.version_id
        == "a"
    )


def test_current_selection_is_per_logical_key_and_preserves_plain_rows(
    analytics_module,
):
    root = _revision_record(analytics_module)
    other = _revision_record(
        analytics_module,
        "other",
        fiscal_year=2022,
        revision_changes={"logical_disclosure_key": "annual-capex-2022"},
    )
    plain = analytics_module.DisclosureRecord("Example operator", 2021, 80, "operator")
    result = analytics_module.load_current_effective_disclosure_rows(
        [root, other, plain]
    )
    assert len(result) == 3
    assert {r.fiscal_year for r in result} == {2021, 2022, 2023}
    assert analytics_module.load_disclosure_revision_history([]) == []


@pytest.mark.parametrize(
    "view", ["load_operator_annual_capex_view", "load_project_cost_revision_view"]
)
def test_annual_series_selects_effective_revision_before_yoy(analytics_module, view):
    scope = "operator" if "operator" in view else "project"
    project = None if scope == "operator" else "Example asset"
    root = _revision_record(analytics_module, scope=scope, project_name=project)
    revised = _revision_record(
        analytics_module,
        "v2",
        "v1",
        reported_capex_usd_mm=120,
        scope=scope,
        project_name=project,
    )
    following = analytics_module.DisclosureRecord(
        "Example operator", 2024, 150, scope, project_name=project
    )
    result = getattr(analytics_module, view)([revised, following, root])
    assert [r.reported_capex_usd_mm for r in result] == [120, 150]
    assert result[0].yoy_delta_usd_mm is None
    assert result[1].yoy_delta_usd_mm == 30
    assert result[1].yoy_delta_pct == pytest.approx(0.25)
    assert result[0].revision.version_id == "v2"
    assert not hasattr(result[1], "revision")


@pytest.mark.parametrize(
    "kind", ["dangling", "foreign", "cycle", "duplicate", "two-roots"]
)
@pytest.mark.parametrize(
    "selector",
    ["load_current_effective_disclosure_rows", "load_disclosure_revision_history"],
)
def test_analytics_rejects_invalid_lineage(analytics_module, kind, selector):
    root = _revision_record(analytics_module)
    second = _revision_record(analytics_module, "v2", "v1")
    if kind == "dangling":
        rows = [second]
    elif kind == "foreign":
        rows = [
            root,
            _revision_record(
                analytics_module,
                "v2",
                "v1",
                revision_changes={"logical_disclosure_key": "other"},
            ),
        ]
    elif kind == "cycle":
        rows = [_revision_record(analytics_module, "v1", "v2"), second]
    elif kind == "duplicate":
        rows = [root, root]
    else:
        rows = [root, _revision_record(analytics_module, "v2")]
    with pytest.raises(ValueError):
        getattr(analytics_module, selector)(rows)


@pytest.mark.parametrize("kind", ["plain", "other-key", "changed-year"])
def test_revision_selector_rejects_ambiguous_annual_groups(analytics_module, kind):
    root = _revision_record(analytics_module)
    if kind == "plain":
        second = analytics_module.DisclosureRecord(
            "Example operator", 2023, 80, "operator"
        )
    elif kind == "other-key":
        second = _revision_record(
            analytics_module,
            "other",
            revision_changes={"logical_disclosure_key": "other"},
        )
    else:
        second = _revision_record(analytics_module, "v2", "v1", fiscal_year=2024)
    with pytest.raises(ValueError):
        analytics_module.load_current_effective_disclosure_rows([root, second])


@pytest.mark.parametrize(
    "view", ["load_operator_annual_capex_view", "load_project_cost_revision_view"]
)
def test_plain_derived_serialization_keeps_legacy_shape(analytics_module, view):
    from dataclasses import asdict

    scope = "operator" if "operator" in view else "project"
    plain = analytics_module.DisclosureRecord(
        "Example operator", 2023, 100, scope, project_name="Example asset"
    )
    assert "revision" not in asdict(getattr(analytics_module, view)([plain])[0])
    versioned = _revision_record(
        analytics_module, scope=scope, project_name="Example asset"
    )
    derived = getattr(analytics_module, view)([versioned])[0]
    assert asdict(derived)["revision"].version_id == "v1"
