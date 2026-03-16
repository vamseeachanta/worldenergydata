"""P10/P50/P90 probabilistic resource estimation via Monte Carlo simulation.

Implements volumetric OOIP/EUR calculation per SPE PRMS (2018) with
configurable input distributions and sensitivity analysis.

Reference: SPE/WPC/AAPG/SPEE/SEG PRMS (2018)
"""

import random
import statistics

# Barrel conversion constant: 1 acre-ft = 7758 barrels
BARRELS_PER_ACRE_FT = 7758


def compute_ooip(
    area_acres: float,
    thickness_ft: float,
    porosity: float,
    water_saturation: float,
    fvf: float,
) -> float:
    """Original Oil In Place (STB).

    OOIP = 7758 * A * h * phi * (1 - Sw) / Boi
    """
    return (
        BARRELS_PER_ACRE_FT
        * area_acres
        * thickness_ft
        * porosity
        * (1 - water_saturation)
        / fvf
    )


def compute_eur(ooip: float, recovery_factor: float) -> float:
    """Estimated Ultimate Recovery (STB)."""
    return ooip * recovery_factor


class MonteCarloEngine:
    """Monte Carlo sampling engine with configurable distributions."""

    def __init__(self, n_iterations: int = 10000, seed: int | None = None):
        self.n_iterations = n_iterations
        self._rng = random.Random(seed)
        self._distributions: dict[str, tuple[str, dict]] = {}
        self._cache: dict[str, list[float]] = {}

    def add_triangular(self, name: str, low: float, mode: float, high: float) -> None:
        self._distributions[name] = (
            "triangular",
            {"low": low, "mode": mode, "high": high},
        )

    def add_normal(self, name: str, mean: float, std: float) -> None:
        self._distributions[name] = ("normal", {"mu": mean, "sigma": std})

    def add_uniform(self, name: str, low: float, high: float) -> None:
        self._distributions[name] = ("uniform", {"a": low, "b": high})

    def sample(self, name: str) -> list[float]:
        if name in self._cache:
            return self._cache[name]
        dist_type, params = self._distributions[name]
        if dist_type == "triangular":
            samples = [
                self._rng.triangular(params["low"], params["high"], params["mode"])
                for _ in range(self.n_iterations)
            ]
        elif dist_type == "normal":
            samples = [
                self._rng.gauss(params["mu"], params["sigma"])
                for _ in range(self.n_iterations)
            ]
        elif dist_type == "uniform":
            samples = [
                self._rng.uniform(params["a"], params["b"])
                for _ in range(self.n_iterations)
            ]
        else:
            raise ValueError(f"Unknown distribution: {dist_type}")
        self._cache[name] = samples
        return samples


def _parse_dist(spec: dict) -> tuple[str, dict]:
    """Parse a distribution spec dict into (type, params)."""
    dist = spec["dist"]
    params = {k: v for k, v in spec.items() if k != "dist"}
    return dist, params


def run_resource_estimation(
    area: dict,
    thickness: dict,
    porosity: dict,
    water_saturation: dict,
    fvf: dict,
    recovery_factor: dict,
    n_iterations: int = 10000,
    seed: int = 42,
) -> dict:
    """Run Monte Carlo resource estimation.

    Each parameter is a dict with 'dist' key and distribution params.
    Returns P10/P50/P90/mean and the full EUR distribution.
    """
    engine = MonteCarloEngine(n_iterations=n_iterations, seed=seed)

    # Register distributions
    for name, spec in [
        ("area", area),
        ("thickness", thickness),
        ("porosity", porosity),
        ("water_saturation", water_saturation),
        ("fvf", fvf),
        ("recovery_factor", recovery_factor),
    ]:
        dist_type, params = _parse_dist(spec)
        if dist_type == "triangular":
            engine.add_triangular(name, **params)
        elif dist_type == "normal":
            engine.add_normal(name, **params)
        elif dist_type == "uniform":
            engine.add_uniform(name, **params)

    # Sample all parameters
    areas = engine.sample("area")
    thicknesses = engine.sample("thickness")
    porosities = engine.sample("porosity")
    saturations = engine.sample("water_saturation")
    fvfs = engine.sample("fvf")
    rfs = engine.sample("recovery_factor")

    # Compute EUR for each iteration
    eur_dist = []
    for i in range(n_iterations):
        ooip = compute_ooip(
            areas[i], thicknesses[i], porosities[i], saturations[i], fvfs[i]
        )
        eur = compute_eur(ooip, rfs[i])
        eur_dist.append(eur)

    eur_sorted = sorted(eur_dist)

    # SPE PRMS convention: P10 = 90th percentile (high), P90 = 10th percentile (low)
    p90_idx = int(0.10 * n_iterations)
    p50_idx = int(0.50 * n_iterations)
    p10_idx = int(0.90 * n_iterations)

    return {
        "p10": eur_sorted[p10_idx],
        "p50": eur_sorted[p50_idx],
        "p90": eur_sorted[p90_idx],
        "mean": statistics.mean(eur_dist),
        "eur_distribution": eur_dist,
    }


def run_sensitivity_analysis(
    base_inputs: dict[str, float],
    ranges: dict[str, tuple[float, float]],
) -> list[dict]:
    """One-at-a-time sensitivity analysis for tornado chart.

    Varies each parameter between its low and high while holding others at base.
    """
    base_ooip = compute_ooip(
        base_inputs["area"],
        base_inputs["thickness"],
        base_inputs["porosity"],
        base_inputs["water_saturation"],
        base_inputs["fvf"],
    )
    base_eur = compute_eur(base_ooip, base_inputs["recovery_factor"])

    results = []
    for param, (low, high) in ranges.items():
        inputs_low = dict(base_inputs)
        inputs_low[param] = low
        inputs_high = dict(base_inputs)
        inputs_high[param] = high

        ooip_low = compute_ooip(
            inputs_low["area"],
            inputs_low["thickness"],
            inputs_low["porosity"],
            inputs_low["water_saturation"],
            inputs_low["fvf"],
        )
        eur_low = compute_eur(ooip_low, inputs_low["recovery_factor"])

        ooip_high = compute_ooip(
            inputs_high["area"],
            inputs_high["thickness"],
            inputs_high["porosity"],
            inputs_high["water_saturation"],
            inputs_high["fvf"],
        )
        eur_high = compute_eur(ooip_high, inputs_high["recovery_factor"])

        results.append(
            {
                "parameter": param,
                "low_eur": eur_low,
                "high_eur": eur_high,
                "swing": abs(eur_high - eur_low),
                "base_eur": base_eur,
            }
        )

    return results
