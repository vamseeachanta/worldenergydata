"""
Financial and economic views for well detail dashboard.

Contains economic metrics calculation, NPV, IRR, payback period,
and waterfall chart visualization.
"""

from typing import Any, Dict

import numpy as np
from scipy import optimize

from .views_utils import PLOTLY_AVAILABLE, logger

# Import plotly components if available
if PLOTLY_AVAILABLE:
    import plotly.graph_objects as go


class EconomicMetricsCalculator:
    """Calculates economic metrics for wells."""

    def calculate_revenue(
        self,
        oil_production: np.ndarray,
        oil_price: np.ndarray,
        gas_production: np.ndarray,
        gas_price: np.ndarray,
    ) -> np.ndarray:
        """Calculate total revenue from production."""
        oil_revenue = oil_production * oil_price
        gas_revenue = gas_production * gas_price / 1000  # Convert mcf to $
        return oil_revenue + gas_revenue

    def calculate_npv(
        self, cash_flows: np.ndarray, discount_rate: float = 0.1
    ) -> float:
        """Calculate Net Present Value."""
        periods = np.arange(len(cash_flows))
        discount_factors = (1 + discount_rate) ** periods
        return np.sum(cash_flows / discount_factors)

    def calculate_irr(self, cash_flows: np.ndarray) -> float:
        """Calculate Internal Rate of Return."""
        try:
            # Use numpy's IRR calculation
            irr = np.irr(cash_flows)
            return irr if not np.isnan(irr) else 0.0
        except Exception:
            # Fallback to manual calculation
            def npv_func(rate):
                return self.calculate_npv(cash_flows, rate)

            try:
                result = optimize.brentq(npv_func, -0.99, 10.0)
                return result
            except Exception:
                return 0.0

    def calculate_payback_period(self, cash_flows: np.ndarray) -> float:
        """Calculate payback period in periods."""
        cumulative = np.cumsum(cash_flows)
        positive_indices = np.where(cumulative > 0)[0]

        if len(positive_indices) == 0:
            return float(len(cash_flows))  # Never pays back

        payback_index = positive_indices[0]

        # Interpolate for fractional period
        if payback_index > 0:
            prev_cumulative = cumulative[payback_index - 1]
            current_flow = cash_flows[payback_index]
            fraction = -prev_cumulative / current_flow
            return float(payback_index - 1 + fraction)

        return float(payback_index)

    def create_waterfall_chart(
        self, revenue: float, opex: float, capex: float, taxes: float, well_name: str
    ) -> Dict[str, Any]:
        """Create economic waterfall chart."""
        if not PLOTLY_AVAILABLE:
            return {"type": "waterfall", "error": "Plotly not available"}

        fig = go.Figure()

        # Calculate net income
        net_income = revenue - opex - capex - taxes

        fig.add_trace(
            go.Waterfall(
                name="Economic Waterfall",
                orientation="v",
                measure=["absolute", "relative", "relative", "relative", "total"],
                x=["Revenue", "OPEX", "CAPEX", "Taxes", "Net Income"],
                y=[revenue, -opex, -capex, -taxes, net_income],
                text=[
                    f"${revenue:,.0f}",
                    f"-${opex:,.0f}",
                    f"-${capex:,.0f}",
                    f"-${taxes:,.0f}",
                    f"${net_income:,.0f}",
                ],
                textposition="outside",
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                increasing={"marker": {"color": "green"}},
                decreasing={"marker": {"color": "red"}},
                totals={"marker": {"color": "blue"}},
            )
        )

        fig.update_layout(
            title=f"{well_name} Economic Waterfall",
            yaxis_title="Value ($)",
            template="plotly_white",
            height=500,
            showlegend=False,
        )

        return {
            "type": "waterfall",
            "data": {
                "categories": ["Revenue", "OPEX", "CAPEX", "Taxes", "Net Income"],
                "values": [revenue, -opex, -capex, -taxes, net_income],
            },
            "figure": fig,
        }


# Export all public names
__all__ = ["EconomicMetricsCalculator"]
