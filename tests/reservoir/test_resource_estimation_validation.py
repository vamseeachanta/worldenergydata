"""Independent arithmetic and domain contracts for resource estimation.

All inputs below are synthetic, dimensionless where appropriate. Bounds of zero
and one follow the definitions of fractions and nonnegative volumes. Numerical
comparisons use pytest's floating-point tolerance, not an engineering limit.
"""

import math

import pytest

from worldenergydata.reservoir.resource_estimation import (
    MonteCarloEngine,
    compute_eur,
    compute_ooip,
    run_resource_estimation,
    run_sensitivity_analysis,
)


def constant(value):
    return {"dist": "constant", "value": value}


@pytest.fixture
def inputs():
    """Synthetic unit-acre case: 7758 * 1 * 1 * .5 * .5 / 1 = 1939.5 STB."""
    return {
        "area": constant(1),
        "thickness": constant(1),
        "porosity": constant(0.5),
        "water_saturation": constant(0.5),
        "fvf": constant(1),
        "recovery_factor": constant(0.5),
    }


def test_constant_case_and_audit_metadata(inputs):
    """Hand calculation: 1939.5 * .5 = 969.75 STB for every realization."""
    result = run_resource_estimation(**inputs, n_iterations=4, seed=7)
    for key in ("p10", "p50", "p90", "mean"):
        assert result[key] == 969.75
    assert result["eur_distribution"] == [969.75] * 4
    assert result["ooip_distribution"] == [1939.5] * 4
    assert result["units"] == "STB"
    assert result["n_iterations"] == 4
    assert result["seed"] == 7
    assert result["quantile_method"] == "linear (R7)"
    assert result["reserves_classification"] == "NOT_EVALUATED"


def test_percentiles_use_linear_interpolation():
    """R7 hand calculation for [0,10,20,30]: h=3q.

    PRMS exceedance P90 uses q=.1: h=.3, giving 0+.3*10=3.
    P50: h=1.5 gives 10+.5*10=15. P10: h=2.7 gives 20+.7*10=27.
    Arithmetic mean is (0+10+20+30)/4=15. Input ordering is irrelevant.
    """
    from worldenergydata.reservoir.resource_estimation import summarize_resources

    values = [30, 0, 20, 10]
    result = summarize_resources(values)
    assert result == pytest.approx({"p90": 3, "p50": 15, "p10": 27, "mean": 15})
    assert values == [30, 0, 20, 10]


def test_single_realization(inputs):
    """A point distribution has identical mean and every percentile."""
    result = run_resource_estimation(**inputs, n_iterations=1)
    assert result["p90"] == result["p50"] == result["p10"] == 969.75


@pytest.mark.parametrize("values", [[], [-1], [math.nan], [math.inf]])
def test_invalid_resource_samples(values):
    from worldenergydata.reservoir.resource_estimation import summarize_resources

    with pytest.raises(ValueError):
        summarize_resources(values)


@pytest.mark.parametrize("count", [0, -1, 1.5, True])
def test_invalid_iteration_count(count):
    with pytest.raises(ValueError, match="n_iterations"):
        MonteCarloEngine(count)


@pytest.mark.parametrize(
    "args",
    [
        (-1, 1, 0.5, 0.5, 1),
        (1, -1, 0.5, 0.5, 1),
        (1, 1, -0.1, 0.5, 1),
        (1, 1, 1.1, 0.5, 1),
        (1, 1, 0.5, -0.1, 1),
        (1, 1, 0.5, 1.1, 1),
        (1, 1, 0.5, 0.5, 0),
        (1, 1, 0.5, 0.5, -1),
        (math.inf, 1, 0.5, 0.5, 1),
        (1, math.nan, 0.5, 0.5, 1),
    ],
)
def test_invalid_volumetric_inputs(args):
    with pytest.raises(ValueError):
        compute_ooip(*args)


@pytest.mark.parametrize(
    "ooip,rf", [(-1, 0.5), (1, -0.1), (1, 1.1), (math.inf, 0.5), (1, math.nan)]
)
def test_invalid_recovery_inputs(ooip, rf):
    with pytest.raises(ValueError):
        compute_eur(ooip, rf)


def test_fraction_boundaries():
    """Zero pore or hydrocarbon fraction yields zero; full recovery yields OOIP."""
    assert compute_ooip(1, 1, 0, 0, 1) == 0
    assert compute_ooip(1, 1, 1, 1, 1) == 0
    assert compute_eur(100, 0) == 0
    assert compute_eur(100, 1) == 100


@pytest.mark.parametrize(
    "method,args",
    [
        ("add_uniform", (2, 1)),
        ("add_triangular", (1, 3, 2)),
        ("add_triangular", (2, 2, 1)),
        ("add_normal", (1, -1)),
        ("add_normal", (math.nan, 1)),
        ("add_uniform", (0, math.inf)),
    ],
)
def test_invalid_distribution_parameters(method, args):
    with pytest.raises(ValueError):
        getattr(MonteCarloEngine(2), method)("x", *args)


def test_replacement_invalidates_cache_and_samples_are_defensive():
    engine = MonteCarloEngine(2, seed=7)
    engine.add_uniform("x", 1, 1)
    first = engine.sample("x")
    first[0] = -99
    assert engine.sample("x") == [1, 1]
    engine.add_uniform("x", 2, 2)
    assert engine.sample("x") == [2, 2]


@pytest.mark.parametrize(
    "spec",
    [
        {"dist": "unknown"},
        {},
        {"dist": "uniform", "low": 0},
        {"dist": "constant", "value": 1, "typo": 1},
    ],
)
def test_bad_spec_is_named(inputs, spec):
    inputs["area"] = spec
    with pytest.raises(ValueError, match="area"):
        run_resource_estimation(**inputs, n_iterations=2)


@pytest.mark.parametrize(
    "name,spec",
    [
        ("porosity", {"dist": "uniform", "low": 0, "high": 1.1}),
        ("water_saturation", constant(-0.1)),
        ("recovery_factor", constant(1.1)),
        ("fvf", constant(0)),
        ("area", {"dist": "uniform", "low": -1, "high": 1}),
    ],
)
def test_unphysical_support_rejected(inputs, name, spec):
    inputs[name] = spec
    with pytest.raises(ValueError, match=name):
        run_resource_estimation(**inputs, n_iterations=2)


def test_unphysical_normal_draw_is_rejected_without_clipping(inputs):
    inputs["porosity"] = {"dist": "normal", "mean": -1, "std": 0}
    with pytest.raises(ValueError, match="porosity"):
        run_resource_estimation(**inputs, n_iterations=2)


def test_simulation_uses_joint_realizations(inputs, monkeypatch):
    """Area [1,2,3,4] times 969.75 gives EUR [969.75,...,3879].

    R7 h=.3,1.5,2.7 gives 1260.675,2424.375,3588.075 STB;
    mean = 969.75*(1+2+3+4)/4 = 2424.375 STB.
    """
    original = MonteCarloEngine.sample

    def sample(engine, name):
        return [1, 2, 3, 4] if name == "area" else original(engine, name)

    monkeypatch.setattr(MonteCarloEngine, "sample", sample)
    result = run_resource_estimation(**inputs, n_iterations=4)
    assert result["p90"] == pytest.approx(1260.675)
    assert result["p50"] == pytest.approx(2424.375)
    assert result["p10"] == pytest.approx(3588.075)
    assert result["mean"] == pytest.approx(2424.375)


def test_seeded_full_run_is_reproducible(inputs):
    inputs["area"] = {"dist": "triangular", "low": 1, "mode": 2, "high": 3}
    inputs["thickness"] = {"dist": "normal", "mean": 1, "std": 0}
    inputs["recovery_factor"] = {"dist": "uniform", "low": 0, "high": 1}
    first = run_resource_estimation(**inputs, n_iterations=20, seed=7)
    assert first == run_resource_estimation(**inputs, n_iterations=20, seed=7)
    assert first != run_resource_estimation(**inputs, n_iterations=20, seed=8)


@pytest.fixture
def base_inputs():
    return {
        "area": 1,
        "thickness": 1,
        "porosity": 0.5,
        "water_saturation": 0.5,
        "fvf": 1,
        "recovery_factor": 0.5,
    }


def test_sensitivity_preserves_endpoint_direction_and_sorts(base_inputs):
    """Base=969.75. Sw 0..1 gives 1939.5..0 (swing 1939.5).

    Area 1..2 gives 969.75..1939.5 (swing 969.75). Largest swing first.
    """
    result = run_sensitivity_analysis(
        base_inputs, {"area": (1, 2), "water_saturation": (0, 1)}
    )
    assert [row["parameter"] for row in result] == ["water_saturation", "area"]
    assert result[0]["low_eur"] == 1939.5
    assert result[0]["high_eur"] == 0
    assert result[0]["swing"] == 1939.5
    assert result[0]["base_eur"] == 969.75
    assert base_inputs["water_saturation"] == 0.5


@pytest.mark.parametrize(
    "ranges",
    [{"typo": (1, 2)}, {"area": (2, 1)}, {"porosity": (0, 2)}, {"fvf": (0, 1)}],
)
def test_invalid_sensitivity_ranges(base_inputs, ranges):
    with pytest.raises(ValueError):
        run_sensitivity_analysis(base_inputs, ranges)


def test_overflow_rejected():
    with pytest.raises(ValueError, match="finite"):
        compute_ooip(1e308, 1e308, 1, 0, 1)
    with pytest.raises(ValueError, match="finite"):
        compute_eur(math.inf, 1)


def test_sampler_arithmetic(monkeypatch):
    """Synthetic uniform [2,6]: x=2+u*(6-2); u=0,.25,.5 gives 2,3,4.

    Symmetric triangular [0,4] with mode 2 has inverse CDF at u=.125,.5,.875
    equal to sqrt(8*.125)=1, 2, and 4-sqrt(8*.125)=3. These are independent
    distribution identities, not expectations obtained from sampled results.
    """
    engine = MonteCarloEngine(3)
    engine.add_uniform("uniform", 2, 6)
    values = iter([0, 0.25, 0.5])
    monkeypatch.setattr(engine._rng, "random", lambda: next(values))
    assert engine.sample("uniform") == [2, 3, 4]
    engine.add_triangular("triangle", 0, 2, 4)
    values = iter([0.125, 0.5, 0.875])
    assert engine.sample("triangle") == [1, 2, 3]
    engine.add_normal("point", 2, 0)
    monkeypatch.setattr(engine._rng, "random", lambda: 0.5)
    assert engine.sample("point") == [2, 2, 2]


def test_unknown_sample_name():
    with pytest.raises(ValueError, match="missing"):
        MonteCarloEngine(1).sample("missing")


def test_invalid_specs_are_validated_before_sampling(inputs, monkeypatch):
    def unexpected_sample(*args):
        pytest.fail("invalid bounded support must be rejected before sampling")

    monkeypatch.setattr(MonteCarloEngine, "sample", unexpected_sample)
    inputs["recovery_factor"] = {"dist": "uniform", "low": 0, "high": 2}
    with pytest.raises(ValueError, match="recovery_factor"):
        run_resource_estimation(**inputs, n_iterations=1)
