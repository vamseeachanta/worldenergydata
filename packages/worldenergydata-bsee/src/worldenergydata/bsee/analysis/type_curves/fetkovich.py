"""Fetkovich type curve generation and matching.

References:
    Fetkovich, M.J. (1980). "Decline Rate Analysis Using Type Curves,"
    JPT, SPE 4629-PA.
"""

import numpy as np
from numpy.typing import NDArray

from .models import MatchResult, ProductionData, ReservoirParams, TypeCurveSet


def _edwardson_wed(tD: NDArray[np.float64]) -> NDArray[np.float64]:
    """Cumulative dimensionless influx WeD(tD) via Edwardson polynomial.

    Approximation for constant-pressure radial flow (infinite-acting).
    Edwardson et al. (1962), also used by Fetkovich (1980).
    """
    weD = np.zeros_like(tD, dtype=np.float64)

    small = tD < 0.01
    mid = (tD >= 0.01) & (tD <= 200.0)
    large = tD > 200.0

    weD[small] = np.sqrt(tD[small] / np.pi)

    t_mid = tD[mid]
    sqrt_t = np.sqrt(t_mid)
    num = 1.2838 * sqrt_t + 1.19328 * t_mid + 0.269872 * t_mid**1.5 + 0.00855294 * t_mid**2
    den = 1.0 + 0.616599 * sqrt_t + 0.0413008 * t_mid
    weD[mid] = num / den

    t_large = tD[large]
    weD[large] = -4.29881 + 2.02566 * t_large / np.log(t_large)

    return weD


def _constant_pressure_qD(tD: NDArray[np.float64]) -> NDArray[np.float64]:
    """Dimensionless rate qD = dWeD/dtD via finite differences."""
    weD = _edwardson_wed(tD)
    qD = np.gradient(weD, tD)
    return np.maximum(qD, 1e-30)


def fetkovich_transient(
    tD: NDArray[np.float64], reD: float
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Generate Fetkovich transient stem for a given reD.

    Rescales well-test (qD, tD) to decline (qDd, tDd).

    Returns:
        (tDd, qDd) arrays for the transient portion.
    """
    if reD <= 1.0:
        raise ValueError(f"reD must be > 1, got {reD}")

    ln_reD = np.log(reD)
    qD = _constant_pressure_qD(tD)
    qDd = qD * (ln_reD - 0.5)
    scale_t = 0.5 * (reD**2 - 1.0) * (ln_reD - 0.5)
    tDd = tD / scale_t
    return tDd, qDd


def fetkovich_boundary(
    tDd: NDArray[np.float64], b: float
) -> NDArray[np.float64]:
    """Arps decline for boundary-dominated flow.

    Args:
        tDd: dimensionless decline time array.
        b: Arps b-factor (0=exponential, 0<b<1=hyperbolic, 1=harmonic).

    Returns:
        qDd array.
    """
    if b < 0 or b > 1:
        raise ValueError(f"b must be in [0, 1], got {b}")

    if b == 0:
        return np.exp(-tDd)

    if b == 1:
        return 1.0 / (1.0 + tDd)

    return (1.0 + b * tDd) ** (-1.0 / b)


def fetkovich_typecurve(
    reD_values: list[float] | None = None,
    b_values: list[float] | None = None,
    n_points: int = 200,
) -> TypeCurveSet:
    """Generate complete Fetkovich type curve set.

    Args:
        reD_values: list of reD for transient stems.
        b_values: list of b for boundary-dominated stems.
        n_points: points per curve.

    Returns:
        TypeCurveSet with transient + boundary curves.
    """
    if reD_values is None:
        reD_values = [2, 5, 10, 20, 50, 100, 200, 1000]
    if b_values is None:
        b_values = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

    tD = np.logspace(-2, 4, n_points)
    tDd_bd = np.logspace(-2, 2, n_points)
    result = TypeCurveSet()

    for reD in reD_values:
        tDd, qDd = fetkovich_transient(tD, reD)
        mask = tDd > 0
        result.tDd.append(tDd[mask])
        result.qDd.append(qDd[mask])
        result.labels.append(f"reD={reD}")

    for b in b_values:
        qDd = fetkovich_boundary(tDd_bd, b)
        result.tDd.append(tDd_bd)
        result.qDd.append(qDd)
        result.labels.append(f"b={b}")

    return result


def match_fetkovich(
    data: ProductionData,
    params: ReservoirParams,
    b_range: tuple[float, float] = (0.0, 1.0),
    reD_guesses: list[float] | None = None,
) -> MatchResult:
    """Automatic Fetkovich type curve matching.

    Uses multi-start optimization over (log_Ct, log_Cq, b).
    Boundary-only decline matching does not identify drainage radius, so reD is
    derived from the supplied reservoir geometry instead of optimizer guesses.
    """
    from scipy.optimize import minimize

    del reD_guesses

    b_min, b_max = b_range
    if b_min < 0 or b_max > 1 or b_min > b_max:
        raise ValueError(f"b_range must be within [0, 1], got {b_range}")

    dp = data.pressure_drawdown
    if dp is None:
        dp = np.full_like(data.rate, params.pi - params.pwf)
    q_norm = data.rate / dp

    reD = max(params.re / params.rw, 1.01)
    positive = q_norm > 0
    if positive.sum() < 3:
        raise ValueError("Insufficient valid data points for matching")
    qn_v = q_norm[positive]
    t_v = data.time[positive]
    decline_span = max(t_v[-1] - t_v[0], 1.0)
    rate_ratio = max(qn_v[-1] / qn_v[0], 1e-12)
    initial_Ct = max(-np.log(rate_ratio) / decline_span, 1e-8)
    initial_Cq = max(1.0 / qn_v[0], 1e-12)

    def objective(x):
        log_Ct, log_Cq, b = x
        if b < b_min or b > b_max:
            return 1e12
        Ct = 10**log_Ct
        Cq = 10**log_Cq
        tDd_data = Ct * data.time
        qDd_data = Cq * q_norm
        qDd_model = fetkovich_boundary(tDd_data, b)
        mask = (qDd_data > 0) & (qDd_model > 0)
        if mask.sum() < 3:
            return 1e12
        return np.sum(
            (np.log(qDd_data[mask]) - np.log(qDd_model[mask])) ** 2
        )

    best = None
    if b_min == b_max:
        b_inits = [b_min]
    else:
        b_inits = np.linspace(b_min, b_max, 4)
    for b_init in b_inits:
        x0 = [np.log10(initial_Ct), np.log10(initial_Cq), float(b_init)]
        try:
            res = minimize(
                objective,
                x0,
                method="L-BFGS-B",
                bounds=[(-8.0, 2.0), (-12.0, 6.0), (b_min, b_max)],
                options={"maxiter": 1000, "ftol": 1e-10},
            )
            if best is None or res.fun < best.fun:
                best = res
        except Exception:
            continue

    if best is None:
        raise RuntimeError("Optimization failed to converge")

    log_Ct, log_Cq, b = best.x
    b = float(np.clip(b, b_min, b_max))
    Ct = 10**log_Ct
    Cq = 10**log_Cq

    ln_reD = np.log(max(reD, 1.01))
    bDpss = ln_reD - 0.5
    k = Cq * 141.2 * params.Bo * params.mu * bDpss / params.h
    rwa = np.sqrt(
        0.0002637 * k / (params.phi * params.mu * params.ct * Ct)
    )
    skin = np.log(params.rw / rwa) if rwa > 0 else 0.0
    re = reD * rwa
    area_ft2 = np.pi * re**2
    ooip = area_ft2 * params.h * params.phi * (1 - params.Sw) / (5.615 * params.Bo)

    qi = q_norm[0] / Cq if Cq > 0 else 0.0
    Di = Ct

    return MatchResult(
        k=k, skin=skin, re=re, rwa=rwa, ooip=ooip,
        qi=qi, Di=Di, b=b, reD=reD, residual=best.fun,
        Ct=Ct, Cq=Cq, model="fetkovich",
    )
