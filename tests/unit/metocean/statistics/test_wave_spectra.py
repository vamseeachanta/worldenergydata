"""
ABOUTME: Tests for WaveSpectra (JONSWAP, Torsethaugen, spectral moments).
ABOUTME: Uses parametric inputs — no live API calls.
"""

import numpy as np
import pandas as pd
import pytest
import plotly.graph_objects as go

from worldenergydata.metocean.statistics.wave_spectra import (
    SpectralResult,
    WaveSpectra,
)


class TestSpectralResult:
    def test_spectral_result_fields(self):
        freqs = np.linspace(0.05, 0.5, 100)
        energy = np.exp(-freqs)
        result = SpectralResult(
            frequencies=freqs,
            energy=energy,
            spectrum_type="JONSWAP",
            hs=3.5,
            tp=10.0,
            spectral_moments={"m0": 0.076, "m2": 0.012},
        )
        assert result.spectrum_type == "JONSWAP"
        assert result.hs == pytest.approx(3.5, rel=0.001)
        assert result.tp == pytest.approx(10.0, rel=0.001)
        assert "m0" in result.spectral_moments


class TestJONSWAP:
    def setup_method(self):
        self.ws = WaveSpectra()

    def test_jonswap_returns_spectral_result(self):
        result = self.ws.jonswap(hs=3.5, tp=10.0)
        assert isinstance(result, SpectralResult)

    def test_jonswap_spectrum_type_label(self):
        result = self.ws.jonswap(hs=3.5, tp=10.0)
        assert result.spectrum_type == "JONSWAP"

    def test_jonswap_frequencies_positive(self):
        result = self.ws.jonswap(hs=3.5, tp=10.0)
        assert (result.frequencies > 0).all()

    def test_jonswap_energy_non_negative(self):
        result = self.ws.jonswap(hs=3.5, tp=10.0)
        assert (result.energy >= 0).all()

    def test_jonswap_energy_sum_nonzero(self):
        result = self.ws.jonswap(hs=3.5, tp=10.0)
        assert result.energy.sum() > 0

    def test_jonswap_has_spectral_moments(self):
        result = self.ws.jonswap(hs=3.5, tp=10.0)
        assert isinstance(result.spectral_moments, dict)
        assert "m0" in result.spectral_moments

    def test_jonswap_m0_relates_to_hs(self):
        """Hs ≈ 4*sqrt(m0)."""
        result = self.ws.jonswap(hs=3.5, tp=10.0)
        m0 = result.spectral_moments["m0"]
        hs_from_m0 = 4.0 * np.sqrt(m0)
        assert hs_from_m0 == pytest.approx(3.5, rel=0.15)  # 15% tolerance

    def test_jonswap_custom_frequency_range(self):
        freqs = np.linspace(0.02, 0.6, 200)
        result = self.ws.jonswap(hs=3.5, tp=10.0, frequencies=freqs)
        assert len(result.frequencies) == 200

    def test_jonswap_custom_gamma(self):
        result = self.ws.jonswap(hs=3.5, tp=10.0, gamma=3.3)
        assert isinstance(result, SpectralResult)


class TestTorsethaugen:
    def setup_method(self):
        self.ws = WaveSpectra()

    def test_torsethaugen_returns_spectral_result(self):
        result = self.ws.torsethaugen(hs=4.0, tp=12.0)
        assert isinstance(result, SpectralResult)

    def test_torsethaugen_spectrum_type_label(self):
        result = self.ws.torsethaugen(hs=4.0, tp=12.0)
        assert result.spectrum_type == "Torsethaugen"

    def test_torsethaugen_energy_non_negative(self):
        result = self.ws.torsethaugen(hs=4.0, tp=12.0)
        assert (result.energy >= 0).all()

    def test_torsethaugen_has_frequencies(self):
        result = self.ws.torsethaugen(hs=4.0, tp=12.0)
        assert len(result.frequencies) > 0


class TestSpectralMoments:
    def setup_method(self):
        self.ws = WaveSpectra()

    def test_spectral_moments_dict_keys(self):
        result = self.ws.jonswap(hs=3.5, tp=10.0)
        moments = result.spectral_moments
        assert "m0" in moments

    def test_spectral_moments_m0_positive(self):
        result = self.ws.jonswap(hs=3.5, tp=10.0)
        assert result.spectral_moments["m0"] > 0


class TestWaveSpectraPlot:
    def setup_method(self):
        self.ws = WaveSpectra()

    def test_plot_spectrum_returns_plotly_figure(self):
        result = self.ws.jonswap(hs=3.5, tp=10.0)
        fig = self.ws.plot_spectrum(result)
        assert isinstance(fig, go.Figure)

    def test_plot_spectrum_has_traces(self):
        result = self.ws.jonswap(hs=3.5, tp=10.0)
        fig = self.ws.plot_spectrum(result)
        assert len(fig.data) >= 1

    def test_plot_compare_spectra(self):
        r1 = self.ws.jonswap(hs=3.5, tp=10.0)
        r2 = self.ws.torsethaugen(hs=3.5, tp=10.0)
        fig = self.ws.plot_spectrum(r1, overlay=r2)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 2
