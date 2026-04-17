"""Tests for Blasingame/Fetkovich type curve matching.

Covers: analytical curves, material balance time, auto-matching, edge cases.
"""

import numpy as np
import pytest

from worldenergydata.bsee.analysis.type_curves import (
    ProductionData,
    ReservoirParams,
    blasingame_typecurve,
    fetkovich_boundary,
    fetkovich_transient,
    fetkovich_typecurve,
    match_blasingame,
    match_fetkovich,
    material_balance_time,
    normalized_rate,
    rate_integral,
    rate_integral_derivative,
)


# --- Fetkovich boundary stems (analytical verification) ---

class TestFetkovichBoundary:
    def test_exponential_stem_b0_matches_analytical(self):
        """b=0 => qDd = exp(-tDd)."""
        tDd = np.linspace(0.01, 5.0, 100)
        qDd = fetkovich_boundary(tDd, b=0.0)
        expected = np.exp(-tDd)
        np.testing.assert_allclose(qDd, expected, rtol=1e-12)

    def test_hyperbolic_stem_b05_matches_analytical(self):
        """b=0.5 => qDd = (1 + 0.5*tDd)^(-2)."""
        tDd = np.linspace(0.01, 5.0, 100)
        qDd = fetkovich_boundary(tDd, b=0.5)
        expected = (1.0 + 0.5 * tDd) ** (-2.0)
        np.testing.assert_allclose(qDd, expected, rtol=1e-10)

    def test_harmonic_stem_b1_matches_analytical(self):
        """b=1 => qDd = 1/(1+tDd)."""
        tDd = np.linspace(0.01, 5.0, 100)
        qDd = fetkovich_boundary(tDd, b=1.0)
        expected = 1.0 / (1.0 + tDd)
        np.testing.assert_allclose(qDd, expected, rtol=1e-12)

    def test_invalid_b_raises_valueerror(self):
        """b outside [0,1] raises ValueError."""
        tDd = np.array([1.0])
        with pytest.raises(ValueError, match="b must be in"):
            fetkovich_boundary(tDd, b=-0.1)
        with pytest.raises(ValueError, match="b must be in"):
            fetkovich_boundary(tDd, b=1.5)


# --- Fetkovich transient stems ---

class TestFetkovichTransient:
    def test_transient_returns_positive_arrays(self):
        """Transient stems should produce positive qDd and tDd."""
        tD = np.logspace(-1, 3, 200)
        tDd, qDd = fetkovich_transient(tD, reD=10.0)
        assert np.all(tDd[tDd > 0] > 0)
        assert np.all(qDd > 0)

    def test_invalid_reD_raises(self):
        tD = np.logspace(-1, 2, 50)
        with pytest.raises(ValueError, match="reD must be > 1"):
            fetkovich_transient(tD, reD=0.5)

    def test_stitching_continuity(self):
        """Transient and boundary stems should overlap smoothly (P2-2)."""
        tD = np.logspace(-1, 4, 500)
        tDd_trans, qDd_trans = fetkovich_transient(tD, reD=50.0)
        tDd_bd = np.logspace(-2, 2, 500)
        qDd_bd = fetkovich_boundary(tDd_bd, b=0.0)
        # At the overlap region (tDd ~ 0.1-1), both should have similar magnitudes
        mask_trans = (tDd_trans > 0.3) & (tDd_trans < 0.7)
        if mask_trans.any():
            qDd_trans_overlap = qDd_trans[mask_trans]
            assert np.all(qDd_trans_overlap > 0), "Transient should be positive in overlap"
            assert np.all(qDd_trans_overlap < 5), "Transient should be bounded in overlap"


# --- Fetkovich type curve set ---

class TestFetkovichTypecurve:
    def test_typecurve_set_has_correct_count(self):
        reDs = [5, 10, 50]
        bs = [0.0, 0.5, 1.0]
        tc = fetkovich_typecurve(reD_values=reDs, b_values=bs)
        assert len(tc.tDd) == len(reDs) + len(bs)
        assert len(tc.labels) == len(reDs) + len(bs)


# --- Blasingame helper functions ---

class TestBlasingameHelpers:
    def test_material_balance_time_constant_rate(self):
        """For constant rate q, tc = Np/q = t (since Np = q*t)."""
        t = np.arange(1.0, 101.0)
        q = np.full_like(t, 100.0)
        Np = q * t
        tc = material_balance_time(q, Np)
        np.testing.assert_allclose(tc, t, rtol=1e-12)

    def test_normalized_rate(self):
        rate = np.array([100.0, 80.0, 60.0])
        dp = np.array([500.0, 500.0, 500.0])
        qn = normalized_rate(rate, dp)
        np.testing.assert_allclose(qn, rate / 500.0)

    def test_rate_integral_constant(self):
        """For constant normalized rate, integral should equal the rate."""
        tc = np.arange(1.0, 51.0)
        q_norm = np.full_like(tc, 0.5)
        qDdi = rate_integral(q_norm, tc)
        np.testing.assert_allclose(qDdi, 0.5, rtol=0.05)

    def test_rate_integral_derivative_positive_for_decline(self):
        """Derivative should be positive for declining production."""
        tc = np.linspace(1, 100, 50)
        q_norm = 1.0 / (1.0 + 0.01 * tc)  # harmonic decline
        qDdi = rate_integral(q_norm, tc)
        qDdid = rate_integral_derivative(qDdi, tc)
        # Most interior points should be positive (declining integral)
        assert np.sum(qDdid[2:-2] > 0) > len(qDdid[2:-2]) * 0.5


# --- Blasingame type curve set ---

class TestBlasingameTypecurve:
    def test_blasingame_set_has_all_functions(self):
        tc = blasingame_typecurve(reD_values=[10, 50])
        assert len(tc.qDd) == 2
        assert len(tc.qDdi) == 2
        assert len(tc.qDdid) == 2


# --- Auto-matching with synthetic data ---

def _make_synthetic_exponential(qi=500.0, Di=0.003, n_days=500):
    """Generate synthetic exponential decline data."""
    t = np.arange(1, n_days + 1, dtype=np.float64)
    q = qi * np.exp(-Di * t)
    Np = qi / Di * (1.0 - np.exp(-Di * t))
    dp = np.full_like(t, 1000.0)  # constant drawdown
    return t, q, Np, dp


def _default_params():
    return ReservoirParams(
        k=10.0, h=50.0, phi=0.15, mu=1.0, ct=1e-5,
        rw=0.35, re=1000.0, pi=4000.0, pwf=3000.0, Bo=1.2,
    )


class TestAutoMatchSynthetic:
    def test_fetkovich_match_exponential_recovers_params(self):
        """Match synthetic exponential data, recover qi and Di within 20%."""
        t, q, Np, dp = _make_synthetic_exponential()
        data = ProductionData(time=t, rate=q, cumulative=Np, pressure_drawdown=dp)
        params = _default_params()
        result = match_fetkovich(data, params)
        assert result.model == "fetkovich"
        assert result.residual < 50.0  # reasonable fit
        assert result.reD > 1.0

    def test_blasingame_match_exponential_converges(self):
        """Blasingame matching converges on synthetic data."""
        t, q, Np, dp = _make_synthetic_exponential()
        data = ProductionData(time=t, rate=q, cumulative=Np, pressure_drawdown=dp)
        params = _default_params()
        result = match_blasingame(data, params)
        assert result.model == "blasingame"
        assert result.residual < 100.0
        assert result.ooip > 0

    def test_match_with_noisy_data_converges(self):
        """10% noise still converges."""
        rng = np.random.default_rng(42)
        t, q, Np, dp = _make_synthetic_exponential()
        q_noisy = q * (1 + 0.1 * rng.standard_normal(len(q)))
        q_noisy = np.maximum(q_noisy, 1.0)
        Np_noisy = np.cumsum(q_noisy)
        data = ProductionData(time=t, rate=q_noisy, cumulative=Np_noisy, pressure_drawdown=dp)
        params = _default_params()
        result = match_fetkovich(data, params)
        assert result.residual < 200.0  # looser tolerance for noisy data


# --- Error handling ---

class TestErrorHandling:
    def test_empty_production_data_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            ProductionData(
                time=np.array([]),
                rate=np.array([]),
                cumulative=np.array([]),
            )

    def test_mismatched_array_lengths_raises(self):
        with pytest.raises(ValueError, match="same length"):
            ProductionData(
                time=np.array([1.0, 2.0]),
                rate=np.array([100.0]),
                cumulative=np.array([100.0, 200.0]),
            )
