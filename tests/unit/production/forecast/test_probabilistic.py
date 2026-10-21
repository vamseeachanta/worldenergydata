"""Independent hand calculations; all numerical inputs are synthetic test data.

Equations: ResInsight, Decline Curve Analysis, rate/time and cumulative sections
(accessed 2026), https://resinsight.org/plot-window/declinecurveanalysis/.
Percentiles: NumPy 2.2 percentile documentation, linear method.
NPV: numpy-financial npv documentation, end-of-period convention.
"""

import copy
import json
import math

import numpy as np
import pandas as pd
import pytest

from worldenergydata.production.forecast.decline import ArpsDeclineCurve
from worldenergydata.production.forecast.probabilistic import ProbabilisticForecast
from worldenergydata.production.forecast.router import ProductionForecast
from worldenergydata.production.forecast.uq import PriorSpec, sample_priors


def study():
    """Synthetic boundary case: constant price, uncertain rate only."""
    return {
        "field": "Synthetic example",
        "data_basis": "synthetic",
        "engine": "builtin",
        "seed": 42,
        "n_samples": 20,
        "forecast_months": 2,
        "base": {
            "qi": 1000,
            "Di": math.log(2),
            "b": 0,
            "economic_limit": 250,
            "oil_price": 2,
            "opex": 1,
            "capex": 10,
            "discount_rate": 0,
        },
        "priors": [{"name": "qi", "dist": "uniform", "low": 1000, "high": 1100}],
    }


@pytest.mark.parametrize(
    "b,expected", [(0, 9000), (0.5, 10000), (1, 10000 * math.log(4))]
)
def test_simulate_integral(b, expected):
    """qi=1000, Di=.1. qlim=100 for exp, 250 otherwise.

    Exp: (1000-100)/.1=9000. Hyperbolic b=.5:
    1000/(.1*.5)*(1-sqrt(250/1000))=10000.
    Harmonic: 1000/.1*ln(1000/250)=10000*ln(4).
    """
    limit = 100 if b == 0 else 250
    result = ArpsDeclineCurve().simulate(
        qi=1000, Di=0.1, b=b, economic_limit=limit, months=200
    )
    assert result.eur_bbl == pytest.approx(expected)
    assert result.forecast_df.volume_bbl.sum() == pytest.approx(expected)
    assert result.r_squared is None  # Forward simulation has no fitted R squared.


def test_partial_month_and_small_limit():
    """q=exp(-ln(2)*t); limit=.75 at t=ln(4/3)/ln(2)<1.

    First month volume=(1-.75)/ln(2); following months produce zero.
    This also guards against the historical 1 bbl/month EUR floor.
    """
    result = ArpsDeclineCurve().simulate(
        qi=1, Di=math.log(2), b=0, economic_limit=0.75, months=2
    )
    assert result.eur_bbl == pytest.approx(0.25 / math.log(2))
    assert result.forecast_df.volume_bbl.tolist() == pytest.approx([result.eur_bbl, 0])
    assert result.forecast_df.rate_bbl.tolist() == [0, 0]


@pytest.mark.parametrize(
    "changes",
    [
        {"qi": 0},
        {"Di": 0},
        {"b": -1},
        {"b": 1.1},
        {"economic_limit": 0},
        {"qi": float("nan")},
        {"months": 1.5},
        {"months": True},
    ],
)
def test_invalid_simulation(changes):
    params = {"qi": 1000, "Di": 0.1, "b": 0.5, "economic_limit": 100, "months": 2}
    params.update(changes)
    with pytest.raises(ValueError):
        ArpsDeclineCurve().simulate(**params)


def test_reproducibility_and_economics():
    """For each sampled qi, exp rate halves each month.

    Month 1 volume=qi/(2 ln2), month 2=qi/(4 ln2).
    NPV at zero discount=-10+(2-1)*3qi/(4 ln2).
    EUR=(qi-250)/ln2, independent of the two-month NPV horizon.
    """
    result = ProbabilisticForecast().run(study())
    repeat = ProbabilisticForecast().run(study())
    pd.testing.assert_frame_equal(result.run_matrix, repeat.run_matrix)
    qi = result.run_matrix.qi.to_numpy()
    np.testing.assert_allclose(
        result.run_matrix.npv_usd, -10 + 3 * qi / (4 * math.log(2))
    )
    np.testing.assert_allclose(result.run_matrix.eur_bbl, (qi - 250) / math.log(2))
    assert result.summary["screening_status"] == "NOT_EVALUATED"
    assert result.summary["spearman"]["qi"] == pytest.approx(1)
    assert (result.fan.p10 <= result.fan.p50).all()
    assert (result.fan.p50 <= result.fan.p90).all()
    json.dumps(result.summary, allow_nan=False)


def test_discount_timing():
    """Annual discount=1 means monthly factor=2**(1/12).

    NPV=-10+V1/factor+V2/factor**2; capex is at time zero.
    """
    cfg = study()
    cfg["base"]["discount_rate"] = 1
    result = ProbabilisticForecast().run(cfg)
    qi = result.run_matrix.qi.to_numpy()
    expected = -10 + qi / (2 * math.log(2) * 2 ** (1 / 12))
    expected += qi / (4 * math.log(2) * 2 ** (2 / 12))
    np.testing.assert_allclose(result.run_matrix.npv_usd, expected)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c.update(n_samples=0),
        lambda c: c.update(n_samples=2.5),
        lambda c: c.update(engine="typo"),
        lambda c: c["base"].update(oil_price=-1),
        lambda c: c["base"].update(discount_rate=-1),
        lambda c: c["priors"][0].update(name="typo"),
        lambda c: c["priors"].append(copy.deepcopy(c["priors"][0])),
        lambda c: c["priors"][0].update(dist="typo"),
        lambda c: c["priors"][0].update(low=1200),
        lambda c: c["priors"][0].update(ignored_parameter=1),
    ],
)
def test_invalid_study(mutate):
    cfg = study()
    mutate(cfg)
    with pytest.raises(ValueError):
        ProbabilisticForecast().run(cfg)


@pytest.mark.parametrize(
    "spec",
    [
        {"dist": "uniform", "low": 1, "high": 2},
        {"dist": "normal", "mean": 1, "std": 0.1},
        {"dist": "lognormal", "median": 1, "std_log": 0.1},
        {"dist": "triangular", "low": 1, "mode": 1.5, "high": 2},
    ],
)
def test_prior_families(spec):
    priors = [PriorSpec(name="qi", **spec)]
    first, backend = sample_priors(priors, 20, 42, "builtin")
    second, _ = sample_priors(priors, 20, 42, "builtin")
    pd.testing.assert_frame_equal(first, second)
    assert np.isfinite(first.to_numpy()).all()
    assert backend == "builtin.naive-mc"


def test_router_and_report(tmp_path):
    cfg = {
        "analysis": {"type": "probabilistic"},
        "probabilistic": study(),
        "Analysis": {"result_folder": str(tmp_path)},
    }
    outputs = ProductionForecast().router(cfg)["production_forecast"]["outputs"]
    from pathlib import Path

    summary = json.loads(Path(outputs["summary_json"]).read_text())
    assert summary["n_samples"] == 20
    html = Path(outputs["report_html"]).read_text()
    assert "NOT_EVALUATED" in html and "Synthetic example" in html
    assert "<script src=" not in html
    assert "data:image/svg+xml" in html  # Inline vector charts, no network assets.
    assert "Non-exceedance" in html and "qi" in html
    assert len(pd.read_csv(outputs["run_matrix_csv"])) == 20


def test_percentiles_and_negative_constant_ranks():
    """Linear interpolation on [0,10] gives [1,5,9].

    Reversed ranks have rho=-1; constant ranks are undefined (not zero).
    SciPy 1.15.2 spearmanr documentation, ConstantInputWarning.
    """
    from worldenergydata.production.forecast.uq import percentiles, rank_sensitivity

    assert percentiles([0, 10]) == {"p10": 1, "p50": 5, "p90": 9}
    matrix = pd.DataFrame({"x": [1, 2, 3], "fixed": [1, 1, 1], "npv_usd": [3, 2, 1]})
    assert rank_sensitivity(matrix, ["x", "fixed"]) == {"x": -1, "fixed": None}


def test_no_silent_resampling_of_invalid_physics():
    cfg = study()
    cfg["priors"][0].update(low=-2, high=-1)
    with pytest.raises(ValueError, match="qi"):
        ProbabilisticForecast().run(cfg)


def test_shut_in_and_screening():
    """No production if qi <= limit: EUR=0, cash flow=-CAPEX at t=0."""
    cfg = study()
    cfg["base"]["economic_limit"] = 2000
    cfg["minimum_p10_npv_usd"] = -10
    result = ProbabilisticForecast().run(cfg)
    assert result.summary["eur_bbl"] == {"p10": 0, "p50": 0, "p90": 0}
    assert result.summary["npv_usd"] == {"p10": -10, "p50": -10, "p90": -10}
    assert result.summary["screening_status"] == "pass"
    assert result.summary["spearman"]["qi"] is None
    cfg["minimum_p10_npv_usd"] = 0
    assert ProbabilisticForecast().run(cfg).summary["screening_status"] == "fail"


def test_price_deck_and_invalid_deck():
    """First month's price is zero; second month's price doubles.

    Net = -V1 + 3*V2 at zero discount. V1=qi/(2ln2), V2=qi/(4ln2).
    """
    cfg = study()
    cfg["price_multipliers"] = [0, 2]
    result = ProbabilisticForecast().run(cfg)
    expected = -10 + result.run_matrix.qi / (4 * math.log(2))
    np.testing.assert_allclose(result.run_matrix.npv_usd, expected)
    cfg["price_multipliers"] = [1]
    with pytest.raises(ValueError, match="price_multipliers"):
        ProbabilisticForecast().run(cfg)


def test_backend_selection_is_explicit(monkeypatch):
    from worldenergydata.production.forecast import uq

    def missing_engine(name):
        raise ModuleNotFoundError("test missing engine", name="digitalmodel")

    monkeypatch.setattr(uq.importlib, "import_module", missing_engine)
    assert uq.shared_engine("auto") is None
    with pytest.raises(ModuleNotFoundError):
        uq.shared_engine("digitalmodel")

    def broken_engine(name):
        raise ModuleNotFoundError("test missing dependency", name="engine_dependency")

    monkeypatch.setattr(uq.importlib, "import_module", broken_engine)
    with pytest.raises(ModuleNotFoundError):
        uq.shared_engine("auto")


def test_native_engine_if_installed():
    """Exercise the real optional engine contract, rather than a mock sampler."""
    pytest.importorskip("digitalmodel.uncertainty")
    cfg = study()
    cfg["engine"] = "digitalmodel"
    result = ProbabilisticForecast().run(cfg)
    assert result.sampler_used == "digitalmodel.lhs"
    assert result.summary["spearman"]["qi"] == pytest.approx(1)
    assert 1000 <= result.run_matrix.qi.min() < result.run_matrix.qi.max() <= 1100


def test_forward_result_plot_has_no_fitted_statistic():
    adc = ArpsDeclineCurve()
    result = adc.simulate(qi=1000, Di=0.1, b=0.5, economic_limit=100, months=2)
    history = pd.DataFrame({"month": [], "rate_bbl": []})
    assert "not fitted" in adc.plot(history, result).layout.title.text


def test_small_exponent_has_continuous_exponential_limit():
    """As b tends to zero, q(1)=1000*exp(-ln(2))=500 bbl/month.

    ResInsight rate-time equations; no finite perturbation tolerance is a field
    acceptance criterion here, only pytest's numerical approximation default.
    """
    result = ArpsDeclineCurve().simulate(
        qi=1000, Di=math.log(2), b=1e-16, economic_limit=100, months=2
    )
    assert result.forecast_df.rate_bbl.iloc[0] == pytest.approx(500)
    assert result.forecast_df.volume_bbl.iloc[0] == pytest.approx(500 / math.log(2))


@pytest.mark.parametrize("label", ["../escape", "..\\escape"])
def test_output_label_cannot_escape_result_folder(label, tmp_path):
    cfg = {
        "analysis": {"type": "probabilistic"},
        "probabilistic": study(),
        "meta": {"label": label},
        "Analysis": {"result_folder": str(tmp_path)},
    }
    with pytest.raises(ValueError, match="label"):
        ProductionForecast().router(cfg)
    assert list(tmp_path.iterdir()) == []
