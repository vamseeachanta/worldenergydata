"""LoNoWe contour regression and explicit unsupported-method contracts.

Basis: metocean-stats v.1.2.0 extreme.py L610-L766 and aux_funcs.py
L121-L175 (Tp first, constant joint density, data-derived duration).
Synthetic inputs and hand calculations are specified in lonowe_example.py.
"""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.metocean.statistics.environmental_contours import (
    EnvironmentalContour,
)
from worldenergydata.metocean.statistics.joint_probability import (
    JointModel,
    JointProbabilityModel,
)


@pytest.fixture(scope="module")
def sample():
    from worldenergydata.metocean.statistics.examples.lonowe_example import (
        synthetic_sample,
    )

    return synthetic_sample()


@pytest.fixture(scope="module")
def joint_model(sample):
    return JointProbabilityModel().fit(*sample, periods=[1, 100])


def test_axes_are_bounded_by_their_own_input_ranges(joint_model, sample):
    """Bounds are sample extrema expanded by that variable's sample span.

    This data-derived dimensional bound allows tail extrapolation, but fails
    if Tp is used as Hs: max(Tp contour) exceeds max(Hs) + span(Hs).
    No environmental acceptance limit is asserted.
    """
    contour = EnvironmentalContour().lonowe(joint_model, 100)
    hs, tp = sample
    assert 0 < contour.hs_values.min() < hs.min()
    assert hs.max() < contour.hs_values.max() < hs.max() + np.ptp(hs)
    assert 0 < contour.tp_values.min() < tp.min()
    assert tp.max() < contour.tp_values.max() < tp.max() + np.ptp(tp)
    # Exact upstream position contract, aux_funcs.py L165-L175.
    np.testing.assert_array_equal(contour.hs_values, joint_model._raw_result[9][1])
    np.testing.assert_array_equal(contour.tp_values, joint_model._raw_result[8][1])
    assert contour.method == "LoNoWe"


def test_larger_contour_encloses_smaller(joint_model):
    """Nested density superlevel sets must have nested Tp intervals at each Hs.

    Compare the branches on the smaller contour's Hs grid; no fitted constants
    or arbitrary numerical tolerances enter this ordering check.
    """

    def branches(contour):
        heights = np.unique(contour.hs_values)
        bounds = [contour.tp_values[contour.hs_values == height] for height in heights]
        return (
            heights,
            np.array([t.min() for t in bounds]),
            np.array([t.max() for t in bounds]),
        )

    ec = EnvironmentalContour()
    small, large = ec.lonowe(joint_model, 1), ec.lonowe(joint_model, 100)
    h, low, high = branches(small)
    outer_h, outer_low, outer_high = branches(large)
    assert outer_h.min() <= h.min() < h.max() <= outer_h.max()
    assert np.all(np.interp(h, outer_h, outer_low) <= low)
    assert np.all(np.interp(h, outer_h, outer_high) >= high)
    assert large.hs_values.max() > small.hs_values.max()


@pytest.mark.parametrize("period", [10, 0, -1, float("nan")])
def test_unfitted_period_is_rejected(joint_model, period):
    with pytest.raises(ValueError, match="fitted return periods"):
        EnvironmentalContour().lonowe(joint_model, period)


@pytest.mark.parametrize("method", ["iform", "isorm"])
def test_reliability_methods_are_not_density_contours(joint_model, method):
    with pytest.raises(NotImplementedError, match="NOT_EVALUATED.*constant-density"):
        getattr(EnvironmentalContour(), method)(joint_model, 100)


def test_duration_mismatch_is_rejected(joint_model):
    with pytest.raises(ValueError, match="duration"):
        EnvironmentalContour(state_duration_hours=3).lonowe(joint_model, 100)


def test_matching_duration_is_accepted(joint_model):
    ec = EnvironmentalContour(state_duration_hours=joint_model.state_duration_hours)
    np.testing.assert_array_equal(
        ec.lonowe(joint_model, 1).hs_values, joint_model._raw_result[9][0]
    )


def test_missing_fit_never_fabricates_an_ellipse():
    model = JointModel(marginal_hs={}, conditional_tp={}, n_samples=0)
    with pytest.raises(NotImplementedError, match="NOT_EVALUATED"):
        EnvironmentalContour().lonowe(model, 100)


def test_plot_preserves_units_and_coordinates(joint_model, sample):
    contour = EnvironmentalContour().lonowe(joint_model, 100)
    data = pd.DataFrame({"hs": sample[0], "tp": sample[1]})
    fig = EnvironmentalContour().plot_contour(contour, data)
    np.testing.assert_array_equal(fig.data[1].x[:-1], contour.tp_values)
    np.testing.assert_array_equal(fig.data[1].y[:-1], contour.hs_values)
    assert fig.layout.xaxis.title.text == "Tp (s)"
    assert fig.layout.yaxis.title.text == "Hs (m)"


def test_one_point_by_independent_log_density_algebra(joint_model, sample):
    """Hand check, not a call to the backend density/contour implementation.

    From v.1.2.0 extreme.py L740-L746, put y=ln(Tp). Constant density at
    fixed Hs gives (y-mu)**2/(2*v)+y=constant. Completing the square gives
    (y-(mu-v))**2=constant, hence t_low*t_high=exp(2*(mu-v)).
    The two sampled roots bracket true roots within one Tp grid cell;
    the grid endpoints and count are upstream extreme.py L735. Thus the
    product of the two lower cell edges bounds the analytic product below,
    and the upper edges bound it above. No fitted-output reference number
    or arbitrary tolerance is used. Test height is nearest the sample median.
    """
    import math

    for period in (1, 100):
        contour = EnvironmentalContour().lonowe(joint_model, period)
        heights = np.unique(contour.hs_values)
        h = float(heights[np.argmin(abs(heights - sample[0].median()))])
        t = contour.tp_values[contour.hs_values == h]
        low, high = float(t.min()), float(t.max())
        a = joint_model.conditional_tp["mu"]
        b = joint_model.conditional_tp["variance"]
        mu = a["a1"] + a["a2"] * h ** a["a3"]
        v = b["b1"] + b["b2"] * math.exp(-b["b3"] * h)
        # Grid resolution: v.1.2.0 extreme.py L735, linspace(.01,40,2000).
        cell = (40.0 - 0.01) / (2000 - 1)
        expected_product = math.exp(2 * (mu - v))
        assert (low - cell) * (high - cell) < expected_product
        assert expected_product < (low + cell) * (high + cell)
