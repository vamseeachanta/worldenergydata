"""Probabilistic oil volumetrics with PRMS-style exceedance estimates.

Equations: AAPG Wiki, Reserves estimation (2022), Volumetric estimation:
https://wiki.aapg.org/Reserves_estimation#Volumetric_estimation
Exceedance convention: docs/reference/petroleum-domain/reserves-classification.md,
Probabilistic ranges (2026), documenting SPE PRMS (2018).
Quantiles: Python 3.10 statistics.quantiles, inclusive method:
https://docs.python.org/3.10/library/statistics.html#statistics.quantiles

These estimates do not assess discovery, commerciality or project maturity and
cannot by themselves establish PRMS Reserves. Inputs are sampled independently.
"""

import math
import random
import statistics
from collections.abc import Iterable, Mapping

# AAPG Wiki (2022), Volumetric estimation: rounded acre-ft to barrel factor.
BARRELS_PER_ACRE_FT = 7758
# Computational defaults retained for compatibility; not accuracy criteria.
DEFAULT_ITERATIONS = 10000
DEFAULT_SEED = 42


def _finite(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _physical(name: str, value: float) -> None:
    """Bounds follow nonnegative volumes and the definition of a fraction."""
    _finite(name, value)
    if name in {"porosity", "water_saturation", "recovery_factor"}:
        if not 0 <= value <= 1:
            raise ValueError(f"{name} must be a fraction in [0, 1]")
    elif name == "fvf":
        if value <= 0:
            raise ValueError("fvf must be positive")
    elif value < 0:
        raise ValueError(f"{name} must be nonnegative")


def compute_ooip(
    area_acres: float,
    thickness_ft: float,
    porosity: float,
    water_saturation: float,
    fvf: float,
) -> float:
    """OOIP in STB = 7758 A h phi (1-Sw) / Boi (AAPG, 2022).

    Thickness is net pay in feet; area is acres; Boi is reservoir bbl/STB.
    Porosity and saturation are fractions. Zero rock/pore/oil volume is valid.
    """
    for name, value in (
        ("area", area_acres),
        ("thickness", thickness_ft),
        ("porosity", porosity),
        ("water_saturation", water_saturation),
        ("fvf", fvf),
    ):
        _physical(name, value)
    result = (
        BARRELS_PER_ACRE_FT
        * area_acres
        * thickness_ft
        * porosity
        * (1 - water_saturation)
        / fvf
    )
    _finite("ooip result", result)
    return result


def compute_eur(ooip: float, recovery_factor: float) -> float:
    """Ultimate recoverable oil in STB = OOIP * RF (AAPG, 2022).

    This is total ultimate recovery, not remaining recoverable volume.
    """
    _physical("ooip", ooip)
    _physical("recovery_factor", recovery_factor)
    result = ooip * recovery_factor
    _finite("eur result", result)
    return result


class MonteCarloEngine:
    """Independent draws using a local RNG; repeated samples reuse realizations.

    Normal distributions are unbounded. Resource estimation rejects unphysical
    draws rather than silently clipping or resampling them.
    """

    def __init__(self, n_iterations: int = DEFAULT_ITERATIONS, seed: int | None = None):
        if (
            isinstance(n_iterations, bool)
            or not isinstance(n_iterations, int)
            or n_iterations <= 0
        ):
            raise ValueError("n_iterations must be a positive integer")
        self.n_iterations = n_iterations
        self._rng = random.Random(seed)
        self._distributions: dict[str, tuple[str, dict]] = {}
        self._cache: dict[str, list[float]] = {}

    def _register(self, name: str, kind: str, params: dict) -> None:
        if not isinstance(name, str) or not name:
            raise ValueError("distribution name must be a nonempty string")
        for key, value in params.items():
            _finite(f"{name}.{key}", value)
        self._distributions[name] = kind, params
        self._cache.pop(name, None)

    def add_constant(self, name: str, value: float) -> None:
        """Register a deterministic value with no sampling uncertainty."""
        self._register(name, "constant", {"value": value})

    def add_triangular(self, name: str, low: float, mode: float, high: float) -> None:
        for key, value in (("low", low), ("mode", mode), ("high", high)):
            _finite(f"{name}.{key}", value)
        if not low <= mode <= high:
            raise ValueError(f"{name}: triangular requires low <= mode <= high")
        self._register(name, "triangular", {"low": low, "mode": mode, "high": high})

    def add_normal(self, name: str, mean: float, std: float) -> None:
        _finite(f"{name}.std", std)
        if std < 0:
            raise ValueError(f"{name}: normal std must be nonnegative")
        self._register(name, "normal", {"mu": mean, "sigma": std})

    def add_uniform(self, name: str, low: float, high: float) -> None:
        _finite(f"{name}.low", low)
        _finite(f"{name}.high", high)
        if low > high:
            raise ValueError(f"{name}: uniform requires low <= high")
        self._register(name, "uniform", {"a": low, "b": high})

    def sample(self, name: str) -> list[float]:
        """Return a copy so callers cannot corrupt cached realizations."""
        if name not in self._cache:
            if name not in self._distributions:
                raise ValueError(f"Unknown distribution name: {name}")
            kind, params = self._distributions[name]
            if kind == "constant":
                samples = [params["value"]] * self.n_iterations
            elif kind == "triangular":
                samples = [
                    self._rng.triangular(params["low"], params["high"], params["mode"])
                    for _ in range(self.n_iterations)
                ]
            elif kind == "normal":
                samples = [
                    self._rng.gauss(params["mu"], params["sigma"])
                    for _ in range(self.n_iterations)
                ]
            else:
                samples = [
                    self._rng.uniform(params["a"], params["b"])
                    for _ in range(self.n_iterations)
                ]
            self._cache[name] = samples
        return list(self._cache[name])


def summarize_resources(samples: Iterable[float]) -> dict[str, float]:
    """Return mean and P90/P50/P10 exceedance volumes from finite STB samples.

    Python 3.10 statistics.quantiles inclusive interpolation (R7) uses sorted
    index h=(n-1)q and interpolates adjacent values. The repository PRMS reference
    maps exceedance P90/P50/P10 to cumulative q=.1/.5/.9 respectively. A point
    distribution returns its sole value at every percentile.
    """
    values = list(samples)
    if not values:
        raise ValueError("resource samples must not be empty")
    for value in values:
        _physical("resource sample", value)
    if len(values) == 1:
        p90 = p50 = p10 = values[0]
    else:
        # Deciles and their indices follow the cited PRMS exceedance convention.
        deciles = statistics.quantiles(values, n=10, method="inclusive")
        p90, p50, p10 = deciles[0], deciles[4], deciles[8]
    result = {"p90": p90, "p50": p50, "p10": p10, "mean": statistics.mean(values)}
    for name, value in result.items():
        _finite(name, value)
    return result


def _register_spec(engine: MonteCarloEngine, name: str, spec: dict) -> None:
    """Reject malformed specifications and impossible bounded support early."""
    methods = {
        "constant": (engine.add_constant, {"value"}),
        "triangular": (engine.add_triangular, {"low", "mode", "high"}),
        "normal": (engine.add_normal, {"mean", "std"}),
        "uniform": (engine.add_uniform, {"low", "high"}),
    }
    if not isinstance(spec, Mapping):
        raise TypeError(f"{name}: expected a distribution specification mapping")
    kind = spec.get("dist")
    if kind not in tuple(methods):
        raise ValueError(f"{name}: unknown distribution {kind!r}")
    method, keys = methods[kind]
    if set(spec) != keys | {"dist"}:
        raise ValueError(f"{name}: {kind} requires exactly {sorted(keys)}")
    method(name, **{key: spec[key] for key in keys})
    if kind != "normal":
        for key in keys:
            _physical(name, spec[key])


def run_resource_estimation(
    area: dict,
    thickness: dict,
    porosity: dict,
    water_saturation: dict,
    fvf: dict,
    recovery_factor: dict,
    n_iterations: int = DEFAULT_ITERATIONS,
    seed: int | None = DEFAULT_SEED,
) -> dict:
    """Sample independent volumetric inputs and summarize ultimate recovery.

    Specifications use 'dist' plus: constant(value), uniform(low, high),
    triangular(low, mode, high), or normal(mean, std). All parameters and samples
    must be finite and physically valid. No risk weighting is applied.

    Original result keys remain available. Metadata records units, seed, count,
    interpolation and the unevaluated reserves classification; raw OOIP and EUR
    realizations permit further analysis without adding marginal percentiles.
    """
    engine = MonteCarloEngine(n_iterations=n_iterations, seed=seed)
    specs = {
        "area": area,
        "thickness": thickness,
        "porosity": porosity,
        "water_saturation": water_saturation,
        "fvf": fvf,
        "recovery_factor": recovery_factor,
    }
    for name, spec in specs.items():
        _register_spec(engine, name, spec)
    draws = {name: engine.sample(name) for name in specs}
    for name, values in draws.items():
        for value in values:
            _physical(name, value)

    ooip_dist = [
        compute_ooip(*args)
        for args in zip(
            draws["area"],
            draws["thickness"],
            draws["porosity"],
            draws["water_saturation"],
            draws["fvf"],
        )
    ]
    eur_dist = [
        compute_eur(ooip, rf) for ooip, rf in zip(ooip_dist, draws["recovery_factor"])
    ]
    return {
        **summarize_resources(eur_dist),
        "eur_distribution": eur_dist,
        "ooip_distribution": ooip_dist,
        "units": "STB",
        "n_iterations": n_iterations,
        "seed": seed,
        "quantile_method": "linear (R7)",
        "reserves_classification": "NOT_EVALUATED",
    }


def _eur_from_inputs(inputs: dict[str, float]) -> float:
    return compute_eur(
        compute_ooip(
            inputs["area"],
            inputs["thickness"],
            inputs["porosity"],
            inputs["water_saturation"],
            inputs["fvf"],
        ),
        inputs["recovery_factor"],
    )


def run_sensitivity_analysis(
    base_inputs: dict[str, float],
    ranges: dict[str, tuple[float, float]],
) -> list[dict]:
    """One-at-a-time endpoint EURs, sorted by descending absolute swing.

    low_eur/high_eur refer to low/high INPUT values; a parameter such as water
    saturation therefore has low_eur >= high_eur. This is a deterministic
    screening calculation, not a variance decomposition or correlation model.
    """
    expected = {
        "area",
        "thickness",
        "porosity",
        "water_saturation",
        "fvf",
        "recovery_factor",
    }
    if set(base_inputs) != expected:
        raise ValueError(f"base_inputs requires exactly {sorted(expected)}")
    base_eur = _eur_from_inputs(base_inputs)
    results = []
    for param, bounds in ranges.items():
        if param not in expected:
            raise ValueError(f"Unknown sensitivity parameter: {param}")
        if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
            raise ValueError(f"{param}: expected (low, high) range")
        low, high = bounds
        _physical(param, low)
        _physical(param, high)
        if low > high:
            raise ValueError(f"{param}: range requires low <= high")
        eur_low = _eur_from_inputs({**base_inputs, param: low})
        eur_high = _eur_from_inputs({**base_inputs, param: high})
        results.append(
            {
                "parameter": param,
                "low_eur": eur_low,
                "high_eur": eur_high,
                "swing": abs(eur_high - eur_low),
                "base_eur": base_eur,
            }
        )
    return sorted(results, key=lambda row: row["swing"], reverse=True)
