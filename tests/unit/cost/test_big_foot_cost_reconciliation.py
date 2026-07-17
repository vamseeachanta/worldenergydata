"""Exact bidirectional reconciliation tests for the Big Foot cost-map pilot."""

from decimal import Decimal

import pytest


def test_bottom_up_rejects_incompatible_currency_basis_scope_or_ownership():
    from worldenergydata.cost.timeseries.cost_map import (
        ComparisonBasis,
        ObservedContribution,
        reconcile_bottom_up,
    )

    target = ComparisonBasis(
        currency="USD",
        price_basis="nominal",
        ownership_basis="gross",
        scope_basis="project",
        capex_basis="project_capex",
    )
    changes = {
        "currency": "NOK",
        "price_basis": "real",
        "ownership_basis": "net",
        "scope_basis": "midstream",
        "capex_basis": "total_investment",
    }
    for field, incompatible in changes.items():
        mapping = ComparisonBasis(**{**target.__dict__, field: incompatible})
        row = ObservedContribution.point(
            award_id=f"awd-{field}",
            requirement_ids=("req-000005",),
            value=Decimal("45"),
            source_basis=target,
            comparison_basis=mapping,
            counting_disposition="included",
        )
        with pytest.raises(ValueError, match=field):
            reconcile_bottom_up(Decimal("4000"), target, (row,))
    for field, incompatible in {"currency": "NOK", "price_basis": "real"}.items():
        source = ComparisonBasis(**{**target.__dict__, field: incompatible})
        row = ObservedContribution.point(
            award_id=f"awd-source-{field}",
            requirement_ids=("req-000005",),
            value=Decimal("45"),
            source_basis=source,
            comparison_basis=target,
            counting_disposition="included",
        )
        with pytest.raises(ValueError, match=field):
            reconcile_bottom_up(Decimal("4000"), target, (row,))


def test_bundled_link_contributes_value_once():
    from worldenergydata.cost.timeseries.cost_map import (
        ComparisonBasis,
        ObservedContribution,
        reconcile_bottom_up,
    )

    basis = ComparisonBasis("USD", "nominal", "gross", "project", "project_capex")
    bundled = ObservedContribution.point(
        award_id="awd-000001",
        requirement_ids=("req-000004", "req-000005"),
        value=Decimal("45"),
        source_basis=basis,
        comparison_basis=basis,
        counting_disposition="included",
    )
    result = reconcile_bottom_up(Decimal("4000"), basis, (bundled, bundled))

    assert result.eligible.low == result.eligible.high == Decimal("45")
    conflicting = ObservedContribution.point(
        award_id="awd-000001",
        requirement_ids=("req-000004", "req-000005"),
        value=Decimal("46"),
        source_basis=basis,
        comparison_basis=basis,
        counting_disposition="included",
    )
    with pytest.raises(ValueError, match="conflicting duplicate award_id"):
        reconcile_bottom_up(Decimal("4000"), basis, (bundled, conflicting))


def test_synthetic_status_axis_fixture_supports_linked_midstream_excluded_and_linked_not_public():
    from worldenergydata.cost.timeseries.cost_map import (
        ComparisonBasis,
        ObservedContribution,
        reconcile_bottom_up,
    )

    target = ComparisonBasis("USD", "nominal", "gross", "project", "project_capex")
    midstream = ObservedContribution.point(
        award_id="awd-midstream",
        requirement_ids=("req-000006",),
        value=Decimal("200"),
        source_basis=ComparisonBasis(
            "USD", "nominal", "gross", "midstream", "non_capex"
        ),
        comparison_basis=None,
        counting_disposition="excluded",
        value_basis="midstream",
    )
    undisclosed = ObservedContribution.not_public(
        award_id="awd-undisclosed",
        requirement_ids=("req-000001",),
        source_basis=target,
        comparison_basis=None,
        counting_disposition="excluded",
    )
    result = reconcile_bottom_up(Decimal("4000"), target, (midstream, undisclosed))

    assert result.excluded == result.excluded.__class__(Decimal("200"), Decimal("200"))
    assert result.not_public_awards == ("awd-undisclosed",)


def test_bottom_up_subtotal_preserves_included_excluded_overlap_and_residual():
    from worldenergydata.cost.timeseries.cost_map import (
        ClosedInterval,
        load_big_foot_evidence,
        reconcile_bottom_up,
    )

    evidence = load_big_foot_evidence()
    result = reconcile_bottom_up(
        Decimal("4000"), evidence.target_basis, evidence.contributions
    )

    assert len(evidence.requirement_ids) == 8
    assert evidence.linked_requirement_ids == ("req-000005", "req-000006")
    assert result.eligible == ClosedInterval(Decimal("45"), Decimal("45"))
    assert result.excluded == ClosedInterval(Decimal("200"), Decimal("200"))
    assert result.overlap == ClosedInterval(Decimal("0"), Decimal("0"))
    assert result.residual == ClosedInterval(Decimal("3955"), Decimal("3955"))
    assert "req-000001" not in evidence.amount_by_requirement


def test_interval_residual_uses_outward_endpoint_arithmetic():
    from worldenergydata.cost.timeseries.cost_map import (
        ClosedInterval,
        compute_interval_metrics,
    )

    metrics = compute_interval_metrics(
        ClosedInterval(Decimal("90"), Decimal("110")),
        ClosedInterval(Decimal("80"), Decimal("100")),
    )

    assert metrics.residual == ClosedInterval(Decimal("-10"), Decimal("30"))
    assert metrics.coverage == ClosedInterval(Decimal("80") / Decimal("110"), Decimal("100") / Decimal("90"))
    endpoint_ratios = (
        Decimal("-10") / Decimal("90"),
        Decimal("-10") / Decimal("110"),
        Decimal("30") / Decimal("90"),
        Decimal("30") / Decimal("110"),
    )
    assert metrics.residual_percentage == ClosedInterval(
        min(endpoint_ratios), max(endpoint_ratios)
    )


def test_residual_unallocated_and_unreconciled_are_distinct():
    from worldenergydata.cost.timeseries.cost_map import reconcile_top_down

    accounting = reconcile_top_down(
        total=Decimal("100.00"),
        allocations={"req-1": Decimal("60.00")},
        unallocated=Decimal("35.00"),
        bottom_up_residual=Decimal("55.00"),
    )

    assert accounting.residual == Decimal("55.00")
    assert accounting.unallocated == Decimal("35.00")
    assert accounting.unreconciled_variance == Decimal("5.00")


def test_sanction_and_outturn_reconcile_as_distinct_total_bases():
    from worldenergydata.cost.timeseries.cost_map import reconcile_big_foot_targets

    results = reconcile_big_foot_targets()

    assert tuple(results) == ("evt-000003", "evt-000004")
    assert results["evt-000003"].target == Decimal("4000")
    assert results["evt-000003"].accounting.residual.low == Decimal("3955")
    assert results["evt-000004"].target == Decimal("5100")
    assert results["evt-000004"].accounting.residual.low == Decimal("5055")


def test_current_evidence_vintage_is_not_backdated_to_sanction():
    from worldenergydata.cost.timeseries.cost_map import reconcile_big_foot_targets

    sanction = reconcile_big_foot_targets()["evt-000003"]

    assert sanction.target_vintage == "2010"
    assert sanction.accounting.evidence_vintage == "current_registry"
    assert sanction.accounting.target_event_id == "evt-000003"
    assert sanction.accounting.evidence_vintage != sanction.target_vintage


def test_each_joint_allocation_scenario_sums_exactly_to_project_total():
    from worldenergydata.cost.timeseries.cost_map import (
        BIG_FOOT_JOINT_SCENARIOS,
        largest_remainder_allocate,
        reconcile_top_down,
    )

    assert tuple(BIG_FOOT_JOINT_SCENARIOS) == ("reference", "host_heavy", "well_heavy")
    for total in (Decimal("4000"), Decimal("5100")):
        for shares in BIG_FOOT_JOINT_SCENARIOS.values():
            assert sum(shares.values(), Decimal("0")) == Decimal("1.00")
            allocations = largest_remainder_allocate(total, shares)
            assert sum(allocations.values(), Decimal("0")) == total
            accounting = reconcile_top_down(
                total=total,
                allocations=allocations,
                unallocated=Decimal("0"),
                bottom_up_residual=total - Decimal("45"),
            )
            assert accounting.unallocated == accounting.unreconciled_variance == Decimal("0")


def test_largest_remainder_uses_stable_requirement_id_ties():
    from worldenergydata.cost.timeseries.cost_map import largest_remainder_allocate

    allocations = largest_remainder_allocate(
        Decimal("0.03"),
        {"req-000002": Decimal("0.50"), "req-000001": Decimal("0.50")},
    )

    assert tuple(allocations) == ("req-000001", "req-000002")
    assert allocations == {
        "req-000001": Decimal("0.02"),
        "req-000002": Decimal("0.01"),
    }


def test_top_down_allocations_are_banded_and_marked_allocated():
    from worldenergydata.cost.timeseries.cost_map import allocate_big_foot_bands

    bands = allocate_big_foot_bands(Decimal("4000"))

    assert len(bands) == 8
    assert bands["req-000001"].low == Decimal("800.00")
    assert bands["req-000001"].high == Decimal("1520.00")
    assert {
        (band.derivation, band.provenance, band.scenario_status, band.confidence)
        for band in bands.values()
    } == {("allocated", "assumed", "proposed", "low")}


def test_non_additive_marginal_bands_are_never_summed():
    from worldenergydata.cost.timeseries.cost_map import allocate_big_foot_bands

    bands = allocate_big_foot_bands(Decimal("4000"))

    assert bands.additive is False
    assert sum((band.low for band in bands.values()), Decimal("0")) < Decimal("4000")
    assert sum((band.high for band in bands.values()), Decimal("0")) > Decimal("4000")
