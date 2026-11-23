"""Calendar, units and independent numerical checks for monthly oil DCA."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.bsee.analysis.forecasting.monthly_dca import (
    ModifiedArps,
    analyze_monthly,
    prepare_monthly,
)


def records(n=72):
    dates = pd.date_range("2018-01-31", periods=n, freq="ME")
    t = (dates - dates[0]).days.to_numpy() / 365.25
    return pd.DataFrame(
        {
            "PRODUCTION_DATE": dates.strftime("%Y%m"),
            "API_WELL_NUMBER": "608124003301",
            "FIELD_NAME_CODE": "WR627",
            "LEASE_NUMBER": "G20351",
            "COMPLETION_NAME": "A",
            "MON_O_PROD_VOL": 1000 * np.exp(-0.3 * t) * dates.days_in_month,
            "DAYS_ON_PROD": dates.days_in_month,
        }
    )


def test_exponential_worked_example_barrels_and_limit():
    # q=100 exp(-0.2t) bbl/d, t in years. q=50 at ln(2)/0.2
    # =3.465735903 yr; integral=365.25*(100-50)/0.2=91,312.5 bbl.
    curve = ModifiedArps(100, 0.2, 0, 0.06)
    end = curve.time_to_rate(50)
    assert end == pytest.approx(3.465735903)
    assert curve.volume(0, end) == pytest.approx(91312.5)
    assert curve.rate(end) == pytest.approx(50)


def test_terminal_switch_and_harmonic_integral():
    # D(t)=0.4/(1+0.5*0.4t); D=0.1 at t=15; q=100/4**2=6.25.
    curve = ModifiedArps(100, 0.4, 0.5, 0.1)
    assert curve.switch_years == pytest.approx(15)
    assert curve.rate(15) == pytest.approx(6.25)
    assert curve.rate(16) == pytest.approx(6.25 * np.exp(-0.1))
    assert curve.volume(15, 16) == pytest.approx(
        365.25 * 6.25 / 0.1 * (1 - np.exp(-0.1))
    )
    # Harmonic q=100/(1+0.2t); integral 0..5 =365.25*500*ln(2).
    harmonic = ModifiedArps(100, 0.2, 1, 0.06)
    assert harmonic.volume(0, 5) == pytest.approx(365.25 * 500 * np.log(2))
    assert harmonic.time_to_rate(harmonic.rate(25)) == pytest.approx(25)


def test_field_calendar_rate_and_completion_sums():
    df = records(6)
    other = df.assign(API_WELL_NUMBER="608124009400", COMPLETION_NAME="B")
    field = prepare_monthly(pd.concat([df, other]), "FIELD_NAME_CODE", "WR627")
    assert field.frame.rate_bpd.iloc[0] == pytest.approx(2000)
    assert field.frame.oil_bbl.sum() == pytest.approx(2 * df.MON_O_PROD_VOL.sum())
    assert field.frame.index[1] == pd.Timestamp("2018-02-28")
    assert field.frame.rate_bpd.iloc[1] == pytest.approx(
        2 * df.MON_O_PROD_VOL.iloc[1] / 28
    )


def test_shut_in_not_fitted_missing_not_zero_and_time_not_compressed():
    df = records()
    df.loc[20, ["MON_O_PROD_VOL", "DAYS_ON_PROD"]] = 0
    df = df.drop(index=25)
    history = prepare_monthly(df, "API_WELL_NUMBER", "608124003301")
    assert history.frame.shut_in.sum() == 1
    assert history.frame.missing.sum() == 1
    assert np.isnan(history.frame.rate_bpd.iloc[25])
    result = analyze_monthly(
        history, economic_limit=50, terminal_decline=0.06, fit_months=72
    )
    assert len(result.fit_dates) == 70
    assert result.model.decline == pytest.approx(0.3, rel=1e-4)
    assert result.eur_bbl is None
    assert result.observed_bbl == pytest.approx(df.MON_O_PROD_VOL.sum())


def test_field_partial_month_is_excluded():
    df = records()
    other = df.assign(API_WELL_NUMBER="608124009400", COMPLETION_NAME="B").drop(
        index=40
    )
    history = prepare_monthly(pd.concat([df, other]), "FIELD_NAME_CODE", "WR627")
    assert history.frame.partial.iloc[40]
    result = analyze_monthly(history, economic_limit=50, terminal_decline=0.06)
    assert history.frame.index[40] not in result.fit_dates
    assert result.eur_bbl is None


def test_missing_completion_is_partial_even_when_same_api_reports():
    df = records()
    other = df.assign(COMPLETION_NAME="B").drop(index=40)
    history = prepare_monthly(pd.concat([df, other]), "API_WELL_NUMBER", "608124003301")
    assert history.frame.partial.iloc[40]


def test_calendar_leap_month_and_analytic_integral_against_quadrature():
    from scipy.integrate import quad

    history = prepare_monthly(records(), "API_WELL_NUMBER", "608124003301")
    assert history.frame.loc["2020-02-29", "oil_bbl"] / history.frame.loc[
        "2020-02-29", "rate_bpd"
    ] == pytest.approx(29)
    for b in (0, 1e-8, 0.5, 1):
        model = ModifiedArps(100, 0.4, b, 0.1)
        numeric, _ = quad(
            lambda t, model=model: float(model.rate(t)) * 365.25,
            2,
            25,
            points=[model.switch_years] if 2 < model.switch_years < 25 else None,
        )
        assert model.volume(2, 25) == pytest.approx(numeric, rel=1e-8)


def test_forecast_starts_at_reporting_boundary_and_backtest_has_no_leakage():
    df = records()
    history = prepare_monthly(df, "API_WELL_NUMBER", "608124003301")
    result = analyze_monthly(history, economic_limit=50, terminal_decline=0.06)
    assert result.forecast_dates[0] == history.frame.index[-1]
    assert result.forecast_rates[-1] == pytest.approx(50)
    assert result.eur_bbl == pytest.approx(result.observed_bbl + result.remaining_bbl)
    assert result.backtest.rmse_bpd < 0.01
    assert result.backtest.dates.min() > result.backtest.cutoff
    changed = df.copy()
    changed.loc[
        changed.PRODUCTION_DATE > result.backtest.cutoff.strftime("%Y%m"),
        "MON_O_PROD_VOL",
    ] *= 2
    rerun = analyze_monthly(
        prepare_monthly(changed, "API_WELL_NUMBER", "608124003301"),
        economic_limit=50,
        terminal_decline=0.06,
    )
    np.testing.assert_allclose(rerun.backtest.predicted, result.backtest.predicted)


def test_capped_fit_and_horizon_not_presented_as_eur():
    history = prepare_monthly(records(), "API_WELL_NUMBER", "608124003301")
    result = analyze_monthly(
        history, economic_limit=1, terminal_decline=0.06, b_max=0.5, max_years=1
    )
    assert 0 <= result.model.b <= 0.5
    assert not result.limit_reached
    assert result.eur_bbl is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"economic_limit": 0},
        {"terminal_decline": 0},
        {"b_max": 1.1},
        {"economic_limit": np.nan},
        {"max_years": -1},
        {"fit_months": 2},
        {"backtest_years": 0},
    ],
)
def test_invalid_settings(kwargs):
    settings = {"economic_limit": 50, "terminal_decline": 0.06}
    settings.update(kwargs)
    with pytest.raises(ValueError):
        analyze_monthly(
            prepare_monthly(records(), "API_WELL_NUMBER", "608124003301"), **settings
        )


@pytest.mark.parametrize(
    "column,value",
    [
        ("MON_O_PROD_VOL", -1),
        ("MON_O_PROD_VOL", np.inf),
        ("DAYS_ON_PROD", 32),
        ("DAYS_ON_PROD", 0),
        ("PRODUCTION_DATE", "201813"),
    ],
)
def test_invalid_records(column, value):
    df = records()
    df.loc[0, column] = value
    with pytest.raises(ValueError):
        prepare_monthly(df, "API_WELL_NUMBER", "608124003301")


def test_duplicate_records_and_unknown_selection_rejected():
    df = records()
    with pytest.raises(ValueError, match="duplicate"):
        prepare_monthly(pd.concat([df, df.iloc[:1]]), "API_WELL_NUMBER", "608124003301")
    with pytest.raises(ValueError):
        prepare_monthly(df, "API_WELL_NUMBER", "missing")
    with pytest.raises(ValueError):
        prepare_monthly(
            df.rename(columns={"MON_O_PROD_VOL": "oil_m3"}), "FIELD_NAME_CODE", "WR627"
        )


def test_insufficient_history_and_already_below_limit():
    history = prepare_monthly(records(6), "API_WELL_NUMBER", "608124003301")
    result = analyze_monthly(history, economic_limit=2000, terminal_decline=0.06)
    assert result.remaining_bbl == 0
    assert result.backtest is None
    assert len(result.forecast_dates) == 1
    with pytest.raises(ValueError):
        analyze_monthly(
            prepare_monthly(records(2), "API_WELL_NUMBER", "608124003301"),
            economic_limit=50,
            terminal_decline=0.06,
        )
