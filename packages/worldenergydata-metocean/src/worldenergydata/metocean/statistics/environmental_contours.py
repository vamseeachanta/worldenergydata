"""
ABOUTME: Native LoNoWe density contours with explicit method restrictions.
ABOUTME: Derives contours from the JointModel fitted by JointProbabilityModel.

Reliability contours are NOT_EVALUATED: the backend provides density curves.
All visualisations use Plotly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from worldenergydata.metocean.statistics.joint_probability import JointModel


@dataclass
class ContourResult:
    """Container for an environmental contour result."""

    method: str
    """Contour construction method ('LoNoWe' for native density curves)."""
    return_period: int
    """Return period in years."""
    hs_values: np.ndarray
    """Hs coordinates of the contour."""
    tp_values: np.ndarray
    """Tp coordinates of the contour."""


class EnvironmentalContour:
    """Read native LoNoWe constant-density curves without relabelling them.

    Source: metocean-stats v.1.2.0 aux_funcs.py L121-L175. These curves
    are not inverse reliability transforms. IFORM and ISORM are rejected.
    """

    def __init__(self, state_duration_hours: float | None = None) -> None:
        """Use the fitted duration, or require an exact match if supplied."""
        if state_duration_hours is not None and (
            not np.isfinite(state_duration_hours) or state_duration_hours <= 0
        ):
            raise ValueError("Sea-state duration must be finite and positive")
        self._state_duration = state_duration_hours

    def lonowe(self, joint_model: JointModel, return_period: int = 50) -> ContourResult:
        """Return a fitted constant-density contour in Hs (m), Tp (s)."""
        hs, tp = self._compute_contour(joint_model, return_period, method="LoNoWe")
        return ContourResult("LoNoWe", return_period, hs, tp)

    def iform(self, joint_model: JointModel, return_period: int = 50) -> NoReturn:
        """Raise: an IFORM transform is not available for this tabulated fit."""
        self._unsupported_method("IFORM")

    def isorm(self, joint_model: JointModel, return_period: int = 50) -> NoReturn:
        """Raise: an ISORM transform is not available for this tabulated fit."""
        self._unsupported_method("ISORM")

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

    def _compute_contour(
        self,
        joint_model: JointModel,
        return_period: int,
        method: str,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Read only the requested method, duration and exact fitted period."""
        if method != "LoNoWe":
            self._unsupported_method(method)
        if joint_model._raw_result is None:
            raise NotImplementedError("NOT_EVALUATED: no fitted LoNoWe contour data")
        if self._state_duration is not None and (
            self._state_duration != joint_model.state_duration_hours
        ):
            raise ValueError("Requested duration differs from fitted sea-state duration")
        periods = tuple(joint_model.fitted_periods)
        if return_period not in periods:
            raise ValueError(f"Choose one of the fitted return periods: {periods}")
        idx = periods.index(return_period)
        # extreme.py L756-L766, aux_funcs.py L165-L175 (v.1.2.0): t3, h3.
        raw = joint_model._raw_result
        hs = np.asarray(raw[9][idx], dtype=float)
        tp = np.asarray(raw[8][idx], dtype=float)
        if hs.ndim != 1 or hs.shape != tp.shape or not hs.size:
            raise ValueError("Invalid upstream LoNoWe contour coordinate shape")
        if not (np.isfinite(hs).all() and np.isfinite(tp).all()):
            raise ValueError("Non-finite upstream LoNoWe contour coordinates")
        return hs, tp

    @staticmethod
    def _unsupported_method(method: str) -> NoReturn:
        raise NotImplementedError(
            f"NOT_EVALUATED: {method} requires a reliability transform; "
            "the upstream LoNoWe curves are constant-density contours"
        )
