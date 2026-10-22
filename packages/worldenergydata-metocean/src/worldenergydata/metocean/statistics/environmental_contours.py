"""
ABOUTME: IFORM/ISORM transforms and explicitly labelled backend contours.
ABOUTME: Derives contours from the JointModel fitted by JointProbabilityModel.

Uses normal-space transforms and the fitted tabulated marginal distribution.
All visualisations use Plotly.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.integrate import cumulative_trapezoid
from scipy.stats import chi2, norm, weibull_min

from worldenergydata.metocean.statistics.backend import JointBackendResult
from worldenergydata.metocean.statistics.joint_probability import JointModel


@dataclass
class ContourResult:
    """Container for an environmental contour result."""

    method: str
    """'IFORM', 'ISORM', or 'backend_iso_density'."""
    return_period: int
    """Return period in years."""
    hs_values: np.ndarray
    """Hs coordinates of the contour."""
    tp_values: np.ndarray
    """Tp coordinates of the contour."""


class EnvironmentalContour:
    """
    IFORM and ISORM environmental contour computation.

    Leverages the joint model fitted by ``JointProbabilityModel.fit``.
    IFORM/ISORM use the normalized tabulated Hs marginal and conditional
    lognormal model. Backend iso-density curves are available separately;
    they are neither IFORM nor ISORM. See the optional-backends guide for
    numerical and engineering validation limits.

    Examples
    --------
    >>> ec = EnvironmentalContour()
    >>> contour = ec.iform(joint_model, return_period=50)
    >>> fig = ec.plot_contour(contour, data=df)
    """

    def __init__(self, state_duration_hours: float = 3.0) -> None:
        """
        Parameters
        ----------
        state_duration_hours:
            Duration of each sea state in hours (commonly 1 or 3).
        """
        if not np.isfinite(state_duration_hours) or state_duration_hours <= 0:
            raise ValueError("state_duration_hours must be finite and positive")
        self._state_duration = state_duration_hours

    # ------------------------------------------------------------------
    # Contour computation
    # ------------------------------------------------------------------

    def iform(
        self,
        joint_model: JointModel,
        return_period: int = 50,
    ) -> ContourResult:
        """
        Compute IFORM (Inverse First-Order Reliability Method) contour.

        Parameters
        ----------
        joint_model:
            Fitted JointModel from JointProbabilityModel.fit().
        return_period:
            Return period in years.

        Returns
        -------
        ContourResult
        """
        hs_contour, tp_contour = self._compute_contour(
            joint_model, return_period, method="IFORM"
        )
        return ContourResult(
            method="IFORM",
            return_period=return_period,
            hs_values=hs_contour,
            tp_values=tp_contour,
        )

    def isorm(
        self,
        joint_model: JointModel,
        return_period: int = 50,
    ) -> ContourResult:
        """
        Compute ISORM (Inverse Second-Order Reliability Method) contour.

        Parameters
        ----------
        joint_model:
            Fitted JointModel from JointProbabilityModel.fit().
        return_period:
            Return period in years.

        Returns
        -------
        ContourResult
        """
        hs_contour, tp_contour = self._compute_contour(
            joint_model, return_period, method="ISORM"
        )
        return ContourResult(
            method="ISORM",
            return_period=return_period,
            hs_values=hs_contour,
            tp_values=tp_contour,
        )

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def plot_contour(
        self,
        contour: ContourResult,
        data: pd.DataFrame | None = None,
    ) -> go.Figure:
        """
        Plotly Hs-Tp contour plot with optional data overlay.

        Parameters
        ----------
        contour:
            ContourResult to plot.
        data:
            Optional DataFrame with columns 'hs' and 'tp' for overlay scatter.

        Returns
        -------
        plotly.graph_objects.Figure
        """
        fig = go.Figure()

        # Optional data scatter underneath
        if data is not None and "hs" in data.columns and "tp" in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data["tp"].values,
                    y=data["hs"].values,
                    mode="markers",
                    name="Observations",
                    marker={"color": "lightgrey", "size": 3, "opacity": 0.5},
                )
            )

        # Contour line — close it by appending the first point
        hs = np.append(contour.hs_values, contour.hs_values[0])
        tp = np.append(contour.tp_values, contour.tp_values[0])

        fig.add_trace(
            go.Scatter(
                x=tp,
                y=hs,
                mode="lines",
                name=f"{contour.method} {contour.return_period}-yr",
                line={"color": "firebrick", "width": 2},
            )
        )

        fig.update_layout(
            title={
                "text": (
                    f"{contour.method} Environmental Contour "
                    f"({contour.return_period}-year return period)"
                )
            },
            xaxis={"title": "Tp (s)"},
            yaxis={"title": "Hs (m)"},
            template="plotly_white",
        )
        return fig

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def backend_contour(
        self, joint_model: JointModel, return_period: int
    ) -> ContourResult:
        """Return an exactly requested backend iso-density curve, without relabelling."""
        hs, tp = self._compute_contour(
            joint_model, return_period, "backend_iso_density"
        )
        return ContourResult("backend_iso_density", return_period, hs, tp)

    def _compute_contour(self, joint_model, return_period, method):
        if not np.isfinite(return_period) or return_period <= 0:
            raise ValueError("return period must be finite and positive")
        if method == "backend_iso_density":
            if joint_model._raw_result is None:
                raise ValueError("No backend contour is stored")
            raw = JointBackendResult.from_raw(joint_model._raw_result)
            if return_period not in raw.X:
                raise ValueError("Requested return period was not fitted")
            index = list(raw.X).index(return_period)
            hs = np.asarray(raw.h3[index], dtype=float)
            tp = np.asarray(raw.t3[index], dtype=float)
            if hs.ndim != 1 or hs.shape != tp.shape or not hs.size:
                raise ValueError("Invalid backend contour coordinate shapes")
            if not np.isfinite(hs).all() or not np.isfinite(tp).all():
                raise ValueError("Nonfinite backend contour coordinates")
            return hs, tp

        # Coastal Engineering 123 (2017), Eq. (7): annual sea-state conversion.
        alpha = self._state_duration / (return_period * 365.25 * 24)
        if not 0 < alpha < 1:
            raise ValueError(
                "Sea-state exceedance probability must be between zero and one"
            )
        # Normal-space radii and angular discretization: virocon 2.4.0,
        # contours.py, IFORMContour and ISORMContour (180 points by default).
        if method == "IFORM":
            if alpha >= 0.5:
                raise ValueError("IFORM requires exceedance probability below one half")
            radius = norm.isf(alpha)
        elif method == "ISORM":
            radius = np.sqrt(chi2.isf(alpha, df=2))
        else:
            raise ValueError("Unknown contour method")
        angle = np.linspace(0, 2 * np.pi, 180, endpoint=False)
        return self.inverse_transform(
            joint_model,
            norm.cdf(radius * np.cos(angle)),
            norm.cdf(radius * np.sin(angle)),
        )

    @staticmethod
    def inverse_transform(joint_model, hs_probability, tp_probability, *, weibull=None):
        """Invert the marginal and conditional CDFs without heuristic fallbacks.

        The backend's finite-grid marginal is integrated by trapezoids and
        normalized on its stored support. Tail extrapolation is not implied.
        An explicit (shape, location, scale) Weibull is accepted for independent
        analytic cases. No Weibull parameters are inferred from conditional
        coefficients. Coastal Engineering 123 (2017), Eqs. (2),(3),(6).
        """
        p = np.asarray(hs_probability, dtype=float)
        q = np.asarray(tp_probability, dtype=float)
        if p.shape != q.shape or not ((p > 0) & (p < 1) & (q > 0) & (q < 1)).all():
            raise ValueError(
                "Paired probabilities must be strictly between zero and one"
            )
        if weibull is not None:
            shape, location, scale = weibull
            if shape <= 0 or scale <= 0 or not np.isfinite(weibull).all():
                raise ValueError("Invalid Weibull parameters")
            hs = weibull_min.ppf(p, shape, loc=location, scale=scale)
        else:
            h = np.asarray(joint_model.marginal_hs["h"], dtype=float)
            pdf = np.asarray(joint_model.marginal_hs["pdf"], dtype=float)
            if (
                h.ndim != 1
                or h.size < 2
                or h.shape != pdf.shape
                or not np.isfinite(h).all()
                or not np.isfinite(pdf).all()
                or (np.diff(h) <= 0).any()
                or (pdf < 0).any()
            ):
                raise ValueError("Invalid marginal PDF grid")
            cdf = cumulative_trapezoid(pdf, h, initial=0)
            if cdf[-1] <= 0:
                raise ValueError("Marginal PDF grid has no probability mass")
            cdf /= cdf[-1]
            hs = np.interp(p, cdf, h)
        a1, a2, a3 = joint_model.conditional_tp["mu_coefficients"]
        b1, b2, b3 = joint_model.conditional_tp["variance_coefficients"]
        mu = a1 + a2 * hs**a3
        # Backend 1.2.0 extreme.py: b1+b2*exp(-b3*Hs) is VARIANCE.
        variance = b1 + b2 * np.exp(-b3 * hs)
        if (
            not np.isfinite(mu).all()
            or not np.isfinite(variance).all()
            or (variance <= 0).any()
        ):
            raise ValueError("Invalid conditional lognormal parameters")
        tp = np.exp(mu + np.sqrt(variance) * norm.ppf(q))
        if not np.isfinite(tp).all():
            raise ValueError("Nonfinite inverse-transform result")
        return hs, tp
