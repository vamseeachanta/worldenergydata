"""Additive reanalysis corrections; see the package README for equations and limits.

Reference: Oikonomou et al. (2026), Applied Ocean Research 176, 105259,
https://doi.org/10.1016/j.apor.2026.105259 (data/code: Zenodo 19239166).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

_METHODS = {"delta_change", "eqm", "qdm", "conditional_qdm"}


def _vectors(*values):
    """Require positional pairs, refusing implicit pandas index alignment."""
    indexes = [v.index for v in values if isinstance(v, pd.Series)]
    if indexes and any(not indexes[0].equals(i) for i in indexes[1:]):
        raise ValueError("Paired Series must have the same index")
    arrays = [np.asarray(v, dtype=float) for v in values]
    if any(a.ndim != 1 for a in arrays):
        raise ValueError("Inputs must be one-dimensional")
    if len({a.size for a in arrays}) != 1:
        raise ValueError("Paired inputs must have equal lengths")
    return arrays


def _knots(x, y):
    """Collapse repeated abscissae using mean ordinates, without jitter."""
    unique, inverse, counts = np.unique(x, return_inverse=True, return_counts=True)
    return unique, np.bincount(inverse, weights=y) / counts


@dataclass(frozen=True)
class Correction:
    """Fitted correction with JSON-serializable provenance.

    ``apply`` returns an array in input order; nonfinite inputs become NaN.
    For conditional QDM, ``hs`` is concurrent model Hs (m), before correction.
    QDM defaults to the empirical CDF of the complete application block.
    Apply each intended validation/projection block together, not in chunks.
    ``qdm_reference="calibration"`` reproduces the stationary formulation in
    the accompanying paper code and is independent of application batch size.
    """

    method: str
    _model_quantiles: tuple
    _observed_quantiles: tuple
    _delta: float
    _children: tuple
    _edges: tuple
    _metadata: dict

    @property
    def provenance(self):
        """Return a detached copy so caller edits cannot alter fitted metadata."""
        from copy import deepcopy

        return deepcopy(self._metadata)

    def apply(self, model, *, hs=None):
        if self.method == "conditional_qdm":
            if hs is None:
                raise ValueError("Conditional QDM requires concurrent hs")
            x, h = _vectors(model, hs)
            valid = np.isfinite(x) & np.isfinite(h)
            groups = np.searchsorted(self._edges, h, side="right")
            out = np.full(x.shape, np.nan)
            for i, child in enumerate(self._children):
                mask = valid & (groups == i)
                out[mask] = child.apply(x[mask])
            return out
        (x,) = _vectors(model)
        valid = np.isfinite(x)
        out = np.full(x.shape, np.nan)
        if self.method == "delta_change":
            out[valid] = x[valid] + self._delta
            return out
        qm, qo = np.array(self._model_quantiles), np.array(self._observed_quantiles)
        if self.method == "qdm":
            reference = qm
            if self._metadata["qdm_reference"] == "application_cdf":
                if not valid.any():
                    return out
                reference = np.quantile(x[valid], self._metadata["quantile_levels"])
            knots, delta = _knots(reference, qo - qm)
            out[valid] = x[valid] + np.interp(x[valid], knots, delta)
        else:
            knots, mapped = _knots(qm, qo)
            y = np.interp(x[valid], knots, mapped)
            # Extend the boundary *offset*, never the fitted slope or a clipped value.
            low, high = x[valid] < knots[0], x[valid] > knots[-1]
            y[low] = x[valid][low] + mapped[0] - knots[0]
            y[high] = x[valid][high] + mapped[-1] - knots[-1]
            out[valid] = y
        return out


def fit(
    model_cal,
    obs_cal,
    method,
    n_quantiles=200,
    q_range=(0.01, 0.999),
    *,
    model_hs=None,
    obs_hs=None,
    bin_edges=None,
    times=None,
    qdm_reference="application",
):
    """Fit finite paired calibration samples only, never validation observations.

    Conditional QDM learns paired period maps within bins of ``model_hs``.
    Default internal edges are observed calibration Hs P25/P50/P75/P95;
    explicit edges override them. Bins are left-closed and extend to infinity.
    Every bin needs at least two finite pairs; sparse bins raise rather than
    silently substitute a different method. ``times`` (or a DatetimeIndex on
    the model Series) records the effective calibration window in provenance.
    """
    if qdm_reference not in {"application", "calibration"}:
        raise ValueError("qdm_reference must be application or calibration")
    if method not in _METHODS:
        raise ValueError(f"Unknown method: {method}")
    if (
        isinstance(n_quantiles, bool)
        or not isinstance(n_quantiles, int)
        or n_quantiles < 2
    ):
        raise ValueError("n_quantiles must be an integer >= 2")
    if len(q_range) != 2 or not 0 <= q_range[0] < q_range[1] <= 1:
        raise ValueError("q_range must satisfy 0 <= lower < upper <= 1")
    values = [model_cal, obs_cal]
    if method == "conditional_qdm":
        if model_hs is None or obs_hs is None:
            raise ValueError("Conditional QDM requires model_hs and obs_hs")
        values += [model_hs, obs_hs]
    arrays = _vectors(*values)
    valid = np.logical_and.reduce([np.isfinite(a) for a in arrays])
    if valid.sum() < 2:
        raise ValueError("At least two finite paired samples are required")
    m, o = [a[valid] for a in arrays[:2]]
    if times is None and isinstance(model_cal, pd.Series):
        if isinstance(model_cal.index, pd.DatetimeIndex):
            times = model_cal.index
    window = None
    if times is not None:
        t = pd.DatetimeIndex(times)
        if len(t) != len(valid) or t.hasnans:
            raise ValueError("times must match calibration samples and contain no NaT")
        window = [t[valid].min().isoformat(), t[valid].max().isoformat()]
    q = np.linspace(*q_range, n_quantiles)
    qm, qo = np.quantile(m, q), np.quantile(o, q)
    children, edges = (), ()
    metadata = {
        "method": method,
        "calibration_window": window,
        "n_pairs": int(valid.sum()),
        "n_dropped": int((~valid).sum()),
        "quantile_levels": q.tolist(),
        "bin_edges": [],
        "tied_quantiles": bool(np.any(np.diff(qm) == 0)),
        "tail_policy": "constant_boundary_offset",
        "qdm_reference": (
            f"{qdm_reference}_cdf" if method in {"qdm", "conditional_qdm"} else None
        ),
        "extreme_value_fitting_allowed": False,
        "references": [
            "https://doi.org/10.1016/j.apor.2026.105259",
            "https://doi.org/10.1175/JCLI-D-14-00754.1",
        ],
    }
    if method == "conditional_qdm":
        h, oh = [a[valid] for a in arrays[2:]]
        e = np.asarray(
            (
                bin_edges
                if bin_edges is not None
                else np.quantile(oh, [0.25, 0.5, 0.75, 0.95])
            ),
            dtype=float,
        )
        if (
            e.ndim != 1
            or not e.size
            or not np.isfinite(e).all()
            or np.any(np.diff(e) <= 0)
        ):
            raise ValueError(
                "bin_edges must be finite, strictly increasing internal edges"
            )
        groups = np.searchsorted(e, h, side="right")
        maps = []
        for i in range(len(e) + 1):
            mask = groups == i
            if mask.sum() < 2:
                raise ValueError(f"Conditional bin {i} has fewer than two finite pairs")
            maps.append(
                fit(
                    m[mask],
                    o[mask],
                    "qdm",
                    n_quantiles,
                    q_range,
                    times=None if times is None else t[valid][mask],
                    qdm_reference=qdm_reference,
                )
            )
        children, edges = tuple(maps), tuple(e)
        metadata["bin_edges"] = e.tolist()
        metadata["bin_pair_counts"] = [c.provenance["n_pairs"] for c in children]
        metadata["conditioning_variable"] = "concurrent_model_hs"
        metadata["tied_quantiles"] = any(
            c.provenance["tied_quantiles"] for c in children
        )
    return Correction(
        method,
        tuple(qm),
        tuple(qo),
        float(o.mean() - m.mean()),
        children,
        edges,
        metadata,
    )
