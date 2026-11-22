"""Authoritative equally spaced cash-flow discounting equations.

Source: NumPy Financial 1.0.0 (2019), ``npv``, Notes and Warnings:
https://raw.githubusercontent.com/numpy/numpy-financial/v1.0.0/numpy_financial/_financial.py
The first cash flow occurs at time zero; the rate must match the cash-flow
interval. Frequency conversion, trimming and validation belong to adapters.
"""

import numpy as np


def discounted_cash_flows(cash_flows, discount_rate: float) -> np.ndarray:
    """Return CF[t] / (1 + rate)**t for a one-dimensional periodic stream.

    The unit factor and zero-based exponent follow the cited NPV definition.
    """
    values = np.asarray(cash_flows, dtype=float)
    periods = np.arange(len(values))
    return values / (1.0 + discount_rate) ** periods


def net_present_value(cash_flows, discount_rate: float) -> float:
    """Sum discounted cash flows, including the undiscounted initial flow."""
    return float(np.sum(discounted_cash_flows(cash_flows, discount_rate)))
