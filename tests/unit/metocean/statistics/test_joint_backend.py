"""Numerical and return-contract regressions for the LoNoWe backend adapter.

All data and grids are synthetic. No environmental qualification is asserted.
"""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.metocean.statistics.examples.lonowe_example import synthetic_sample
from worldenergydata.metocean.statistics.joint_probability import JointProbabilityModel


def test_fit_exposes_backend_division_errors(monkeypatch):
    """A numerical failure during parameter estimation must reach the caller."""
    import metocean_stats.stats as ms

    original = ms.joint_distribution_Hs_Tp.__globals__["curve_fit"]

    def invalid_fit(*args, **kwargs):
        np.divide(1.0, 0.0)
        return original(*args, **kwargs)

    monkeypatch.setitem(
        ms.joint_distribution_Hs_Tp.__globals__, "curve_fit", invalid_fit
    )
    with pytest.raises(RuntimeWarning, match="divide by zero"):
        JointProbabilityModel().fit(*synthetic_sample(), periods=[50])


def test_fit_avoids_unsafe_upstream_curve_without_patching_it(monkeypatch):
    import metocean_stats.stats.aux_funcs as aux

    def unsafe_curve(*args, **kwargs):
        raise AssertionError("reciprocal-distance curve was called")

    monkeypatch.setattr(aux, "Hs_Tp_curve", unsafe_curve)
    hs, tp = synthetic_sample()
    result = JointProbabilityModel().fit(hs, tp, periods=[50])
    assert np.isfinite(result._raw_result[8][0]).all()
    assert aux.Hs_Tp_curve is unsafe_curve


@pytest.fixture
def curve_inputs(monkeypatch):
    import metocean_stats.stats.aux_funcs as aux

    # Stipulated exponential marginal: isf(1/e) = 1 m, exactly on the Hs grid.
    monkeypatch.setattr(aux, "Weibull_method_of_moment", lambda data: (1.0, 0.0, 1.0))
    marginal = np.array([1.0, 0.5, 0.0])
    conditional = np.tile([0.0, 0.4, 0.8, 0.4, 0.0], (3, 1))
    return (
        np.array([0.5, 1.0, 1.5]),
        marginal,
        marginal[:, None] * conditional,
        conditional,
        np.array([0.5, 1.0, 1.5]),
        np.arange(1.0, 6.0),
        100 * 365.2422 * 24 / np.e,
    )


def test_curve_handles_exact_matches_and_zero_marginal(curve_inputs):
    from worldenergydata.metocean.statistics._joint_backend import _hs_tp_curve

    with np.errstate(divide="raise", invalid="raise"):
        tp, hs, period, table = _hs_tp_curve(*curve_inputs, X=100)
    # Joint density at Hs=1 is .5*.8=.4; at Hs=.5 its roots are Tp=2,4.
    np.testing.assert_array_equal(tp, [2.0, 4.0, 2.0])
    np.testing.assert_array_equal(hs, [0.5, 0.5, 0.5])
    assert period == 100
    pd.testing.assert_frame_equal(
        table, pd.DataFrame({"hs": [0.5], "t1": [2.0], "t2": [4.0]})
    )


@pytest.mark.parametrize("bad_value", [-1.0, np.nan, np.inf])
def test_curve_rejects_invalid_density(curve_inputs, bad_value):
    from worldenergydata.metocean.statistics._joint_backend import _hs_tp_curve

    curve_inputs[1][0] = bad_value
    with pytest.raises(ValueError, match="density"):
        _hs_tp_curve(*curve_inputs, X=100)


def test_curve_rejects_empty_contour(curve_inputs):
    from worldenergydata.metocean.statistics._joint_backend import _hs_tp_curve

    curve_inputs[3][:] = 0.8  # Flat rows have no pair of interior branches.
    curve_inputs[2][:] = curve_inputs[1][:, None] * curve_inputs[3]
    with pytest.raises(ValueError, match="contour"):
        _hs_tp_curve(*curve_inputs, X=100)


def _valid_result():
    return (
        1.5,
        0.4,
        0.36,
        0.005,
        0.1,
        0.5,
        np.array([0.1, 0.5, 0.1]),
        np.array([0.5, 1.0, 1.5]),
        [np.array([2.0, 3.0, 2.0])],
        [np.array([0.5, 0.5, 0.5])],
        [50],
        pd.DataFrame({"hs_50": [0.5], "t1_50": [2.0], "t2_50": [3.0]}),
    )


@pytest.mark.parametrize(
    "index,replacement,message",
    [
        (0, np.nan, "conditional coefficients"),
        (3, -1.0, "conditional variance"),
        (6, np.array([0.1, -0.5, 0.1]), "density.*finite and nonnegative"),
        (6, np.array([0.1, np.nan, 0.1]), "density.*finite and nonnegative"),
        (6, np.array([0.1]), "marginal grid shape"),
        (7, np.array([1.0, 0.5, 1.5]), "height grid"),
        (8, [np.array([2.0, np.nan, 2.0])], "Non-finite.*coordinates"),
        (8, [np.array([-2.0, 3.0, -2.0])], "positive.*coordinates"),
        (9, [np.array([0.5])], "coordinate shape"),
        (10, [100], "unexpected return periods"),
    ],
)
def test_return_contract_rejects_malformed_results(index, replacement, message):
    from worldenergydata.metocean.statistics._joint_backend import validate_joint_result

    raw = list(_valid_result())
    raw[index] = replacement
    with pytest.raises(ValueError, match=message):
        validate_joint_result(tuple(raw), [50])


def test_return_contract_checks_tuple_length():
    from worldenergydata.metocean.statistics._joint_backend import validate_joint_result

    with pytest.raises(ValueError, match="12"):
        validate_joint_result(_valid_result()[:-1], [50])


def test_return_contract_accepts_valid_tuple():
    from worldenergydata.metocean.statistics._joint_backend import validate_joint_result

    validate_joint_result(_valid_result(), [50])


@pytest.mark.parametrize("invalid", ["index", "nan", "nonpositive", "empty"])
def test_fit_rejects_invalid_observations(invalid):
    hs, tp = synthetic_sample()
    if invalid == "index":
        tp.index = tp.index + pd.Timedelta(hours=1)
    elif invalid == "nan":
        hs.iloc[0] = np.nan
    elif invalid == "nonpositive":
        tp.iloc[0] = 0
    else:
        hs, tp = hs.iloc[:0], tp.iloc[:0]
    with pytest.raises(ValueError, match="observations|index"):
        JointProbabilityModel().fit(hs, tp, periods=[50])


def test_adapter_rejects_unreviewed_backend_version(monkeypatch):
    from worldenergydata.metocean.statistics import _joint_backend as backend

    monkeypatch.setattr(backend, "version", lambda package: "9.0.0")
    hs, tp = synthetic_sample()
    with pytest.raises(ValueError, match="version"):
        backend.fit_joint_distribution(pd.DataFrame({"hs": hs, "tp": tp}), [50])


@pytest.mark.parametrize("periods", [[], [0], [-1], [np.nan], [50, 50]])
def test_fit_rejects_invalid_return_periods(periods):
    with pytest.raises(ValueError, match="period"):
        JointProbabilityModel().fit(*synthetic_sample(), periods=periods)


def test_fit_succeeds_with_floating_point_errors_enabled():
    with np.errstate(divide="raise", invalid="raise"):
        result = JointProbabilityModel().fit(*synthetic_sample(), periods=[1, 100])
    assert result.fitted_periods == (1, 100)


def test_curve_rejects_zero_level(curve_inputs):
    from worldenergydata.metocean.statistics._joint_backend import _hs_tp_curve

    curve_inputs[2][1] = 0
    with pytest.raises(ValueError, match="level"):
        _hs_tp_curve(*curve_inputs, X=100)


def test_curve_rejects_return_height_outside_grid(curve_inputs, monkeypatch):
    import metocean_stats.stats.aux_funcs as aux

    from worldenergydata.metocean.statistics._joint_backend import _hs_tp_curve

    monkeypatch.setattr(aux, "Weibull_method_of_moment", lambda data: (1.0, 10.0, 1.0))
    with pytest.raises(ValueError, match="grid"):
        _hs_tp_curve(*curve_inputs, X=100)


def test_curve_ignores_tiny_marginal_without_overflow(curve_inputs):
    from worldenergydata.metocean.statistics._joint_backend import _hs_tp_curve

    # The level divided by this marginal would overflow float64.
    curve_inputs[1][2] = np.nextafter(0.0, 1.0)
    tiny = curve_inputs[1][2]
    curve_inputs[2][2] = [0.0, tiny, tiny, 0.0, 0.0]
    curve_inputs[3][2] = [0.0, 1.0, 1.0, 0.0, 0.0]
    with np.errstate(divide="raise", invalid="raise", over="raise"):
        tp, _, _, _ = _hs_tp_curve(*curve_inputs, X=100)
    np.testing.assert_array_equal(tp, [2.0, 4.0, 2.0])


def test_adapter_matches_legacy_reference():
    import metocean_stats.stats as ms

    from worldenergydata.metocean.statistics._joint_backend import (
        fit_joint_distribution,
    )

    hs, tp = synthetic_sample()
    frame = pd.DataFrame({"hs": hs, "tp": tp})
    # Only the legacy reference needs this: it deliberately computes 1/0.
    # The adapter itself is evaluated with strict floating-point handling.
    with np.errstate(divide="ignore"):
        expected = ms.joint_distribution_Hs_Tp(frame.copy(), periods=[1, 100])
    with np.errstate(divide="raise", invalid="raise"):
        actual = fit_joint_distribution(frame.copy(), [1, 100])
    for position in range(8):
        np.testing.assert_array_equal(actual[position], expected[position])
    for position in (8, 9):
        for got, want in zip(actual[position], expected[position], strict=True):
            np.testing.assert_array_equal(got, want)
    assert actual[10] == expected[10]
    pd.testing.assert_frame_equal(actual[11], expected[11])


def test_curve_preserves_plateau_branch_order(curve_inputs):
    from worldenergydata.metocean.statistics._joint_backend import _hs_tp_curve

    conditional = np.tile([0.0, 0.4, 0.4, 0.8, 0.4, 0.4, 0.0], (3, 1))
    args = list(curve_inputs)
    args[2] = args[1][:, None] * conditional
    args[3], args[5] = conditional, np.arange(1.0, 8.0)
    tp, hs, _, _ = _hs_tp_curve(*args, X=100)
    # SciPy chooses the lower centre for an even plateau: [2,3] and [5,6].
    np.testing.assert_array_equal(tp, [2.0, 5.0, 2.0])
    np.testing.assert_array_equal(hs, [0.5, 0.5, 0.5])


@pytest.mark.parametrize("invalid", ["type", "columns", "values", "coordinates"])
def test_return_contract_rejects_inconsistent_branch_table(invalid):
    from worldenergydata.metocean.statistics._joint_backend import validate_joint_result

    raw = list(_valid_result())
    if invalid == "type":
        raw[11] = None
    elif invalid == "columns":
        raw[11] = raw[11].rename(columns={"t1_50": "tp_50"})
    elif invalid == "values":
        raw[11].loc[0, "t1_50"] = np.nan
    else:
        raw[11].loc[0, "t1_50"] = 1.5
    with pytest.raises(ValueError, match="table"):
        validate_joint_result(tuple(raw), [50])


def test_adapter_failure_preserves_backend_bindings(monkeypatch):
    import metocean_stats.stats as ms
    import metocean_stats.stats.aux_funcs as aux

    from worldenergydata.metocean.statistics import _joint_backend as backend

    original = ms.joint_distribution_Hs_Tp
    globals_before = {name: id(value) for name, value in original.__globals__.items()}
    curve_before = aux.Hs_Tp_curve

    def failed_curve(*args, **kwargs):
        raise ArithmeticError("synthetic contour failure")

    monkeypatch.setattr(backend, "_hs_tp_curve", failed_curve)
    hs, tp = synthetic_sample()
    with pytest.raises(ArithmeticError, match="synthetic contour failure"):
        backend.fit_joint_distribution(pd.DataFrame({"hs": hs, "tp": tp}), [50])
    assert ms.joint_distribution_Hs_Tp is original
    assert aux.Hs_Tp_curve is curve_before
    assert {
        name: id(value) for name, value in original.__globals__.items()
    } == globals_before


@pytest.mark.parametrize(
    "invalid", ["range_index", "unsorted", "duplicate", "one_sample"]
)
def test_fit_rejects_invalid_time_index(invalid):
    hs, tp = synthetic_sample()
    if invalid == "range_index":
        hs, tp = hs.reset_index(drop=True), tp.reset_index(drop=True)
    elif invalid == "unsorted":
        hs, tp = hs.iloc[::-1], tp.iloc[::-1]
    elif invalid == "duplicate":
        hs.index = tp.index = pd.DatetimeIndex([hs.index[0]] * len(hs))
    else:
        hs, tp = hs.iloc[:1], tp.iloc[:1]
    with pytest.raises(ValueError, match="observations|index"):
        JointProbabilityModel().fit(hs, tp, periods=[50])


@pytest.mark.parametrize("missing_column", ["hs", "tp"])
def test_fit_rejects_nullable_missing_observations_before_backend(
    monkeypatch, missing_column
):
    import worldenergydata.metocean.statistics.joint_probability as module

    hs, tp = synthetic_sample()
    hs, tp = hs.astype("Float64"), tp.astype("Float64")
    (hs if missing_column == "hs" else tp).iloc[0] = pd.NA

    def unexpected_backend(*args, **kwargs):
        pytest.fail("missing observations reached the backend")

    monkeypatch.setattr(module, "fit_joint_distribution", unexpected_backend)
    with pytest.raises(ValueError, match="observations"):
        JointProbabilityModel().fit(hs, tp, periods=[50])
