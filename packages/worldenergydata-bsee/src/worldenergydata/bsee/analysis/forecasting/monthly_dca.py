"""Calendar-aware oil decline analysis for public OGOR-A monthly records.

Engineering basis (public sources, accessed 2026-11-02):
* Arps, J.J., 1945, Analysis of Decline Curves, Trans. AIME 160,
  pp. 228-247, doi:10.2118/945228-G: exponential, hyperbolic and harmonic.
* Penn State EME 801, Production Decline for Shale Gas Wells, eqs. (1)-(2):
  https://www.e-education.psu.edu/eme801/sites/www.e-education.psu.edu.eme801/files/Production%20Decline%20for%20Shale%20Gas%20Wells.pdf
* Pradhan, 2020, Texas A&M MS thesis, section 2.1, p. 9: continuous
  hyperbolic-to-terminal-exponential splice, including q_lim and t_lim.
  https://blasingame.engr.tamu.edu/0_TAB_Grad/TAB_Grad_Thesis_Archive/MS_073_PRADHAN_Yogashril_Thesis_TAMU_%28Dec_2020%29.pdf
* BSEE OGORA field definitions, PRODUCTION_DATE, DAYS_ON_PROD,
  MON_O_PROD_VOL, API_WELL_NUMBER and FIELD_NAME_CODE:
  https://www.data.bsee.gov/Main/HtmlPage.aspx?page=ogorA

Oil volumes are input in bbl, rates in bbl/calendar-day, nominal declines
in year^-1. A year is defined here as 365.25 days (calendar convention).
Economic limit and terminal decline are required scenario inputs; neither
is inferred from operating costs. No standards-derived coefficient is used.
The b <= 1 bound is a deliberate conventional-Arps scope restriction.
This is an empirical screening forecast, not a reserves classification.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from worldenergydata.common.decline import hyperbolic_rate

DAYS_PER_YEAR = 365.25


@dataclass(frozen=True)
class ModifiedArps:
    """Arps rate with a continuous terminal tail (Pradhan 2020, §2.1).

    D(t)=Di/(1+b*Di*t); switch=max(0,(Di/Dterm-1)/(b*Di)).
    The b=0 case is exponential. Di >= Dterm > 0 is required.
    """

    initial_rate: float
    decline: float
    b: float
    terminal_decline: float

    def __post_init__(self):
        values = [self.initial_rate, self.decline, self.b, self.terminal_decline]
        if (
            not np.isfinite(values).all()
            or self.initial_rate <= 0
            or not 0 <= self.b <= 1
            or self.terminal_decline <= 0
            or self.decline < self.terminal_decline
        ):
            raise ValueError("require qi > 0, Di >= Dterm > 0 and 0 <= b <= 1")

    @property
    def switch_years(self):
        if self.b == 0:
            return float("inf")
        return max(
            0.0, (self.decline / self.terminal_decline - 1) / (self.b * self.decline)
        )

    def rate(self, years):
        """Return bbl/d from the shared Arps equation and continuous tail."""
        years = np.asarray(years, dtype=float)
        if not np.isfinite(years).all() or (years < 0).any():
            raise ValueError("elapsed years must be finite and nonnegative")
        switch = self.switch_years
        early = hyperbolic_rate(
            np.minimum(years, switch), self.initial_rate, self.decline, self.b
        )
        if np.isfinite(switch):
            early = early * np.exp(
                -self.terminal_decline * np.maximum(0, years - switch)
            )
        return early

    def time_to_rate(self, limit):
        """Invert the rate equation; return elapsed years at a positive limit."""
        if not np.isfinite(limit) or limit <= 0:
            raise ValueError("economic limit must be positive bbl/d")
        if limit >= self.initial_rate:
            return 0.0
        if self.b == 0:
            return np.log(self.initial_rate / limit) / self.decline
        switch = self.switch_years
        switch_rate = float(self.rate(switch))
        if limit < switch_rate:
            return switch + np.log(switch_rate / limit) / self.terminal_decline
        return np.expm1(self.b * np.log(self.initial_rate / limit)) / (
            self.b * self.decline
        )

    def volume(self, start, end):
        """Integrate q dt in bbl, using Arps antiderivatives and terminal tail.

        Derived directly from the cited rate equations: exponential qi/D
        (exp(-Da)-exp(-Dz)); harmonic qi/D log((1+Dz)/(1+Da)); otherwise
        qi/[D(b-1)] * [(1+bDz)^((b-1)/b)-(1+bDa)^((b-1)/b)].
        Multiplication by 365.25 converts rate-years to barrels.
        """
        if not np.isfinite([start, end]).all() or start < 0 or end < start:
            raise ValueError("require finite 0 <= start <= end in years")
        switch = self.switch_years
        stop = min(end, switch)
        total = 0.0
        if start < stop:
            if self.b == 0:
                total = (
                    self.initial_rate
                    / self.decline
                    * np.exp(-self.decline * start)
                    * -np.expm1(-self.decline * (stop - start))
                )
            elif self.b == 1:
                total = (
                    self.initial_rate
                    / self.decline
                    * np.log1p(
                        self.decline * (stop - start) / (1 + self.decline * start)
                    )
                )
            else:
                exponent = (self.b - 1) / self.b
                log_a = np.log1p(self.b * self.decline * start)
                log_delta = np.log1p(
                    self.b
                    * self.decline
                    * (stop - start)
                    / (1 + self.b * self.decline * start)
                )
                total = (
                    self.initial_rate
                    / (self.decline * (self.b - 1))
                    * np.exp(exponent * log_a)
                    * np.expm1(exponent * log_delta)
                )
        if end > switch:
            tail_start = max(start, switch)
            total += (
                float(self.rate(tail_start))
                / self.terminal_decline
                * -np.expm1(-self.terminal_decline * (end - tail_start))
            )
        return float(total * DAYS_PER_YEAR)


@dataclass
class MonthlyProduction:
    """Observed monthly oil, including unreported and zero-oil months."""

    label: str
    frame: pd.DataFrame


def prepare_monthly(records, group_by, key):
    """Sum completion oil by well/field and divide by calendar month days.

    BSEE OGORA column definitions are cited in the module docstring. No
    interpolation or volume inference is performed. A partial month
    lacks a completion that reports on both sides of that month; starts/ends of
    member histories cannot establish reporting completeness. Shut-in marks
    mean reported zero oil, not a diagnosis of well status or pump condition.
    """
    if group_by not in {"API_WELL_NUMBER", "FIELD_NAME_CODE"}:
        raise ValueError("group_by must be API_WELL_NUMBER or FIELD_NAME_CODE")
    required = {
        group_by,
        "API_WELL_NUMBER",
        "PRODUCTION_DATE",
        "MON_O_PROD_VOL",
        "DAYS_ON_PROD",
        "LEASE_NUMBER",
        "COMPLETION_NAME",
    }
    if not required.issubset(records.columns):
        raise ValueError(
            f"missing OGOR-A columns: {sorted(required - set(records.columns))}"
        )
    df = records.loc[records[group_by].astype(str).str.strip() == str(key)].copy()
    if df.empty:
        raise ValueError("selection has no reported records")
    for col in ("API_WELL_NUMBER", "LEASE_NUMBER", "COMPLETION_NAME"):
        if df[col].isna().any() or df[col].astype(str).str.strip().eq("").any():
            raise ValueError(f"missing identity: {col}")
        df[col] = df[col].astype(str).str.strip()
    raw_dates = df.PRODUCTION_DATE.astype(str).str.strip()
    if not raw_dates.str.fullmatch(r"\d{6}").all():
        raise ValueError("PRODUCTION_DATE must be YYYYMM")
    df["date"] = pd.to_datetime(
        raw_dates, format="%Y%m", errors="raise"
    ) + pd.offsets.MonthEnd(0)
    identity = ["LEASE_NUMBER", "COMPLETION_NAME", "API_WELL_NUMBER", "date"]
    if "PROD_INTERVAL_CD" in df:
        identity.append("PROD_INTERVAL_CD")
    if df.duplicated(identity).any():
        raise ValueError("duplicate completion-month records")
    oil = pd.to_numeric(df.MON_O_PROD_VOL, errors="raise").astype(float)
    days = pd.to_numeric(df.DAYS_ON_PROD, errors="raise").astype(float)
    if (
        not np.isfinite(oil).all()
        or not np.isfinite(days).all()
        or (oil < 0).any()
        or (days < 0).any()
        or (days % 1 != 0).any()
        or (days > df.date.dt.days_in_month).any()
        or ((days == 0) & (oil > 0)).any()
    ):
        raise ValueError("invalid oil barrels or days on production")
    df["oil_bbl"] = oil
    dates = pd.date_range(df.date.min(), df.date.max(), freq="ME")
    grouped = df.groupby("date").oil_bbl.sum().reindex(dates)
    frame = pd.DataFrame({"oil_bbl": grouped}, index=dates)
    frame["rate_bpd"] = frame.oil_bbl / frame.index.days_in_month
    frame["missing"] = frame.oil_bbl.isna()
    frame["shut_in"] = frame.oil_bbl.eq(0) & ~frame.missing
    partial = pd.Series(False, index=dates)
    member_keys = [col for col in identity if col != "date"]
    for _, member in df.groupby(member_keys):
        expected = pd.date_range(member.date.min(), member.date.max(), freq="ME")
        partial.loc[expected.difference(pd.DatetimeIndex(member.date))] = True
    frame["partial"] = partial & ~frame.missing
    return MonthlyProduction(
        f"{'Well' if group_by == 'API_WELL_NUMBER' else 'Field'} {key}", frame
    )


@dataclass
class Backtest:
    cutoff: pd.Timestamp
    dates: pd.DatetimeIndex
    predicted: np.ndarray
    actual: np.ndarray
    rmse_bpd: float


@dataclass
class MonthlyDca:
    history: MonthlyProduction
    model: ModifiedArps
    model_name: str
    origin: pd.Timestamp
    fit_dates: pd.DatetimeIndex
    forecast_dates: pd.DatetimeIndex
    forecast_rates: np.ndarray
    forecast_cumulative_bbl: np.ndarray
    observed_bbl: float
    remaining_bbl: float
    eur_bbl: float | None
    economic_limit: float
    limit_reached: bool
    backtest: Backtest | None
    rmse_bpd: float


def _years(dates, origin):
    return np.asarray((dates - origin) / pd.Timedelta(days=DAYS_PER_YEAR), dtype=float)


def _fit(frame, terminal, cap, months):
    window = frame.loc[frame.index > frame.index[-1] - pd.DateOffset(months=months)]
    active = window.loc[~(window.missing | window.shut_in | window.partial)]
    if len(active) < 6:
        raise ValueError(
            "at least six active, complete months are required in the fit window"
        )
    origin = active.index[0]
    time = _years(active.index, origin)
    observed = active.rate_bpd.to_numpy()
    scale = observed.max()
    candidates = []
    models = [("exponential", 0)]
    if cap > 0:
        models.append(("hyperbolic", None))
    if cap == 1:
        models.append(("harmonic", 1))
    for name, fixed_b in models:

        def curve(params, fixed_b=fixed_b):
            return ModifiedArps(
                params[0] * scale,
                params[1],
                params[2] if fixed_b is None else fixed_b,
                terminal,
            )

        free_b = fixed_b is None
        solution = least_squares(
            lambda p, curve=curve: (curve(p).rate(time) - observed) / scale,
            [observed[0] / scale, max(terminal * 2, 0.3)]
            + ([cap / 2] if free_b else []),
            bounds=(
                [np.finfo(float).eps, terminal] + ([0] if free_b else []),
                [np.inf, np.inf] + ([cap] if free_b else []),
            ),
            max_nfev=3000,
            ftol=1e-12,
            xtol=1e-12,
            gtol=1e-12,
        )
        if not solution.success:
            continue
        fitted = curve(solution.x)
        rss = float(np.sum((fitted.rate(time) - observed) ** 2))
        # Gaussian residual AIC, up to the shared additive constant:
        # Akaike 1974, IEEE Trans. Automatic Control 19(6), pp.716-723,
        # doi:10.1109/TAC.1974.1100705. This is model selection, not uncertainty.
        aic = len(active) * np.log(
            max(rss / len(active), np.finfo(float).tiny)
        ) + 2 * len(solution.x)
        candidates.append((aic, fitted, name, np.sqrt(rss / len(active))))
    if not candidates:
        raise ValueError("bounded model fitting did not converge")
    _, model, name, rmse = min(candidates, key=lambda x: x[0])
    return model, name, origin, active.index, float(rmse)


def analyze_monthly(
    history,
    *,
    economic_limit,
    terminal_decline,
    b_max=1.0,
    fit_months=36,
    backtest_years=2,
    max_years=60,
):
    """Fit trailing months and forecast to a limit or explicit horizon.

    EUR = observed bbl + integrated remaining bbl, only when the supplied
    history has no internal missing/partial reports and the limit is reached.
    Complete lifecycle reporting before/after the supplied history is not
    established. Back-tests refit the same trailing window using only records
    at or before the historical cutoff. Metrics include reported shut-ins.
    """
    numeric = [
        economic_limit,
        terminal_decline,
        b_max,
        max_years,
        fit_months,
        backtest_years,
    ]
    if (
        not np.isfinite(numeric).all()
        or economic_limit <= 0
        or terminal_decline <= 0
        or not 0 <= b_max <= 1
        or not 0 < max_years <= 100
        or fit_months < 6
        or int(fit_months) != fit_months
        or backtest_years <= 0
        or int(backtest_years) != backtest_years
    ):
        raise ValueError(
            "invalid limit, decline, cap, fit window, back-test or horizon"
        )
    frame = history.frame
    model, name, origin, fit_dates, rmse = _fit(
        frame, terminal_decline, b_max, fit_months
    )
    today = frame.index[-1]
    start = float(_years(pd.DatetimeIndex([today]), origin)[0])
    limit_time = max(start, model.time_to_rate(economic_limit))
    end = min(limit_time, start + max_years)
    limit_reached = bool(limit_time <= start + max_years)
    count = max(2, int(np.ceil((end - start) * 12)) + 1) if end > start else 1
    time = np.linspace(start, end, count)
    forecast_dates = pd.DatetimeIndex(
        [today + pd.Timedelta(days=(t - start) * DAYS_PER_YEAR) for t in time]
    )
    observed = float(frame.oil_bbl.sum())
    cumulative = np.array([observed + model.volume(start, t) for t in time])
    remaining = model.volume(start, end)
    complete = not (frame.missing | frame.partial).any()
    cutoff = today - pd.DateOffset(years=int(backtest_years))
    train = frame.loc[frame.index <= cutoff]
    held = frame.loc[(frame.index > cutoff) & ~(frame.missing | frame.partial)]
    backtest = None
    if len(train) and len(held):
        try:
            old_model, _, old_origin, _, _ = _fit(
                train, terminal_decline, b_max, fit_months
            )
        except ValueError:
            pass  # Insufficient training is exposed as unavailable, never a zero-error result.
        else:
            held_time = _years(held.index, old_origin)
            predicted = old_model.rate(held_time)
            old_limit = old_model.time_to_rate(economic_limit)
            predicted = np.where(held_time > old_limit, 0.0, predicted)
            actual = held.rate_bpd.to_numpy()
            backtest = Backtest(
                train.index[-1],
                held.index,
                predicted,
                actual,
                float(np.sqrt(np.mean((actual - predicted) ** 2))),
            )
    return MonthlyDca(
        history,
        model,
        name,
        origin,
        fit_dates,
        forecast_dates,
        model.rate(time),
        cumulative,
        observed,
        remaining,
        observed + remaining if complete and limit_reached else None,
        economic_limit,
        limit_reached,
        backtest,
        rmse,
    )
