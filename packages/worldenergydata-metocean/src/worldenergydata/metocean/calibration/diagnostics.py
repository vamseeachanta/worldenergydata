"""Paired marginal/joint diagnostics and strictly ordered time blocks."""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .bias_correction import _vectors


def _finite_pairs(*values):
    arrays = _vectors(*values)
    mask = np.logical_and.reduce([np.isfinite(a) for a in arrays])
    if mask.sum() < 2:
        raise ValueError("At least two finite paired samples are required")
    return [a[mask] for a in arrays]


def _correlation(x, y, rank=False):
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        return float("nan")
    return float(spearmanr(x, y).statistic if rank else np.corrcoef(x, y)[0, 1])


def metrics(observed, model):
    """Model minus observation bias; population CV and quantiles of model.

    Pearson r and CV are NaN when undefined (constant series / zero mean).
    All metrics use the same finite pairs. RMSD has the variable's units.
    """
    o, m = _finite_pairs(observed, model)
    return {
        "n_pairs": len(m),
        "bias": float(np.mean(m - o)),
        "rmsd": float(np.sqrt(np.mean((m - o) ** 2))),
        "pearson_r": _correlation(o, m),
        "cv": float(np.std(m) / np.mean(m)) if np.mean(m) != 0 else float("nan"),
        "p50": float(np.quantile(m, 0.5)),
        "p95": float(np.quantile(m, 0.95)),
    }


def _edges(values, given, width):
    if given is None:
        lower = np.floor(min(a.min() for a in values) / width) * width
        upper = np.ceil(max(a.max() for a in values) / width) * width
        edges = np.arange(lower, max(upper, lower + width) + width / 2, width)
    else:
        edges = np.asarray(given, dtype=float)
    if (
        edges.ndim != 1
        or edges.size < 2
        or not np.isfinite(edges).all()
        or np.any(np.diff(edges) <= 0)
    ):
        raise ValueError("Histogram edges must be finite and strictly increasing")
    return edges


def joint_diagnostics(
    obs_hs, obs_tm02, model_hs, model_tm02, *, hs_edges=None, tm_edges=None
):
    """L1 of probability masses on shared Hs (m) / Tm02 (s) cells; range [0,2].

    Defaults cover all finite paired values in 0.25 m by 0.5 s cells. Explicit
    edges normalize each histogram over its in-range samples, with retained
    counts exposed. Rank correlation uses all finite pairs, including tails.
    """
    oh, ot, mh, mt = _finite_pairs(obs_hs, obs_tm02, model_hs, model_tm02)
    he = _edges((oh, mh), hs_edges, 0.25)
    te = _edges((ot, mt), tm_edges, 0.5)
    p = np.histogram2d(oh, ot, bins=(he, te))[0]
    r = np.histogram2d(mh, mt, bins=(he, te))[0]
    if p.sum() == 0 or r.sum() == 0:
        raise ValueError("No samples in histogram range")
    return {
        "n_pairs": len(oh),
        "l1": float(np.abs(p / p.sum() - r / r.sum()).sum()),
        "spearman_observed": _correlation(oh, ot, rank=True),
        "spearman_model": _correlation(mh, mt, rank=True),
        "observed_in_range": int(p.sum()),
        "model_in_range": int(r.sum()),
        "hs_edges": he.tolist(),
        "tm_edges": te.tolist(),
    }


def time_block_split(times, calibration, validation, *, random=False):
    """Return boolean masks for half-open [start, end) timestamp windows.

    Calibration must precede validation, with no overlap. Input timestamps
    must be sorted (ties permit simultaneous observations at different sites).
    Gaps and excluded times are allowed; both selected blocks must be nonempty.
    Random or interleaved sampling is refused.
    """
    if random:
        raise ValueError("random splits are refused; use contiguous time blocks")
    t = pd.DatetimeIndex(times)
    if t.hasnans or not t.is_monotonic_increasing:
        raise ValueError("times must be sorted and contain no NaT")
    if len(calibration) != 2 or len(validation) != 2:
        raise ValueError("Each window must contain a start and end")
    cs, ce, vs, ve = map(pd.Timestamp, (*calibration, *validation))
    if any(pd.isna(v) for v in (cs, ce, vs, ve)) or not cs < ce <= vs < ve:
        raise ValueError("Windows must be ordered, nonempty and nonoverlapping")
    cal, val = (t >= cs) & (t < ce), (t >= vs) & (t < ve)
    if not cal.any() or not val.any():
        raise ValueError("Each time block must select at least one sample")
    return cal, val
