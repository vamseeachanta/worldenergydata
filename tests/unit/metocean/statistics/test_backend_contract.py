"""Independent algebra and backend-boundary regressions for issue #1362.

Synthetic fixture numbers below define test inputs, not engineering limits.
Distribution equations: Coastal Engineering 123 (2017), 42–51,
'Deriving environmental contours from highest density regions', Eqs. (2)–(6).
"""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.metocean.statistics.backend import (
    JointBackendResult,
    guarded_reciprocal,
)
from worldenergydata.metocean.statistics.environmental_contours import (
    EnvironmentalContour,
)
from worldenergydata.metocean.statistics.joint_probability import (
    JointModel,
    JointProbabilityModel,
)


def raw_result():
    # Twelve fields, in the release contract recorded in issue #1362.
    return (
        1,
        2,
        3,
        4,
        5,
        6,
        np.array([0.1, 0.2]),
        np.array([1, 2]),
        [np.array([7, 8])],
        [np.array([3, 4])],
        [50],
        pd.DataFrame(),
    )


def test_return_contract_names():
    result = JointBackendResult.from_raw(raw_result())
    assert (result.a1, result.a2, result.a3) == (1, 2, 3)
    assert (result.b1, result.b2, result.b3) == (4, 5, 6)
    np.testing.assert_array_equal(result.h, [1, 2])
    np.testing.assert_array_equal(result.t3[0], [7, 8])
    np.testing.assert_array_equal(result.h3[0], [3, 4])


@pytest.mark.parametrize("size", [0, 11, 13])
def test_return_contract_rejects_wrong_length(size):
    with pytest.raises(ValueError, match="12"):
        JointBackendResult.from_raw(tuple(range(size)))


def test_zero_residual_is_reported_and_nonzero_values_are_unchanged():
    """1/2=0.5, 1/4=0.25; a zero residual is an exact minimum.

    Infinite peak height preserves that minimum without evaluating 1/0.
    This is an ordering rule, not an epsilon chosen from a tolerance.
    """
    guarded = []
    result = guarded_reciprocal(np.array([2.0, 0.0, 4.0]), guarded, "row")
    np.testing.assert_array_equal(result, [0.5, np.inf, 0.25])
    assert guarded == [{"location": "row", "indices": [1]}]


@pytest.mark.parametrize("values", [[-1.0], [np.nan], [np.inf]])
def test_invalid_residual_is_rejected(values):
    with pytest.raises(ValueError, match="residual"):
        guarded_reciprocal(np.array(values), [], "row")


def test_fit_decodes_coefficients_and_keeps_observations(monkeypatch):
    import worldenergydata.metocean.statistics.joint_probability as module

    monkeypatch.setattr(
        module,
        "fit_backend",
        lambda *args, **kwargs: (JointBackendResult.from_raw(raw_result()), []),
    )
    index = pd.date_range("2020-01-01", periods=3, freq="h")
    hs = pd.Series([1.0, 2.0, 3.0], index=index)
    tp = pd.Series([4.0, 5.0, 6.0], index=index)
    model = JointProbabilityModel().fit(hs, tp, periods=[50])
    assert model.conditional_tp["mu_coefficients"] == (1.0, 2.0, 3.0)
    assert model.conditional_tp["variance_coefficients"] == (4.0, 5.0, 6.0)
    assert model.marginal_hs["distribution"] == "tabulated_LogNoWe"
    np.testing.assert_array_equal(model.hs_samples, hs)
    np.testing.assert_array_equal(model.tp_samples, tp)


def test_backend_contour_axes_and_exact_period():
    model = JointModel({}, {}, 3, _raw_result=JointBackendResult.from_raw(raw_result()))
    contour = EnvironmentalContour().backend_contour(model, 50)
    np.testing.assert_array_equal(contour.hs_values, [3, 4])
    np.testing.assert_array_equal(contour.tp_values, [7, 8])
    assert contour.method == "backend_iso_density"
    with pytest.raises(ValueError, match="period"):
        EnvironmentalContour().backend_contour(model, 51)


def test_inverse_transform_hand_calculation():
    """Constrained fit to six pairs: Hs=(1,1,2,2,3,3), Tp=(1,4,1,4,1,4).

    Fix Weibull shape=1 and location=0: exponential MLE scale=sum(Hs)/6=2.
    In each Hs bin, mean(log Tp)=log(2), variance(log Tp)=log(2)^2.
    Choose zero slope for each conditional parameter. Thus at probabilities
    (1/2,1/2), Hs=-2*log(1-1/2)=2*log(2), Tp=exp(log(2))=2.
    Eqs. (2),(3),(6) in the 2017 paper above; these expected values are
    independent of the backend fit. The backend's unconstrained nonlinear
    fit on this underdetermined sample is NOT_EVALUATED.
    """
    model = JointModel(
        {
            "distribution": "tabulated_LogNoWe",
            "h": np.array([0.0, 2.0, 4.0]),
            "pdf": np.array([0.5, 0.25, 0.0]),
        },
        {
            "mu_coefficients": (np.log(2), 0.0, 1.0),
            "variance_coefficients": (np.log(2) ** 2, 0.0, 1.0),
        },
        6,
    )
    # The tabulated CDF is tested separately; the analytic Weibull transform
    # here uses the independently fitted parameters above.
    hs, tp = EnvironmentalContour.inverse_transform(
        model, np.array([0.5]), np.array([0.5]), weibull=(1.0, 0.0, 2.0)
    )
    np.testing.assert_allclose(hs, [2 * np.log(2)])
    np.testing.assert_allclose(tp, [2.0])


def uniform_model():
    # Synthetic uniform Hs on [0,2] and ln(Tp)~N(0,1).
    return JointModel(
        {"h": np.array([0.0, 1.0, 2.0]), "pdf": np.array([0.5, 0.5, 0.5])},
        {"mu_coefficients": (0.0, 0.0, 1.0), "variance_coefficients": (1.0, 0.0, 1.0)},
        6,
    )


def test_iform_and_isorm_are_distinct_hand_calculations():
    """Choose one sea state per quarter-year and return period one year.

    Eq. (7), Coastal Engineering 123 (2017), gives alpha=1/4.
    At angle zero, IFORM maps Phi(Phi^-1(3/4)) to uniform Hs=2*(3/4)=1.5,
    and the second normal coordinate is zero, giving Tp=1.
    For ISORM, chi-square survival with two dimensions is exp(-r^2/2),
    so r=sqrt(2*log(4)). At the quarter circle, Hs=1 and Tp=exp(r).
    Radius definitions: virocon 2.4.0, contours.py IFORMContour/ISORMContour.
    """
    ec = EnvironmentalContour(state_duration_hours=365.25 * 24 / 4)
    iform = ec.iform(uniform_model(), return_period=1)
    isorm = ec.isorm(uniform_model(), return_period=1)
    np.testing.assert_allclose(iform.hs_values[0], 1.5)
    np.testing.assert_allclose(iform.tp_values[0], 1.0)
    # 180 points is the cited virocon discretization; index 180/4 is pi/2.
    np.testing.assert_allclose(isorm.hs_values[45], 1.0)
    np.testing.assert_allclose(isorm.tp_values[45], np.exp(np.sqrt(2 * np.log(4))))
    assert not np.array_equal(iform.hs_values, isorm.hs_values)


@pytest.mark.parametrize("pdf", [[-1, 1, 1], [0, 0, 0], [np.nan, 1, 1]])
def test_invalid_marginal_has_no_silent_fallback(pdf):
    model = uniform_model()
    model.marginal_hs["pdf"] = pdf
    with pytest.raises(ValueError, match="PDF"):
        EnvironmentalContour().iform(model)


def test_negative_conditional_variance_has_no_silent_fallback():
    model = uniform_model()
    model.conditional_tp["variance_coefficients"] = (-1.0, 0.0, 1.0)
    with pytest.raises(ValueError, match="conditional"):
        EnvironmentalContour().iform(model)


def test_local_curve_exact_matches_hand_case(monkeypatch):
    """Each row has conditional density [1,3,0,3,1], marginal PDF=2.

    Select height=2 and joint peak=6, hence target conditional density=3.
    Exact intersections occur at period indices 1 and 3 (Tp=2 and 4).
    Walking the lower branch and returning on the upper branch gives the
    closed curve asserted below. Seven zero residuals are guarded: one at
    Hs=2, two at each of the three height rows. No threshold is selected.
    """
    from worldenergydata.metocean.statistics import backend

    monkeypatch.setattr(
        backend.ms.aux_funcs, "Weibull_method_of_moment", lambda data: (1, 0, 1)
    )
    monkeypatch.setattr(backend.weibull_min, "isf", lambda *args: 2.0)
    conditional = np.tile([1.0, 3.0, 0.0, 3.0, 1.0], (3, 1))
    guarded = []
    tp, hs, period, table = backend._curve(
        np.array([1.0, 2.0, 3.0]),
        np.array([2.0, 2.0, 2.0]),
        conditional * 2,
        conditional,
        np.array([1.0, 2.0, 3.0]),
        np.arange(1.0, 6.0),
        1,
        50,
        guarded,
    )
    np.testing.assert_array_equal(hs, [1, 2, 3, 3, 2, 1, 1])
    np.testing.assert_array_equal(tp, [2, 2, 2, 4, 4, 4, 2])
    assert period == 50
    assert len(table) == 3
    assert sum(len(item["indices"]) for item in guarded) == 7


def test_worked_example_against_independent_answer():
    """Six-pair derivation is written out in test_inverse_transform_hand_calculation.

    For normal point (0,1), the fitted conditional ln(Tp) mean=ln(2) and
    std=ln(2), giving Tp=exp(2*ln(2))=4. Hs remains 2*ln(2).
    Neither expected value is obtained from the example or backend fitter.
    """
    from worldenergydata.metocean.statistics.examples.conditional_hand_case import (
        worked_example,
    )

    result = worked_example()
    np.testing.assert_allclose(result["scale"], 2.0)
    np.testing.assert_allclose(result["mu"], np.log(2))
    np.testing.assert_allclose(result["variance"], np.log(2) ** 2)
    np.testing.assert_allclose(result["hs_point"], 2 * np.log(2))
    np.testing.assert_allclose(result["tp_point"], 4.0)
    assert result["backend_fit_validation"] == "NOT_EVALUATED"


def test_documented_statistics_api_replacements_exist():
    import metocean_stats
    from metocean_stats import stats

    from worldenergydata.metocean.statistics.eva import ExtremeValueAnalysis

    for old in ("EVA", "return_periods", "joint_probability", "directional"):
        assert not hasattr(metocean_stats, old)
    for name in (
        "return_levels_annual_max",
        "return_levels_pot",
        "joint_distribution_Hs_Tp",
        "directional_extremes",
        "calculate_scatter",
    ):
        assert callable(getattr(stats, name))
    for name in ("fit_annual_maxima", "fit_pot", "return_period_table"):
        assert callable(getattr(ExtremeValueAnalysis, name))


def test_report_uses_coefficient_roles_and_reports_guarded_points():
    """The report must not relabel a variance coefficient as constant sigma."""
    from worldenergydata.metocean.statistics.reporting import MetoceanReport

    model = uniform_model()
    model.guarded_points = [{"location": "synthetic", "indices": [1, 2]}]
    report = MetoceanReport(location_name="Synthetic example", lat=0.0, lon=0.0)
    report.add_joint(model)
    content = report._sections[-1].html_content
    assert "mu_coefficients" in content
    assert "variance_coefficients" in content
    assert "guarded_zero_residuals" in content
    assert "NOT_EVALUATED" in content
    assert "sigma_tp" not in content
    assert "marginal_hs_pdf" not in content
