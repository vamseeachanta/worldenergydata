"""Focused contract tests for cost-map schema primitives (issue #1039)."""

from decimal import Decimal

import pytest
from pydantic import ValidationError


def test_immutable_money_interval_rejects_low_above_high() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import MoneyInterval

    with pytest.raises(ValidationError, match="low_value must not exceed high_value"):
        MoneyInterval(
            currency="USD",
            price_basis="nominal",
            basis_year=2025,
            ownership_basis="gross",
            scope_basis="award",
            capex_basis="total_installed_cost",
            value_basis="range",
            bound_type="closed_range",
            low_value=Decimal("2.1"),
            high_value=Decimal("2.0"),
            source_precision="USD 0.1 million",
        )


def test_point_requires_equal_finite_bounds() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import MoneyInterval

    common = dict(
        currency="USD",
        price_basis="nominal",
        basis_year=2025,
        ownership_basis="gross",
        scope_basis="award",
        capex_basis="total_installed_cost",
        value_basis="point",
        bound_type="point",
        source_precision="USD 1 million",
    )
    with pytest.raises(ValidationError, match="point bounds must be equal and finite"):
        MoneyInterval(**common, low_value=Decimal("1"), high_value=Decimal("2"))
    with pytest.raises(ValidationError, match="point bounds must be equal and finite"):
        MoneyInterval(
            **common, low_value=Decimal("Infinity"), high_value=Decimal("Infinity")
        )


def test_not_public_retains_no_invented_amount() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import MoneyInterval

    common = dict(
        currency="NOK",
        price_basis="nominal",
        basis_year=2024,
        ownership_basis="gross",
        scope_basis="award",
        capex_basis="contract_value",
        value_basis="not_public",
        bound_type="open_range",
        source_precision="not disclosed",
    )
    interval = MoneyInterval(**common)
    assert interval.low_value is None
    assert interval.high_value is None
    with pytest.raises(ValidationError, match="not_public must not carry an amount"):
        MoneyInterval(**common, low_value=Decimal("1"))


def test_status_axes_support_linked_scope_bundle_and_exclusion_independently() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import CostMapStatus

    partial = CostMapStatus(
        link_resolution="linked",
        scope_coverage="partial",
        bundle_group_id="bundle-umbilicals",
        counting_disposition="excluded",
        counting_reason="out_of_scope",
    )
    full = CostMapStatus(
        link_resolution="linked",
        scope_coverage="full",
        counting_disposition="included",
    )
    assert partial.scope_coverage == "partial"
    assert partial.bundle_group_id == "bundle-umbilicals"
    assert partial.counting_disposition == "excluded"
    assert full.scope_coverage == "full"
    assert full.bundle_group_id is None


def test_counting_reasons_cannot_masquerade_across_dispositions() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import CostMapStatus

    common = dict(link_resolution="linked", scope_coverage="partial")
    with pytest.raises(ValidationError, match="invalid reason for excluded"):
        CostMapStatus(
            **common,
            counting_disposition="excluded",
            counting_reason="overlap_avoidance",
        )
    with pytest.raises(ValidationError, match="invalid reason for overlap"):
        CostMapStatus(
            **common,
            counting_disposition="overlap",
            counting_reason="out_of_scope",
        )


def test_bundled_link_stores_requirement_ids_without_money_duplication() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import AwardRequirementLink

    link = AwardRequirementLink(
        award_id="awd-subsea-001",
        requirement_ids=("req-flowline-001", "req-umbilical-001"),
        commercial_amount_id="awd-subsea-001",
        bundle_group_id="bundle-subsea",
    )
    assert link.requirement_ids == ("req-flowline-001", "req-umbilical-001")
    assert link.award_id == link.commercial_amount_id
    with pytest.raises(ValidationError):
        AwardRequirementLink(
            award_id="awd-subsea-001",
            requirement_ids=("req-flowline-001",),
            commercial_amount_id="awd-subsea-001",
            monetary_amount=Decimal("500"),
        )


def test_award_requirement_link_rejects_invalid_opaque_ids() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import AwardRequirementLink

    common = dict(
        award_id="awd-subsea-001",
        requirement_ids=("req-flowline-001",),
        commercial_amount_id="awd-subsea-001",
    )
    with pytest.raises(ValidationError, match="award_id must use prefix awd-"):
        AwardRequirementLink(**{**common, "award_id": "award-subsea-001"})
    with pytest.raises(ValidationError, match="requirement_ids must use prefix req-"):
        AwardRequirementLink(**{**common, "requirement_ids": ("",)})
    with pytest.raises(ValidationError, match="requirement_ids must use prefix req-"):
        AwardRequirementLink(**{**common, "requirement_ids": ("prj-field-001",)})
    with pytest.raises(
        ValidationError, match="commercial_amount_id must equal award_id"
    ):
        AwardRequirementLink(**{**common, "commercial_amount_id": "awd-commercial-002"})


def test_invalid_opaque_id_prefix_fails_closed() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import IdentityRegistryEntry

    with pytest.raises(ValidationError, match="opaque_id must use prefix prj-"):
        IdentityRegistryEntry(
            opaque_id="project-thunder-horse",
            entity_kind="project",
            display_label="Thunder Horse",
            state="active",
            active=True,
            aliases=("Thunder Horse North",),
            validation_group_id="vg-thunder-horse",
        )


def test_tombstoned_identity_remains_addressable_and_cannot_be_active() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import IdentityRegistryEntry

    common = dict(
        opaque_id="awd-retired-001",
        entity_kind="award",
        display_label="Retired award",
        state="tombstoned",
        aliases=("Legacy award label",),
        validation_group_id="vg-retired-award",
    )
    entry = IdentityRegistryEntry(**common, active=False)
    assert entry.opaque_id == "awd-retired-001"
    assert entry.aliases == ("Legacy award label",)
    assert entry.validation_group_id == "vg-retired-award"
    with pytest.raises(ValidationError, match="tombstoned identity cannot be active"):
        IdentityRegistryEntry(**common, active=True)


def test_native_currency_bases_and_source_precision_survive_round_trip() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import (
        MoneyInterval,
        PriceBasis,
    )

    interval = MoneyInterval(
        currency="NOK",
        price_basis=PriceBasis.NOMINAL,
        basis_year=2024,
        ownership_basis="operator_net",
        scope_basis="subsea_award",
        capex_basis="contract_value",
        value_basis="range",
        bound_type="closed_range",
        low_value=Decimal("123456789.123456789"),
        high_value=Decimal("223456789.987654321"),
        source_precision="nearest NOK 0.1 million",
    )
    restored = MoneyInterval.model_validate_json(interval.model_dump_json())
    assert restored == interval
    assert restored.currency == "NOK"
    assert restored.price_basis is PriceBasis.NOMINAL
    assert restored.low_value == Decimal("123456789.123456789")
    assert restored.high_value == Decimal("223456789.987654321")
    assert restored.source_precision == "nearest NOK 0.1 million"


def test_source_provenance_remains_independent_of_evidence_derivation() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import Evidence

    disclosed = Evidence(
        derivation="disclosed",
        source_provenance="operator annual report",
        source_url="https://example.com/annual-report",
        source_locator="p. 42",
        confidence="low",
    )
    modeled = Evidence(
        derivation="modeled",
        source_provenance="operator annual report",
        source_url="https://example.com/annual-report",
        source_locator="p. 42",
        confidence="high",
    )
    assert disclosed.source_provenance == modeled.source_provenance
    assert disclosed.derivation == "disclosed"
    assert modeled.derivation == "modeled"
    assert disclosed.confidence == "low"
    assert modeled.confidence == "high"


def test_work_package_retains_required_assets() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import (
        RequiredAsset,
        WorkPackageRequirement,
    )

    asset = RequiredAsset(asset_type="subsea_tree", quantity=2)
    requirement = WorkPackageRequirement(
        requirement_id="req-subsea-production-001",
        project_id="prj-field-001",
        work_package="subsea production system",
        required_assets=(asset,),
    )
    assert requirement.required_assets == (asset,)
    with pytest.raises(ValidationError):
        WorkPackageRequirement(
            requirement_id="req-empty-001",
            project_id="prj-field-001",
            work_package="empty package",
            required_assets=(),
        )


def test_required_asset_quantity_is_positive_integer_or_explicit_unknown() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import RequiredAsset

    assert RequiredAsset(asset_type="subsea_tree", quantity=38).quantity == 38
    assert (
        RequiredAsset(asset_type="subsea_tree", quantity="unknown").quantity
        == "unknown"
    )
    for invalid_quantity in (None, 0, -1, "", "unproven", "38", True, 1.5):
        with pytest.raises(ValidationError):
            RequiredAsset(
                asset_type="subsea_tree",
                quantity=invalid_quantity,
            )


def test_work_package_rejects_empty_opaque_identity_suffixes() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import (
        RequiredAsset,
        WorkPackageRequirement,
    )

    common = dict(
        requirement_id="req-subsea-001",
        project_id="prj-field-001",
        work_package="subsea production system",
        required_assets=(RequiredAsset(asset_type="subsea_tree", quantity=1),),
    )
    with pytest.raises(ValidationError, match="requirement_id must use prefix req-"):
        WorkPackageRequirement(**{**common, "requirement_id": "req-"})
    with pytest.raises(ValidationError, match="project_id must use prefix prj-"):
        WorkPackageRequirement(**{**common, "project_id": "prj-"})


def test_floor_ceiling_and_open_range_retain_open_sides() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import MoneyInterval

    common = dict(
        currency="USD",
        price_basis="nominal",
        basis_year=2025,
        ownership_basis="gross",
        scope_basis="award",
        capex_basis="contract_value",
        value_basis="range",
        source_precision="USD 1 million",
    )
    floor = MoneyInterval(**common, bound_type="floor", low_value=Decimal("10"))
    ceiling = MoneyInterval(**common, bound_type="ceiling", high_value=Decimal("20"))
    open_range = MoneyInterval(
        **common, bound_type="open_range", low_value=Decimal("10")
    )
    assert floor.high_value is None
    assert ceiling.low_value is None
    assert open_range.high_value is None
    with pytest.raises(ValidationError, match="open_range must retain an open side"):
        MoneyInterval(
            **common,
            bound_type="open_range",
            low_value=Decimal("10"),
            high_value=Decimal("20"),
        )


def test_value_basis_and_bound_type_must_be_compatible() -> None:
    from worldenergydata.cost.timeseries.cost_map_schema import MoneyInterval

    common = dict(
        currency="USD",
        price_basis="nominal",
        basis_year=2025,
        ownership_basis="gross",
        scope_basis="award",
        capex_basis="contract_value",
        source_precision="USD 1 million",
    )
    with pytest.raises(ValidationError, match="incompatible with value_basis point"):
        MoneyInterval(
            **common,
            value_basis="point",
            bound_type="closed_range",
            low_value=Decimal("10"),
            high_value=Decimal("20"),
        )
    with pytest.raises(ValidationError, match="incompatible with value_basis range"):
        MoneyInterval(
            **common,
            value_basis="range",
            bound_type="point",
            low_value=Decimal("10"),
            high_value=Decimal("10"),
        )
    with pytest.raises(
        ValidationError, match="incompatible with value_basis not_public"
    ):
        MoneyInterval(
            **common,
            value_basis="not_public",
            bound_type="point",
            low_value=Decimal("10"),
            high_value=Decimal("10"),
        )
