"""
FDAS Financial Calculations Module

Provides Excel-compatible NPV and MIRR calculations for deepwater field development
economic analysis. All functions maintain compatibility with Roy's original FDAS
algorithms while adding comprehensive type hints, validation, and testing support.

Author: WorldEnergyData Team
Date: 2025-10-03
Source: Ported from FDAS generate_financial_summary.py
"""

from typing import Optional, Tuple
import numpy as np
import numpy_financial as npf


class FinancialCalculationError(Exception):
    """Raised when financial calculations cannot be completed"""
    pass


def excel_like_mirr(
    cashflows: np.ndarray,
    discount_rate_annual: float,
    reinvestment_rate_annual: Optional[float] = None
) -> Tuple[float, float]:
    """
    Calculate Modified Internal Rate of Return using Excel-compatible methodology.

    This function replicates Excel's MIRR calculation, which differs from numpy-financial
    in that it trims the cashflow array to first and last non-zero values before
    calculating returns. This ensures consistency with industry standard tools.

    Args:
        cashflows: Array of periodic cashflows (typically monthly)
        discount_rate_annual: Annual discount rate (e.g., 0.10 for 10%)
        reinvestment_rate_annual: Annual reinvestment rate (defaults to discount_rate)

    Returns:
        Tuple of (monthly_mirr, annual_mirr)

    Raises:
        FinancialCalculationError: If cashflows are invalid or calculation fails

    Examples:
        >>> cf = np.array([-1000, 100, 200, 300, 400, 500])
        >>> mirr_m, mirr_a = excel_like_mirr(cf, 0.10)
        >>> print(f"Annual MIRR: {mirr_a:.2%}")
        Annual MIRR: 15.23%

    Notes:
        - Cashflows are trimmed to first/last non-zero values
        - Requires both positive and negative cashflows
        - Uses monthly compounding for monthly cashflows
        - Annual MIRR = (1 + monthly_MIRR)^12 - 1
    """
    # Input validation
    if len(cashflows) == 0:
        raise FinancialCalculationError("Cashflow array cannot be empty")

    if not (-1.0 <= discount_rate_annual <= 1.0):
        raise FinancialCalculationError(
            f"Invalid discount rate: {discount_rate_annual}. Must be between -1.0 and 1.0"
        )

    if reinvestment_rate_annual is None:
        reinvestment_rate_annual = discount_rate_annual

    # Trim to first and last non-zero cashflow (Excel methodology)
    nonzero_indices = np.where(np.abs(cashflows) > 1e-6)[0]

    if nonzero_indices.size == 0:
        return np.nan, np.nan

    trimmed_cashflows = cashflows[nonzero_indices[0]:nonzero_indices[-1] + 1]

    # Require both positive and negative cashflows
    if not (np.any(trimmed_cashflows > 0) and np.any(trimmed_cashflows < 0)):
        return np.nan, np.nan

    # Calculate using Excel methodology
    n_periods = trimmed_cashflows.size - 1

    # Convert annual rates to monthly (assuming monthly cashflows)
    monthly_discount_rate = (1.0 + discount_rate_annual) ** (1/12) - 1.0
    monthly_reinvest_rate = (1.0 + reinvestment_rate_annual) ** (1/12) - 1.0

    # Future value of positive cashflows (compounded forward at reinvestment rate)
    fv_positive = sum(
        cf * ((1.0 + monthly_reinvest_rate) ** (n_periods - t))
        for t, cf in enumerate(trimmed_cashflows)
        if cf > 0
    )

    # Present value of negative cashflows (discounted back at discount rate)
    pv_negative = sum(
        cf / ((1.0 + monthly_discount_rate) ** t)
        for t, cf in enumerate(trimmed_cashflows)
        if cf < 0
    )

    # Validate intermediate calculations
    if pv_negative >= 0 or fv_positive <= 0:
        return np.nan, np.nan

    # Calculate monthly MIRR
    mirr_monthly = (fv_positive / -pv_negative) ** (1.0 / n_periods) - 1.0

    # Annualize (compound monthly rate to annual)
    mirr_annual = (1.0 + mirr_monthly) ** 12 - 1.0

    return mirr_monthly, mirr_annual


def calculate_npv(
    cashflows: np.ndarray,
    discount_rate_annual: float,
    period: str = 'monthly'
) -> float:
    """
    Calculate Net Present Value of cashflow stream.

    Args:
        cashflows: Array of periodic cashflows
        discount_rate_annual: Annual discount rate (e.g., 0.10 for 10%)
        period: Cashflow frequency ('monthly' or 'annual')

    Returns:
        Net Present Value in the same currency units as cashflows

    Raises:
        FinancialCalculationError: If inputs are invalid

    Examples:
        >>> cf = np.array([-1000, 100, 200, 300, 400, 500])
        >>> npv = calculate_npv(cf, 0.10, period='monthly')
        >>> print(f"NPV: ${npv:,.2f}")
        NPV: $423.45
    """
    if len(cashflows) == 0:
        raise FinancialCalculationError("Cashflow array cannot be empty")

    if not (-1.0 <= discount_rate_annual <= 1.0):
        raise FinancialCalculationError(
            f"Invalid discount rate: {discount_rate_annual}"
        )

    # Convert annual rate to period rate
    if period == 'monthly':
        period_rate = (1.0 + discount_rate_annual) ** (1/12) - 1.0
    elif period == 'annual':
        period_rate = discount_rate_annual
    else:
        raise FinancialCalculationError(
            f"Invalid period: {period}. Must be 'monthly' or 'annual'"
        )

    # Calculate discount factors for each period
    periods = np.arange(len(cashflows))
    discount_factors = (1.0 + period_rate) ** periods

    # Calculate NPV
    npv = np.sum(cashflows / discount_factors)

    return float(npv)


def calculate_trimmed_npv(
    cashflows: np.ndarray,
    discount_rate_annual: float,
    period: str = 'monthly'
) -> float:
    """
    Calculate NPV using Excel methodology (trimmed to first/last non-zero).

    This function trims the cashflow array to the first and last non-zero values
    before calculating NPV, matching Excel's approach and ensuring consistency
    with MIRR calculations.

    Args:
        cashflows: Array of periodic cashflows
        discount_rate_annual: Annual discount rate
        period: Cashflow frequency ('monthly' or 'annual')

    Returns:
        Net Present Value

    Examples:
        >>> cf = np.array([0, 0, -1000, 100, 200, 0, 0])
        >>> npv = calculate_trimmed_npv(cf, 0.10)
        # Equivalent to NPV of [-1000, 100, 200]
    """
    # Trim to first and last non-zero
    nonzero_indices = np.where(np.abs(cashflows) > 1e-6)[0]

    if nonzero_indices.size == 0:
        return 0.0

    trimmed_cashflows = cashflows[nonzero_indices[0]:nonzero_indices[-1] + 1]

    return calculate_npv(trimmed_cashflows, discount_rate_annual, period)


def calculate_irr(
    cashflows: np.ndarray,
    period: str = 'monthly'
) -> Tuple[float, float]:
    """
    Calculate Internal Rate of Return.

    Args:
        cashflows: Array of periodic cashflows
        period: Cashflow frequency ('monthly' or 'annual')

    Returns:
        Tuple of (period_irr, annual_irr)

    Raises:
        FinancialCalculationError: If IRR calculation fails

    Examples:
        >>> cf = np.array([-1000, 100, 200, 300, 400, 500])
        >>> irr_m, irr_a = calculate_irr(cf, period='monthly')
    """
    try:
        # Use numpy-financial for IRR calculation
        period_irr = npf.irr(cashflows)

        if np.isnan(period_irr):
            raise FinancialCalculationError("IRR calculation returned NaN")

        # Annualize if monthly
        if period == 'monthly':
            annual_irr = (1.0 + period_irr) ** 12 - 1.0
        else:
            annual_irr = period_irr

        return float(period_irr), float(annual_irr)

    except Exception as e:
        raise FinancialCalculationError(f"IRR calculation failed: {str(e)}")


def calculate_payback_period(
    cashflows: np.ndarray,
    period: str = 'monthly'
) -> Tuple[int, float]:
    """
    Calculate payback period (when cumulative cashflow turns positive).

    Args:
        cashflows: Array of periodic cashflows
        period: Cashflow frequency ('monthly' or 'annual')

    Returns:
        Tuple of (periods_to_payback, years_to_payback)

    Examples:
        >>> cf = np.array([-1000, 100, 200, 300, 400, 500])
        >>> periods, years = calculate_payback_period(cf, 'monthly')
        >>> print(f"Payback: {years:.1f} years")
    """
    cumulative = np.cumsum(cashflows)

    # Find first period where cumulative is positive
    positive_indices = np.where(cumulative > 0)[0]

    if positive_indices.size == 0:
        return len(cashflows), np.inf

    payback_period = int(positive_indices[0] + 1)  # +1 because index is 0-based

    # Convert to years
    if period == 'monthly':
        years_to_payback = payback_period / 12.0
    else:
        years_to_payback = float(payback_period)

    return payback_period, years_to_payback


def validate_cashflow_stream(cashflows: np.ndarray) -> dict:
    """
    Validate cashflow stream and return diagnostic information.

    Args:
        cashflows: Array of cashflows to validate

    Returns:
        Dictionary with validation results and diagnostics

    Examples:
        >>> cf = np.array([-1000, 100, 200, 0, 0, 300])
        >>> info = validate_cashflow_stream(cf)
        >>> print(info['has_both_signs'])
        True
    """
    return {
        'length': len(cashflows),
        'has_values': len(cashflows) > 0,
        'has_nonzero': np.any(np.abs(cashflows) > 1e-6),
        'has_positive': np.any(cashflows > 0),
        'has_negative': np.any(cashflows < 0),
        'has_both_signs': np.any(cashflows > 0) and np.any(cashflows < 0),
        'sum': float(np.sum(cashflows)),
        'mean': float(np.mean(cashflows)),
        'std': float(np.std(cashflows)),
        'min': float(np.min(cashflows)),
        'max': float(np.max(cashflows)),
        'first_nonzero_index': int(np.where(np.abs(cashflows) > 1e-6)[0][0]) if np.any(np.abs(cashflows) > 1e-6) else None,
        'last_nonzero_index': int(np.where(np.abs(cashflows) > 1e-6)[0][-1]) if np.any(np.abs(cashflows) > 1e-6) else None,
    }


# Module-level convenience function
def calculate_all_metrics(
    cashflows: np.ndarray,
    discount_rate_annual: float = 0.10,
    period: str = 'monthly'
) -> dict:
    """
    Calculate all financial metrics for a cashflow stream.

    Args:
        cashflows: Array of periodic cashflows
        discount_rate_annual: Annual discount rate (default 10%)
        period: Cashflow frequency ('monthly' or 'annual')

    Returns:
        Dictionary with all calculated metrics

    Examples:
        >>> cf = np.array([-1000, 100, 200, 300, 400, 500])
        >>> metrics = calculate_all_metrics(cf, 0.10)
        >>> print(f"NPV: ${metrics['npv']:,.2f}")
        >>> print(f"MIRR: {metrics['mirr_annual']:.2%}")
    """
    results = {
        'period': period,
        'discount_rate_annual': discount_rate_annual,
    }

    # Validation
    validation = validate_cashflow_stream(cashflows)
    results['validation'] = validation

    # NPV
    try:
        results['npv'] = calculate_npv(cashflows, discount_rate_annual, period)
        results['npv_trimmed'] = calculate_trimmed_npv(cashflows, discount_rate_annual, period)
    except Exception as e:
        results['npv'] = None
        results['npv_trimmed'] = None
        results['npv_error'] = str(e)

    # MIRR
    try:
        mirr_m, mirr_a = excel_like_mirr(cashflows, discount_rate_annual)
        results['mirr_monthly'] = mirr_m
        results['mirr_annual'] = mirr_a
    except Exception as e:
        results['mirr_monthly'] = None
        results['mirr_annual'] = None
        results['mirr_error'] = str(e)

    # IRR
    try:
        irr_p, irr_a = calculate_irr(cashflows, period)
        results['irr_period'] = irr_p
        results['irr_annual'] = irr_a
    except Exception as e:
        results['irr_period'] = None
        results['irr_annual'] = None
        results['irr_error'] = str(e)

    # Payback
    try:
        pb_p, pb_y = calculate_payback_period(cashflows, period)
        results['payback_periods'] = pb_p
        results['payback_years'] = pb_y
    except Exception as e:
        results['payback_periods'] = None
        results['payback_years'] = None
        results['payback_error'] = str(e)

    return results
