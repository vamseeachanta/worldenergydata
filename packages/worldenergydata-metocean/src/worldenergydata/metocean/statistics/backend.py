"""Pinned metocean-stats contract and local zero-residual adaptation.

Algorithm basis: metocean-stats 1.2.0, stats/aux_funcs.py, Hs_Tp_curve.
No installed module or process-wide numerical warning policy is changed.
"""

from types import FunctionType, SimpleNamespace
from typing import NamedTuple

import metocean_stats.stats as ms
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from scipy.stats import weibull_min


class JointBackendResult(NamedTuple):
    """The twelve outputs of joint_distribution_Hs_Tp in release 1.2.0."""

    a1: float
    a2: float
    a3: float
    b1: float
    b2: float
    b3: float
    pdf_Hs: np.ndarray
    h: np.ndarray
    t3: list
    h3: list
    X: list
    hs_tpl_tph: pd.DataFrame

    @classmethod
    def from_raw(cls, raw):
        if not isinstance(raw, tuple) or len(raw) != len(cls._fields):
            raise ValueError("Expected the metocean-stats 1.2.0 12-tuple")
        return cls(*raw)


def guarded_reciprocal(residual, guarded_points, location):
    """Rank exact matches as infinite peaks, without ever evaluating 1/0."""
    residual = np.asarray(residual, dtype=float)
    if not np.isfinite(residual).all() or (residual < 0).any():
        raise ValueError("Expected finite nonnegative residuals")
    zeros = residual == 0
    if zeros.any():
        guarded_points.append(
            {"location": location, "indices": np.flatnonzero(zeros).tolist()}
        )
    reciprocal = np.full_like(residual, np.inf)
    np.divide(1, residual, out=reciprocal, where=~zeros)
    return reciprocal


def _curve(data, pdf_hs, joint_pdf, conditional_pdf, h, t, interval, X, guarded):
    """Release 1.2.0 Hs_Tp_curve with only reciprocal evaluation guarded.

    Calendar and one-year conversion below are retained from that release's
    Hs_Tp_curve; their physical suitability is NOT_EVALUATED. No epsilon
    threshold is introduced. Other numerical warnings continue to fail.
    """
    shape, loc, scale = ms.aux_funcs.Weibull_method_of_moment(data)
    if X == 1:
        period = 1.5873 * 365.2422 * 24 / interval
    else:
        period = X * 365.2422 * 24 / interval
    rve = weibull_min.isf(1 / period, shape, loc, scale)
    inverse = guarded_reciprocal(abs(h - rve), guarded, f"{X}:height")
    peaks, _ = find_peaks(inverse)
    index = peaks[0] if len(peaks) else np.argmax(inverse)
    density = joint_pdf[index, :]
    peaks, _ = find_peaks(density)
    index = peaks[0] if len(peaks) else np.argmax(density)
    level = density[index]

    heights, lower, upper = [], [], []
    for row, height in enumerate(h):
        target = level / pdf_hs[row]
        inverse = guarded_reciprocal(
            abs(conditional_pdf[row, :] - target), guarded, f"{X}:row:{row}"
        )
        indices, _ = find_peaks(inverse)
        if len(indices) == 2:
            heights.append(height)
            lower.append(t[indices[0]])
            upper.append(t[indices[1]])
    heights, lower, upper = map(np.asarray, (heights, lower, upper))
    tp = np.concatenate((lower, upper[::-1], lower[:1]))
    hs = np.concatenate((heights, heights[::-1], heights[:1]))
    table = pd.DataFrame({"hs": heights, "t1": lower, "t2": upper})
    return tp, hs, X, table


def fit_backend(data, periods):
    """Call a local function clone with a private auxiliary-function namespace.

    The shared auxiliary-function binding is not replaced. No installed-library
    file is edited. Other upstream side effects are inherited, not isolated.
    """
    guarded = []
    original = ms.joint_distribution_Hs_Tp
    namespace = dict(original.__globals__)
    auxiliary = SimpleNamespace(**vars(namespace["aux_funcs"]))

    def curve(data, pdf_Hs, pdf_Hs_Tp, f_Hs_Tp, h, t, interval, X=100):
        return _curve(data, pdf_Hs, pdf_Hs_Tp, f_Hs_Tp, h, t, interval, X, guarded)

    auxiliary.Hs_Tp_curve = curve
    namespace["aux_funcs"] = auxiliary
    local = FunctionType(
        original.__code__, namespace, original.__name__, original.__defaults__
    )
    raw = local(data, var_hs="hs", var_tp="tp", periods=periods)
    return JointBackendResult.from_raw(raw), guarded
