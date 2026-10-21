"""Optional digitalmodel UQ adapter and explicit naive-MC compatibility backend.

The compatibility backend will be removable once digitalmodel is a declared
dependency; see https://github.com/vamseeachanta/digitalmodel/issues/1427 and
https://github.com/vamseeachanta/worldenergydata/issues/833. No local LHS or
regression tornado is implemented. Distribution parameters are caller inputs.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(init=False)
class PriorSpec:
    """Validated subset of the shared engine's flat prior configuration.

    Parameter mappings follow digitalmodel.uncertainty.Prior.frozen and SciPy
    stats distribution documentation (1.15.2): uniform, norm, lognorm, triang.
    The constants in the mappings are distribution identities, not priors.
    """

    config: dict

    def __init__(self, *, name, dist, **params):
        required = {
            "uniform": {"low", "high"},
            "normal": {"mean", "std"},
            "lognormal": {"median", "std_log"},
            "triangular": {"low", "mode", "high"},
        }
        if not isinstance(name, str) or not name.strip() or dist not in required:
            raise ValueError("prior needs a name and a supported distribution")
        expected = required[dist]
        if dist == "lognormal" and "mean_log" in params:
            expected = {"mean_log", "std_log"}
        if set(params) != expected:
            raise ValueError(f"{dist} prior requires exactly {sorted(expected)}")
        if not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and np.isfinite(v)
            for v in params.values()
        ):
            raise ValueError("prior parameters must be finite numbers")
        if "low" in params and params["low"] >= params["high"]:
            raise ValueError("prior requires low < high")
        if dist == "normal" and params["std"] <= 0:
            raise ValueError("normal requires std > 0")
        if dist == "lognormal" and (
            params["std_log"] <= 0 or params.get("median", 1) <= 0
        ):
            raise ValueError("lognormal requires positive median and std_log")
        if (
            dist == "triangular"
            and not params["low"] <= params["mode"] <= params["high"]
        ):
            raise ValueError("triangular mode must lie within bounds")
        self.config = {"name": name, "dist": dist, **params}

    def frozen(self):
        p = self.config
        dist = p["dist"]
        if dist == "uniform":
            return stats.uniform(loc=p["low"], scale=p["high"] - p["low"])
        if dist == "normal":
            return stats.norm(loc=p["mean"], scale=p["std"])
        if dist == "lognormal":
            scale = p["median"] if "median" in p else np.exp(p["mean_log"])
            if not np.isfinite(scale):
                raise ValueError("lognormal scale overflow")
            return stats.lognorm(s=p["std_log"], scale=scale)
        return stats.triang(
            c=(p["mode"] - p["low"]) / (p["high"] - p["low"]),
            loc=p["low"],
            scale=p["high"] - p["low"],
        )


def shared_engine(engine):
    """Select backend; a broken installed engine never silently falls back."""
    if engine not in {"auto", "builtin", "digitalmodel"}:
        raise ValueError("engine must be auto, builtin or digitalmodel")
    if engine == "builtin":
        return None
    try:
        return importlib.import_module("digitalmodel.uncertainty")
    except ModuleNotFoundError as exc:
        if engine == "auto" and exc.name in {
            "digitalmodel",
            "digitalmodel.uncertainty",
        }:
            return None
        raise


def sample_priors(priors, n_samples, seed, engine="auto"):
    """Return independent samples and the selected backend's identity."""
    if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples < 2:
        raise ValueError("n_samples must be an integer of at least two for ranks")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    names = [p.config["name"] for p in priors]
    if not priors or len(names) != len(set(names)):
        raise ValueError("at least one uniquely named prior is required")
    backend = shared_engine(engine)
    if backend is not None:
        native = [backend.Prior.from_dict(p.config) for p in priors]
        return backend.sample_lhs(native, n_samples, seed), "digitalmodel.lhs"
    rng = np.random.default_rng(seed)
    return (
        pd.DataFrame(
            {
                p.config["name"]: p.frozen().rvs(size=n_samples, random_state=rng)
                for p in priors
            }
        ),
        "builtin.naive-mc",
    )


def percentiles(values, backend=None):
    """Non-exceedance percentiles; NumPy 2.2 linear method (Hyndman-Fan 7).

    The requested 10/50/90 levels follow the issue's percentile convention;
    petroleum exceedance P10 would instead be this function's p90.
    """
    if backend is not None:
        return backend.percentile_summary(pd.DataFrame({"value": values}), "value")
    return dict(
        zip(
            ("p10", "p50", "p90"),
            map(float, np.percentile(values, [10, 50, 90], method="linear")),
        )
    )


def rank_sensitivity(matrix, names, backend=None):
    """Spearman rho; constant inputs/outputs are undefined, represented as None.

    Source: SciPy 1.15.2 scipy.stats.spearmanr, Notes and ConstantInputWarning.
    """
    ranks = {}
    for name in names:
        if matrix[name].nunique() < 2 or matrix.npv_usd.nunique() < 2:
            ranks[name] = None
        elif backend is not None:
            ranks[name] = float(
                backend.spearman_ranks(matrix, [name], "npv_usd").iloc[0].coefficient
            )
        else:
            ranks[name] = float(stats.spearmanr(matrix[name], matrix.npv_usd).statistic)
    return ranks
