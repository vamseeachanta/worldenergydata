"""Blasingame type curve generation and matching.

References:
    Blasingame, T.A. & Lee, W.J. (1986). SPE 15028.
    Palacio, J.C. & Blasingame, T.A. (1993). SPE 25909.
"""

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from .models import MatchResult, ProductionData, ReservoirParams, TypeCurveSet


def material_balance_time(
    rate: NDArray[np.float64],
    cumulative: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Compute material balance time tc = Np / q.

    Returns tc array (same units as time in cumulative/rate).
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        tc = np.where(rate > 0, cumulative / rate, 0.0)
    return tc


def normalized_rate(
    rate: NDArray[np.float64],
    pressure_drawdown: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Compute q / (pi - pwf)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(pressure_drawdown > 0, rate / pressure_drawdown, 0.0)


def rate_integral(
    q_norm: NDArray[np.float64],
    tc: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Rate integral: (1/tc) * integral(q_norm * dtc) via trapezoidal rule."""
    n = len(tc)
    if n == 0:
        return np.array([])

    cum = np.zeros(n)
    cum[0] = q_norm[0] * tc[0] if tc[0] > 0 else 0.0
    for i in range(1, n):
        cum[i] = cum[i - 1] + 0.5 * (q_norm[i] + q_norm[i - 1]) * (tc[i] - tc[i - 1])

    with np.errstate(divide="ignore", invalid="ignore"):
        qDdi = np.where(tc > 0, cum / tc, q_norm)
    return qDdi


def rate_integral_derivative(
    qDdi: NDArray[np.float64],
    tc: NDArray[np.float64],
    window: float = 0.2,
) -> NDArray[np.float64]:
    """Bourdet semi-log derivative of rate integral.

    qDdid = -d(qDdi) / d(ln(tc))

    Args:
        window: smoothing window in log-cycles (not currently used for
                simple 3-point derivative; kept for API compatibility).
    """
    n = len(tc)
    if n < 3:
        return np.zeros(n)

    ln_tc = np.log(np.maximum(tc, 1e-30))
    deriv = np.zeros(n)

    for i in range(1, n - 1):
        dxL = ln_tc[i] - ln_tc[i - 1]
        dxR = ln_tc[i + 1] - ln_tc[i]
        dyL = qDdi[i] - qDdi[i - 1]
        dyR = qDdi[i + 1] - qDdi[i]
        if dxL > 0 and dxR > 0:
            deriv[i] = -((dyL / dxL) * dxR + (dyR / dxR) * dxL) / (dxL + dxR)

    deriv[0] = deriv[1]
    deriv[-1] = deriv[-2]
    return np.maximum(deriv, 1e-30)


def _bDpss_radial(reD: float) -> float:
    """Pseudo-steady-state constant for radial model."""
    if reD <= 1.0:
        raise ValueError(f"reD must be > 1, got {reD}")
    return max(np.log(reD) - 0.5, 1e-6)


def _analytical_qDd(
    tDd: NDArray[np.float64], reD: float
) -> NDArray[np.float64]:
    """Analytical boundary-dominated qDd for Blasingame radial model."""
    bDpss = _bDpss_radial(reD)
    return 1.0 / (1.0 + tDd / bDpss)


def _analytical_qDdi(
    tDd: NDArray[np.float64], reD: float
) -> NDArray[np.float64]:
    """Analytical rate integral for harmonic decline."""
    bDpss = _bDpss_radial(reD)
    scaled_tDd = tDd / bDpss
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(scaled_tDd > 0, np.log1p(scaled_tDd) / scaled_tDd, 1.0)


def _analytical_qDdid(
    tDd: NDArray[np.float64], reD: float
) -> NDArray[np.float64]:
    """Analytical rate integral derivative for harmonic decline."""
    qDdi = _analytical_qDdi(tDd, reD)
    qDd = _analytical_qDd(tDd, reD)
    return np.maximum(qDdi - qDd, 1e-30)


def blasingame_typecurve(
    reD_values: list[float] | None = None,
    n_points: int = 300,
) -> TypeCurveSet:
    """Generate Blasingame type curves (qDd, qDdi, qDdid) for radial model.

    Args:
        reD_values: dimensionless drainage radii.
        n_points: points per curve.

    Returns:
        TypeCurveSet with qDd, qDdi, qDdid for each reD.
    """
    if reD_values is None:
        reD_values = [2, 5, 10, 20, 50, 100, 200, 1000]

    tDd = np.logspace(-3, 3, n_points)
    result = TypeCurveSet()

    for reD in reD_values:
        qDd = _analytical_qDd(tDd, reD)
        qDdi = _analytical_qDdi(tDd, reD)
        qDdid = _analytical_qDdid(tDd, reD)
        result.tDd.append(tDd)
        result.qDd.append(qDd)
        result.qDdi.append(qDdi)
        result.qDdid.append(qDdid)
        result.labels.append(f"reD={reD}")

    return result


def match_blasingame(
    data: ProductionData,
    params: ReservoirParams,
    reD_guesses: list[float] | None = None,
    weights: tuple[float, float, float] = (0.2, 0.5, 0.3),
) -> MatchResult:
    """Automatic Blasingame type curve matching.

    Multi-start optimization over (log_Ct, log_Cq, reD).
    Matches qDd, qDdi, qDdid simultaneously with given weights.
    """
    if reD_guesses is None:
        reD_guesses = [5.0, 20.0, 50.0, 100.0, 500.0]

    dp = data.pressure_drawdown
    if dp is None:
        dp = np.full_like(data.rate, params.pi - params.pwf)

    q_norm = normalized_rate(data.rate, dp)
    tc = material_balance_time(data.rate, data.cumulative)
    qDdi_data = rate_integral(q_norm, tc)
    qDdid_data = rate_integral_derivative(qDdi_data, tc)

    valid = (tc > 0) & (q_norm > 0) & (qDdi_data > 0) & (qDdid_data > 0)
    tc_v = tc[valid]
    qn_v = q_norm[valid]
    qDdi_v = qDdi_data[valid]
    qDdid_v = qDdid_data[valid]

    if len(tc_v) < 3:
        raise ValueError("Insufficient valid data points for matching")

    w1, w2, w3 = weights

    def objective(x):
        log_Ct, log_Cq, reD = x
        if reD <= 1.0:
            return 1e12
        Ct = 10**log_Ct
        Cq = 10**log_Cq
        tDd = Ct * tc_v

        qDd_m = _analytical_qDd(tDd, reD)
        qDdi_m = _analytical_qDdi(tDd, reD)
        qDdid_m = _analytical_qDdid(tDd, reD)

        qDd_d = Cq * qn_v
        qDdi_d = Cq * qDdi_v
        qDdid_d = Cq * qDdid_v

        mask = (qDd_d > 0) & (qDd_m > 0) & (qDdi_m > 0) & (qDdid_m > 0)
        if mask.sum() < 3:
            return 1e12

        res = (
            w1 * np.sum((np.log(qDd_d[mask]) - np.log(qDd_m[mask])) ** 2)
            + w2 * np.sum((np.log(qDdi_d[mask]) - np.log(qDdi_m[mask])) ** 2)
            + w3 * np.sum((np.log(qDdid_d[mask]) - np.log(qDdid_m[mask])) ** 2)
        )
        return res

    best = None
    for reD_init in reD_guesses:
        x0 = [0.0, -3.0, reD_init]
        try:
            res = minimize(
                objective, x0, method="Nelder-Mead",
                options={"maxiter": 10000, "xatol": 1e-8, "fatol": 1e-10},
            )
            if best is None or res.fun < best.fun:
                best = res
        except Exception:
            continue

    if best is None:
        raise RuntimeError("Optimization failed to converge")

    log_Ct, log_Cq, reD = best.x
    Ct = 10**log_Ct
    Cq = 10**log_Cq

    bDpss = _bDpss_radial(max(reD, 1.01))
    k = Cq * 141.2 * params.Bo * params.mu * bDpss / params.h
    rwa = np.sqrt(
        0.0002637 * k / (params.phi * params.mu * params.ct * Ct)
    )
    skin = np.log(params.rw / rwa) if rwa > 0 else 0.0
    re = reD * rwa
    ooip = np.pi * re**2 * params.h * params.phi * (1 - params.Sw) / (5.615 * params.Bo)

    qi = q_norm[0] / Cq if Cq > 0 else 0.0
    Di = Ct

    return MatchResult(
        k=k, skin=skin, re=re, rwa=rwa, ooip=ooip,
        qi=qi, Di=Di, b=1.0, reD=reD, residual=best.fun,
        Ct=Ct, Cq=Cq, model="blasingame",
    )
