"""
ABOUTME: Joint probability model for Hs-Tp (or any two-variable) analysis.
ABOUTME: Wraps metocean-stats joint_distribution_Hs_Tp and calculate_scatter.

Uses real metocean-stats library (v1.1.9) as the statistical backend.
All visualisations use Plotly — metocean-stats matplotlib outputs are converted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import metocean_stats.stats as ms
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


@dataclass
class JointModel:
    """Container for a fitted joint probability model."""

    marginal_hs: dict
    """Parameters of the fitted marginal Hs distribution."""
    conditional_tp: dict
    """Parameters of the conditional Tp|Hs distribution."""
    n_samples: int
    """Number of data points used to fit the model."""
    hs_samples: Optional[np.ndarray] = None
    """Monte-Carlo Hs samples from the fitted model."""
    tp_samples: Optional[np.ndarray] = None
    """Monte-Carlo Tp samples from the fitted model."""
    _raw_result: Optional[tuple] = field(default=None, repr=False)
    """Raw tuple returned by metocean-stats joint_distribution_Hs_Tp."""


class JointProbabilityModel:
    """
    Hs-Tp (or any two-variable) joint probability via metocean-stats CMA.

    Wraps ``metocean_stats.stats.joint_distribution_Hs_Tp`` and
    ``metocean_stats.stats.calculate_scatter`` with a clean API and
    Plotly visualisation.

    Examples
    --------
    >>> jpm = JointProbabilityModel()
    >>> model = jpm.fit(hs_series, tp_series)
    >>> df = jpm.scatter_diagram(hs_series, tp_series)
    >>> fig = jpm.plot_scatter(hs_series, tp_series)
    """

    def __init__(
        self,
        hs_bin_size: float = 0.5,
        tp_bin_size: float = 1.0,
    ) -> None:
        self._hs_bin_size = hs_bin_size
        self._tp_bin_size = tp_bin_size

    # ------------------------------------------------------------------
    # Fitting
    # ------------------------------------------------------------------

    def fit(
        self,
        hs: pd.Series,
        tp: pd.Series,
        periods: list[int] = None,
    ) -> JointModel:
        """
        Fit a conditional Hs-Tp joint model using metocean-stats.

        Parameters
        ----------
        hs:
            Significant wave height time series.
        tp:
            Peak period time series (same index as hs).
        periods:
            Return periods for the joint distribution contours.

        Returns
        -------
        JointModel
        """
        if periods is None:
            periods = [50, 100]

        df = pd.DataFrame({"hs": hs.values, "tp": tp.values}, index=hs.index)

        # metocean-stats returns a 12-element tuple
        raw = ms.joint_distribution_Hs_Tp(
            df,
            var_hs="hs",
            var_tp="tp",
            periods=periods,
        )

        # Decode the tuple (indices documented in aux_funcs.py)
        a1, b1, a2, b2, mu_tp, sigma_tp = raw[0], raw[1], raw[2], raw[3], raw[4], raw[5]
        hs_samples = raw[6]
        tp_samples = raw[7]

        marginal_hs = {
            "distribution": "Weibull_2P",
            "params": (float(a1), float(b1)),
            "shape_a2": float(a2),
            "shape_b2": float(b2),
        }
        conditional_tp = {
            "model": "lognormal_conditional",
            "mu": float(mu_tp),
            "sigma": float(sigma_tp),
        }

        return JointModel(
            marginal_hs=marginal_hs,
            conditional_tp=conditional_tp,
            n_samples=len(hs),
            hs_samples=hs_samples,
            tp_samples=tp_samples,
            _raw_result=raw,
        )

    # ------------------------------------------------------------------
    # Scatter diagram
    # ------------------------------------------------------------------

    def scatter_diagram(
        self,
        hs: pd.Series,
        tp: pd.Series,
        hs_bins: Optional[np.ndarray] = None,
        tp_bins: Optional[np.ndarray] = None,
    ) -> pd.DataFrame:
        """
        Compute a 2D Hs-Tp occurrence table in percent.

        Parameters
        ----------
        hs:
            Significant wave height series.
        tp:
            Peak period series.
        hs_bins:
            Custom bin edges for Hs. If None, bin size from constructor is used.
        tp_bins:
            Custom bin edges for Tp. If None, bin size from constructor is used.

        Returns
        -------
        pd.DataFrame
            Percentage occurrence table. Rows = Hs bins, columns = Tp bins.
            Values sum to 100.0.
        """
        df = pd.DataFrame({"hs": hs.values, "tp": tp.values}, index=hs.index)

        if hs_bins is not None:
            hs_step = (
                float(hs_bins[1] - hs_bins[0])
                if len(hs_bins) > 1
                else self._hs_bin_size
            )
        else:
            hs_step = self._hs_bin_size

        if tp_bins is not None:
            tp_step = (
                float(tp_bins[1] - tp_bins[0])
                if len(tp_bins) > 1
                else self._tp_bin_size
            )
        else:
            tp_step = self._tp_bin_size

        # metocean-stats returns raw counts
        sd = ms.calculate_scatter(df, "hs", hs_step, "tp", tp_step)

        # Convert to percentage
        total = sd.values.sum()
        if total > 0:
            pct = (sd / total * 100.0).round(3)
        else:
            pct = sd.astype(float)

        return pct

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def plot_scatter(self, hs: pd.Series, tp: pd.Series) -> go.Figure:
        """
        Plotly Hs-Tp scatter density plot with marginal histograms.

        Parameters
        ----------
        hs:
            Significant wave height series.
        tp:
            Peak period series.

        Returns
        -------
        plotly.graph_objects.Figure
        """
        hs_vals = hs.values
        tp_vals = tp.values

        # Create 2×2 subplot grid for scatter + marginals
        fig = make_subplots(
            rows=2,
            cols=2,
            column_widths=[0.8, 0.2],
            row_heights=[0.2, 0.8],
            shared_xaxes=True,
            shared_yaxes=True,
        )

        # Main scatter density (hexbin approximation via 2D histogram)
        fig.add_trace(
            go.Histogram2dContour(
                x=tp_vals,
                y=hs_vals,
                colorscale="Blues",
                name="Density",
                showscale=True,
                ncontours=20,
            ),
            row=2,
            col=1,
        )

        # Top marginal: Tp
        fig.add_trace(
            go.Histogram(
                x=tp_vals,
                name="Tp distribution",
                marker_color="steelblue",
                showlegend=False,
                opacity=0.7,
            ),
            row=1,
            col=1,
        )

        # Right marginal: Hs
        fig.add_trace(
            go.Histogram(
                y=hs_vals,
                name="Hs distribution",
                marker_color="darkorange",
                showlegend=False,
                opacity=0.7,
            ),
            row=2,
            col=2,
        )

        fig.update_layout(
            title="Hs-Tp Joint Distribution",
            template="plotly_white",
            xaxis3=dict(title="Tp (s)"),
            yaxis3=dict(title="Hs (m)"),
        )
        return fig
