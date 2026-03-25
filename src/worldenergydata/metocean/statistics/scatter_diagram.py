"""
ABOUTME: 2D Hs-Tp occurrence table (scatter diagram) with Plotly visualisation.
ABOUTME: Wraps metocean-stats calculate_scatter for the tabular backend.

Uses real metocean-stats library (v1.1.9).
All visualisations use Plotly.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import metocean_stats.stats as ms


class ScatterDiagram:
    """
    2D occurrence table for any two metocean variables.

    Wraps ``metocean_stats.stats.calculate_scatter`` for the bin-count
    backend, converting raw counts to percentage and providing Plotly
    visualisation.

    Examples
    --------
    >>> sd = ScatterDiagram()
    >>> df = sd.compute(data, var1="hs", var2="tp")
    >>> fig = sd.plot(df)
    """

    def __init__(
        self,
        default_step_var1: float = 0.5,
        default_step_var2: float = 1.0,
    ) -> None:
        self._step1 = default_step_var1
        self._step2 = default_step_var2

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------

    def compute(
        self,
        data: pd.DataFrame,
        var1: str = "hs",
        var2: str = "tp",
        step_var1: Optional[float] = None,
        step_var2: Optional[float] = None,
    ) -> pd.DataFrame:
        """
        Compute a 2D occurrence table in percent.

        Parameters
        ----------
        data:
            DataFrame containing columns ``var1`` and ``var2``.
        var1:
            Row variable name (e.g. 'hs').
        var2:
            Column variable name (e.g. 'tp').
        step_var1:
            Bin width for var1. Uses instance default if None.
        step_var2:
            Bin width for var2. Uses instance default if None.

        Returns
        -------
        pd.DataFrame
            Percentage occurrence table. Rows = var1 bins, columns = var2 bins.
            Values sum to 100.0 (within floating-point precision).
        """
        s1 = step_var1 if step_var1 is not None else self._step1
        s2 = step_var2 if step_var2 is not None else self._step2

        counts = ms.calculate_scatter(data, var1, s1, var2, s2)

        total = counts.values.sum()
        if total > 0:
            pct = (counts / total * 100.0).round(4)
        else:
            pct = counts.astype(float)

        return pct

    def plot(self, scatter_df: pd.DataFrame, title: str = "Scatter Diagram") -> go.Figure:
        """
        Plotly heatmap of a pre-computed scatter diagram.

        Parameters
        ----------
        scatter_df:
            Output of ``compute()``.
        title:
            Figure title.

        Returns
        -------
        plotly.graph_objects.Figure
        """
        z = scatter_df.values
        x_labels = [str(c) for c in scatter_df.columns]
        y_labels = [str(r) for r in scatter_df.index]

        # Build text annotations (show non-zero cells only)
        text = []
        for row in z:
            text.append([f"{v:.2f}%" if v > 0 else "" for v in row])

        fig = go.Figure(
            data=go.Heatmap(
                z=z,
                x=x_labels,
                y=y_labels,
                colorscale="Blues",
                text=text,
                texttemplate="%{text}",
                showscale=True,
                colorbar=dict(title="Occurrence (%)"),
                zmin=0,
            )
        )

        fig.update_layout(
            title=title,
            xaxis=dict(title="Tp (s)"),
            yaxis=dict(title="Hs (m)"),
            template="plotly_white",
        )
        return fig

    def plot_from_data(
        self,
        data: pd.DataFrame,
        var1: str = "hs",
        var2: str = "tp",
        step_var1: Optional[float] = None,
        step_var2: Optional[float] = None,
    ) -> go.Figure:
        """
        Compute and plot scatter diagram from raw data in one call.

        Parameters
        ----------
        data:
            DataFrame with columns var1 and var2.
        var1:
            Row variable name.
        var2:
            Column variable name.
        step_var1:
            Bin width for var1.
        step_var2:
            Bin width for var2.

        Returns
        -------
        plotly.graph_objects.Figure
        """
        scatter_df = self.compute(data, var1, var2, step_var1, step_var2)
        return self.plot(scatter_df, title=f"{var1.upper()}-{var2.upper()} Scatter Diagram")
