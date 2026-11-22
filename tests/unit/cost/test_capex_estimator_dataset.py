"""Eligibility tests use invented records, never engineering calibration data."""

from datetime import date

import pytest
from pydantic import ValidationError

from worldenergydata.cost.calibration.capex_estimator_schema import (
    CapexBasis,
    Feature,
    FeatureSnapshot,
    TrainingRecord,
)
from worldenergydata.cost.calibration.estimator_dataset import select_cohort

DAY = date(2020, 1, 1)  # Synthetic fixture date; no empirical interpretation.


def snapshot(project="target", **changes):
    data = dict(
        project_id=project,
        validation_group_id=project,
        as_of=DAY,
        architecture="subsea",
        host_type="floating",
        region="region-a",
        basis=CapexBasis(
            currency="USD",
            price_basis="real",
            basis_year=2020,
            ownership_basis="gross",
            scope_basis="total_project",
            capex_basis="development",
            normalization_source="fixture only",
        ),
        features={"well_count": Feature(value=2, available_on=DAY)},
    )
    return FeatureSnapshot(**(data | changes))


def record(project="a", **changes):
    data = dict(
        snapshot=snapshot(project),
        amount=10,
        disclosed_on=DAY,
        derivation="disclosed",
        bound_type="point",
        source="synthetic test fixture",
    )
    return TrainingRecord(**(data | changes))


def test_request_forbids_target_and_unknown_features():
    with pytest.raises(ValidationError):
        snapshot(final_cost=100)
    with pytest.raises(ValidationError):
        snapshot(features={"final_cost": Feature(value=100, available_on=DAY)})


def test_future_features_are_rejected():
    with pytest.raises(ValidationError, match="available"):
        snapshot(
            features={"well_count": Feature(value=2, available_on=date(2021, 1, 1))}
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"derivation": "modeled"},
        {"derivation": "allocated"},
        {"derivation": "synthetic"},
        {"bound_type": "range"},
        {"disclosed_on": date(2021, 1, 1)},
        {"snapshot": snapshot("a", architecture="platform")},
        {"snapshot": snapshot("a", host_type="fixed")},
        {
            "snapshot": snapshot(
                "a", basis=snapshot().basis.model_copy(update={"currency": "EUR"})
            )
        },
        {"snapshot": snapshot("target")},
        {"snapshot": snapshot("a", validation_group_id="target")},
    ],
)
def test_incompatible_unobserved_future_and_same_group_are_excluded(changes):
    cohort = select_cohort([record(**changes)], snapshot(), DAY)
    assert not cohort.records
    assert cohort.exclusions


def test_cutoff_cannot_follow_prediction():
    with pytest.raises(ValueError, match="cutoff"):
        select_cohort([], snapshot(), date(2021, 1, 1))


def test_duplicates_do_not_inflate_independent_project_count():
    cohort = select_cohort([record(), record()], snapshot(), DAY)
    assert not cohort.records
    assert "duplicate" in str(cohort.exclusions)


def test_separate_asset_scope_does_not_poison_project_total_cohort():
    """Same-project asset and total labels are different prediction tasks."""
    other_basis = snapshot().basis.model_copy(update={"scope_basis": "wells"})
    asset = record(snapshot=snapshot("a", basis=other_basis))
    cohort = select_cohort([record(), asset], snapshot(), DAY)
    assert len(cohort.records) == 1


def test_missing_features_are_visible_and_training_requires_target_features():
    target = snapshot(
        features={
            "well_count": Feature(value=2, available_on=DAY),
            "water_depth_m": None,
        }
    )
    cohort = select_cohort(
        [record(), record("b", snapshot=snapshot("b", features={}))], target, DAY
    )
    assert [r.snapshot.project_id for r in cohort.records] == ["a"]
    assert cohort.feature_names == ("well_count",)
    assert "water_depth_m" in cohort.missing_features


def test_omitted_and_null_features_report_the_same_missing_inputs():
    """Invented records: omitting an unavailable driver cannot hide its absence."""
    implicit = snapshot()
    explicit = snapshot(
        features=implicit.features
        | {
            "water_depth_m": None,
            "capacity_boe_day": None,
            "asset_quantity": None,
            "vintage_year": None,
        }
    )
    omitted = select_cohort([record()], implicit, DAY)
    nulls = select_cohort([record()], explicit, DAY)
    assert (
        omitted.missing_features
        == nulls.missing_features
        == (
            "asset_quantity",
            "capacity_boe_day",
            "vintage_year",
            "water_depth_m",
        )
    )
    assert omitted.feature_names == nulls.feature_names == ("well_count",)
    assert omitted.records == nulls.records


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1])
def test_invalid_physical_values(value):
    with pytest.raises(ValidationError):
        Feature(value=value, available_on=DAY)


def test_nominal_cross_vintage_and_unreferenced_real_basis_fail_closed():
    with pytest.raises(ValidationError):
        CapexBasis(**(snapshot().basis.model_dump() | {"normalization_source": ""}))
    old = snapshot().basis.model_copy(update={"basis_year": 2019})
    assert not select_cohort(
        [record(snapshot=snapshot("a", basis=old))], snapshot(), DAY
    ).records
