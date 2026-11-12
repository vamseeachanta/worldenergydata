"""Finite contour extraction for the metocean-stats LoNoWe return contract.

The fitted model is retained from releases 1.1.9 and 1.2.0. Only the
reciprocal-distance contour search in stats/aux_funcs.py is replaced.
Source: https://github.com/MET-OM/metocean-stats/blob/v.1.2.0/metocean_stats/stats/aux_funcs.py
"""

from importlib.metadata import version
from types import FunctionType, SimpleNamespace

import metocean_stats.stats as ms
import metocean_stats.stats.aux_funcs as aux
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from scipy.stats import weibull_min


def _density(array):
    values = np.asarray(array, dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("LoNoWe density must be finite and nonnegative")
    return values


def _hs_tp_curve(data, pdf_hs, joint_pdf, conditional_pdf, h, t, interval, X=100):
    """Retain upstream grid minima and Tp-first ordering without reciprocals."""
    pdf_hs, joint_pdf, conditional_pdf = map(
        _density, (pdf_hs, joint_pdf, conditional_pdf)
    )
    if pdf_hs.shape != h.shape or joint_pdf.shape != (len(h), len(t)):
        raise ValueError("Invalid LoNoWe density grid shape")
    if conditional_pdf.shape != joint_pdf.shape:
        raise ValueError("Invalid LoNoWe conditional density grid shape")
    shape, loc, scale = aux.Weibull_method_of_moment(data)
    # Upstream aux_funcs.py L127-L130 retains the label 1 for this level.
    years = 1.5873 if X == 1 else X
    period = years * 365.2422 * 24 / interval
    return_hs = weibull_min.isf(1 / period, shape, loc, scale)
    if not np.isfinite(return_hs) or not h[0] <= return_hs <= h[-1]:
        raise ValueError("Return height lies outside the fitted LoNoWe grid")
    row = joint_pdf[np.argmin(np.abs(h - return_hs))]
    peaks = find_peaks(row)[0]
    level = row[peaks[0] if peaks.size else np.argmax(row)]
    if not np.isfinite(level) or level <= 0:
        raise ValueError("LoNoWe contour level must be finite and positive")
    heights, lower, upper = [], [], []
    for height, marginal, joint_row in zip(h, pdf_hs, joint_pdf, strict=True):
        if marginal == 0:
            continue
        # |p*f-L| = p*|f-L/p| for p>0; local minima avoid both divisions.
        # Floating-point ties can differ from the reciprocal formulation.
        indices = find_peaks(-np.abs(joint_row - level))[0]
        if indices.size == 2:
            heights.append(height)
            lower.append(t[indices[0]])
            upper.append(t[indices[1]])
    if not heights:
        raise ValueError("No two-branch LoNoWe contour exists on the fitted grid")
    table = pd.DataFrame({"hs": heights, "t1": lower, "t2": upper})
    tp = np.concatenate((lower, upper[::-1], lower[:1]))
    hs = np.concatenate((heights, heights[::-1], heights[:1]))
    return tp, hs, X, table


def fit_joint_distribution(frame, periods):
    """Adapt one function's globals without changing the installed backend."""
    if version("metocean-stats") not in {"1.1.9", "1.2.0"}:
        raise ValueError("Unsupported metocean-stats version for LoNoWe adapter")
    backend = ms.joint_distribution_Hs_Tp
    if not isinstance(backend, FunctionType) or not {
        "aux_funcs",
        "Hs_Tp_curve",
    }.issubset(backend.__code__.co_names):
        raise ValueError("Unsupported metocean-stats joint-fit interface")
    local_aux = SimpleNamespace(**{**vars(aux), "Hs_Tp_curve": _hs_tp_curve})
    local_globals = {**backend.__globals__, "aux_funcs": local_aux}
    fit = FunctionType(
        backend.__code__,
        local_globals,
        backend.__name__,
        backend.__defaults__,
        backend.__closure__,
    )
    fit.__kwdefaults__ = backend.__kwdefaults__
    return fit(frame, var_hs="hs", var_tp="tp", periods=periods)


def validate_joint_result(raw, periods):
    """Validate numerical structure, not statistical or design suitability."""
    if not isinstance(raw, tuple) or len(raw) != 12:
        raise ValueError("Expected the 12-position LoNoWe backend result")
    coefficients = np.asarray(raw[:6], dtype=float)
    if coefficients.shape != (6,) or not np.isfinite(coefficients).all():
        raise ValueError("Invalid LoNoWe conditional coefficients")
    pdf, h = _density(raw[6]), np.asarray(raw[7], dtype=float)
    if h.ndim != 1 or h.size < 2 or pdf.shape != h.shape:
        raise ValueError("Invalid LoNoWe marginal grid shape")
    if not np.isfinite(h).all() or (h <= 0).any() or (np.diff(h) <= 0).any():
        raise ValueError("LoNoWe height grid must be positive and increasing")
    if not (pdf > 0).any():
        raise ValueError("LoNoWe marginal density is zero everywhere")
    b1, b2, b3 = coefficients[3:]
    variance = b1 + b2 * np.exp(-b3 * h)
    if not np.isfinite(variance).all() or (variance <= 0).any():
        raise ValueError("LoNoWe conditional variance must be finite and positive")
    if list(raw[10]) != list(periods):
        raise ValueError("LoNoWe backend returned unexpected return periods")
    if len(raw[8]) != len(periods) or len(raw[9]) != len(periods):
        raise ValueError("LoNoWe backend returned an unexpected contour count")
    table = raw[11]
    columns = [f"{name}_{period}" for period in periods for name in ("hs", "t1", "t2")]
    if not isinstance(table, pd.DataFrame) or list(table.columns) != columns:
        raise ValueError("Invalid LoNoWe branch table columns")
    for i, period in enumerate(periods):
        _validate_contour(raw[9][i], raw[8][i], table, period, h)


def _validate_contour(hs, tp, table, period, grid):
    hs, tp = np.asarray(hs, dtype=float), np.asarray(tp, dtype=float)
    if hs.ndim != 1 or hs.shape != tp.shape or not hs.size:
        raise ValueError("Invalid LoNoWe contour coordinate shape")
    if not (np.isfinite(hs).all() and np.isfinite(tp).all()):
        raise ValueError("Non-finite LoNoWe contour coordinates")
    if (hs <= 0).any() or (tp <= 0).any() or not np.isin(hs, grid).all():
        raise ValueError("Invalid positive LoNoWe contour coordinates")
    branch = table[[f"{name}_{period}" for name in ("hs", "t1", "t2")]]
    branch = branch.dropna(how="all").to_numpy(dtype=float)
    if not branch.size or not np.isfinite(branch).all() or (branch <= 0).any():
        raise ValueError("Invalid LoNoWe branch table values")
    h, low, high = branch.T
    if (np.diff(h) <= 0).any() or (low >= high).any():
        raise ValueError("Invalid LoNoWe branch table ordering")
    expected_hs = np.concatenate((h, h[::-1], h[:1]))
    expected_tp = np.concatenate((low, high[::-1], low[:1]))
    if not (np.array_equal(hs, expected_hs) and np.array_equal(tp, expected_tp)):
        raise ValueError("LoNoWe contour coordinates disagree with branch table")
