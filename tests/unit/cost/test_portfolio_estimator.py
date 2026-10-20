"""Synthetic regression examples, independent calculations below.

OLS: NIST/SEMATECH e-Handbook (2003), section 4.4.3.1.
Intervals: A Gentle Introduction to Conformal Prediction and Distribution-Free
Uncertainty Quantification (2021), section 2, regression example.
All validation policy values are test inputs, not engineering recommendations.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal as D

import pytest

from worldenergydata.cost.portfolio.accounting import Basis, Evidence, Interval
from worldenergydata.cost.portfolio.estimator import (
    Comparable,
    EstimateRequest,
    ValidationPolicy,
    estimate,
)

BASIS = Basis("USD", "million", "real", "2020", "gross", "a", "upstream", "capex")
AS_OF = date(2022, 1, 1)


def request(**changes):
    return replace(
        EstimateRequest(
            "target",
            "target-group",
            "subsea",
            "region-a",
            BASIS,
            "well_count",
            "well",
            D(3),
            AS_OF,
            Evidence("example features", date(2020, 1, 1), "disclosed"),
        ),
        **changes,
    )


def record(key, x, y, **changes):
    return replace(
        Comparable(
            key,
            key,
            "subsea",
            "region-a",
            BASIS,
            "well_count",
            "well",
            D(x),
            date(2020, 1, 1),
            Interval(D(y), D(y)),
            Evidence("synthetic hand calculation", date(2020, 2, 1), "disclosed"),
            False,
        ),
        **changes,
    )


def policy(**changes):
    # Synthetic acceptance inputs: exact fits expected; alpha=.5 needs >=1 cal group.
    return replace(
        ValidationPolicy(D(".5"), 3, 2, D(".01"), D(".5"), "synthetic example policy"),
        **changes,
    )


def dataset():
    # Training y=10+2x for x=1..5. Cal errors 1,3. Validation at x=2,4 is exact.
    train = tuple(record(f"t-{x}", x, 10 + 2 * x) for x in range(1, 6))
    cal = (record("c-1", 2, 15), record("c-2", 4, 21))
    valid = (record("v-1", 2, 14), record("v-2", 4, 18))
    return train + cal + valid


def run(rows=None, **changes):
    return estimate(
        request(),
        dataset() if rows is None else rows,
        ("t-1", "t-2", "t-3", "t-4", "t-5"),
        ("c-1", "c-2"),
        ("v-1", "v-2"),
        policy(**changes),
    )


def test_linear_prediction_and_finite_sample_interval():
    """OLS line=10+2x; at 3 ->16. k=ceil(3*.5)=2; errors [1,3] -> [13,19]."""
    result = run()
    assert result.status == "modeled"
    assert result.point == D(16)
    assert result.interval == Interval(D(13), D(19))
    assert result.method == "linear"
    assert result.validation_mae == 0
    assert result.validation_coverage == 1
    assert len(result.validation) == 2
    assert len(result.comparables) == 9
    assert result == run(tuple(reversed(dataset())))


def test_quadratic_alternative_selected_inside_training_only():
    """Training y=x², so quadratic predicts 9 at x=3; calibration is also exact."""
    rows = tuple(
        replace(row, target=Interval(row.driver**2, row.driver**2)) for row in dataset()
    )
    result = run(rows)
    assert result.method == "quadratic"
    assert result.point == 9
    assert result.interval == Interval(D(9), D(9))
    assert result.candidate_mae["quadratic"] < result.candidate_mae["linear"]


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"synthetic": True}, "synthetic"),
        (
            {"evidence": Evidence("allocation", date(2020, 1, 1), "allocated")},
            "not_disclosed",
        ),
        ({"basis": replace(BASIS, currency="EUR")}, "basis"),
        ({"architecture": "dry_tree"}, "architecture"),
        ({"features_on": date(2023, 1, 1)}, "future_features"),
        (
            {"evidence": Evidence("later", date(2023, 1, 1), "disclosed")},
            "future_target",
        ),
        ({"target": Interval(D(1), D(2))}, "nonpoint_target"),
        ({"driver_name": "final_cost"}, "driver"),
        ({"group": "target-group"}, "target_group"),
    ],
)
def test_ineligible_training_rows_remain_visible(changes, reason):
    # t-5 exclusion still leaves four training groups, enough for the defined policy.
    rows = tuple(replace(r, **changes) if r.project == "t-5" else r for r in dataset())
    result = run(rows)
    assert result.excluded["t-5"] == reason
    assert "t-5" not in result.comparables


def test_sparse_cohort_and_unattainable_quantile_fail_closed():
    assert run(dataset()[:2]).status == "NOT_EVALUATED"
    result = run(alpha=D(".01"))
    assert result.status == "NOT_EVALUATED"
    assert result.reason == "insufficient_calibration"
    assert result.interval is None


def test_validation_failure_keeps_diagnostics_and_hides_prediction():
    rows = tuple(
        replace(r, target=Interval(D(100), D(100))) if r.project.startswith("v-") else r
        for r in dataset()
    )
    result = run(rows)
    assert result.status == "NOT_EVALUATED"
    assert result.reason == "validation_failed"
    assert result.interval is None
    assert result.validation_mae == D(84)  # (abs(100-14)+abs(100-18))/2.
    assert result.validation_coverage == 0
    # Validation outcomes cannot influence candidate choice or fitted coefficients.
    assert result.method == run().method
    assert result.coefficients == run().coefficients


def test_partition_overlap_and_duplicate_projects_rejected():
    with pytest.raises(ValueError, match="partition"):
        estimate(request(), dataset(), ("t-1",), ("t-1",), ("v-1",), policy())
    with pytest.raises(ValueError, match="duplicate"):
        run(dataset() + (dataset()[0],))


def test_group_members_never_cross_model_selection_holdouts():
    rows = tuple(
        replace(r, group="t-1") if r.project == "t-2" else r for r in dataset()
    )
    result = run(rows)
    assert result.status == "modeled"
    for fold in result.selection_folds:
        assert not set(fold["train_groups"]) & set(fold["test_groups"])


def test_target_future_features_and_extrapolation_fail_closed():
    assert (
        estimate(
            request(driver=D(99)),
            dataset(),
            ("t-1", "t-2", "t-3", "t-4", "t-5"),
            ("c-1", "c-2"),
            ("v-1", "v-2"),
            policy(),
        ).reason
        == "extrapolation"
    )
    with pytest.raises(ValueError, match="future"):
        estimate(
            request(feature_evidence=Evidence("future", date(2023, 1, 1), "disclosed")),
            dataset(),
            ("t-1",),
            ("c-1",),
            ("v-1",),
            policy(),
        )
