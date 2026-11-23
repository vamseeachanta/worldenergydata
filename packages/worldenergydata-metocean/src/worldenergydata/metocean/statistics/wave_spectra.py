"""
ABOUTME: Wave spectra computation — JONSWAP, Torsethaugen, and spectral moments.
ABOUTME: Wraps metocean-stats spec_funcs with a clean API and Plotly visualisation.

Uses real metocean-stats library (v1.1.9).
All visualisations use Plotly — not matplotlib.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import metocean_stats.stats.spec_funcs as spec_funcs
import numpy as np
import plotly.graph_objects as go

# Default frequency vector (Hz): 0.02–0.5 Hz in 200 steps
_DEFAULT_FREQUENCIES = np.linspace(0.02, 0.5, 200)


@dataclass
class SpectralResult:
    """Container for a computed wave spectrum."""

    frequencies: np.ndarray
    """Frequency array (Hz)."""
    energy: np.ndarray
    """Spectral energy density (m²/Hz)."""
    spectrum_type: str
    """'JONSWAP' or 'Torsethaugen'."""
    hs: float
    """Significant wave height (m) used as input."""
    tp: float
    """Peak period (s) used as input."""
    spectral_moments: dict[str, float] = field(default_factory=dict)
    """Computed spectral moments (m0, m1, m2, ...)."""


class WaveSpectra:
    """
    Wave spectra computation wrapping metocean-stats spec_funcs.

    Supports JONSWAP and Torsethaugen spectra with spectral moment
    calculation and Plotly visualisation.

    Examples
    --------
    >>> ws = WaveSpectra()
    >>> result = ws.jonswap(hs=3.5, tp=10.0)
    >>> fig = ws.plot_spectrum(result)
    """

    # ------------------------------------------------------------------
    # Spectrum computation
    # ------------------------------------------------------------------

    def jonswap(
        self,
        hs: float,
        tp: float,
        frequencies: Optional[np.ndarray] = None,
        gamma: float | str = "fit",
        sigma_low: float = 0.07,
        sigma_high: float = 0.09,
    ) -> SpectralResult:
        """
        Compute JONSWAP wave spectrum.

        Parameters
        ----------
        hs:
            Significant wave height (m).
        tp:
            Peak period (s).
        frequencies:
            Frequency array (Hz). Defaults to 0.02–0.5 Hz in 200 steps.
        gamma:
            Peak enhancement factor. 'fit' uses the empirical Hasselmann formula.
        sigma_low, sigma_high:
            Spectral width parameters.

        Returns
        -------
        SpectralResult
        """
        f = frequencies if frequencies is not None else _DEFAULT_FREQUENCIES.copy()

        energy = spec_funcs.jonswap(
            f=f,
            hs=hs,
            tp=tp,
            gamma=gamma,
            sigma_low=sigma_low,
            sigma_high=sigma_high,
        )

        moments = self._compute_moments(f, energy)

        return SpectralResult(
            frequencies=f,
            energy=energy,
            spectrum_type="JONSWAP",
            hs=hs,
            tp=tp,
            spectral_moments=moments,
        )

    def torsethaugen(
        self,
        hs: float,
        tp: float,
        frequencies: Optional[np.ndarray] = None,
    ) -> SpectralResult:
        """
        Compute Torsethaugen double-peaked wave spectrum.

        Parameters
        ----------
        hs:
            Significant wave height (m).
        tp:
            Peak period (s).
        frequencies:
            Frequency array (Hz). Defaults to 0.02–0.5 Hz in 200 steps.

        Returns
        -------
        SpectralResult
        """
        f = frequencies if frequencies is not None else _DEFAULT_FREQUENCIES.copy()

        energy = spec_funcs.torsethaugen(f=f, hs=hs, tp=tp)

        moments = self._compute_moments(f, energy)

        return SpectralResult(
            frequencies=f,
            energy=energy,
            spectrum_type="Torsethaugen",
            hs=hs,
            tp=tp,
            spectral_moments=moments,
        )

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def plot_spectrum(
        self,
        result: SpectralResult,
        overlay: Optional[SpectralResult] = None,
    ) -> go.Figure:
        """
        Plotly 1-D wave spectrum plot.

        Parameters
        ----------
        result:
            Primary SpectralResult to plot.
        overlay:
            Optional second SpectralResult to overlay for comparison.

        Returns
        -------
        plotly.graph_objects.Figure
        """
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=result.frequencies,
                y=result.energy,
                mode="lines",
                name=f"{result.spectrum_type} (Hs={result.hs:.1f}m, Tp={result.tp:.1f}s)",
                line=dict(color="steelblue", width=2),
            )
        )

        if overlay is not None:
            fig.add_trace(
                go.Scatter(
                    x=overlay.frequencies,
                    y=overlay.energy,
                    mode="lines",
                    name=f"{overlay.spectrum_type} (Hs={overlay.hs:.1f}m, Tp={overlay.tp:.1f}s)",
                    line=dict(color="darkorange", width=2, dash="dash"),
                )
            )

        m0 = result.spectral_moments.get("m0", float("nan"))
        hs_check = 4.0 * np.sqrt(m0) if not np.isnan(m0) else float("nan")

        annotation = (
            f"m₀={m0:.4f} m², Hs_check={hs_check:.2f} m" if not np.isnan(m0) else ""
        )

        fig.update_layout(
            title=dict(text=f"{result.spectrum_type} Wave Spectrum — {annotation}"),
            xaxis=dict(title="Frequency (Hz)"),
            yaxis=dict(title="Spectral Energy Density (m²/Hz)"),
            legend=dict(x=0.7, y=0.99),
            template="plotly_white",
        )
        return fig

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_moments(
        frequencies: np.ndarray,
        energy: np.ndarray,
    ) -> dict[str, float]:
        """
        Compute spectral moments via numerical integration.

        m_n = ∫ f^n · S(f) df

        Parameters
        ----------
        frequencies:
            Frequency array (Hz).
        energy:
            Spectral energy density array (m²/Hz).

        Returns
        -------
        dict with keys 'm0', 'm1', 'm2'.
        """
        df = np.diff(frequencies)
        # Use trapezoidal integration
        f_mid = (frequencies[:-1] + frequencies[1:]) / 2.0
        e_mid = (energy[:-1] + energy[1:]) / 2.0

        m0 = float(np.sum(e_mid * df))
        m1 = float(np.sum(f_mid * e_mid * df))
        m2 = float(np.sum(f_mid**2 * e_mid * df))

        return {"m0": max(0.0, m0), "m1": max(0.0, m1), "m2": max(0.0, m2)}
