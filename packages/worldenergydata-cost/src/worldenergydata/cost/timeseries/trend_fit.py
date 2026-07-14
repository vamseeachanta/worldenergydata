"""
ABOUTME: Fits trend curves per cost component so gap years can be interpolated/extrapolated.
ABOUTME: Implements issue #844 scope addition #3 — functional form, fit quality, oil-price cycle driver.

What this is for
----------------
The observed cost series are sparse and uneven: some years have five sourced rig
fixtures, some have none. A deck that can only tabulate observed years is not
usable for field economics, which needs a cost for *every* year of a multi-decade
lifecycle. So we fit.

What this is NOT for
--------------------
A fitted value is not a datum. Everything produced here is stamped
``Provenance.FITTED`` and is visually distinct in the report. Fitting is how we
fill gaps *honestly* — by publishing the curve, its form, and its fit quality so
a reader can judge how much to trust year 2011 when we sourced 2009 and 2013.

Functional forms
----------------
Four candidates, fitted per component, best chosen by **adjusted R²** (which
penalises the extra parameter of the richer models, so a 2-parameter form has to
actually earn its keep):

* ``linear``       — value = a + b·t.  The null hypothesis.
* ``exponential``  — value = a·e^(b·t), fitted log-linear. Constant % growth;
  the natural form for something inflating.
* ``oil_linked``   — value = a + b·(oil price).  Offshore day rates are famously
  a *cyclical* function of the oil price, not a function of time. When this form
  wins, that is itself the finding #844 asks for ("cycle drivers such as oil
  price").
* ``oil_linked_lagged`` — value = a + b·(oil price at t−1). Rig contracting lags
  the price signal: an operator sanctions a well programme on last year's cash
  flow, and the fixture prints this year. When the lagged form beats the
  contemporaneous one, that lag is real and worth stating.

Honesty rails
-------------
* A fit needs ``MIN_POINTS_FOR_FIT`` sourced points. Below that we return no fit
  at all rather than draw a confident line through three dots.
* Extrapolation beyond the sourced range is permitted (that is the point) but
  every projected year is flagged ``extrapolated=True``, and the report renders
  it differently. Two years past the last datum is a projection; twenty is
  fiction, and the flag is what lets a reader tell which they're looking at.
* We report R², adjusted R², RMSE and n — never a bare curve.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

import numpy as np

from worldenergydata.cost.timeseries.schema import CostComponent, CostObservation

__all__ = [
    "FunctionalForm",
    "FitResult",
    "MIN_POINTS_FOR_FIT",
    "fit_component",
    "predict",
]

#: Below this many distinct sourced years, we decline to fit. Three points can
#: be fitted by anything; a curve through them says more about the fitter than
#: the market.
MIN_POINTS_FOR_FIT = 5


class FunctionalForm(str, Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    OIL_LINKED = "oil_linked"
    OIL_LINKED_LAGGED = "oil_linked_lagged"


@dataclass(frozen=True)
class FitResult:
    """A fitted trend curve for one component, with its quality stated."""

    component: CostComponent
    form: FunctionalForm
    #: Coefficients, named per form (e.g. {"a": .., "b": ..}).
    coefficients: dict[str, float]
    r_squared: float
    adj_r_squared: float
    rmse: float
    n_points: int
    fit_year_min: int
    fit_year_max: int
    #: Pearson r between the component and the contemporaneous oil price, for
    #: the cycle-driver commentary #844 asks for. None when unavailable.
    oil_price_corr: Optional[float]
    equation: str
    #: Every candidate form's adjusted R², so the reader can see what lost.
    candidates: dict[str, float] = field(default_factory=dict)

    @property
    def is_weak(self) -> bool:
        """A fit we would not want a reader to lean on without seeing the caveat."""
        return self.adj_r_squared < 0.35


def _r2_and_rmse(actual: np.ndarray, predicted: np.ndarray) -> tuple[float, float]:
    residuals = actual - predicted
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((actual - actual.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    rmse = float(math.sqrt(ss_res / len(actual)))
    return r2, rmse


def _adjusted(r2: float, n: int, k: int) -> float:
    """Adjusted R². ``k`` = number of predictors (excluding the intercept)."""
    if n - k - 1 <= 0:
        return float("-inf")
    return 1.0 - (1.0 - r2) * (n - 1) / (n - k - 1)


def _annual_means(
    observations: list[CostObservation], component: CostComponent
) -> dict[int, float]:
    """Collapse sourced rows for one component to one value per year.

    Multiple fixtures in a year are averaged, so a heavily-reported year does
    not dominate the fit purely by having been written about more.
    """
    buckets: dict[int, list[float]] = {}
    for obs in observations:
        if (
            obs.component is component
            and obs.value is not None
            and obs.provenance.value == "sourced"
        ):
            buckets.setdefault(obs.year, []).append(obs.value)
    return {year: sum(v) / len(v) for year, v in sorted(buckets.items())}


def fit_component(
    observations: list[CostObservation],
    component: CostComponent,
    oil_price_by_year: Optional[dict[int, float]] = None,
) -> Optional[FitResult]:
    """Fit the best-supported trend curve for one component.

    Returns ``None`` when there are too few sourced points to fit responsibly —
    a legitimate and common outcome for the thinner series.
    """
    annual = _annual_means(observations, component)
    if len(annual) < MIN_POINTS_FOR_FIT:
        return None

    years = np.array(sorted(annual), dtype=float)
    values = np.array([annual[int(y)] for y in years], dtype=float)
    # Centre the time axis on the first fitted year: keeps the design matrix
    # well-conditioned and makes the intercept `a` interpretable as "the level
    # at the start of the fitted window" instead of the level in the year 0 AD.
    t = years - years.min()

    candidates: list[tuple[FunctionalForm, dict[str, float], np.ndarray, int]] = []

    # --- linear -----------------------------------------------------------
    b, a = np.polyfit(t, values, 1)
    candidates.append((FunctionalForm.LINEAR, {"a": float(a), "b": float(b)},
                       a + b * t, 1))

    # --- exponential (log-linear) ----------------------------------------
    # Only defined for strictly positive values. Costs are, but guard anyway.
    if np.all(values > 0):
        log_b, log_a = np.polyfit(t, np.log(values), 1)
        exp_pred = np.exp(log_a) * np.exp(log_b * t)
        candidates.append((
            FunctionalForm.EXPONENTIAL,
            {"a": float(np.exp(log_a)), "b": float(log_b)},
            exp_pred,
            1,
        ))

    # --- oil-linked (contemporaneous and lagged) --------------------------
    oil_corr: Optional[float] = None
    if oil_price_by_year:
        for form, lag in (
            (FunctionalForm.OIL_LINKED, 0),
            (FunctionalForm.OIL_LINKED_LAGGED, 1),
        ):
            paired = [
                (oil_price_by_year[int(y) - lag], annual[int(y)])
                for y in years
                if int(y) - lag in oil_price_by_year
            ]
            if len(paired) < MIN_POINTS_FOR_FIT:
                continue
            oil = np.array([p[0] for p in paired], dtype=float)
            val = np.array([p[1] for p in paired], dtype=float)
            b_oil, a_oil = np.polyfit(oil, val, 1)
            # NOTE: this candidate is scored against `val`, its own aligned
            # subset — not against the full `values` — so the r2 comparison
            # below stays apples-to-apples on the rows each form actually saw.
            pred = a_oil + b_oil * oil
            r2_oil, rmse_oil = _r2_and_rmse(val, pred)
            adj_oil = _adjusted(r2_oil, len(val), 1)
            candidates.append((
                form,
                {"a": float(a_oil), "b": float(b_oil), "lag_years": float(lag)},
                pred,
                1,
            ))
            if lag == 0:
                # Pearson r for the cycle-driver commentary.
                if val.std() > 0 and oil.std() > 0:
                    oil_corr = float(np.corrcoef(oil, val)[0, 1])

    # --- score and choose -------------------------------------------------
    scored: list[tuple[float, FunctionalForm, dict[str, float], float, float, int]] = []
    for form, coeffs, pred, k in candidates:
        # Oil-linked forms were fitted on their own aligned subset, which may be
        # shorter than `values`; recompute against the matching actuals.
        if form in (FunctionalForm.OIL_LINKED, FunctionalForm.OIL_LINKED_LAGGED):
            lag = int(coeffs["lag_years"])
            actual = np.array(
                [annual[int(y)] for y in years if int(y) - lag in (oil_price_by_year or {})],
                dtype=float,
            )
        else:
            actual = values
        if len(actual) != len(pred) or len(actual) == 0:
            continue
        r2, rmse = _r2_and_rmse(actual, pred)
        adj = _adjusted(r2, len(actual), k)
        scored.append((adj, form, coeffs, r2, rmse, len(actual)))

    if not scored:
        return None

    scored.sort(key=lambda row: row[0], reverse=True)
    adj, form, coeffs, r2, rmse, n = scored[0]

    if form is FunctionalForm.LINEAR:
        equation = f"value = {coeffs['a']:.4g} + {coeffs['b']:.4g}·(year − {int(years.min())})"
    elif form is FunctionalForm.EXPONENTIAL:
        equation = (
            f"value = {coeffs['a']:.4g} · exp({coeffs['b']:.4g}·(year − {int(years.min())}))"
            f"   [{coeffs['b'] * 100:.1f}% per year]"
        )
    else:
        lag = int(coeffs["lag_years"])
        lag_txt = "" if lag == 0 else f" at t−{lag}"
        equation = f"value = {coeffs['a']:.4g} + {coeffs['b']:.4g}·(Brent $/bbl{lag_txt})"

    return FitResult(
        component=component,
        form=form,
        coefficients=coeffs,
        r_squared=r2,
        adj_r_squared=adj,
        rmse=rmse,
        n_points=n,
        fit_year_min=int(years.min()),
        fit_year_max=int(years.max()),
        oil_price_corr=oil_corr,
        equation=equation,
        candidates={f.value: round(a, 4) for a, f, _, _, _, _ in scored},
    )


def predict(
    fit: FitResult,
    year: int,
    oil_price_by_year: Optional[dict[int, float]] = None,
) -> Optional[tuple[float, bool]]:
    """Evaluate a fitted curve at ``year``.

    Returns ``(value, extrapolated)`` where ``extrapolated`` is True when the
    year lies outside the window the curve was fitted on — the caller is
    expected to propagate that flag, not drop it.

    Returns ``None`` for an oil-linked form when the oil price for the required
    year is unknown: the curve's own input is missing, so there is nothing to
    evaluate and nothing to invent.
    """
    t = year - fit.fit_year_min
    extrapolated = year < fit.fit_year_min or year > fit.fit_year_max

    if fit.form is FunctionalForm.LINEAR:
        return fit.coefficients["a"] + fit.coefficients["b"] * t, extrapolated

    if fit.form is FunctionalForm.EXPONENTIAL:
        return (
            fit.coefficients["a"] * math.exp(fit.coefficients["b"] * t),
            extrapolated,
        )

    lag = int(fit.coefficients.get("lag_years", 0))
    if not oil_price_by_year:
        return None
    oil = oil_price_by_year.get(year - lag)
    if oil is None:
        return None
    return fit.coefficients["a"] + fit.coefficients["b"] * oil, extrapolated
