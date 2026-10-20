"""Analytic fixtures are unit-test inputs, never an observed cost corpus."""

import math
from dataclasses import replace

import pytest

from worldenergydata.cost.calibration.capex_estimator import (
    CapexEstimator,
    conformal_radius,
    reconcile,
    reconcile_estimates,
    render_report,
)
from worldenergydata.cost.calibration.capex_estimator_schema import (
    EstimatorPolicy,
    Feature,
)

from .test_capex_estimator_dataset import DAY, record, snapshot


def policy(**changes):
    """Fixture criteria: 4 fit, 4 calibration, 8 validation, 50% miscoverage.

    These are deliberately permissive test inputs, not engineering thresholds.
    """
    return EstimatorPolicy(
        **(
            dict(
                min_training_projects=4,
                calibration_projects=4,
                min_backtests=8,
                alpha=0.5,
                max_median_ape=1,
                min_coverage=0,
                source="test-only application criteria",
                split_salt="test-only-split",
            )
            | changes
        )
    )


def corpus(curved=False):
    """Hand equations: ln(C)=1+x/10 or ln(C)=1+x²/100; x=1,...,16.

    Each row is a distinct invented project; disclosure labels here exercise
    the trusted ingestion boundary only. No public observations are claimed.
    """
    return [
        record(
            f"p{i:02d}",
            snapshot=snapshot(
                f"p{i:02d}",
                features={
                    "well_count": Feature(value=i, available_on=DAY),
                },
            ),
            amount=math.exp(1 + (i * i / 100 if curved else i / 10)),
        )
        for i in range(1, 17)
    ]


def test_conformal_order_statistic_and_insufficient_calibration():
    """Sec. 2.2, arXiv:1604.04173v2 (2017): k=ceil((m+1)(1-alpha)).

    For residuals [1,2,3,4], alpha=0.5: ceil(5/2)=3, radius=3.
    For alpha=0.1, rank=ceil(4.5)=5>m: no finite interval.
    """
    assert conformal_radius([4, 2, 1, 3], 0.5) == 3
    with pytest.raises(ValueError, match="calibration"):
        conformal_radius([1, 2, 3, 4], 0.1)


def test_deterministic_prediction_matches_hand_calculated_line():
    """At x=2, ln(C)=1+2/10=1.2; C=exp(1.2), in currency millions.

    NIST e-Handbook sec. 4.4.3.1 OLS reproduces a full-rank exact line.
    """
    model = CapexEstimator(corpus(), policy(), DAY)
    result = model.predict(snapshot())
    assert result.status == "modeled"
    assert result.estimate == pytest.approx(math.exp(1.2))
    assert result.lower <= result.estimate <= result.upper
    assert result == model.predict(snapshot())
    assert result == CapexEstimator(list(reversed(corpus())), policy(), DAY).predict(
        snapshot()
    )
    assert len(result.comparables) == 16
    assert result.validation["overall"]["count"] == 16
    assert result.model_vintage == DAY.isoformat()
    assert result.model_hash
    assert result.feature_completeness == 1
    assert set(result.fit_groups) | set(result.calibration_groups) == set(
        result.comparables
    )
    assert not set(result.fit_groups) & set(result.calibration_groups)
    assert result.comparable_evidence[0]["derivation"] == "disclosed"
    assert result.comparable_evidence[0]["source"] == "synthetic test fixture"
    assert result.model_parameters["coefficients"]


def test_nonlinear_selection_and_untouched_outer_groups():
    """ln(C)=1+x²/100 has a quadratic solution; linear cannot reproduce it."""
    result = CapexEstimator(corpus(curved=True), policy(), DAY).predict(snapshot())
    assert result.status == "modeled"
    assert result.method == "log_quadratic"
    assert result.estimate == pytest.approx(math.exp(1.04))
    for fold in result.backtests:
        assert fold["held_out"] not in fold["fit_groups"]
        assert fold["held_out"] not in fold["calibration_groups"]
        assert not set(fold["fit_groups"]) & set(fold["calibration_groups"])
    assert result.validation["region:region-a"]["count"] == 16
    assert result.validation["architecture:subsea"]["count"] == 16


def test_sparse_and_small_cohorts_do_not_fabricate_values():
    for records, target in [
        (corpus()[:2], snapshot()),
        (corpus(), snapshot(features={})),
    ]:
        result = CapexEstimator(records, policy(), DAY).predict(target)
        assert result.status == "NOT_EVALUATED"
        assert result.estimate is result.lower is result.upper is None
        assert result.reason


def test_insufficient_calibration_and_failed_validation_are_closed():
    result = CapexEstimator(corpus(), policy(alpha=0.01), DAY).predict(snapshot())
    assert result.status == "NOT_EVALUATED"
    assert "calibration" in result.reason
    result = CapexEstimator(corpus(), policy(min_backtests=100), DAY).predict(
        snapshot()
    )
    assert result.status == "NOT_EVALUATED"
    assert result.backtests


def test_no_variation_and_extrapolation_are_closed():
    rows = [record(str(i)) for i in range(16)]
    assert (
        CapexEstimator(rows, policy(), DAY).predict(snapshot()).status
        == "NOT_EVALUATED"
    )
    target = snapshot(features={"well_count": Feature(value=100, available_on=DAY)})
    assert (
        CapexEstimator(corpus(), policy(), DAY).predict(target).status
        == "NOT_EVALUATED"
    )


def test_reconciliation_preserves_interval_relation_and_variance():
    """Interval arithmetic by hand: [2,4]+[3,5]=[5,9]; 10-8=2.

    Disjoint direct [9.5,11] is above [5,9]; missing components are indeterminate.
    """
    direct = (10, 9.5, 11)
    result = reconcile(direct, [(3, 2, 4), (5, 3, 5)])
    assert result == dict(
        bottom_up=8, lower=5, upper=9, variance=2, relation="direct_above"
    )
    assert reconcile(direct, [None])["relation"] == "indeterminate"
    assert reconcile((6, 5, 7), [(8, 8, 9)])["relation"] == "bottom_up_above"
    assert reconcile((6, 5, 7), [(8, 7, 9)])["relation"] == "overlap"


def test_report_escapes_values_and_shows_non_estimable_cases():
    target = snapshot(project="<script>alert(1)</script>")
    result = CapexEstimator([], policy(), DAY).predict(target)
    report = render_report([result], revision="initial", issued_on=DAY)
    assert "<script>" not in report
    assert "&lt;script&gt;" in report
    assert "NOT_EVALUATED" in report
    assert (
        report.index("Summary")
        < report.index("Revision history")
        < report.index("Predictions")
    )
    assert "Known-project backtests" in report


def test_hash_changes_with_policy_and_evidence():
    a = CapexEstimator(corpus(), policy(), DAY).predict(snapshot())
    b = CapexEstimator(corpus(), policy(source="different criteria"), DAY).predict(
        snapshot()
    )
    assert a.model_hash != b.model_hash


def test_bad_reconciliation_bounds_are_rejected():
    with pytest.raises(ValueError):
        reconcile((3, 5, 1), [(1, 1, 1)])


def test_reconciliation_requires_complete_disjoint_compatible_asset_scopes():
    """[2,4]+[3,5]=[5,9], and direct midpoint variance is 10-(3+5)=2."""
    direct = CapexEstimator(corpus(), policy(), DAY).predict(snapshot())
    direct = replace(direct, estimate=10, lower=9.5, upper=11)
    a = replace(
        direct,
        estimate=3,
        lower=2,
        upper=4,
        basis=direct.basis | {"scope_basis": "wells"},
    )
    b = replace(
        direct,
        estimate=5,
        lower=3,
        upper=5,
        basis=direct.basis | {"scope_basis": "host"},
    )
    result = reconcile_estimates(direct, {"wells": a, "host": b}, {"wells", "host"})
    assert result["variance"] == 2
    assert (
        reconcile_estimates(direct, {"wells": a}, {"wells", "host"})["relation"]
        == "indeterminate"
    )
    bad = replace(b, basis=b.basis | {"currency": "EUR"})
    with pytest.raises(ValueError, match="basis"):
        reconcile_estimates(direct, {"wells": a, "host": bad}, {"wells", "host"})
    with pytest.raises(ValueError, match="scope"):
        reconcile_estimates(direct, {"wells": a, "host": a}, {"wells", "host"})


def test_meaningful_nonzero_uncertainty_bounds():
    """Hand perturbation exp(±1/10) creates nonzero log residuals."""
    rows = [
        r.model_copy(update={"amount": r.amount * math.exp(0.1 if i % 2 else -0.1)})
        for i, r in enumerate(corpus())
    ]
    result = CapexEstimator(rows, policy(), DAY).predict(snapshot())
    assert result.status == "modeled"
    assert result.lower < result.estimate < result.upper
    assert result.validation["overall"]["errors"]


def test_model_selection_does_not_use_outer_label_or_calibration_labels():
    """Changing a held-out label cannot change that fold's model or interval."""
    rows = corpus()
    original = CapexEstimator(rows, policy(), DAY).predict(snapshot())
    rows[0] = rows[0].model_copy(update={"amount": rows[0].amount * 10})
    changed = CapexEstimator(rows, policy(), DAY).predict(snapshot())
    before, after = original.backtests[0], changed.backtests[0]
    for key in ("estimate", "lower", "upper", "selection", "method"):
        assert before[key] == after[key]
