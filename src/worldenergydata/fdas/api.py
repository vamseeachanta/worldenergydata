# ABOUTME: FDAS data query API — thin wrappers over existing financial calculators.
# ABOUTME: Provides EconomicsQuery for NPV, IRR, MIRR, payback calculations.

"""FDAS economics query API.

Thin wrappers over existing FDAS financial calculation functions that provide
a clean, discoverable interface for programmatic consumers.

Usage::

    import worldenergydata as wed

    # Calculate NPV
    npv = wed.fdas.economics.npv(
        cashflows=[-1000, 100, 200, 300, 400, 500],
        discount_rate=0.10,
    )

    # Calculate IRR
    period_irr, annual_irr = wed.fdas.economics.irr(
        cashflows=[-1000, 100, 200, 300, 400, 500],
    )

    # All metrics at once
    metrics = wed.fdas.economics.all_metrics(
        cashflows=[-1000, 100, 200, 300],
        discount_rate=0.10,
    )
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np


class EconomicsQuery:
    """Financial economics calculations for field development analysis.

    Wraps :mod:`worldenergydata.fdas.core.financial` functions with a
    simpler interface that accepts plain Python lists as well as numpy arrays.

    Examples
    --------
    >>> from worldenergydata.fdas.api import EconomicsQuery
    >>> econ = EconomicsQuery()
    >>> npv = econ.npv([-1000, 100, 200, 300, 400, 500], discount_rate=0.10)
    >>> irr_p, irr_a = econ.irr([-1000, 100, 200, 300, 400, 500])
    """

    @staticmethod
    def npv(
        cashflows: Union[Sequence[float], np.ndarray],
        discount_rate: float,
        *,
        period: str = "monthly",
        trimmed: bool = False,
    ) -> float:
        """Calculate Net Present Value of a cashflow stream.

        Parameters
        ----------
        cashflows : list or np.ndarray
            Periodic cashflows (negative = outflows, positive = inflows).
        discount_rate : float
            Annual discount rate (e.g. ``0.10`` for 10%).
        period : str, default ``"monthly"``
            Cashflow frequency: ``"monthly"`` or ``"annual"``.
        trimmed : bool, default False
            If True, use Excel-style trimming (first/last non-zero values).

        Returns
        -------
        float
            Net Present Value in the same currency units as cashflows.

        Raises
        ------
        FinancialCalculationError
            If inputs are invalid (empty array, bad discount rate).

        Examples
        --------
        >>> EconomicsQuery.npv([-1000, 100, 200, 300, 400, 500], 0.10)
        423.45  # approximate
        >>> EconomicsQuery.npv([-1000, 100, 200, 300], 0.10, period="annual")
        -481.57  # approximate
        """
        from worldenergydata.fdas.core.financial import (
            calculate_npv,
            calculate_trimmed_npv,
        )

        cf = np.asarray(cashflows, dtype=float)
        if trimmed:
            return calculate_trimmed_npv(cf, discount_rate, period=period)
        return calculate_npv(cf, discount_rate, period=period)

    @staticmethod
    def irr(
        cashflows: Union[Sequence[float], np.ndarray],
        *,
        period: str = "monthly",
    ) -> Tuple[float, float]:
        """Calculate Internal Rate of Return.

        Parameters
        ----------
        cashflows : list or np.ndarray
            Periodic cashflows (must contain both positive and negative values).
        period : str, default ``"monthly"``
            Cashflow frequency: ``"monthly"`` or ``"annual"``.

        Returns
        -------
        tuple of (float, float)
            ``(period_irr, annual_irr)``.

        Raises
        ------
        FinancialCalculationError
            If IRR calculation fails or returns NaN.

        Examples
        --------
        >>> period_irr, annual_irr = EconomicsQuery.irr(
        ...     [-1000, 100, 200, 300, 400, 500]
        ... )
        """
        from worldenergydata.fdas.core.financial import calculate_irr

        cf = np.asarray(cashflows, dtype=float)
        return calculate_irr(cf, period=period)

    @staticmethod
    def mirr(
        cashflows: Union[Sequence[float], np.ndarray],
        discount_rate: float,
        *,
        reinvestment_rate: Optional[float] = None,
    ) -> Tuple[float, float]:
        """Calculate Modified Internal Rate of Return (Excel-compatible).

        Parameters
        ----------
        cashflows : list or np.ndarray
            Periodic cashflows.
        discount_rate : float
            Annual discount rate.
        reinvestment_rate : float, optional
            Annual reinvestment rate. Defaults to ``discount_rate``.

        Returns
        -------
        tuple of (float, float)
            ``(monthly_mirr, annual_mirr)``.

        Examples
        --------
        >>> mirr_m, mirr_a = EconomicsQuery.mirr(
        ...     [-1000, 100, 200, 300, 400, 500], 0.10
        ... )
        >>> print(f"Annual MIRR: {mirr_a:.2%}")
        """
        from worldenergydata.fdas.core.financial import excel_like_mirr

        cf = np.asarray(cashflows, dtype=float)
        return excel_like_mirr(cf, discount_rate, reinvestment_rate)

    @staticmethod
    def payback_period(
        cashflows: Union[Sequence[float], np.ndarray],
        *,
        period: str = "monthly",
    ) -> Tuple[int, float]:
        """Calculate payback period (when cumulative cashflow turns positive).

        Parameters
        ----------
        cashflows : list or np.ndarray
            Periodic cashflows.
        period : str, default ``"monthly"``
            Cashflow frequency: ``"monthly"`` or ``"annual"``.

        Returns
        -------
        tuple of (int, float)
            ``(periods_to_payback, years_to_payback)``.

        Examples
        --------
        >>> periods, years = EconomicsQuery.payback_period(
        ...     [-1000, 100, 200, 300, 400, 500]
        ... )
        >>> print(f"Payback: {years:.1f} years")
        """
        from worldenergydata.fdas.core.financial import calculate_payback_period

        cf = np.asarray(cashflows, dtype=float)
        return calculate_payback_period(cf, period=period)

    @staticmethod
    def all_metrics(
        cashflows: Union[Sequence[float], np.ndarray],
        discount_rate: float = 0.10,
        *,
        period: str = "monthly",
    ) -> Dict[str, Any]:
        """Calculate all financial metrics for a cashflow stream.

        Convenience method that computes NPV, MIRR, IRR, and payback period
        in a single call.

        Parameters
        ----------
        cashflows : list or np.ndarray
            Periodic cashflows.
        discount_rate : float, default 0.10
            Annual discount rate.
        period : str, default ``"monthly"``
            Cashflow frequency.

        Returns
        -------
        dict
            Keys include ``npv``, ``mirr_annual``, ``irr_annual``,
            ``payback_years``, and more. See
            :func:`~worldenergydata.fdas.core.financial.calculate_all_metrics`.

        Examples
        --------
        >>> metrics = EconomicsQuery.all_metrics(
        ...     [-1000, 100, 200, 300, 400, 500], 0.10
        ... )
        >>> print(f"NPV: ${metrics['npv']:,.2f}")
        >>> print(f"MIRR: {metrics['mirr_annual']:.2%}")
        """
        from worldenergydata.fdas.core.financial import calculate_all_metrics

        cf = np.asarray(cashflows, dtype=float)
        return calculate_all_metrics(cf, discount_rate, period=period)

    @staticmethod
    def validate_cashflows(
        cashflows: Union[Sequence[float], np.ndarray],
    ) -> Dict[str, Any]:
        """Validate a cashflow stream and return diagnostic information.

        Parameters
        ----------
        cashflows : list or np.ndarray
            Cashflows to validate.

        Returns
        -------
        dict
            Diagnostic info including ``has_both_signs``, ``sum``,
            ``first_nonzero_index``, etc.

        Examples
        --------
        >>> info = EconomicsQuery.validate_cashflows([-1000, 100, 200])
        >>> print(info['has_both_signs'])
        True
        """
        from worldenergydata.fdas.core.financial import validate_cashflow_stream

        cf = np.asarray(cashflows, dtype=float)
        return validate_cashflow_stream(cf)


# Module-level singleton instance for convenience attribute access
economics = EconomicsQuery()
